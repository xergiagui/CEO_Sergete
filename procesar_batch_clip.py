#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch — reels 9:16 a partir de clips YA cortados (carpeta externa).

Recorre subcarpetas de una raíz (por defecto C:/Users/ico858/Desktop/Clip),
trata cada subcarpeta como un "vídeo" (slug = nombre de la carpeta) y por cada
.mp4 hace el FLUJO COMPLETO de reel:
  1) reencuadre 9:16 vertical (1080x1920) siguiendo al hablante (bust-crop
     adaptativo anti-piernas, clips.cortar_vertical)
  2) quita silencios (auto-editor, clips.quitar_silencios)
  3) edición final Fase C: b-roll local + música local + de-click + subtítulos
     palabra a palabra (pipeline_core.burn_subs_and_music). SIN gancho.

Además guarda en Supabase (viral_phrases) la transcripción verbatim de cada clip
como frase viral (best-effort, dedup por hash).

Eficiencia: transcribe cada clip UNA sola vez (sobre el 9:16 ya desilenciado) y
reutiliza esos word-timestamps para subtítulos + b-roll (words= a burn_subs).

Resumible/idempotente: si ya existe finales/<name>.mp4 Y es vertical (h>w), salta
el clip. Los finales antiguos en 16:9 se REPROCESAN automáticamente.

Uso:
    python procesar_batch_clip.py                       # todas las carpetas
    python procesar_batch_clip.py "C:/ruta/a/Clip"      # otra raíz
    python procesar_batch_clip.py "C:/ruta/a/Clip" "Largo 1 Extractos"  # una sola
"""
import sys
import shutil
import json
import subprocess
import traceback
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / ".claude" / "skills" / "Editor_Sergio"))
import pipeline_core as pc  # noqa: E402
from editar_clips import resolver_env_supabase  # noqa: E402
import clips as C  # noqa: E402  (reencuadre 9:16 + quitar silencios)

MUSIC = RAIZ / "musicas"
OVERLAYS = RAIZ / "superposiciones"
WORKROOT = RAIZ / "whisper" / "_edit_batch"

CLIP_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:/Users/ico858/Desktop/Clip")
SOLO_CARPETA = sys.argv[2] if len(sys.argv) > 2 else None
# Lado del plano donde está el protagonista (Luis Monge). "right" | "left" | "auto".
LADO = (sys.argv[3] if len(sys.argv) > 3 else "right").lower()


def reencuadre_persona(mp4: Path, sw: int, sh: int, dur: float, dest: Path, lado: str = "right"):
    """Recorte 9:16 FIJO bloqueado en una persona de un plano-a-dos (cámara fija).

    Muestrea frames, detecta caras (frontal + perfil) y se queda con las del lado
    indicado (mitad derecha/izquierda). Toma la mediana de x de esas caras y hace
    un recorte 9:16 de altura completa centrado ahí -> estable, sin saltar al otro
    interlocutor. Si no detecta suficientes caras, cae a un centro fijo del lado.
    Escala a 1080x1920.
    """
    import cv2, glob, tempfile, statistics, os, subprocess
    crop_w = int(((sh * 9 / 16) // 2) * 2)  # ancho del recorte 9:16 (par)

    # Modo CENTRO FIJO: `lado` numérico (p.ej. "0.81") -> fracción del ancho.
    # Para planos MUY abiertos donde la detección de cara falla y el protagonista
    # está en un extremo. Determinista, sin muestreo.
    try:
        frac = float(lado)
        cx = sw * frac
        x = int(round(cx - crop_w / 2.0)); x = max(0, min(x, sw - crop_w)); x -= x % 2
        print(f"   [encuadre] CENTRO FIJO {frac:.2f}: crop {crop_w}x{sh}@{x}", flush=True)
        vf = f"crop={crop_w}:{sh}:{x}:0,scale=1080:1920,setsar=1"
        C.run([C.FFMPEG, "-y", "-i", str(mp4), "-vf", vf,
               "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", str(dest)])
        return
    except ValueError:
        pass

    # centro por defecto según el lado (fallback si falla la detección)
    centro_def = sw * 0.68 if lado == "right" else (sw * 0.32 if lado == "left" else sw * 0.5)

    cx_list = []
    d = tempfile.mkdtemp(prefix="lock_")
    try:
        n = int(max(round(dur * 4), 12))  # ~4 fps de muestreo
        subprocess.run(
            [C.FFMPEG, "-y", "-ss", "0", "-i", str(mp4), "-t", f"{dur}",
             "-vf", f"fps={n}/{dur:.3f},scale=960:-2", "-q:v", "4",
             os.path.join(d, "f_%04d.jpg")],
            capture_output=True, text=True, errors="replace")
        casc = [cv2.data.haarcascades + c for c in
                ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
        dets = [cv2.CascadeClassifier(c) for c in casc]
        for p in sorted(glob.glob(os.path.join(d, "*.jpg"))):
            fr = cv2.imread(p)
            if fr is None:
                continue
            H, W = fr.shape[:2]
            sx = sw / W
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            caras = []
            for det in dets:
                for (x, y, w, h) in det.detectMultiScale(gray, 1.15, 5, minSize=(40, 40)):
                    caras.append((x + w / 2.0, w * h))
            # también perfil mirando al otro lado -> flip horizontal
            grayf = cv2.flip(gray, 1)
            for (x, y, w, h) in dets[1].detectMultiScale(grayf, 1.15, 5, minSize=(40, 40)):
                caras.append((W - (x + w / 2.0), w * h))
            if not caras:
                continue
            # nos quedamos con caras del lado pedido
            lado_caras = [cx for (cx, area) in caras
                          if (lado == "right" and cx > W * 0.5)
                          or (lado == "left" and cx < W * 0.5)
                          or (lado == "auto")]
            if not lado_caras:
                continue
            # la cara más a ese lado (más representativa del protagonista)
            cx = (max(lado_caras) if lado == "right" else
                  min(lado_caras) if lado == "left" else
                  statistics.median(lado_caras))
            cx_list.append(cx * sx)  # a px del fuente
    finally:
        shutil.rmtree(d, ignore_errors=True)

    cx = statistics.median(cx_list) if len(cx_list) >= 5 else centro_def
    x = int(round(cx - crop_w / 2.0))
    x = max(0, min(x, sw - crop_w)); x -= x % 2
    print(f"   [encuadre] LOCK {lado}: centro x={cx:.0f}px, crop {crop_w}x{sh}@{x}  "
          f"({len(cx_list)} muestras)", flush=True)
    vf = f"crop={crop_w}:{sh}:{x}:0,scale=1080:1920,setsar=1"
    C.run([C.FFMPEG, "-y", "-i", str(mp4), "-vf", vf,
           "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", str(dest)])


def reencuadre_izq_por_plano(mp4: Path, sw: int, sh: int, dur: float, dest: Path,
                             frac_fallback: float = 0.28, sel: str = "left"):
    """Recorte 9:16 POR PLANO con seguimiento horizontal a ALTURA COMPLETA.

    Segmenta por cortes de cámara y sub-divide en ventanas cortas para seguir al
    sujeto. Selección de cara por ventana según `sel`:
      - "left":   la cara MÁS a la izquierda (Luis en un multicam donde se sienta
                  a la izquierda del plano general).
      - "center": la cara DOMINANTE (mayor área) -> centra a quien protagoniza cada
                  plano (sirve para varias personas; p. ej. entrevistado y entrevistador).
    Recorte de ALTURA COMPLETA (no zoom) -> nunca corta la cara ni muestra solo
    regazo/piernas. Concatena los planos. Escala a 1080x1920.
    """
    import cv2, glob, tempfile, os, statistics, subprocess
    crop_w = int(((sh * 9 / 16) // 2) * 2)  # ancho recorte 9:16 (par)
    # UN SOLO recorte por PLANO (corte de cámara). NADA de sub-ventanas: así el
    # encuadre queda FIJO dentro de cada plano (sin micro-reajustes molestos). Si
    # el sujeto mueve la cabeza dentro del plano, se descentra un poco y no pasa
    # nada: lo importante es que el plano esté centrado en él y estable.
    cortes = C.detectar_cortes_escena(mp4, 0, dur)
    bordes = [0.0] + list(cortes) + [float(dur)]
    ventanas = [(bordes[i], bordes[i + 1]) for i in range(len(bordes) - 1)
                if bordes[i + 1] - bordes[i] > 0.3]
    if not ventanas:
        ventanas = [(0.0, float(dur))]
    casc = [cv2.CascadeClassifier(cv2.data.haarcascades + c) for c in
            ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]

    def cara_ventana(a, b):
        """(cx, top, fh) en px del fuente de la cara elegida (`sel`), o None.

        sel="left"/"right": la cara más a la izquierda/derecha (plano general a varios).
        sel="center": la cara DOMINANTE (mayor área).
        sel="auto"/"auto-right": PRIMER PLANO -> dominante; PLANO GENERAL con varias
                      caras -> la que HABLA (más movimiento de boca); si empate,
                      izquierda (auto) o derecha (auto-right).
        Descarta falsos positivos por tono de piel. Devuelve None si no hay cara.
        """
        durp = max(b - a, 0.15)
        n = int(min(max(round(durp * 4), 6), 30))  # 6..30 frames repartidos por el plano
        d = tempfile.mkdtemp(prefix="izq_")
        frames_faces = []  # por frame: lista de (cx, y, h, area, mouthrel) px fuente
        try:
            subprocess.run(
                [C.FFMPEG, "-y", "-ss", f"{a}", "-i", str(mp4), "-t", f"{durp}",
                 "-vf", f"fps={n}/{durp:.3f},scale=960:-2", "-q:v", "4",
                 os.path.join(d, "f_%04d.jpg")],
                capture_output=True, text=True, errors="replace")
            for p in sorted(glob.glob(os.path.join(d, "*.jpg"))):
                fr = cv2.imread(p)
                if fr is None:
                    continue
                H, W = fr.shape[:2]
                sx, sy = sw / W, sh / H
                gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
                ycc = cv2.cvtColor(fr, cv2.COLOR_BGR2YCrCb)
                skin = cv2.inRange(ycc, (0, 133, 77), (255, 173, 127))

                def es_piel(x, y, w, h):
                    x0, y0 = max(0, x), max(0, y)
                    x1, y1 = min(W, x + w), min(H, y + h)
                    if x1 <= x0 or y1 <= y0:
                        return False
                    return (skin[y0:y1, x0:x1].mean() / 255.0) > 0.20

                def rec(x, y, w, h):
                    # (cx, y, h, area, mouthrel) en px fuente. mouthrel = brillo de la
                    # zona de la boca menos el de la cara (aísla el movimiento de boca
                    # del temblor de cámara).
                    my0, my1 = int(y + 0.55 * h), int(y + 0.92 * h)
                    mx0, mx1 = int(x + 0.25 * w), int(x + 0.75 * w)
                    fx0, fy0 = max(0, x), max(0, y)
                    fx1, fy1 = min(W, x + w), min(H, y + h)
                    try:
                        mm = float(gray[max(0, my0):min(H, my1), max(0, mx0):min(W, mx1)].mean())
                        fm = float(gray[fy0:fy1, fx0:fx1].mean())
                        rel = mm - fm
                    except Exception:
                        rel = 0.0
                    return (x + w / 2.0) * sx, y * sy, h * sy, w * h, rel

                faces = []
                for det in casc:
                    for (x, y, w, h) in det.detectMultiScale(gray, 1.15, 6, minSize=(45, 45)):
                        if es_piel(x, y, w, h):
                            faces.append(rec(x, y, w, h))
                grayf = cv2.flip(gray, 1)
                for (x, y, w, h) in casc[1].detectMultiScale(grayf, 1.15, 6, minSize=(45, 45)):
                    xr = W - (x + w)
                    if es_piel(xr, y, w, h):
                        faces.append(rec(xr, y, w, h))
                frames_faces.append(faces)
        finally:
            shutil.rmtree(d, ignore_errors=True)

        allf = [f for ff in frames_faces for f in ff]
        if len(allf) < 2:
            return None

        # Clustering por cx -> "tracks" (una persona). Caras separadas => personas
        # distintas; el jitter de una persona queda en el mismo cluster.
        gap = 0.12 * sw
        allf.sort(key=lambda f: f[0])
        clusters = []
        for f in allf:
            if clusters and f[0] - clusters[-1]["last"] <= gap:
                c = clusters[-1]
            else:
                c = {"cx": [], "y": [], "h": [], "area": [], "rel": [], "last": f[0]}
                clusters.append(c)
            c["cx"].append(f[0]); c["y"].append(f[1]); c["h"].append(f[2])
            c["area"].append(f[3]); c["rel"].append(f[4]); c["last"] = f[0]

        def med(c, k):
            return statistics.median(c[k])

        def talk(c):
            return statistics.pvariance(c["rel"]) if len(c["rel"]) >= 3 else 0.0

        # ¿primer plano? cara dominante ocupa buena parte de la altura
        big_h = statistics.median([max(ff, key=lambda f: f[3])[2]
                                   for ff in frames_faces if ff])
        cerca = big_h > 0.30 * sh

        # NOTA: la detección del hablante por movimiento de boca resultó poco fiable
        # (elegía al que escucha), así que NO se usa por defecto. `auto` = plano
        # general a la IZQUIERDA (estable/predecible); `auto-right` a la derecha.
        if sel == "center" or (sel in ("auto", "auto-right") and cerca):
            elegido = max(clusters, key=lambda c: med(c, "area"))      # dominante (primer plano)
        elif sel in ("auto-right", "right"):
            elegido = max(clusters, key=lambda c: med(c, "cx"))        # derecha (plano general)
        else:  # auto / left
            elegido = min(clusters, key=lambda c: med(c, "cx"))        # izquierda (plano general)
        return med(elegido, "cx"), med(elegido, "y"), med(elegido, "h")

    tmp = tempfile.mkdtemp(prefix="izqseg_")
    partes = []
    try:
        if sel == "center":
            cx_def = sw * 0.5
        elif sel in ("right", "auto-right"):
            cx_def = sw * (1.0 - frac_fallback)   # fallback lado derecho
        else:
            cx_def = sw * frac_fallback           # fallback lado izquierdo
        for i, (a, b) in enumerate(ventanas):
            f = cara_ventana(a, b)
            cx = f[0] if f is not None else cx_def
            # ALTURA COMPLETA con seguimiento horizontal: estable (nunca zoom a la
            # nuca ni recorte de regazo); la cara queda dentro del encuadre.
            x = int(round(cx - crop_w / 2.0)); x = max(0, min(x, sw - crop_w)); x -= x % 2
            rect = (crop_w, sh, x, 0)
            info = f"{sel} cx={cx:.0f}" + ("" if f is not None else " (fallback)")
            parte = os.path.join(tmp, f"seg_{i:03d}.mp4")
            C._encode_tramo(mp4, a, b - a, rect, parte)
            partes.append(parte)
            print(f"   [encuadre] IZQ {a:.1f}-{b:.1f}s -> {info} rect={rect}", flush=True)
        if len(partes) == 1:
            shutil.move(partes[0], str(dest))
        else:
            lista = os.path.join(tmp, "list.txt")
            with open(lista, "w", encoding="utf-8") as f:
                for p in partes:
                    f.write(f"file '{p}'\n")
            C.run([C.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lista,
                   "-c", "copy", "-movflags", "+faststart", str(dest)])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cargar_env() -> dict:
    env = {}
    try:
        if pc.ENV_PATH.exists():
            env = json.loads(pc.ENV_PATH.read_text(encoding="utf-8"))
    except Exception:
        env = {}
    sup = resolver_env_supabase()
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        if sup.get(k) and not env.get(k):
            env[k] = sup[k]
    env.update({"MUSIC_DIR": str(MUSIC), "OVERLAYS_DIR": str(OVERLAYS)})
    return env


def dims(mp4: Path):
    """(w, h) del vídeo vía ffprobe; (0,0) si falla."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(mp4)],
            capture_output=True, text=True)
        w, h = r.stdout.strip().split("x")
        return int(w), int(h)
    except Exception:
        return 0, 0


def duracion(mp4: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp4)], capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def transcribir_words_y_texto(mp4: Path, lang: str = "es"):
    """UNA transcripción -> (words_enmascaradas_para_subs, texto_verbatim_limpio)."""
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    segs, _info = model.transcribe(str(mp4), language=lang, word_timestamps=True)
    words, raw = [], []
    for s in segs:
        for w in s.words:
            t = w.word.strip()
            if not t:
                continue
            words.append({"word": pc._mask_profanidad(t), "start": w.start, "end": w.end})
            raw.append(t)
    texto = " ".join(raw).strip()
    for a, b in ((" ,", ","), (" .", "."), (" ?", "?"), (" !", "!"), (" :", ":"), (" ;", ";")):
        texto = texto.replace(a, b)
    return words, texto


def main():
    if not CLIP_ROOT.exists():
        raise SystemExit(f"[!] No existe la raíz de clips: {CLIP_ROOT}")

    env = cargar_env()
    tiene_supabase = bool(env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY"))
    print(f"Raíz: {CLIP_ROOT}")
    print(f"Encuadre 9:16 (cara): {'ON' if C._CV2_OK else 'OpenCV NO -> centrado'}")
    print(f"Supabase: {'sí' if tiene_supabase else 'NO'}", flush=True)

    if WORKROOT.exists():
        shutil.rmtree(WORKROOT, ignore_errors=True)

    subcarpetas = sorted([d for d in CLIP_ROOT.iterdir() if d.is_dir()])
    if SOLO_CARPETA:
        subcarpetas = [d for d in subcarpetas if d.name == SOLO_CARPETA]
        if not subcarpetas:
            raise SystemExit(f"[!] No hay subcarpeta '{SOLO_CARPETA}' en {CLIP_ROOT}")
    print(f"{len(subcarpetas)} carpeta(s) a procesar.\n", flush=True)

    hechos = fallos = saltados = 0

    for carpeta in subcarpetas:
        slug = carpeta.name
        base = RAIZ / "transcripciones" / slug
        out = base / "finales"
        textos = base / "textos"
        out.mkdir(parents=True, exist_ok=True)
        textos.mkdir(parents=True, exist_ok=True)

        cls = sorted(carpeta.glob("*.mp4"))
        print(f"\n########## {slug}  ({len(cls)} clips) ##########", flush=True)
        frases_carpeta = []

        for mp4 in cls:
            name = mp4.stem.strip()
            final_path = out / f"{name}.mp4"
            txt_path = textos / f"{name}.txt"

            # Idempotente: salta solo si ya es VERTICAL (h>w)
            if final_path.exists():
                fw, fh = dims(final_path)
                if fh > fw and txt_path.exists():
                    saltados += 1
                    texto = txt_path.read_text(encoding="utf-8").strip()
                    if texto:
                        frases_carpeta.append({"phrase": texto})
                    print(f"= {name}: ya 9:16 -> salto", flush=True)
                    continue

            print(f"=== {name}", flush=True)
            work = WORKROOT / slug / name
            work.mkdir(parents=True, exist_ok=True)
            try:
                sw, sh = dims(mp4)
                dur = duracion(mp4)
                # 1) reencuadre 9:16
                vert = work / "vert.mp4"
                def _es_num(s):
                    try:
                        float(s); return True
                    except ValueError:
                        return False
                if LADO in ("left", "izq"):
                    # Multicam con Luis a la IZQUIERDA: recorte por plano en la
                    # cara más a la izquierda, altura completa (sin regazo/piernas).
                    reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="left")
                elif LADO in ("center", "centro"):
                    # Multicam sin lado fijo: centra la cara dominante de cada plano
                    # (entrevistado y entrevistador), altura completa.
                    reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="center")
                elif LADO == "auto":
                    # Híbrido (Largo 4): primer plano -> centra la cara dominante;
                    # plano general -> la de la izquierda (Luis). Un recorte por plano.
                    reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="auto")
                elif LADO in ("auto-right", "auto-derecha"):
                    # Híbrido (Largo 5): primer plano -> cara dominante; plano
                    # general -> la de la DERECHA (Luis). Un recorte por plano.
                    reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="auto-right")
                elif LADO == "right" or _es_num(LADO):
                    # Plano a dos estático / centro fijo: BLOQUEA en el protagonista
                    reencuadre_persona(mp4, sw, sh, dur, vert, lado=LADO)
                else:
                    # Plano de una sola persona: seguimiento de cara centrado
                    C.cortar_vertical(mp4, 0, dur, vert, src_w=sw, src_h=sh)
                # 2) quitar silencios
                desil = work / "desil.mp4"
                try:
                    C.quitar_silencios(vert, desil)
                except Exception as e:
                    print(f"   [silencios] fallo ({e}); uso el clip sin recortar", flush=True)
                    desil = vert
                # 3) transcribir el 9:16 desilenciado (una vez)
                words, texto = transcribir_words_y_texto(desil, lang="es")
                txt_path.write_text(texto, encoding="utf-8")
                if texto:
                    frases_carpeta.append({"phrase": texto})
                # 4) Fase C
                out_tmp = work / "out.mp4"
                pc.burn_subs_and_music(
                    desil, MUSIC, out_tmp,
                    lang="es", env=env, overlays_dir=OVERLAYS,
                    hook_query=None,
                    clip_text=texto or None,
                    words=words,
                )
                shutil.move(str(out_tmp), str(final_path))
                hechos += 1
                print(f"   OK -> {final_path}", flush=True)
            except Exception as e:
                fallos += 1
                traceback.print_exc()
                print(f"   [!] FALLO en {name}: {e}", flush=True)
            finally:
                shutil.rmtree(work, ignore_errors=True)

        if tiene_supabase and frases_carpeta:
            phrases = [{"phrase": f["phrase"], "category": "clip", "angle": slug}
                       for f in frases_carpeta if f["phrase"]]
            try:
                res = pc.store_viral_phrases(
                    env, phrases, source_url=str(carpeta), lang="es", avatar=slug)
                if res.get("ok"):
                    print(f"   [frases] {res['stored']} guardadas en Supabase ({slug}).", flush=True)
                else:
                    print(f"   [frases] no guardado: {res.get('reason')}", flush=True)
            except Exception as e:
                print(f"   [frases] error (ignorado): {e}", flush=True)

    shutil.rmtree(WORKROOT, ignore_errors=True)
    print(f"\n==================== RESUMEN ====================", flush=True)
    print(f"OK/nuevos: {hechos}   saltados(ya 9:16): {saltados}   fallos: {fallos}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch — reels 9:16 a partir de clips YA cortados (vía 2).

Trabaja por PROYECTO (`--proyecto <id>`, ver proyecto.py). Recorre las
subcarpetas de una raíz (por defecto el buzón del proyecto,
proyectos/<id>/input/), trata cada subcarpeta como un "vídeo" (slug = nombre de
la carpeta) y por cada clip (.mp4, .mov, .m4v, .mkv) hace el FLUJO COMPLETO:
  1) reencuadre 9:16 vertical (1080x1920) según el MODO (argumento o, si no se
     da, el de la carpeta en proyecto.json → encuadre). Si la fuente YA es
     vertical (alto ≥ 1,7 × ancho, con la rotación aplicada), solo se escala,
     salvo con un MODO explícito (argumento o carpeta en encuadre.carpetas)
  2) quita silencios (auto-editor con los `silencios` del proyecto)
  3) edición final Fase C: b-roll + música + de-click + subtítulos palabra a
     palabra (pipeline_core.burn_subs_and_music) SOLO con los recursos que
     permite el proyecto (banco común o propios; sin internet si así lo dice).
     Sin gancho visual; con GANCHO DE TEXTO en la franja superior (~2,5 s) si el
     clip tiene texto en ganchos.json (y el proyecto lleva gancho_texto).
Salida en proyectos/<id>/transcripciones/<carpeta>/finales/.
Los clips SUELTOS en input/ (sin subcarpeta) forman el lote `_sueltos` en los
proyectos de clipping (o pidiendo la CARPETA `_sueltos`).
Al empezar cuenta los recursos según la política y PARA si falta b-roll o
música propios, salvo con --sin-broll / --sin-musica.

Gancho de texto (lo escribe el editor/LLM, nunca se genera mecánicamente):
    1) `--solo-transcribir`: hace reencuadre + silencios + transcripción de cada
       clip, guarda el texto en transcripciones/<carpeta>/textos/<clip>.txt, deja
       el 9:16 desilenciado + los word-timestamps en transcripciones/<carpeta>/_prep/
       y escribe transcripciones/<carpeta>/_para_ganchos.md (todos los textos, con
       la duración de cada clip: LO ÚNICO que lee el editor) y una plantilla
       ganchos.json con todas las claves vacías. No renderiza.
    2) El editor rellena transcripciones/<carpeta>/ganchos.json:
       {"<clip>.mp4": "¿Texto que abre el bucle?", ...}
       (también vale un ganchos.json dentro de la carpeta de origen) y lo
       comprueba con `--validar-ganchos`.
    3) Sin el flag: VALIDA ganchos.json (para si hay errores), renderiza
       reutilizando _prep/ (ni reencuadra ni transcribe otra vez) y quema el
       gancho de cada clip. Clip sin texto -> sale SIN gancho y se avisa.
_prep/ se CONSERVA hasta archivar (`proyecto.py aprobar` lo borra): corregir un
gancho (`--solo`) no repite reencuadre ni Whisper. Cada _prep/<clip>.words.json
guarda con qué MODO y silencios se hizo; si cambian, ese clip se rehace solo.

Además guarda en Supabase (viral_phrases) la transcripción verbatim de cada clip
como frase viral, con la etiqueta `proyecto:<id>` (best-effort, dedup por hash),
si el proyecto tiene guardar_frases. `--sin-frases` lo desactiva.

Eficiencia: transcribe cada clip UNA sola vez (sobre el 9:16 ya desilenciado) y
reutiliza esos word-timestamps para subtítulos + b-roll (words= a burn_subs).

Resumible/idempotente: si ya existe finales/<name>.mp4 Y es vertical (h>w), salta
el clip (salvo con --solo o --forzar). Los finales antiguos en 16:9 se REPROCESAN.
Sin CARPETA, salta los lotes ya aprobados (_Historico/<id>/<carpeta>/), salvo
con --forzar.

Correcciones de UN clip (sin tocar los demás ni proyecto.json):
    … "<CARPETA>" --solo "<clip>" --sin-frases                  # p. ej. gancho nuevo
    … "<CARPETA>" --solo "<clip>" --umbral 3% --margen 0.3s --sin-frases   # silencios
La música y el b-roll al azar salen de una semilla con el nombre del clip: el
re-render da lo mismo salvo lo que se ha corregido.

Uso ([RAIZ] es opcional: si el primer argumento no es una ruta, es la CARPETA):
    python procesar_batch_clip.py --proyecto x                      # todas las carpetas de su input/
    python procesar_batch_clip.py --proyecto x "Carpeta"            # una sola (modo del proyecto)
    python procesar_batch_clip.py --proyecto x "Carpeta" follow --solo-transcribir
    python procesar_batch_clip.py --proyecto x "C:/otra/raiz" "Carpeta" right   # otra raíz
    python procesar_batch_clip.py --proyecto x "Carpeta" --solo "clip 3" --sin-frases
    python procesar_batch_clip.py --proyecto x "Carpeta" --validar-ganchos   # solo valida
Si solo hay un proyecto, --proyecto se puede omitir. Con --quiet (por defecto si
la salida no es una terminal) la consola recibe una línea por clip y el RESUMEN.
"""
import argparse
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
from editar_clips import linea_clip  # noqa: E402
import clips as C  # noqa: E402  (reencuadre 9:16 + quitar silencios)
import herramientas  # noqa: E402
import proyecto  # noqa: E402
import validar  # noqa: E402

# Recursos del proyecto en curso (los fija main() a partir de proyecto.json).
MUSIC = None
OVERLAYS = None
WORKROOT = RAIZ / "whisper" / "_edit_batch"

GANCHOS_JSON = "ganchos.json"   # {"<clip>.mp4": "texto del gancho"} por carpeta
PARA_GANCHOS = "_para_ganchos.md"   # textos de todos los clips (lo que lee el LLM)
PREP_DIR = "_prep"              # 9:16 desilenciado + words de --solo-transcribir


def parse_args():
    ap = argparse.ArgumentParser(description="Reels 9:16 a partir de clips ya cortados.")
    ap.add_argument("posicionales", nargs="*", metavar="[RAIZ] [CARPETA] [MODO]",
                    help="RAIZ (opcional; por defecto proyectos/<id>/input/), CARPETA (solo esa "
                         "subcarpeta) y MODO de encuadre: right|left|center|auto|auto-right|"
                         "follow|<fracción> (por defecto, el de la carpeta en proyecto.json).")
    proyecto.add_argumento(ap)
    ap.add_argument("--raiz", default=None, help="Raíz con subcarpetas de clips (alternativa al posicional).")
    ap.add_argument("--solo-transcribir", action="store_true",
                    help="Reencuadre + silencios + transcripción (textos/ y _prep/), sin renderizar. "
                         "Sirve para escribir ganchos.json antes del render.")
    ap.add_argument("--sin-frases", action="store_true",
                    help="No guarda las transcripciones en viral_phrases.")
    ap.add_argument("--solo", action="append", metavar="CLIP",
                    help="Solo este clip de la CARPETA (repetible o separado por comas); lo "
                         "re-renderiza aunque ya tenga final.")
    ap.add_argument("--umbral", default=None,
                    help="Umbral de silencio SOLO para esta ejecución (p. ej. 3%%); no toca proyecto.json.")
    ap.add_argument("--margen", default=None,
                    help="Margen de silencio SOLO para esta ejecución (p. ej. 0.3s); no toca proyecto.json.")
    ap.add_argument("--forzar", action="store_true",
                    help="Procesa también lotes ya aprobados (_Historico/) y re-renderiza finales existentes.")
    ap.add_argument("--validar-ganchos", action="store_true",
                    help="Solo valida ganchos.json de la CARPETA (claves, líneas, signos, cifras) y sale.")
    ap.add_argument("--sin-musica", action="store_true",
                    help="Sin música en esta ejecución (si el proyecto aún no tiene la suya).")
    ap.add_argument("--sin-broll", action="store_true",
                    help="Sin b-roll en esta ejecución.")
    proyecto.add_salida(ap)
    return ap.parse_args()


def repartir_posicionales(pos: list, input_dir: Path, raiz_opt: str | None):
    """(raiz, carpeta, modo) a partir de [RAIZ] [CARPETA] [MODO].

    El primer argumento es RAIZ si es una ruta (absoluta, con separadores o una
    carpeta existente) y no una subcarpeta del input/ del proyecto; si no, es la
    CARPETA. Compatible con la forma antigua «RAIZ CARPETA MODO».
    """
    pos = list(pos or [])
    if len(pos) > 3:
        raise SystemExit("[!] Sobran argumentos: [RAIZ] [CARPETA] [MODO].")
    raiz = None
    if pos and not raiz_opt:
        a = pos[0]
        es_sub = (not Path(a).is_absolute() and len(Path(a).parts) == 1
                  and (Path(input_dir) / a).is_dir())
        parece_ruta = Path(a).is_absolute() or "/" in a or "\\" in a or Path(a).is_dir()
        if parece_ruta and not es_sub:
            raiz = Path(pos.pop(0))
        elif len(pos) == 3:
            raise SystemExit(f"[!] «{a}» no es una carpeta: usa [RAIZ] [CARPETA] [MODO].")
    carpeta = pos.pop(0) if pos else None
    modo = pos.pop(0) if pos else None
    if pos:
        raise SystemExit("[!] Sobran argumentos: [RAIZ] [CARPETA] [MODO].")
    if raiz_opt:
        raiz = Path(raiz_opt)
    return (raiz or Path(input_dir)), carpeta, modo


def cargar_ganchos(base: Path, carpeta: Path):
    """Textos de gancho por clip: ({nombre_clip: texto}, ruta usada o None).

    Busca transcripciones/<carpeta>/ganchos.json y, si no está, el de la carpeta
    de origen. Claves "<clip>.mp4" (o el nombre sin extensión). Valores vacíos =
    sin gancho. Nunca inventa texto: lo que no esté aquí sale sin gancho.
    """
    for p in (base / GANCHOS_JSON, carpeta / GANCHOS_JSON):
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   [gancho texto] AVISO: no pude leer {p} ({e}) -> sin ganchos.", flush=True)
            return {}, p
        ganchos = {}
        for k, v in (data.items() if isinstance(data, dict) else []):
            if isinstance(v, dict):
                v = v.get("gancho_texto") or v.get("texto")
            key = proyecto.sin_extension(k)
            if isinstance(v, str) and v.strip():
                ganchos[key] = v.strip()
        return ganchos, p
    return {}, None


def leer_ganchos_raw(base: Path, carpeta: Path):
    """(contenido de ganchos.json tal cual, ruta) o (None, None)."""
    for p in (base / GANCHOS_JSON, carpeta / GANCHOS_JSON):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")), p
            except Exception as e:
                return f"no es un JSON válido: {e}", p
    return None, None


def validar_ganchos_carpeta(base: Path, carpeta: Path, cls: list, solo: set | None = None) -> bool:
    """Valida ganchos.json contra los clips de la carpeta (validar.py)."""
    raw, ruta = leer_ganchos_raw(base, carpeta)
    nombres = [m.stem.strip() for m in cls]
    if raw is None:
        proyecto.decir(f"aviso: no hay {GANCHOS_JSON} en {base}: todos los clips saldrían sin gancho")
        return True
    if isinstance(raw, str):
        proyecto.decir(f"ERROR {ruta}: {raw}")
        return False
    textos = {}
    for n in nombres:
        t = base / "textos" / f"{n}.txt"
        if t.exists():
            textos[n] = t.read_text(encoding="utf-8")
    res = validar.validar_ganchos(raw, nombres, textos)
    return validar.informar(res, GANCHOS_JSON, solo=solo, decir=proyecto.decir)


def escribir_para_ganchos(base: Path, cls: list) -> tuple[Path, Path, int]:
    """_para_ganchos.md (## <clip> (34 s) + su texto, todos los clips) y una
    plantilla ganchos.json con todas las claves vacías (sin pisar lo escrito)."""
    prep, textos = base / PREP_DIR, base / "textos"
    partes, n = [f"# Ganchos de {base.name}",
                 "Escribe en ganchos.json un gancho por clip (≤ 2 líneas, ~45 car., con "
                 "¿¡ y tildes; se cumple en el clip; vacío = sin gancho).", ""], 0
    for m in cls:
        name = m.stem.strip()
        t = textos / f"{name}.txt"
        if not t.exists():
            continue
        dur = 0.0
        pw = prep / f"{name}.words.json"
        try:
            d = json.loads(pw.read_text(encoding="utf-8"))
            dur = float(d.get("dur") or 0) or herramientas.duracion(prep / f"{name}.mp4")
        except Exception:
            pass
        partes += [f"## {m.name} ({dur:.0f} s)", t.read_text(encoding="utf-8").strip(), ""]
        n += 1
    md = base / PARA_GANCHOS
    md.write_text("\n".join(partes), encoding="utf-8")
    gj = base / GANCHOS_JSON
    actual = {}
    if gj.exists():
        try:
            actual = json.loads(gj.read_text(encoding="utf-8"))
        except Exception:
            actual = None          # no se pisa un ganchos.json ilegible
    if isinstance(actual, dict):
        tenidas = {proyecto.sin_extension(k) for k in actual}
        nuevo = dict(actual)
        for m in cls:
            if m.stem.strip() not in tenidas:
                nuevo[m.name] = ""
        gj.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, gj, n


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


def _es_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def cargar_env() -> dict:
    """Credenciales (pc.cargar_env) + carpetas de recursos del proyecto."""
    env = pc.cargar_env()
    if MUSIC:
        env["MUSIC_DIR"] = str(MUSIC)
    if OVERLAYS:
        env["OVERLAYS_DIR"] = str(OVERLAYS)
    return env


def dims(mp4: Path):
    """(w, h) de PANTALLA del vídeo (con la rotación aplicada); (0,0) si falla."""
    return herramientas.dimensiones(mp4)


def duracion(mp4: Path) -> float:
    return herramientas.duracion(mp4)


def transcribir_words_y_texto(mp4: Path, lang: str = "es"):
    """UNA transcripción -> (words enmascaradas, texto verbatim). El modelo de
    faster-whisper se carga una sola vez para todo el lote (pc.whisper_model)."""
    return pc.transcribe_words_y_texto(mp4, lang=lang)


def lotes(clip_root: Path, p, solo_carpeta: str | None) -> list[tuple[str, Path, list]]:
    """[(slug, carpeta de origen, clips)]. Cada subcarpeta es un lote; los clips
    sueltos de la raíz forman `_sueltos` (proyectos de clipping, o si se pide)."""
    out = []
    for d in sorted(x for x in clip_root.iterdir() if x.is_dir()):
        cls = sorted(f for f in d.iterdir() if f.is_file() and f.suffix.lower() in proyecto.EXT_CLIPS)
        out.append((d.name, d, cls))
    sueltos = sorted(f for f in clip_root.iterdir()
                     if f.is_file() and f.suffix.lower() in proyecto.EXT_CLIPS)
    if sueltos and (p.tipo == "clipping" or solo_carpeta == proyecto.SUELTOS):
        out.append((proyecto.SUELTOS, clip_root, sueltos))
    elif sueltos and not solo_carpeta:
        proyecto.decir(f"nota: {len(sueltos)} vídeo(s) sueltos en {clip_root} (proyecto «{p.tipo}»: "
                       f"son de la vía 1). Para tratarlos como clips: CARPETA «{proyecto.SUELTOS}».")
    return out


def main():
    global MUSIC, OVERLAYS
    args = parse_args()
    if args.validar_ganchos:
        p = proyecto.abrir(args.proyecto, "batch", log=False, quiet=False)
    else:
        p = proyecto.abrir(args.proyecto, "batch", quiet=args.quiet)
    clip_root, solo_carpeta, modo_arg = repartir_posicionales(args.posicionales, p.input_dir, args.raiz)
    modo_arg = proyecto.normalizar_modo(modo_arg) if modo_arg else None
    solo_transcribir = args.solo_transcribir
    if (args.solo or args.validar_ganchos) and not solo_carpeta:
        raise SystemExit("[!] --solo y --validar-ganchos exigen la CARPETA.")
    if not clip_root.exists():
        raise SystemExit(f"[!] No existe la raíz de clips: {clip_root}")
    todos = lotes(clip_root, p, solo_carpeta)
    if solo_carpeta:
        todos = [t for t in todos if t[0] == solo_carpeta]
        if not todos:
            raise SystemExit(f"[!] No hay subcarpeta '{solo_carpeta}' en {clip_root}")

    if args.validar_ganchos:
        slug, carpeta, cls = todos[0]
        solo = proyecto.filtrar_solo([m.stem.strip() for m in cls], args.solo)
        ok = validar_ganchos_carpeta(p.transcripciones_dir / slug, carpeta, cls, solo)
        sys.exit(0 if ok else 1)

    if not solo_transcribir:
        proyecto.decir(p.comprobar_recursos(args.sin_broll, args.sin_musica))
    else:
        p.comprobar_recursos(args.sin_broll, args.sin_musica)
    MUSIC = None if args.sin_musica else p.music_dir
    OVERLAYS = None if args.sin_broll else p.overlays_dir
    # None = lo de siempre (banco común + internet)
    recursos = p.politica_render(sin_broll=args.sin_broll, sin_musica=args.sin_musica)
    sil = proyecto.silencios_cli(p.silencios, args.umbral, args.margen)
    lang = p.idioma
    if (args.umbral or args.margen) and not args.solo:
        proyecto.decir("AVISO: --umbral/--margen sin --solo se aplican a TODOS los clips de esta "
                       "ejecución (no se guardan en proyecto.json).")

    env = cargar_env()
    tiene_supabase = bool(env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY"))
    guardar_frases = (tiene_supabase and not args.sin_frases and not solo_transcribir
                      and p.guardar_frases)
    print(f"Raíz: {clip_root}")
    print(f"Encuadre 9:16 (cara): {'ON' if C._CV2_OK else 'OpenCV NO -> centrado'}  "
          f"modo={modo_arg or 'el de cada carpeta (proyecto.json)'}")
    print(f"Silencios: umbral {sil['umbral']} · margen {sil['margen']}"
          + ("" if sil == p.silencios else "  (solo esta ejecución)"))
    print(f"Supabase: {'sí' if tiene_supabase else 'NO'}"
          + ("  (frases desactivadas)" if tiene_supabase and not guardar_frases else ""))
    if not p.gancho_texto:
        print("Gancho de texto: el proyecto no lo lleva.")
    if solo_transcribir:
        print("Modo --solo-transcribir: reencuadre + silencios + transcripción, SIN render.")
    sys.stdout.flush()

    if WORKROOT.exists():
        shutil.rmtree(WORKROOT, ignore_errors=True)

    if not args.forzar:
        # Lotes ya aprobados (siguen en input/ pero están en _Historico): no se rehacen.
        # Los sueltos que siguen en input/ son nuevos (aprobar se lleva los aprobados).
        aprobados = [t for t in todos if t[0] != proyecto.SUELTOS and p.archivado(t[0])]
        for t in aprobados:
            proyecto.decir(f"= {t[0]}: ya aprobado y archivado en {p.archivado(t[0])} -> salto "
                           f"(--forzar para rehacerlo)")
        todos = [t for t in todos if t not in aprobados]
    print(f"{len(todos)} carpeta(s) a procesar.\n", flush=True)

    hechos = fallos = saltados = preparados = 0
    sin_gancho = []   # "<carpeta>/<clip>" renderizados sin texto de gancho
    lista_fallos = []

    for slug, carpeta, cls in todos:
        base = p.transcripciones_dir / slug
        out = base / "finales"
        textos = base / "textos"
        prep = base / PREP_DIR
        out.mkdir(parents=True, exist_ok=True)
        textos.mkdir(parents=True, exist_ok=True)
        lado = modo_arg or p.modo_encuadre(slug)
        modo_explicito = bool(modo_arg or p.modo_de_carpeta(slug))

        todos_cls = list(cls)
        solo = proyecto.filtrar_solo([m.stem.strip() for m in cls], args.solo)
        if solo is not None:
            cls = [m for m in cls if m.stem.strip() in solo]
        prep_meta = {"modo": lado, "umbral": sil["umbral"], "margen": sil["margen"]}
        print(f"\n########## {slug}  ({len(cls)} clips, encuadre {lado}"
              + (f", solo {', '.join(sorted(solo))}" if solo else "") + ") ##########", flush=True)
        frases_carpeta = []
        sin_ganchos = solo_transcribir or not p.gancho_texto
        ganchos, ganchos_path = ({}, None) if sin_ganchos else cargar_ganchos(base, carpeta)
        if not sin_ganchos:
            # Validación antes de renderizar: si hay errores en estos clips, para.
            if not validar_ganchos_carpeta(base, carpeta, todos_cls,
                                           solo or {m.stem.strip() for m in cls}):
                raise SystemExit(f"[!] {GANCHOS_JSON} de «{slug}» tiene errores: corrígelos "
                                 f"(--validar-ganchos) y relanza. No se ha renderizado nada.")
            if ganchos_path:
                print(f"   [gancho texto] {len(ganchos)} texto(s) en {ganchos_path}", flush=True)
            else:
                print(f"   [gancho texto] AVISO: no hay {GANCHOS_JSON} en {base} ni en la carpeta "
                      f"de origen -> los clips nuevos salen SIN gancho de texto", flush=True)

        for mp4 in cls:
            name = mp4.stem.strip()
            final_path = out / f"{name}.mp4"
            txt_path = textos / f"{name}.txt"
            prep_mp4 = prep / f"{name}.mp4"
            prep_words = prep / f"{name}.words.json"
            hay_prep = prep_mp4.exists() and prep_words.exists()
            prep_data = None
            if hay_prep:
                try:
                    prep_data = json.loads(prep_words.read_text(encoding="utf-8"))
                except Exception:
                    prep_data = None
                hecho = (prep_data or {}).get("prep")
                if prep_data is None or (hecho and hecho != prep_meta):
                    print(f"   [prep] {name}: _prep/ hecho con {hecho or '¿?'} y ahora es "
                          f"{prep_meta} -> se rehace", flush=True)
                    hay_prep = False

            # Idempotente: salta solo si ya es VERTICAL (h>w), salvo --solo/--forzar.
            # Sus frases ya se guardaron cuando se renderizó: no se vuelven a subir.
            if final_path.exists() and solo is None and not args.forzar:
                fw, fh = dims(final_path)
                if fh > fw and txt_path.exists():
                    saltados += 1
                    print(f"= {name}: ya 9:16 -> salto", flush=True)
                    continue
            if solo_transcribir and hay_prep and txt_path.exists():
                preparados += 1
                print(f"= {name}: ya preparado (_prep/) -> salto", flush=True)
                continue

            print(f"=== {name}", flush=True)
            work = WORKROOT / slug / name
            work.mkdir(parents=True, exist_ok=True)
            try:
                if hay_prep and not solo_transcribir:
                    # Reutiliza lo hecho con --solo-transcribir: ni reencuadre ni
                    # quitar silencios ni Whisper otra vez.
                    desil = work / "desil.mp4"
                    shutil.copy(str(prep_mp4), str(desil))
                    words = prep_data.get("words") or []
                    texto = (prep_data.get("texto") or "").strip()
                    if not txt_path.exists():
                        txt_path.write_text(texto, encoding="utf-8")
                    print("   [prep] reutilizo reencuadre + silencios + transcripción de _prep/", flush=True)
                else:
                    sw, sh = dims(mp4)
                    dur = duracion(mp4)
                    # 1) reencuadre 9:16
                    vert = work / "vert.mp4"
                    if herramientas.es_vertical(sw, sh) and not modo_explicito:
                        # Fuente ya vertical: solo escalar (sin reencuadre).
                        print(f"   [encuadre] fuente vertical {sw}x{sh}: solo escala", flush=True)
                        C.escalar_vertical(mp4, vert)
                    elif lado == "left":
                        # Multicam con Luis a la IZQUIERDA: recorte por plano en la
                        # cara más a la izquierda, altura completa (sin regazo/piernas).
                        reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="left")
                    elif lado == "center":
                        # Multicam sin lado fijo: centra la cara dominante de cada plano
                        # (entrevistado y entrevistador), altura completa.
                        reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="center")
                    elif lado == "auto":
                        # Híbrido (Largo 4): primer plano -> centra la cara dominante;
                        # plano general -> la de la izquierda (Luis). Un recorte por plano.
                        reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="auto")
                    elif lado == "auto-right":
                        # Híbrido: primer plano -> cara dominante; plano general -> la
                        # de la DERECHA. Un recorte por plano.
                        reencuadre_izq_por_plano(mp4, sw, sh, dur, vert, sel="auto-right")
                    elif lado == "right" or _es_num(lado):
                        # Plano a dos estático / centro fijo: BLOQUEA en el protagonista
                        reencuadre_persona(mp4, sw, sh, dur, vert, lado=lado)
                    else:  # follow
                        # Plano de una sola persona: seguimiento de cara centrado
                        C.cortar_vertical(mp4, 0, dur, vert, src_w=sw, src_h=sh)
                    # 2) quitar silencios
                    desil = work / "desil.mp4"
                    try:
                        C.quitar_silencios(vert, desil, umbral=sil["umbral"], margen=sil["margen"])
                    except Exception as e:
                        print(f"   [silencios] fallo ({e}); uso el clip sin recortar", flush=True)
                        desil = vert
                    # 3) transcribir el 9:16 desilenciado (una vez)
                    words, texto = transcribir_words_y_texto(desil, lang=lang)
                    txt_path.write_text(texto, encoding="utf-8")
                    # Deja el 9:16 + words en _prep/ (hasta archivar): el render y
                    # las correcciones lo reutilizan sin repetir nada.
                    prep.mkdir(parents=True, exist_ok=True)
                    shutil.copy(str(desil), str(prep_mp4))
                    prep_words.write_text(json.dumps(
                        {"texto": texto, "words": words, "prep": prep_meta,
                         "dur": round(duracion(desil), 2)}, ensure_ascii=False), encoding="utf-8")
                    if solo_transcribir:
                        preparados += 1
                        print(f"   preparado -> textos/{name}.txt (+ {PREP_DIR}/)", flush=True)
                        proyecto.decir(f"PREP {mp4.name} · {duracion(desil):.0f} s · "
                                       f"{len(texto.split())} palabras")
                        continue
                if texto:
                    frases_carpeta.append({"phrase": texto})
                # 4) Fase C (+ gancho de texto si el editor lo escribió)
                gancho = ganchos.get(name) if p.gancho_texto else None
                if gancho:
                    print(f"   [gancho texto] «{gancho}»", flush=True)
                elif p.gancho_texto:
                    sin_gancho.append(f"{slug}/{name}")
                    print(f"   [gancho texto] AVISO: {name} no tiene texto en {GANCHOS_JSON} "
                          f"-> se renderiza SIN gancho", flush=True)
                out_tmp = work / "out.mp4"
                info = {}
                pc.burn_subs_and_music(
                    desil, MUSIC, out_tmp,
                    lang=lang, env=env, overlays_dir=OVERLAYS,
                    hook_query=None,
                    clip_text=texto or None,
                    words=words,
                    hook_text=gancho, hook_text_dur=p.gancho_duracion,
                    recursos=recursos, seed=name, info=info,
                )
                shutil.move(str(out_tmp), str(final_path))
                hechos += 1
                print(f"   OK -> {final_path}", flush=True)
                proyecto.decir(linea_clip(name, info, False))
            except Exception as e:
                fallos += 1
                lista_fallos.append(f"{slug}/{name}")
                traceback.print_exc(file=sys.stdout)      # al log (y a consola con --verbose)
                proyecto.decir(f"FALLO {mp4.name} · {herramientas.describir_error(e)} "
                               f"(detalle en el log)")
            finally:
                shutil.rmtree(work, ignore_errors=True)

        if prep.exists() and not any(prep.iterdir()):
            prep.rmdir()
        if solo_transcribir:
            md, gj, n = escribir_para_ganchos(base, todos_cls)
            proyecto.decir(f"{slug}: {n} texto(s) -> lee SOLO {md}; rellena {gj} y comprueba con "
                           f"--validar-ganchos antes de renderizar.")

        if guardar_frases and frases_carpeta:
            phrases = [{"phrase": f["phrase"], "category": "clip", "angle": slug,
                        "tags": p.etiquetas_frases()}
                       for f in frases_carpeta if f["phrase"]]
            try:
                res = pc.store_viral_phrases(
                    env, phrases, source_url=str(carpeta), lang=lang, avatar=slug,
                    proyecto=p.id)
                if res.get("ok"):
                    print(f"   [frases] {res['stored']} guardadas en Supabase ({slug}).", flush=True)
                else:
                    print(f"   [frases] no guardado: {res.get('reason')}", flush=True)
            except Exception as e:
                print(f"   [frases] error (ignorado): {e}", flush=True)

    shutil.rmtree(WORKROOT, ignore_errors=True)
    if solo_transcribir:
        proyecto.decir(f"RESUMEN: preparados {preparados} · saltados (ya 9:16) {saltados} · "
                       f"fallos {fallos}" + (f" ({', '.join(lista_fallos)})" if lista_fallos else ""))
    else:
        proyecto.decir(f"RESUMEN: OK/nuevos {hechos} · saltados (ya 9:16) {saltados} · fallos {fallos}"
                       + (f" ({', '.join(lista_fallos)})" if lista_fallos else "")
                       + (f" · sin gancho de texto: {', '.join(sin_gancho)}" if sin_gancho else ""))
        if hechos:
            proyecto.decir(f"QC: .venv\\Scripts\\python.exe qc.py --proyecto {p.id} \"<CARPETA>\"  "
                           f"(y mira finales/_qc.jpg)")
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()

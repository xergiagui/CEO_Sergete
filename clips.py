#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 3 del flujo: a partir del video original y los momentos con mas gancho,
genera clips verticales (9:16) y les quita los silencios con auto-editor.

GENERICO: funciona con cualquier video. Los momentos de corte se leen de un
`cortes.json` (no van fijados en el codigo), asi que el flujo puede ser 100%
automatico: el agente 'editor' genera ese JSON desde la transcripcion aplicando
las reglas de recorte/hook, y este script solo lo ejecuta.

Uso:
    python clips.py "Mi Adicción"                 -> input/Mi Adicción.mp4
    python clips.py "input/video.mp4"             -> ruta concreta
    python clips.py "../TheDescarga/descargas/x.mp4"
    python clips.py "video" --cortes cortes.json  -> spec de cortes explicito

Formato de cortes.json (lista de objetos):
    [
      {"nombre": "01_gancho", "inicio": 42.0, "fin": 66.7,
       "titulo": "La extrana adiccion", "hook_query": "excited entrepreneur"},
      ...
    ]
  - nombre     (obligatorio) -> nombre del clip de salida
  - inicio/fin (obligatorio) -> segundos
  - titulo     (opcional)    -> descriptivo
  - hook_query (opcional)    -> lo usa editar_clips.py para la imagen-gancho
  - frase_viral(opcional)    -> texto VERBATIM mas potente/gancho del clip; lo
                                usa editar_clips.py para guardarlo en el banco de
                                frases virales de Supabase (tabla viral_phrases).
                                Admite tambien angle/virality/category/rationale/
                                tags opcionales por corte. Si falta frase_viral se
                                cae al titulo/hook, y si no hay Supabase no rompe.
Si no se pasa --cortes, se busca en transcripciones/<video>/cortes.json.

Los subtitulos NO se queman aqui. Se anaden UNA sola vez en la edicion final
con la skill Editor_Sergio (b-roll + musica + subs), para no generarlos dos
veces ni acabar con subtitulos duplicados en pantalla.

Pipeline por clip:
  1) ffmpeg  -> recorte + crop vertical 1080x1920
  2) auto-editor (umbral 6%, margen 0.15s) -> quita silencios -> clip final
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Encuadre 9:16 que SIGUE al hablante (A2) --------------------------------
# El recorte vertical de un 16:9 conserva TODA la altura y toma una franja
# horizontal. Si el sujeto está descentrado, una franja CENTRADA fija lo deja
# fuera de cuadro (se ve el centro de la escena: torso/piernas de otra persona,
# "solo piernas sin cara"). Para evitarlo detectamos la CARA (Haar/OpenCV) sobre
# unos frames muestreados del tramo y desplazamos la franja para centrarla en el
# hablante. Es best-effort: si no hay OpenCV o no se detecta cara, se cae al
# recorte centrado de siempre (comportamiento previo, nunca peor).
try:
    import cv2  # opencv-python-headless
    _HAAR = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    # En planos GENERALES el hablante suele estar de PERFIL (mirando al
    # entrevistador) y el detector frontal falla -> sin cara -> no se recorta la
    # pierna. La cascada de perfil recupera esos casos (clave para el anti-piernas).
    _HAAR_PROF = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_profileface.xml")
    _CV2_OK = not _HAAR.empty()
except Exception:
    cv2 = None
    _CV2_OK = False


def _detectar_cara(gray):
    """Mayor cara (x,y,w,h) por Haar frontal; si no hay, perfil (ambos lados)."""
    faces = _HAAR.detectMultiScale(gray, 1.1, 5, minSize=(24, 24))
    if len(faces):
        return max(faces, key=lambda f: f[2] * f[3])
    if _HAAR_PROF is not None and not _HAAR_PROF.empty():
        cand = list(_HAAR_PROF.detectMultiScale(gray, 1.1, 4, minSize=(24, 24)))
        flip = cv2.flip(gray, 1)
        for (x, y, w, h) in _HAAR_PROF.detectMultiScale(flip, 1.1, 4, minSize=(24, 24)):
            cand.append((gray.shape[1] - x - w, y, w, h))  # des-espejar
        if cand:
            return max(cand, key=lambda f: f[2] * f[3])
    return None

# --- Encuadre vertical adaptativo (bust-crop por plano) ----------------------
# Un clip de podcast suele ser MULTICAM: alternan un plano MEDIO (cara grande,
# solo se ve el torso) con un plano GENERAL/wide (dos personas, cuerpos enteros
# con piernas y zapatos). Conservar SIEMPRE toda la altura del 16:9 deja las
# piernas a la vista en los planos generales ("solo piernas"). Para evitarlo, el
# recorte 9:16 se hace por TRAMOS: en cada plano medimos el tamano de la cara y
# elegimos la ALTURA de recorte para encuadrar un BUSTO (cara + pecho):
#   - cara grande (plano medio)  -> recorte ~altura completa (como antes; no
#                                    toca los clips que ya estaban bien).
#   - cara pequena (plano wide)  -> ZOOM al busto: recorta tambien en vertical y
#                                    deja las piernas FUERA de cuadro.
# El fuente es 4K, asi que el zoom tiene margen sin pixelar en exceso (se acota
# con MIN_CROP_FRAC). Si no hay OpenCV o la deteccion es pobre, se cae al recorte
# de altura completa de siempre (fallback seguro, nunca peor que antes).
TARGET_FACE_FRAC = 0.30   # altura de cara objetivo respecto al alto de salida
HEADROOM_FRAC    = 0.12   # aire sobre la cabeza (fraccion del alto de recorte)
MIN_CROP_FRAC    = 0.40   # recorte minimo = 40% del alto fuente (acota el zoom:
                          #   ~2.2x de upscale a 1920 desde 4K -> nitidez OK)

# Salida robusta en Windows (evita UnicodeEncodeError con chars no-cp1252).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent
PY = sys.executable


def resolver_ffmpeg() -> str:
    """Localiza ffmpeg de forma robusta (no depende de una ruta fija de winget)."""
    fijo = r"C:\Users\ico858\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-125875-g5d4d3bdc61-win64-gpl\bin\ffmpeg.exe"
    if Path(fijo).exists():
        return fijo
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    hallado = shutil.which("ffmpeg")
    if hallado:
        return hallado
    raise SystemExit("[!] No se encontro ffmpeg (ni winget, ni imageio-ffmpeg, ni PATH).")


FFMPEG = resolver_ffmpeg()


def resolver_video(arg: str) -> tuple[Path, str]:
    """Devuelve (ruta_video, nombre). Acepta ruta concreta o nombre en input/."""
    p = Path(arg)
    if p.suffix and (p.exists() or p.is_absolute() or len(p.parts) > 1):
        return p.resolve(), p.stem
    nombre = p.stem if p.suffix else arg
    return (RAIZ / "input" / f"{nombre}.mp4").resolve(), nombre


def cargar_cortes(ruta: Path) -> list[dict]:
    if not ruta.exists():
        raise SystemExit(
            f"[!] Falta el spec de cortes: {ruta}\n"
            f"    Genera un cortes.json (ver formato en la cabecera de clips.py) "
            f"a partir de la transcripcion y vuelve a lanzar."
        )
    data = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"[!] {ruta} debe ser una lista no vacia de cortes.")
    for i, c in enumerate(data):
        if not all(k in c for k in ("nombre", "inicio", "fin")):
            raise SystemExit(f"[!] Corte #{i} incompleto (requiere nombre, inicio, fin): {c}")
    return data


def run(cmd):
    print("   $", " ".join(str(c) for c in cmd[:2]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(f"[!] Fallo: {cmd[0]}")
    return r


def probe_dims(video: Path) -> tuple[int, int]:
    """(ancho, alto) del vídeo, parseando stderr de ffmpeg (sin ffprobe)."""
    r = subprocess.run([FFMPEG, "-i", str(video), "-hide_banner"],
                       capture_output=True, text=True, errors="replace")
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", r.stderr)
    if not m:
        return 0, 0
    return int(m.group(1)), int(m.group(2))


def detectar_centro_x(video: Path, inicio, fin, src_w: int,
                      half_norm: float, n: int = 24) -> float | None:
    """Centro horizontal NORMALIZADO (0..1) del hablante en el tramo, o None.

    Extrae ~1 frame/s del tramo (seek rápido de entrada) a baja resolución y
    detecta caras con Haar. Devuelve el centro del RANGO de caras (p10..p90) para
    que el sujeto quepa entero aunque se mueva; si el rango no cabe en la franja,
    usa la mediana (best-effort). None si OpenCV no está o no hay caras fiables.
    """
    if not _CV2_OK or src_w <= 0:
        return None
    dur = max(float(fin) - float(inicio), 0.2)
    n = int(min(max(n, 6), max(6, dur)))  # ~1 fps, tope razonable
    d = tempfile.mkdtemp(prefix="crop9x16_")
    try:
        subprocess.run(
            [FFMPEG, "-y", "-ss", f"{inicio}", "-i", str(video), "-t", f"{dur}",
             "-vf", f"fps={n}/{dur:.3f},scale=640:-2", "-q:v", "4",
             os.path.join(d, "f_%03d.jpg")],
            capture_output=True, text=True, errors="replace")
        xs = []
        import glob as _glob
        for p in sorted(_glob.glob(os.path.join(d, "*.jpg"))):
            fr = cv2.imread(p)
            if fr is None:
                continue
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            faces = _HAAR.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            if len(faces):
                fx, _fy, fw, _fh = max(faces, key=lambda f: f[2] * f[3])
                xs.append((fx + fw / 2) / fr.shape[1])  # normalizado 0..1
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if len(xs) < 4:  # muy pocas detecciones -> no fiable
        return None
    xs.sort()
    import statistics
    med = statistics.median(xs)
    lo = xs[int(0.10 * (len(xs) - 1))]
    hi = xs[int(0.90 * (len(xs) - 1))]
    centro = (lo + hi) / 2 if (hi - lo) / 2 <= half_norm else med
    # clamp para que la franja no se salga del fotograma
    return min(max(centro, half_norm), 1.0 - half_norm)


def _par(v: float) -> int:
    """Entero par >= 0 (libx264 exige dimensiones/offsets pares)."""
    return int(v) - (int(v) % 2)


def _rect_busto(cx_px, top_px, fh_px, src_w, src_h):
    """(w,h,x,y) enteros pares del recorte 9:16 tipo BUSTO para una cara.

    Elige la ALTURA por el tamano de la cara (cara pequena -> mas zoom), acota el
    zoom con MIN_CROP_FRAC y coloca la cabeza con algo de aire arriba, dejando el
    pecho debajo y las piernas fuera. Todo clampeado dentro del fotograma.
    """
    crop_h = fh_px / TARGET_FACE_FRAC
    crop_h = min(max(crop_h, src_h * MIN_CROP_FRAC), float(src_h))
    crop_w = min(crop_h * 9.0 / 16.0, float(src_w))
    x = min(max(cx_px - crop_w / 2.0, 0.0), src_w - crop_w)
    y = min(max(top_px - HEADROOM_FRAC * crop_h, 0.0), src_h - crop_h)
    return _par(crop_w), _par(crop_h), _par(x), _par(y)


def _rect_altura_completa(cx_px, src_w, src_h):
    """Recorte 9:16 de ALTURA COMPLETA centrado en cx (comportamiento previo)."""
    crop_w = min(_par(src_h * 9.0 / 16.0), _par(src_w))
    if cx_px is None:
        x = _par((src_w - crop_w) / 2.0)
    else:
        x = _par(min(max(cx_px - crop_w / 2.0, 0.0), src_w - crop_w))
    return crop_w, _par(src_h), x, 0


def muestrear_caras(video: Path, inicio, fin, src_w, src_h, fps=5):
    """Muestrea la cara del hablante a lo largo del tramo (best-effort).

    Devuelve (samples, dur) donde samples es una lista con un elemento por frame
    muestreado: dict {cx, top, fh} en PIXELES del fuente, o None si no hubo cara.
    None global si OpenCV no esta disponible.
    """
    if not _CV2_OK or src_w <= 0 or src_h <= 0:
        return None, 0.0
    dur = max(float(fin) - float(inicio), 0.2)
    n = int(max(round(dur * fps), 6))
    d = tempfile.mkdtemp(prefix="reframe_")
    samples = []
    try:
        subprocess.run(
            [FFMPEG, "-y", "-ss", f"{inicio}", "-i", str(video), "-t", f"{dur}",
             "-vf", f"fps={n}/{dur:.3f},scale=960:-2", "-q:v", "4",
             os.path.join(d, "f_%04d.jpg")],
            capture_output=True, text=True, errors="replace")
        import glob as _glob
        for p in sorted(_glob.glob(os.path.join(d, "*.jpg"))):
            fr = cv2.imread(p)
            if fr is None:
                samples.append(None)
                continue
            H, W = fr.shape[:2]
            sx, sy = src_w / W, src_h / H  # escala a pixeles del fuente
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            f = _detectar_cara(gray)
            if f is not None:
                fx, fy, fw, fh = f
                samples.append({"cx": (fx + fw / 2) * sx,
                                "top": fy * sy, "fh": fh * sy})
            else:
                samples.append(None)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return samples, dur


def detectar_cortes_escena(video: Path, inicio, dur, thr=0.3):
    """Tiempos (relativos a `inicio`) de los cortes de camara dentro del tramo.

    Un podcast multicam alterna planos con CORTES DUROS; ffmpeg los detecta bien
    con el filtro `select=gt(scene,thr)`. Devolvemos esos instantes para tratar
    cada PLANO por separado (clave para no mezclar un plano medio con uno general
    en el mismo recorte). Best-effort: [] si algo falla.
    """
    try:
        r = subprocess.run(
            [FFMPEG, "-ss", f"{inicio}", "-t", f"{dur}", "-i", str(video),
             "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        ts = sorted({round(float(x[9:]), 2)
                     for x in re.findall(r"pts_time:[0-9.]+", r.stderr)})
        return [t for t in ts if 0.25 < t < dur - 0.15]
    except Exception:
        return []


def construir_segmentos(samples, dur, src_w, src_h, cortes):
    """Tramos [t0,t1) con un recorte 9:16 por PLANO (bust-crop adaptativo).

    Segmenta por cortes de escena y, en cada plano, usa la MEDIANA de las caras
    detectadas para elegir un recorte estable: cara grande -> ~altura completa;
    cara pequena (plano general) -> zoom al busto (piernas fuera). Un plano sin
    caras cae a altura completa centrada (fallback seguro). Devuelve None si la
    deteccion global es demasiado pobre (el llamador usa el fallback de siempre).
    """
    if not samples:
        return None
    import statistics
    n = len(samples)
    if sum(1 for s in samples if s) < 4:
        return None
    dt = dur / n
    bordes = [0.0] + list(cortes) + [dur]
    planos = [(bordes[i], bordes[i + 1]) for i in range(len(bordes) - 1)
              if bordes[i + 1] - bordes[i] > 0.05]

    def rect_de_plano(a, b):
        caras = [samples[i] for i in range(n)
                 if samples[i] and a <= (i + 0.5) * dt < b]
        if not caras:
            return _rect_altura_completa(None, src_w, src_h)
        cx = statistics.median([c["cx"] for c in caras])
        top = statistics.median([c["top"] for c in caras])
        fh = statistics.median([c["fh"] for c in caras])
        return _rect_busto(cx, top, fh, src_w, src_h)

    segs = [[a, b, rect_de_plano(a, b)] for a, b in planos]
    # Fusiona planos muy cortos (<0.4s) con el vecino anterior.
    fusion = [segs[0]]
    for s in segs[1:]:
        if s[1] - s[0] < 0.4:
            fusion[-1][1] = s[1]
        else:
            fusion[-1][1] = s[0]
            fusion.append(s)
    fusion[-1][1] = dur
    return fusion


def cortar_vertical(video: Path, inicio, fin, destino, src_w=0, src_h=0):
    dur = float(fin) - float(inicio)
    samples, sdur = muestrear_caras(video, inicio, fin, src_w, src_h)
    cortes = detectar_cortes_escena(video, inicio, sdur) if samples else []
    segs = construir_segmentos(samples, sdur, src_w, src_h, cortes) if samples else None

    if segs:
        _render_segmentado(video, inicio, dur, segs, destino, src_h)
        return

    # ---- Fallback: recorte de ALTURA COMPLETA (comportamiento previo) --------
    crop_w = int(((src_h * 9 / 16) // 2) * 2) if src_h else 0
    x_expr = "(iw-ow)/2"
    encuadre = "centrado"
    if crop_w and src_w and _CV2_OK:
        half_norm = (crop_w / src_w) / 2
        centro = detectar_centro_x(video, inicio, fin, src_w, half_norm)
        if centro is not None:
            x = int(round(centro * src_w - crop_w / 2))
            x = max(0, min(x, src_w - crop_w)); x -= x % 2
            x_expr = str(x)
            encuadre = f"cara@{centro:.2f} (x={x})"
    vf = (f"crop={crop_w}:ih:{x_expr}:0,scale=1080:1920,setsar=1" if crop_w
          else "crop=trunc(ih*9/16/2)*2:ih,scale=1080:1920,setsar=1")
    print(f"   [encuadre] altura-completa {encuadre} (fallback)")
    run([FFMPEG, "-y", "-ss", f"{inicio}", "-t", f"{dur}", "-i", str(video),
         "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(destino)])


def _encode_tramo(video: Path, ss, t, rect, destino):
    w, h, x, y = rect
    vf = f"crop={w}:{h}:{x}:{y},scale=1080:1920,setsar=1"
    run([FFMPEG, "-y", "-ss", f"{ss}", "-t", f"{t}", "-i", str(video),
         "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-video_track_timescale", "12800", str(destino)])


def _render_segmentado(video: Path, inicio, dur, segs, destino, src_h):
    """Renderiza el clip por tramos (un recorte por plano) y los concatena."""
    zooms = [s for s in segs if s[2][1] < 0.98 * src_h]
    print(f"   [encuadre] busto adaptativo: {len(segs)} planos, "
          f"{len(zooms)} con zoom vertical (anti-piernas)")
    if len(segs) == 1:
        _encode_tramo(video, inicio + segs[0][0], dur, segs[0][2], destino)
        return
    d = tempfile.mkdtemp(prefix="segmerge_")
    try:
        lista = os.path.join(d, "list.txt")
        partes = []
        for i, (t0, t1, rect) in enumerate(segs):
            parte = os.path.join(d, f"seg_{i:03d}.mp4")
            _encode_tramo(video, inicio + t0, t1 - t0, rect, parte)
            partes.append(parte)
        with open(lista, "w", encoding="utf-8") as f:
            for p in partes:
                f.write(f"file '{p}'\n")
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lista,
             "-c", "copy", "-movflags", "+faststart", str(destino)])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def quitar_silencios(origen, destino):
    run([PY, "-m", "auto_editor", str(origen),
         "--edit", "audio:threshold=6%", "--margin", "0.15s",
         "-o", str(destino), "--no-open"])


def main():
    ap = argparse.ArgumentParser(description="Genera clips verticales 9:16 sin silencios.")
    ap.add_argument("video", help="Nombre en input/ o ruta al video.")
    ap.add_argument("--cortes", help="Ruta al cortes.json (por defecto transcripciones/<video>/cortes.json).")
    ap.add_argument("--keep-tmp", action="store_true", help="No borrar intermedios.")
    args = ap.parse_args()

    video, nombre = resolver_video(args.video)
    if not video.exists():
        raise SystemExit(f"[!] No existe el video: {video}")

    salida = RAIZ / "transcripciones" / nombre / "clips"
    tmp = salida / "_tmp"
    cortes_path = Path(args.cortes) if args.cortes else (RAIZ / "transcripciones" / nombre / "cortes.json")
    cortes = cargar_cortes(cortes_path)

    salida.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    src_w, src_h = probe_dims(video)
    encuadre = ("seguimiento de cara ON" if _CV2_OK
               else "OpenCV NO disponible -> recorte centrado (instala "
                    "opencv-python-headless para el seguimiento de cara)")
    print(f"Video: {video}  ({src_w}x{src_h})\n"
          f"Cortes: {cortes_path}  ({len(cortes)} clips)\nEncuadre 9:16: {encuadre}\n")

    for c in cortes:
        cn, ini, fin = c["nombre"], c["inicio"], c["fin"]
        titulo = c.get("titulo", "")
        print(f"\n=== {cn}  ({ini}s -> {fin}s)  {titulo}")
        vert = tmp / f"{cn}_vert.mp4"
        final = salida / f"{cn}.mp4"
        cortar_vertical(video, ini, fin, vert, src_w=src_w, src_h=src_h)
        quitar_silencios(vert, final)
        print(f"   OK -> {final.name}  (sin subtitulos; los pone Editor_Sergio)")

    if tmp.exists() and not args.keep_tmp:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"   Intermedios eliminados: {tmp}")

    print(f"\nListo. Clips (sin subs) en: {salida}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 3 del flujo: a partir del video original y los momentos con mas gancho,
genera clips verticales (9:16) y les quita los silencios con auto-editor.

GENERICO: funciona con cualquier video. Los momentos de corte se leen de un
`cortes.json` (no van fijados en el codigo), asi que el flujo puede ser 100%
automatico: el agente 'editor' genera ese JSON desde la transcripcion aplicando
las reglas de recorte/hook, y este script solo lo ejecuta.

Trabaja por PROYECTO (`--proyecto <id>`, ver proyecto.py): lee el vídeo del
buzón proyectos/<id>/input/ y escribe en proyectos/<id>/transcripciones/<video>/.

Uso:
    python clips.py --proyecto mongemalo "Mi Adicción"   -> su input/Mi Adicción.mp4
    python clips.py --proyecto mongemalo "C:/ruta/video.mp4"   -> ruta concreta
    python clips.py --proyecto x "video" --cortes cortes.json  -> spec explicito
    python clips.py --proyecto x "video" --solo 03_nombre                -> solo ese clip
    python clips.py --proyecto x "video" --solo 03_nombre --umbral 3% --margen 0.3s
                                    -> corrección de silencios de un clip (no toca proyecto.json)
    python clips.py --proyecto x "video" --validar   -> solo valida cortes.json (no corta)
Si solo hay un proyecto, --proyecto se puede omitir. Un vídeo ya aprobado
(_Historico/<id>/<video>/) no se vuelve a cortar salvo con --forzar.

Formato de cortes.json (lista de objetos):
    [
      {"nombre": "01_gancho", "inicio": 42.0, "fin": 66.7,
       "titulo": "La extrana adiccion", "hook_query": "excited entrepreneur"},
      ...
    ]
  - nombre     (obligatorio) -> nombre del clip de salida
  - inicio/fin (obligatorio) -> segundos
  - titulo     (opcional)    -> descriptivo
  - gancho_texto (opcional)  -> texto de gancho en pantalla (2,5 s, franja
                                superior) que quema editar_clips.py; max. 2
                                lineas (~45 car.), con tildes, abre un bucle que
                                el clip cumple. Si falta, el clip sale SIN
                                gancho (con aviso): nunca se usa el titulo.
  - hook_query (opcional)    -> lo usa editar_clips.py para la imagen-gancho
  - frase_viral(opcional)    -> texto VERBATIM mas potente/gancho del clip; lo
                                usa editar_clips.py para guardarlo en el banco de
                                frases virales de Supabase (tabla viral_phrases).
                                Admite tambien angle/virality/category/rationale/
                                tags opcionales por corte. Si falta frase_viral se
                                cae al titulo/hook, y si no hay Supabase no rompe.
Si no se pasa --cortes, se busca en proyectos/<id>/transcripciones/<video>/cortes.json.

Antes de cortar se VALIDA cortes.json (validar.py: nombres, tramos de 15–90 s
sin solapes y ganchos de texto) y, si hay errores, no se corta nada.

Los subtitulos NO se queman aqui. Se anaden UNA sola vez en la edicion final
con la skill Editor_Sergio (b-roll + musica + subs), para no generarlos dos
veces ni acabar con subtitulos duplicados en pantalla.

Pipeline por clip:
  1) ffmpeg  -> recorte + crop vertical 1080x1920
  2) auto-editor (umbral 6%, margen 0.15s, o los `silencios` del proyecto)
     -> quita silencios -> clip final
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

import herramientas
import proyecto
import validar

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


SKIN_MIN_FRAC = 0.20   # fracción mínima de píxeles de piel (YCrCb) en una cara


def _es_piel(color, x, y, w, h) -> bool:
    """¿La detección tiene tono de piel? Filtro YCrCb (el mismo del batch) para
    descartar falsos positivos de Haar (estampados, logos, fondos)."""
    H, W = color.shape[:2]
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(W, int(x + w)), min(H, int(y + h))
    if x1 <= x0 or y1 <= y0:
        return False
    ycc = cv2.cvtColor(color[y0:y1, x0:x1], cv2.COLOR_BGR2YCrCb)
    skin = cv2.inRange(ycc, (0, 133, 77), (255, 173, 127))
    return (skin.mean() / 255.0) > SKIN_MIN_FRAC


def _detectar_cara(gray, color=None, frontal_bruta=None):
    """Mayor cara (x,y,w,h) por Haar frontal; si no hay, perfil (ambos lados).

    Con `color` (el fotograma BGR), solo cuentan las detecciones con tono de
    piel (filtro YCrCb): la cara dominante es la del protagonista, no un falso
    positivo. Sin `color`, como antes. Si se pasa la lista `frontal_bruta`, se
    le añade la mayor cara frontal SIN filtro de piel (si la hay)."""
    def ok(f):
        return color is None or _es_piel(color, *f)

    brutas = list(_HAAR.detectMultiScale(gray, 1.1, 5, minSize=(24, 24)))
    if frontal_bruta is not None and brutas:
        frontal_bruta.append(max(brutas, key=lambda f: f[2] * f[3]))
    faces = [f for f in brutas if ok(f)]
    if faces:
        return max(faces, key=lambda f: f[2] * f[3])
    if _HAAR_PROF is not None and not _HAAR_PROF.empty():
        cand = list(_HAAR_PROF.detectMultiScale(gray, 1.1, 4, minSize=(24, 24)))
        flip = cv2.flip(gray, 1)
        for (x, y, w, h) in _HAAR_PROF.detectMultiScale(flip, 1.1, 4, minSize=(24, 24)):
            cand.append((gray.shape[1] - x - w, y, w, h))  # des-espejar
        cand = [f for f in cand if ok(f)]
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


FFMPEG = herramientas.exigir_ffmpeg()


def resolver_video(arg: str, input_dir: Path) -> tuple[Path, str]:
    """Devuelve (ruta_video, nombre). Acepta ruta concreta o nombre en el
    input/ del proyecto (.mp4 u otra extensión de vídeo)."""
    p = Path(arg)
    if p.suffix and (p.is_absolute() or len(p.parts) > 1):
        return p.resolve(), p.stem
    nombre = p.stem if p.suffix.lower() in proyecto.EXT_VIDEO else arg
    for ext in (".mp4",) + tuple(e for e in proyecto.EXT_VIDEO if e != ".mp4"):
        cand = Path(input_dir) / f"{nombre}{ext}"
        if cand.exists():
            return cand.resolve(), nombre
    return (Path(input_dir) / f"{nombre}.mp4").resolve(), nombre


def cargar_cortes(ruta: Path) -> list[dict]:
    if not ruta.exists():
        raise SystemExit(
            f"[!] Falta el spec de cortes: {ruta}\n"
            f"    Escribe cortes.json (formato en la cabecera de clips.py) leyendo "
            f"<video>.cortes.txt y vuelve a lanzar."
        )
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"[!] {ruta} no es un JSON válido: {e}")
    if not isinstance(data, list) or not data:
        raise SystemExit(f"[!] {ruta} debe ser una lista no vacía de cortes.")
    for i, c in enumerate(data):
        if not isinstance(c, dict) or not all(k in c for k in ("nombre", "inicio", "fin")):
            raise SystemExit(f"[!] Corte #{i} incompleto (requiere nombre, inicio, fin): {c}")
    return data


def validar_cortes(p, base: Path, nombre: str, cortes: list, duracion: float | None,
                   solo: set | None = None) -> bool:
    """Valida cortes.json (validar.py) e imprime errores y avisos. True si vale."""
    res = validar.validar_cortes(cortes, duracion, base / f"{nombre}.json", p.gancho_texto)
    return validar.informar(res, "cortes.json", solo=solo, decir=proyecto.decir)


def run(cmd):
    """Ejecuta sin eco; si falla, solo el nombre del binario y su error (RuntimeError)."""
    return herramientas.ejecutar(cmd)


def probe_dims(video: Path) -> tuple[int, int]:
    """(ancho, alto) de PANTALLA del vídeo (con la rotación aplicada)."""
    return herramientas.dimensiones(video)


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


def muestrear_caras(video: Path, inicio, fin, src_w, src_h, fps=5, brutas=None):
    """Muestrea la cara del hablante a lo largo del tramo (best-effort).

    Devuelve (samples, dur) donde samples es una lista con un elemento por frame
    muestreado: dict {cx, top, fh} en PIXELES del fuente, o None si no hubo cara.
    None global si OpenCV no esta disponible.

    Si se pasa la lista `brutas`, se le añade, por frame, la mayor cara FRONTAL
    sin filtro de piel (mismo formato o None): `construir_segmentos` la usa en
    los planos donde el filtro de piel descarta la cara real (gradación fría o
    contraluz) y deja pasar un falso positivo del fondo (ladrillo, madera).
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
                if brutas is not None:
                    brutas.append(None)
                continue
            H, W = fr.shape[:2]
            sx, sy = src_w / W, src_h / H  # escala a pixeles del fuente
            gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            frontal = []  # mayor cara frontal SIN filtro de piel (la rellena _detectar_cara)
            f = _detectar_cara(gray, fr, frontal_bruta=frontal)
            if f is not None:
                fx, fy, fw, fh = f
                samples.append({"cx": (fx + fw / 2) * sx,
                                "top": fy * sy, "fh": fh * sy})
            else:
                samples.append(None)
            if brutas is not None:
                fb = frontal[0] if frontal else None
                brutas.append(None if fb is None else
                              {"cx": (fb[0] + fb[2] / 2) * sx,
                               "top": fb[1] * sy, "fh": fb[3] * sy})
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
        # Se mide sobre fotogramas reducidos (320 px): mucho más rápido en 4K.
        r = subprocess.run(
            [FFMPEG, "-ss", f"{inicio}", "-t", f"{dur}", "-i", str(video),
             "-vf", f"scale=320:-2,select='gt(scene,{thr})',showinfo",
             "-an", "-sn", "-dn", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        ts = sorted({round(float(x[9:]), 2)
                     for x in re.findall(r"pts_time:[0-9.]+", r.stderr)})
        return [t for t in ts if 0.25 < t < dur - 0.15]
    except Exception:
        return []


BRUTA_MIN_RATIO = 2.0    # caras frontales sin filtro >= 2x las que pasan la piel
BRUTA_MAX_MAD   = 0.08   # y estables: MAD de cx <= 8 % del ancho fuente


def _usar_brutas(caras, brutas, src_w):
    """¿Usar en este plano las caras frontales SIN filtro de piel?

    Solo si el filtro de piel descarta la cara real (gradación fría, contraluz:
    Cr < 133) y deja pasar, como mucho, falsos positivos sueltos del fondo
    (ladrillo, madera): muchas más frontales brutas que filtradas, en una
    posición estable y no más pequeñas. Si la piel funciona, no cambia nada."""
    import statistics
    if len(brutas) < 4 or len(brutas) < BRUTA_MIN_RATIO * max(len(caras), 1):
        return False
    cxs = [c["cx"] for c in brutas]
    med = statistics.median(cxs)
    if statistics.median([abs(x - med) for x in cxs]) > BRUTA_MAX_MAD * src_w:
        return False
    if caras and (statistics.median([c["fh"] for c in brutas])
                  < statistics.median([c["fh"] for c in caras])):
        return False
    return True


def construir_segmentos(samples, dur, src_w, src_h, cortes, brutas=None):
    """Tramos [t0,t1) con un recorte 9:16 por PLANO (bust-crop adaptativo).

    Segmenta por cortes de escena y, en cada plano, usa la MEDIANA de las caras
    detectadas para elegir un recorte estable: cara grande -> ~altura completa;
    cara pequena (plano general) -> zoom al busto (piernas fuera). Un plano sin
    caras cae a altura completa centrada (fallback seguro). Devuelve None si la
    deteccion global es demasiado pobre (el llamador usa el fallback de siempre).
    `brutas` (opcional, de `muestrear_caras`): frontales sin filtro de piel, para
    los planos en que el filtro descarta la cara real (ver `_usar_brutas`).
    """
    if not samples:
        return None
    import statistics
    n = len(samples)
    if brutas is not None and len(brutas) != n:
        brutas = None
    if sum(1 for s in samples if s) < 4 and not (
            brutas and _usar_brutas([s for s in samples if s],
                                    [s for s in brutas if s], src_w)):
        return None
    dt = dur / n
    bordes = [0.0] + list(cortes) + [dur]
    planos = [(bordes[i], bordes[i + 1]) for i in range(len(bordes) - 1)
              if bordes[i + 1] - bordes[i] > 0.05]

    def rect_de_plano(a, b):
        caras = [samples[i] for i in range(n)
                 if samples[i] and a <= (i + 0.5) * dt < b]
        if brutas:
            br = [brutas[i] for i in range(n)
                  if brutas[i] and a <= (i + 0.5) * dt < b]
            if _usar_brutas(caras, br, src_w):
                caras = br
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
    brutas = []
    samples, sdur = muestrear_caras(video, inicio, fin, src_w, src_h, brutas=brutas)
    cortes = detectar_cortes_escena(video, inicio, sdur) if samples else []
    segs = (construir_segmentos(samples, sdur, src_w, src_h, cortes, brutas=brutas)
            if samples else None)

    if segs:
        return _render_segmentado(video, inicio, dur, segs, destino, src_h)

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
    return f"altura completa ({encuadre})"


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
    desc = f"busto {len(segs)} plano(s), {len(zooms)} con zoom"
    print(f"   [encuadre] busto adaptativo: {len(segs)} planos, "
          f"{len(zooms)} con zoom vertical (anti-piernas)")
    if len(segs) == 1:
        _encode_tramo(video, inicio + segs[0][0], dur, segs[0][2], destino)
        return desc
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
    return desc


def escalar_vertical(video: Path, destino: Path, ss: float = 0.0, t: float | None = None):
    """Fuente YA vertical (alto ≥ 1,7 × ancho): solo escala a 1080x1920 (con el
    recorte mínimo para no deformar). Sin reencuadre."""
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    cmd = [FFMPEG, "-y", "-ss", f"{ss}"] + (["-t", f"{t}"] if t else []) + [
        "-i", str(video), "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(destino)]
    run(cmd)
    return "vertical: solo escala"


def quitar_silencios(origen, destino, umbral: str = "6%", margen: str = "0.15s"):
    """auto-editor: ajuste global 6 % / 0,15 s (o el del proyecto)."""
    run([PY, "-m", "auto_editor", str(origen),
         "--edit", f"audio:threshold={umbral}", "--margin", margen,
         "-o", str(destino), "--no-open"])


def main():
    ap = argparse.ArgumentParser(description="Genera clips verticales 9:16 sin silencios.")
    ap.add_argument("video", help="Nombre en el input/ del proyecto o ruta al video.")
    proyecto.add_argumento(ap)
    proyecto.add_salida(ap)
    ap.add_argument("--cortes", help="Ruta al cortes.json (por defecto "
                                     "proyectos/<id>/transcripciones/<video>/cortes.json).")
    ap.add_argument("--validar", action="store_true",
                    help="Solo valida cortes.json (nombres, tramos, ganchos) y sale; no corta.")
    ap.add_argument("--solo", action="append", metavar="NOMBRE",
                    help="Solo este corte (repetible o separado por comas). Para corregir un clip "
                         "sin tocar los demás.")
    ap.add_argument("--umbral", default=None,
                    help="Umbral de silencio SOLO para esta ejecución (p. ej. 3%%); no toca proyecto.json.")
    ap.add_argument("--margen", default=None,
                    help="Margen de silencio SOLO para esta ejecución (p. ej. 0.3s); no toca proyecto.json.")
    ap.add_argument("--forzar", action="store_true",
                    help="Cortar aunque el vídeo ya esté aprobado en _Historico/.")
    ap.add_argument("--keep-tmp", action="store_true", help="No borrar intermedios.")
    args = ap.parse_args()
    p = proyecto.abrir(args.proyecto, "clips", log=not args.validar,
                       quiet=False if args.validar else args.quiet)

    video, nombre = resolver_video(args.video, p.input_dir)
    base = p.transcripciones_dir / nombre
    cortes_path = Path(args.cortes) if args.cortes else (base / "cortes.json")
    cortes = cargar_cortes(cortes_path)
    nombres = [c["nombre"] for c in cortes]
    solo = proyecto.filtrar_solo(nombres, args.solo, "corte") if args.solo else None
    dur_video = herramientas.duracion(video) if video.exists() else None
    if args.validar:
        sys.exit(0 if validar_cortes(p, base, nombre, cortes, dur_video, solo) else 1)

    if not video.exists():
        raise SystemExit(f"[!] No existe el video: {video}")
    arch = p.archivado(nombre)
    if arch and not args.forzar:
        raise SystemExit(f"[!] «{nombre}» ya está aprobado y archivado en {arch}. "
                         f"No se vuelve a cortar (usa --forzar si de verdad hace falta).")
    if not validar_cortes(p, base, nombre, cortes, dur_video, solo):
        raise SystemExit("[!] cortes.json tiene errores: corrígelos y relanza (no se ha cortado nada).")

    salida = base / "clips"
    tmp = salida / "_tmp"
    sil = proyecto.silencios_cli(p.silencios, args.umbral, args.margen)
    if solo is not None:
        cortes = [c for c in cortes if c["nombre"] in solo]
    if (args.umbral or args.margen) and solo is None:
        proyecto.decir("AVISO: --umbral/--margen sin --solo se aplican a TODOS los cortes de esta "
                       "ejecución (no se guardan en proyecto.json).")

    salida.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    src_w, src_h = probe_dims(video)
    vertical = herramientas.es_vertical(src_w, src_h)
    encuadre = ("fuente vertical: solo escala" if vertical else
                "seguimiento de cara ON" if _CV2_OK
                else "OpenCV NO disponible -> recorte centrado (instala "
                     "opencv-python-headless para el seguimiento de cara)")
    print(f"Video: {video}  ({src_w}x{src_h})\n"
          f"Cortes: {cortes_path}  ({len(cortes)} clips"
          f"{', solo ' + ', '.join(sorted(solo)) if solo else ''})\nEncuadre 9:16: {encuadre}\n"
          f"Silencios: umbral {sil['umbral']} · margen {sil['margen']}"
          f"{'' if sil == p.silencios else ' (solo esta ejecución)'}\n")

    hechos, fallos = 0, []
    for c in cortes:
        cn, ini, fin = c["nombre"], float(c["inicio"]), float(c["fin"])
        titulo = c.get("titulo", "")
        print(f"\n=== {cn}  ({ini}s -> {fin}s)  {titulo}")
        vert = tmp / f"{cn}_vert.mp4"
        final = salida / f"{cn}.mp4"
        try:
            if vertical:
                desc = escalar_vertical(video, vert, ss=ini, t=fin - ini)
            else:
                desc = cortar_vertical(video, ini, fin, vert, src_w=src_w, src_h=src_h)
            quitar_silencios(vert, final, umbral=sil["umbral"], margen=sil["margen"])
        except Exception as e:
            fallos.append(cn)
            proyecto.decir(f"FALLO {cn}.mp4 · {herramientas.describir_error(e)} (detalle en el log)")
            continue
        # el clip ha cambiado: los word-timestamps guardados ya no valen
        (salida / f"{cn}.words.json").unlink(missing_ok=True)
        hechos += 1
        d = herramientas.duracion(final)
        print(f"   OK -> {final.name}  (sin subtitulos; los pone Editor_Sergio)")
        proyecto.decir(f"OK {cn}.mp4 · {d:.0f} s (tramo {fin - ini:.0f} s) · {desc}")

    if tmp.exists() and not args.keep_tmp:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"   Intermedios eliminados: {tmp}")

    proyecto.decir(f"RESUMEN clips: {hechos} OK · {len(fallos)} fallo(s)"
                   + (f" ({', '.join(fallos)})" if fallos else "") + f" -> {salida}")
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QC de los finales EXPORTADOS (regla «Exportación y QC» de CLAUDE.md).

Uso:
    python qc.py --proyecto <id> "<video|carpeta>"     -> transcripciones/<v>/finales/
    python qc.py --proyecto <id> "C:/ruta/finales"     -> una carpeta cualquiera
    python qc.py --proyecto <id> "C:/ruta/clip.mp4"    -> un solo archivo
(si no está en transcripciones/, se busca en _Historico/<id>/<v>/finales/)

Por cada MP4, UNA línea:
  - ffprobe: 1080x1920, H.264, fps (igual que la fuente si se encuentra en
    input/ o en _Historico/…/_fuente/), bitrate de vídeo 8–12 Mb/s, AAC 48 kHz
    estéreo y pico de audio por debajo de 0 dBFS (astats);
  - blackdetect=d=0.25 (negros), freezedetect=d=2 (congelados) y
    silencedetect=n=-40dB:d=1.5 (segundos vacíos).
Estado: OK · REVISAR (negros/congelados/silencios: mira esos segundos) ·
FALLA (no cumple la exportación). Sale con código 1 si algún clip FALLA.

Además deja UNA hoja `_qc.jpg` en la carpeta de los finales con el primer y el
último fotograma de cada clip: mírala (gancho en el primero, cola limpia en el
último, restos de superposiciones).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import herramientas
import proyecto

RAIZ = Path(__file__).resolve().parent

BITRATE_MIN, BITRATE_MAX = 8.0, 12.0      # Mb/s (vídeo)
THUMB_W, THUMB_H = 216, 384               # miniaturas de la hoja (1/5 de 1080x1920)

FFMPEG = herramientas.exigir_ffmpeg()
FFPROBE = herramientas.FFPROBE
if not FFPROBE:
    raise SystemExit("[!] qc.py necesita ffprobe (TheDescarga/tools, FFPROBE o el PATH).")


def _fps(s: str | None) -> float | None:
    try:
        f = Fraction(s)
        return float(f) if f > 0 else None
    except Exception:
        return None


def probe(mp4: Path) -> dict:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,"
         "bit_rate,sample_rate,channels:format=duration,bit_rate", "-of", "json", str(mp4)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        data = json.loads(r.stdout or "{}")
    except Exception:
        data = {}
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    dur = float(fmt.get("duration") or 0)
    vbr = float(v.get("bit_rate") or 0)
    if not vbr and fmt.get("bit_rate"):
        vbr = float(fmt["bit_rate"]) - float(a.get("bit_rate") or 0)
    return {"w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
            "vcodec": v.get("codec_name"), "fps": _fps(v.get("avg_frame_rate")) or _fps(v.get("r_frame_rate")),
            "vbr": vbr / 1e6, "acodec": a.get("codec_name"),
            "ar": int(a.get("sample_rate") or 0), "ac": int(a.get("channels") or 0), "dur": dur}


def detectar(mp4: Path) -> dict:
    """Negros, congelados, silencios y pico de audio en una sola pasada."""
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", str(mp4),
         "-vf", "blackdetect=d=0.25,freezedetect=d=2",
         "-af", "silencedetect=n=-40dB:d=1.5,astats=metadata=0",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = r.stderr
    negros = [(float(a), float(b)) for a, b in
              re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", err)]
    f_ini = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", err)]
    f_fin = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", err)]
    congelados = [(a, f_fin[i] if i < len(f_fin) else None) for i, a in enumerate(f_ini)]
    s_ini = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", err)]
    s_fin = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", err)]
    silencios = [(max(a, 0.0), s_fin[i] if i < len(s_fin) else None) for i, a in enumerate(s_ini)]
    picos = [float(x) for x in re.findall(r"Peak level dB:\s*(-?[\d.]+|-inf)", err) if x != "-inf"]
    return {"negros": negros, "congelados": congelados, "silencios": silencios,
            "pico": max(picos) if picos else None}


def fotograma(mp4: Path, ultimo: bool, destino: Path) -> bool:
    if ultimo:
        cmd = [FFMPEG, "-y", "-v", "error", "-sseof", "-0.5", "-i", str(mp4),
               "-update", "1", "-q:v", "3", str(destino)]
    else:
        cmd = [FFMPEG, "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(destino)]
    subprocess.run(cmd, capture_output=True)
    return destino.exists() and destino.stat().st_size > 0


def hoja(filas: list[tuple[str, Path | None, Path | None]], destino: Path) -> None:
    """Una sola imagen: por clip, primer y último fotograma con su nombre."""
    from PIL import Image, ImageDraw, ImageFont
    por_fila = 3 if len(filas) > 2 else max(1, len(filas))
    gap, cab = 16, 34
    celda_w = 2 * THUMB_W + gap
    n_filas = (len(filas) + por_fila - 1) // por_fila
    W = por_fila * celda_w + (por_fila + 1) * gap
    H = n_filas * (THUMB_H + cab) + (n_filas + 1) * gap
    img = Image.new("RGB", (W, H), (24, 24, 24))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(RAIZ / ".claude" / "skills" / "Editor_Sergio" / "fonts"
                                      / "Montserrat-Bold.ttf"), 16)
    except Exception:
        font = ImageFont.load_default()
    for i, (nombre, prim, ult) in enumerate(filas):
        fx, fy = i % por_fila, i // por_fila
        x0 = gap + fx * (celda_w + gap)
        y0 = gap + fy * (THUMB_H + cab + gap)
        etiqueta = nombre if len(nombre) <= 48 else nombre[:45] + "…"
        d.text((x0, y0 + 6), etiqueta, fill=(240, 240, 240), font=font)
        for k, f in enumerate((prim, ult)):
            x = x0 + k * (THUMB_W + gap)
            y = y0 + cab
            if f and f.exists():
                im = Image.open(f).convert("RGB").resize((THUMB_W, THUMB_H))
                img.paste(im, (x, y))
            else:
                d.rectangle([x, y, x + THUMB_W, y + THUMB_H], outline=(200, 60, 60), width=2)
            d.text((x + 6, y + THUMB_H - 22), "inicio" if k == 0 else "final",
                   fill=(255, 220, 0), font=font)
    img.save(destino, quality=88)


def fuente_fps(p, v: str, clip: str) -> float | None:
    """fps de la fuente del clip: input/<v>.<ext>, input/<v>/<clip>.mp4 o lo mismo
    en _Historico/<id>/<v>/_fuente/."""
    cands = []
    for base in (p.input_dir, p.historico_dir / v / "_fuente"):
        for ext in proyecto.EXT_CLIPS:
            cands.append(base / v / f"{clip}{ext}")
            cands.append(base / f"{clip}{ext}")
        cands += [base / f"{v}{ext}" for ext in (".mp4", ".mkv", ".mov", ".webm")]
    for c in cands:
        if c.is_file():
            return probe(c)["fps"]
    return None


def _tramos(xs, maxn=3) -> str:
    out = []
    for a, b in xs[:maxn]:
        out.append(f"{a:.1f}-{b:.1f}s" if b is not None else f"{a:.1f}s-fin")
    return ", ".join(out) + ("…" if len(xs) > maxn else "")


def resolver_objetivo(p, arg: str) -> tuple[list[Path], Path, str]:
    """(mp4s, carpeta de la hoja, nombre del vídeo/carpeta para buscar la fuente)."""
    a = Path(arg)
    if a.is_file():
        return [a], a.parent, a.parent.parent.name if a.parent.name == "finales" else a.stem
    if a.is_dir() and (a.is_absolute() or len(a.parts) > 1):
        fin = a / "finales" if (a / "finales").is_dir() else a
        v = fin.parent.name if fin.name == "finales" else fin.name
        return sorted(fin.glob("*.mp4")), fin, v
    v = arg[:-4] if arg.lower().endswith(".mp4") else arg
    for fin in (p.transcripciones_dir / v / "finales", p.historico_dir / v / "finales"):
        if fin.is_dir():
            return sorted(fin.glob("*.mp4")), fin, v
    raise SystemExit(f"[!] No hay finales de «{v}» en {p.transcripciones_dir} ni en {p.historico_dir}.")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="QC de los finales exportados.")
    ap.add_argument("objetivo", help="Vídeo o carpeta (transcripciones/<v>/finales/) o una ruta.")
    proyecto.add_argumento(ap)
    args = ap.parse_args()
    p = proyecto.resolver(args.proyecto)

    mp4s, carpeta, v = resolver_objetivo(p, args.objetivo)
    if not mp4s:
        raise SystemExit(f"[!] No hay MP4 en {carpeta}.")
    print(f"QC de {len(mp4s)} final(es) en {carpeta}\n")
    tmp = Path(tempfile.mkdtemp(prefix="qc_"))
    filas, fallan, revisar = [], 0, 0
    try:
        for i, mp4 in enumerate(mp4s):
            pr = probe(mp4)
            det = detectar(mp4)
            ffps = fuente_fps(p, v, mp4.stem)
            prim, ult = tmp / f"{i:03d}_a.jpg", tmp / f"{i:03d}_b.jpg"
            filas.append((mp4.name, prim if fotograma(mp4, False, prim) else None,
                          ult if fotograma(mp4, True, ult) else None))

            fallos = []
            if (pr["w"], pr["h"]) != (1080, 1920):
                fallos.append(f"{pr['w']}x{pr['h']}≠1080x1920")
            if pr["vcodec"] != "h264":
                fallos.append(f"vídeo {pr['vcodec']}≠h264")
            if ffps and pr["fps"] and abs(ffps - pr["fps"]) > 0.05:
                fallos.append(f"fps {pr['fps']:.2f}≠fuente {ffps:.2f}")
            if not (BITRATE_MIN <= pr["vbr"] <= BITRATE_MAX):
                fallos.append(f"bitrate {pr['vbr']:.1f} fuera de {BITRATE_MIN:.0f}–{BITRATE_MAX:.0f}")
            if pr["acodec"] != "aac" or pr["ar"] != 48000 or pr["ac"] != 2:
                fallos.append(f"audio {pr['acodec']} {pr['ar']} Hz {pr['ac']}ch≠aac 48000 2ch")
            if det["pico"] is None or det["pico"] >= 0.0:
                fallos.append(f"pico {det['pico']} dBFS ≥ 0")
            avisos = []
            if det["negros"]:
                avisos.append(f"negro {len(det['negros'])} ({_tramos(det['negros'])})")
            if det["congelados"]:
                avisos.append(f"congelado {len(det['congelados'])} ({_tramos(det['congelados'])})")
            if det["silencios"]:
                avisos.append(f"silencio {len(det['silencios'])} ({_tramos(det['silencios'])})")

            estado = "FALLA" if fallos else ("REVISAR" if avisos else "OK")
            fallan += bool(fallos)
            revisar += bool(avisos) and not fallos
            fps_txt = (f"{pr['fps']:.2f}fps" if pr["fps"] else "¿fps?") + (
                "(=fuente)" if ffps and pr["fps"] and abs(ffps - pr["fps"]) <= 0.05 else
                "" if ffps else "(fuente ¿?)")
            pico = f"{det['pico']:.1f}" if det["pico"] is not None else "¿?"
            linea = (f"{estado:<7} {mp4.name}  {pr['dur']:.1f}s  {pr['w']}x{pr['h']} {pr['vcodec']} {fps_txt} "
                     f"{pr['vbr']:.1f}Mb/s {pr['acodec']} {pr['ar'] // 1000 if pr['ar'] else '?'}kHz "
                     f"{pr['ac']}ch pico {pico}dBFS")
            linea += " · " + (" · ".join(avisos) if avisos else "sin negros/congelados/silencios")
            if fallos:
                linea += "  [" + "; ".join(fallos) + "]"
            print(linea, flush=True)

        sheet = carpeta / "_qc.jpg"
        hoja(filas, sheet)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(mp4s) - fallan - revisar} OK · {revisar} REVISAR · {fallan} FALLA")
    print(f"Hoja de fotogramas (inicio/final): {sheet}  <- mírala")
    return 1 if fallan else 0


if __name__ == "__main__":
    sys.exit(main())

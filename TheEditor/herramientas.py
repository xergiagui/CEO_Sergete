#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Binarios comunes de TheEditor: UN solo ffmpeg/ffprobe para todos los scripts
(transcribir, clips, editar_clips, batch, qc, indexar_broll y pipeline_core).

Orden de búsqueda:
    1) variable de entorno FFMPEG / FFPROBE (ruta al ejecutable);
    2) ..\\TheDescarga\\tools\\ffmpeg.exe / ffprobe.exe (build completo con libass);
    3) imageio-ffmpeg (solo trae ffmpeg);
    4) el PATH.
Si no hay ffprobe, `dimensiones()` y `duracion()` leen la cabecera con ffmpeg.

`dimensiones()` devuelve el tamaño de PANTALLA (con la rotación aplicada): un
.MOV de móvil codificado 1920x1080 con rotación -90 es 1080x1920 en vertical.
ffmpeg endereza solo al decodificar (autorotate), así que los recortes se
calculan sobre estas dimensiones.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DESCARGA_TOOLS = RAIZ.parent / "TheDescarga" / "tools"
_EXE = ".exe" if sys.platform.startswith("win") else ""


def _buscar(nombre: str) -> str | None:
    env = os.environ.get(nombre.upper())
    if env and Path(env).is_file():
        return env
    p = DESCARGA_TOOLS / f"{nombre}{_EXE}"
    if p.is_file():
        return str(p)
    if nombre == "ffmpeg":
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    return shutil.which(nombre)


FFMPEG = _buscar("ffmpeg")
FFPROBE = _buscar("ffprobe")
if FFPROBE is None and FFMPEG:
    _hermano = Path(FFMPEG).with_name(f"ffprobe{_EXE}")
    FFPROBE = str(_hermano) if _hermano.is_file() else None


def exigir_ffmpeg() -> str:
    if not FFMPEG:
        raise SystemExit("[!] No encuentro ffmpeg (ni FFMPEG, ni TheDescarga/tools, "
                         "ni imageio-ffmpeg, ni el PATH).")
    return FFMPEG


def ejecutar(cmd, cwd=None, cola: int = 1500) -> subprocess.CompletedProcess:
    """Ejecuta sin eco. Si falla, imprime solo el nombre del binario y la cola
    de su salida, y lanza RuntimeError."""
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        nombre = Path(str(cmd[0])).name
        detalle = ((r.stderr or "") + (r.stdout or ""))[-cola:].strip()
        print(f"   [!] {nombre} falló (código {r.returncode}):\n{detalle}", flush=True)
        raise RuntimeError(f"{nombre} falló (código {r.returncode})")
    return r


def describir_error(e: BaseException) -> str:
    """Error en una línea, sin rutas ni comandos completos (para la consola)."""
    if isinstance(e, subprocess.CalledProcessError):
        cmd = e.cmd if isinstance(e.cmd, (list, tuple)) else str(e.cmd).split()
        return f"{Path(str(cmd[0])).name} falló (código {e.returncode})"
    return f"{type(e).__name__}: {str(e)[:200]}"


def _cabecera(video: Path) -> str:
    r = subprocess.run([exigir_ffmpeg(), "-hide_banner", "-i", str(video)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stderr or ""


def info_video(video: Path) -> dict:
    """{w, h (de pantalla), rotacion, dur} del vídeo; ceros si no se puede leer."""
    out = {"w": 0, "h": 0, "rotacion": 0, "dur": 0.0}
    if FFPROBE:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height:stream_side_data=rotation:format=duration",
             "-of", "json", str(video)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            data = json.loads(r.stdout or "{}")
            st = (data.get("streams") or [{}])[0]
            out["w"], out["h"] = int(st.get("width") or 0), int(st.get("height") or 0)
            for sd in st.get("side_data_list") or []:
                if "rotation" in sd:
                    out["rotacion"] = int(float(sd["rotation"]))
            out["dur"] = float((data.get("format") or {}).get("duration") or 0.0)
        except Exception:
            pass
    else:
        e = _cabecera(video)
        m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", e)
        if m:
            out["w"], out["h"] = int(m.group(1)), int(m.group(2))
        m = re.search(r"rotation of (-?[\d.]+) degrees", e)
        if m:
            out["rotacion"] = int(float(m.group(1)))
        m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", e)
        if m:
            out["dur"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    if abs(out["rotacion"]) % 180 == 90:
        out["w"], out["h"] = out["h"], out["w"]
    return out


def dimensiones(video: Path) -> tuple[int, int]:
    """(ancho, alto) de pantalla, con la rotación aplicada; (0, 0) si falla."""
    i = info_video(video)
    return i["w"], i["h"]


def duracion(video: Path) -> float:
    """Duración en segundos (0.0 si falla)."""
    return info_video(video)["dur"]


def es_vertical(w: int, h: int) -> bool:
    """Fuente ya vertical (alto ≥ 1,7 × ancho): basta con escalar a 1080x1920."""
    return bool(w and h and h >= 1.7 * w)

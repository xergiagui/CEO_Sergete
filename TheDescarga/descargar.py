"""Wrapper de yt-dlp sin pasar por cmd (URLs con = y & seguras).

Uso:  py descargar.py "URL" [best|audio|1080p|720p|480p|360p] [proyecto] [--extra-yt-dlp-args ...]
Igual que descargar.bat: imprime solo la ruta final del archivo.
Variables opcionales: DESCARGA_SIMULAR=1 -> no descarga, imprime el título.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
YTDLP = AQUI / "tools" / "yt-dlp.exe"


def main(argv):
    if not argv:
        print('Uso: py descargar.py "URL" [best|audio|1080p|720p|480p|360p] [proyecto]')
        return 1
    url = argv[0]
    modo = (argv[1] if len(argv) > 1 else "best").lower()
    proy = argv[2] if len(argv) > 2 else "_general"
    if not YTDLP.exists():
        print(f'[ERROR] No se encuentra yt-dlp en "{YTDLP}".')
        return 1
    if modo != "audio" and modo != "best" and not re.fullmatch(r"\d{3,4}p", modo):
        print(f"[ERROR] Modo no válido: {modo!r} (best|audio|1080p|720p|480p|360p).")
        return 1
    out = AQUI / "descargas" / proy
    simular = os.environ.get("DESCARGA_SIMULAR") == "1"
    if not simular:
        out.mkdir(parents=True, exist_ok=True)
    cmd = [str(YTDLP), "-o", str(out / "%(title)s.%(ext)s"), "--no-playlist"]
    if modo == "audio":
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    elif modo == "best":
        cmd += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]
    else:
        h = modo[:-1]
        cmd += ["-f", f"bv*[height<={h}]+ba/b[height<={h}]", "--merge-output-format", "mp4"]
    if simular:
        cmd += ["--simulate", "--print", "title"]
    else:
        cmd += ["--print", "after_move:filepath"]
    cmd.append(url)
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"[ERROR] yt-dlp terminó con código {rc}.")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""
bootstrap.py — instala las deps de viral-pipeline en un venv aislado.

Cross-platform: macOS, Linux, Windows. Idempotente.

Ejecutar:
    python3 bootstrap.py    (Mac/Linux)
    python bootstrap.py     (Windows)

Output: imprime "BOOTSTRAP_OK" al final si todo fue bien.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


VPDIR = Path.home() / ".viral-pipeline"
VENV = VPDIR / "venv"

# Detectar binarios según OS
if os.name == "nt":  # Windows
    PY = VENV / "Scripts" / "python.exe"
    PIP = VENV / "Scripts" / "pip.exe"
else:  # Mac / Linux
    PY = VENV / "bin" / "python3"
    PIP = VENV / "bin" / "pip"


def run(cmd, check=True, capture=False):
    """Wrapper subprocess.run que acepta str path objects."""
    cmd = [str(c) for c in cmd]
    return subprocess.run(
        cmd, check=check,
        capture_output=capture, text=True,
    )


def main():
    VPDIR.mkdir(exist_ok=True)

    # 1. Crear venv si no existe
    if not PY.exists():
        print(f"[bootstrap] creando venv en {VENV}...")
        run([sys.executable, "-m", "venv", str(VENV)])

    # 2. Pip upgrade silencioso (ignora si falla)
    try:
        run([PIP, "install", "--quiet", "--upgrade", "pip"], check=False, capture=True)
    except Exception:
        pass

    # 3. Instalar deps Python (idempotente — pip detecta lo ya instalado)
    print("[bootstrap] instalando deps Python...")
    run([
        PIP, "install", "--quiet",
        "httpx", "faster-whisper", "Pillow", "imageio-ffmpeg", "yt-dlp",
    ])

    # 4. Resolver el ffmpeg bundled
    print("[bootstrap] verificando ffmpeg+libass...")
    result = run(
        [PY, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
        capture=True,
    )
    ff = Path(result.stdout.strip())
    if not ff.exists():
        print(f"[bootstrap] ERROR: ffmpeg bundled no encontrado en {ff}", file=sys.stderr)
        sys.exit(1)

    # 5. Verificar libass en el ffmpeg bundled
    filters = run([ff, "-hide_banner", "-filters"], capture=True)
    has_ass = any(
        ln.split()[1:2] == ["ass"]
        for ln in filters.stdout.splitlines() if ln.strip()
    )
    if not has_ass:
        print("[bootstrap] ERROR: el ffmpeg bundled NO incluye libass.", file=sys.stderr)
        print(f"  binary: {ff}", file=sys.stderr)
        sys.exit(1)

    # 6. Verificar yt-dlp
    try:
        run([PY, "-m", "yt_dlp", "--version"], capture=True)
    except subprocess.CalledProcessError:
        print("[bootstrap] ERROR: yt-dlp no funciona en el venv", file=sys.stderr)
        sys.exit(1)

    print("BOOTSTRAP_OK")
    print(f"  venv:    {VENV}")
    print(f"  python:  {PY}")
    print(f"  ffmpeg:  {ff}")


if __name__ == "__main__":
    main()

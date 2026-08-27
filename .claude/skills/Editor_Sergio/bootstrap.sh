#!/bin/bash
# bootstrap.sh — instala todas las deps de viral-pipeline en un venv aislado.
# Idempotente: si ya existe el venv y las deps están OK, no hace nada.
#
# Crea:
#   ~/.viral-pipeline/venv/         → entorno Python aislado
#   ~/.viral-pipeline/env.json      → (creado por setup después)
#
# Ejecutar:
#   bash bootstrap.sh
#
# Output: imprime "BOOTSTRAP_OK" al final si todo fue bien.

set -e

VPDIR="$HOME/.viral-pipeline"
VENV="$VPDIR/venv"
PY="$VENV/bin/python3"
PIP="$VENV/bin/pip"

mkdir -p "$VPDIR"

# 1. Crear venv si no existe
if [ ! -x "$PY" ]; then
    echo "[bootstrap] creando venv en $VENV..."
    python3 -m venv "$VENV"
fi

# 2. Pip upgrade (silencioso)
"$PIP" install --quiet --upgrade pip >/dev/null 2>&1 || true

# 3. Instalar deps Python (idempotente — pip detecta lo ya instalado)
echo "[bootstrap] instalando deps Python..."
"$PIP" install --quiet \
    httpx \
    faster-whisper \
    Pillow \
    imageio-ffmpeg \
    yt-dlp \
    fastembed

# 4. Verificar que el ffmpeg bundled tiene libass
echo "[bootstrap] verificando ffmpeg+libass..."
FF=$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
if ! "$FF" -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx "ass"; then
    echo "[bootstrap] ERROR: el ffmpeg bundled NO tiene libass"
    echo "  binary: $FF"
    exit 1
fi

# 5. Verificar yt-dlp
"$PY" -m yt_dlp --version >/dev/null 2>&1 || { echo "[bootstrap] ERROR: yt-dlp no funciona"; exit 1; }

echo "BOOTSTRAP_OK"
echo "  venv:    $VENV"
echo "  python:  $PY"
echo "  ffmpeg:  $FF"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 1 del flujo — Transcripcion.

Convierte el audio a WAV 16 kHz mono y lo transcribe con whisper.cpp usando el
modelo large-v3 con DTW activado (-dtw large.v3 -nfa). 100% local.

Por cada archivo genera en transcripciones/<nombre>/:
    - <nombre>.txt   -> texto plano
    - <nombre>.srt   -> subtitulos con marcas de tiempo (DTW)
    - <nombre>.json  -> JSON completo (tokens/tiempos)

Uso:
    python transcribir.py                      -> todo lo que haya en input/
    python transcribir.py "input/video.mp4"    -> un archivo concreto
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "input"
SALIDA = RAIZ / "transcripciones"
EXTENSIONES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4a", ".mp3", ".wav", ".flac", ".ogg", ".aac"}

FFMPEG = r"C:\Users\ico858\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-125875-g5d4d3bdc61-win64-gpl\bin\ffmpeg.exe"
WHISPER_CLI = RAIZ / "whisper" / "bin" / "whisper-cli.exe"
MODELO = RAIZ / "whisper" / "models" / "ggml-large-v3.bin"


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit(f"[!] Fallo: {Path(str(cmd[0])).name}")
    return r


def a_wav_16k_mono(origen: Path, destino: Path):
    """Convierte a WAV 16 kHz mono PCM (lo que espera whisper.cpp)."""
    run([FFMPEG, "-y", "-i", str(origen), "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", str(destino)])


def transcribir(origen: Path, idioma: str = "es"):
    print(f"\n=> Paso 1 — Transcribiendo: {origen.name}")
    base = SALIDA / origen.stem
    base.mkdir(parents=True, exist_ok=True)

    # whisper-cli usa fopen ANSI: las tildes de la ruta ('Transcripción',
    # 'Adicción') lo rompen. Trabajamos en un area ASCII bajo whisper/_work y
    # pasamos rutas RELATIVAS ASCII con cwd=RAIZ; luego movemos a `base`.
    work = RAIZ / "whisper" / "_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    wav = work / "audio.wav"

    print("   [1/2] convirtiendo a WAV 16 kHz mono...")
    a_wav_16k_mono(origen, wav)  # ffmpeg maneja bien las tildes

    print("   [2/2] whisper.cpp large-v3 + DTW (-dtw large.v3 -nfa)...")
    run([str(WHISPER_CLI),
         "-m", "whisper/models/ggml-large-v3.bin",
         "-f", "whisper/_work/audio.wav",
         "-l", idioma,
         "-dtw", "large.v3", "-nfa",
         "-t", str(max(4, os.cpu_count() or 4)),
         "-otxt", "-osrt", "-oj",
         "-of", "whisper/_work/out"],
        cwd=str(RAIZ))

    # mover resultados a la carpeta final (con tildes) renombrando al stem
    for ext in (".txt", ".srt", ".json"):
        src = work / f"out{ext}"
        if src.exists():
            shutil.move(str(src), str(base / f"{origen.stem}{ext}"))
    shutil.rmtree(work, ignore_errors=True)  # limpiar intermedios (WAV incluido)
    print(f"   OK -> {base}/  ({origen.stem}.txt + .srt + .json)")


def main():
    parser = argparse.ArgumentParser(description="Paso 1 — Transcripcion con whisper.cpp large-v3 + DTW")
    parser.add_argument("archivo", nargs="?", help="Archivo concreto (opcional)")
    parser.add_argument("--idioma", default="es", help="Codigo de idioma (def: es)")
    args = parser.parse_args()

    if not WHISPER_CLI.exists():
        raise SystemExit(f"[!] No existe whisper-cli: {WHISPER_CLI}")
    if not MODELO.exists():
        raise SystemExit(f"[!] No existe el modelo: {MODELO}")

    if args.archivo:
        objetivos = [Path(args.archivo)]
    else:
        ENTRADA.mkdir(exist_ok=True)
        objetivos = sorted(p for p in ENTRADA.iterdir()
                           if p.is_file() and p.suffix.lower() in EXTENSIONES)
    if not objetivos:
        raise SystemExit(f"[!] No hay archivos para transcribir en {ENTRADA}")

    for ruta in objetivos:
        if not ruta.exists():
            print(f"[!] No existe: {ruta}")
            continue
        transcribir(ruta, args.idioma)

    print(f"\nListo. Transcripciones en: {SALIDA}")


if __name__ == "__main__":
    main()

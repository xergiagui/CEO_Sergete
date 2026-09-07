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

Vídeos largos: para que la transcripción no se corte por el límite de tiempo de
las tareas en segundo plano (~45 min), si el audio supera --umbral-min (def 35)
se trocea automáticamente en fragmentos de --chunk-min (def 10). Cada fragmento
se transcribe por separado (large-v3, SIN DTW: basta el timing a nivel de frase
para elegir cortes) y luego se FUSIONAN los tres formatos aplicando el offset de
tiempo de cada fragmento. La salida es idéntica en formato a la de un vídeo corto.

Uso:
    python transcribir.py                      -> todo lo que haya en input/
    python transcribir.py "input/video.mp4"    -> un archivo concreto
    python transcribir.py "input/largo.mp4" --umbral-min 35 --chunk-min 10
"""
import argparse
import json
import math
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
FFPROBE = str(Path(FFMPEG).with_name("ffprobe.exe"))
WHISPER_CLI = RAIZ / "whisper" / "bin" / "whisper-cli.exe"
MODELO = RAIZ / "whisper" / "models" / "ggml-large-v3.bin"

# Troceo automático de vídeos largos (evita que whisper se corte por el límite
# de tiempo de las tareas en segundo plano). Valores por defecto sensatos.
UMBRAL_TROCEO_MIN = 35   # a partir de esta duración (min) se trocea
CHUNK_MIN = 10           # duración (min) de cada fragmento


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


def duracion_seg(wav: Path) -> float:
    """Duración en segundos del audio (ffprobe)."""
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(wav)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _ms_a_ts(ms: int) -> str:
    """Milisegundos -> 'HH:MM:SS,mmm' (formato SRT / whisper)."""
    h, ms = divmod(int(ms), 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def whisper_cli(wav_rel: str, out_rel: str, idioma: str, dtw: bool, formatos):
    """Ejecuta whisper.cpp large-v3 sobre un WAV (rutas RELATIVAS ASCII, cwd=RAIZ).

    dtw=True  -> timing por palabra (-dtw large.v3), como en vídeos cortos.
    dtw=False -> más rápido, timing a nivel de frase (para fragmentos largos).
    formatos  -> subconjunto de {'txt','srt','json'} a emitir.
    """
    cmd = [str(WHISPER_CLI),
           "-m", "whisper/models/ggml-large-v3.bin",
           "-f", wav_rel,
           "-l", idioma]
    if dtw:
        cmd += ["-dtw", "large.v3"]
    cmd += ["-nfa", "-t", str(max(4, os.cpu_count() or 4))]
    if "txt" in formatos:
        cmd.append("-otxt")
    if "srt" in formatos:
        cmd.append("-osrt")
    if "json" in formatos:
        cmd.append("-oj")
    cmd += ["-of", out_rel]
    run(cmd, cwd=str(RAIZ))


def escribir_srt(destino: Path, segmentos: list):
    """Escribe un .srt idéntico en formato al de whisper.cpp (CRLF, texto con el
    espacio inicial tal cual, línea en blanco entre bloques)."""
    lineas = []
    for i, s in enumerate(segmentos, 1):
        lineas.append(str(i))
        lineas.append(f"{s['timestamps']['from']} --> {s['timestamps']['to']}")
        lineas.append(s["text"])
        lineas.append("")
    destino.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8", newline="")


def escribir_txt(destino: Path, segmentos: list):
    """Escribe un .txt idéntico en formato al de whisper.cpp (una frase por
    línea, CRLF, sin el espacio inicial)."""
    lineas = [s["text"].strip() for s in segmentos]
    destino.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8", newline="")


def transcribir(origen: Path, idioma: str = "es",
                umbral_seg: float = UMBRAL_TROCEO_MIN * 60,
                chunk_seg: float = CHUNK_MIN * 60):
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

    dur = duracion_seg(wav)

    if dur <= umbral_seg:
        # ---- Vídeo corto: comportamiento de siempre (una sola pasada + DTW) ----
        print("   [2/2] whisper.cpp large-v3 + DTW (-dtw large.v3 -nfa)...")
        whisper_cli("whisper/_work/audio.wav", "whisper/_work/out",
                    idioma, dtw=True, formatos=("txt", "srt", "json"))
        # mover resultados a la carpeta final (con tildes) renombrando al stem
        for ext in (".txt", ".srt", ".json"):
            src = work / f"out{ext}"
            if src.exists():
                shutil.move(str(src), str(base / f"{origen.stem}{ext}"))
    else:
        # ---- Vídeo largo: trocear, transcribir por fragmentos y fusionar ----
        n = math.ceil(dur / chunk_seg)
        print(f"   [2/2] audio largo ({dur/60:.1f} min > {umbral_seg/60:.0f} min): "
              f"troceo en {n} fragmentos de ~{chunk_seg/60:.0f} min "
              f"(large-v3 sin DTW, timing por frase)...")

        template = None       # metadatos (systeminfo/model/params/result) del 1er trozo
        segmentos = []        # transcripción fusionada con offsets globales
        for i in range(n):
            off_seg = i * chunk_seg
            off_ms = int(round(off_seg * 1000))
            chunk_wav = work / "chunk.wav"
            # extraer el fragmento del WAV ya normalizado (pcm -> copia exacta)
            run([FFMPEG, "-y", "-ss", f"{off_seg:.3f}", "-i", str(wav),
                 "-t", f"{chunk_seg:.3f}", "-c", "copy", str(chunk_wav)])
            print(f"      - fragmento {i+1}/{n} (offset {off_seg/60:.1f} min)...")
            whisper_cli("whisper/_work/chunk.wav", "whisper/_work/cout",
                        idioma, dtw=False, formatos=("json",))
            data = json.loads((work / "cout.json").read_text(encoding="utf-8"))
            if template is None:
                template = data
            for s in data.get("transcription", []):
                ns = dict(s)  # preserva claves/orden que emita whisper
                a = s["offsets"]["from"] + off_ms
                b = s["offsets"]["to"] + off_ms
                ns["offsets"] = {"from": a, "to": b}
                ns["timestamps"] = {"from": _ms_a_ts(a), "to": _ms_a_ts(b)}
                segmentos.append(ns)
            # limpiar parciales del fragmento antes del siguiente
            for p in (chunk_wav, work / "cout.json"):
                p.unlink(missing_ok=True)

        # escribir los tres formatos fusionados en la carpeta final
        template = template or {"transcription": []}
        template["transcription"] = segmentos
        (base / f"{origen.stem}.json").write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        escribir_srt(base / f"{origen.stem}.srt", segmentos)
        escribir_txt(base / f"{origen.stem}.txt", segmentos)

    shutil.rmtree(work, ignore_errors=True)  # limpiar intermedios (WAV incluido)
    print(f"   OK -> {base}/  ({origen.stem}.txt + .srt + .json)")


def main():
    parser = argparse.ArgumentParser(description="Paso 1 — Transcripcion con whisper.cpp large-v3 + DTW")
    parser.add_argument("archivo", nargs="?", help="Archivo concreto (opcional)")
    parser.add_argument("--idioma", default="es", help="Codigo de idioma (def: es)")
    parser.add_argument("--umbral-min", type=float, default=UMBRAL_TROCEO_MIN,
                        help=f"Duracion (min) a partir de la cual se trocea (def: {UMBRAL_TROCEO_MIN})")
    parser.add_argument("--chunk-min", type=float, default=CHUNK_MIN,
                        help=f"Duracion (min) de cada fragmento al trocear (def: {CHUNK_MIN})")
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

    umbral_seg = args.umbral_min * 60
    chunk_seg = args.chunk_min * 60
    for ruta in objetivos:
        if not ruta.exists():
            print(f"[!] No existe: {ruta}")
            continue
        transcribir(ruta, args.idioma, umbral_seg, chunk_seg)

    print(f"\nListo. Transcripciones en: {SALIDA}")


if __name__ == "__main__":
    main()

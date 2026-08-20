#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 3 del flujo: a partir del video original y los momentos con mas gancho,
genera clips verticales (9:16) y les quita los silencios con auto-editor.

Los subtitulos NO se queman aqui. Se anaden UNA sola vez en la edicion final
con la skill Editor_Sergio (b-roll + musica + subs), para no generarlos dos
veces ni acabar con subtitulos duplicados en pantalla.

Pipeline por clip:
  1) ffmpeg  -> recorte + crop vertical 1080x1920
  2) auto-editor (umbral 8%, margen 0.1s) -> quita silencios -> clip final
"""
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
NOMBRE = "Mi Adicción"
VIDEO = RAIZ / "input" / f"{NOMBRE}.mp4"
SALIDA = RAIZ / "transcripciones" / NOMBRE / "clips"
TMP = SALIDA / "_tmp"

FFMPEG = r"C:\Users\ico858\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-125875-g5d4d3bdc61-win64-gpl\bin\ffmpeg.exe"
PY = sys.executable

# (nombre, inicio_seg, fin_seg, titulo)  — 6 momentos (video ~16.5min, ~1/3min)
CLIPS = [
    ("01_adiccion_emprendedores", 42.0,  66.7, "La extrana adiccion de los emprendedores"),
    ("02_empresa_como_bebe",      88.7, 116.5, "Una empresa es como un bebe"),
    ("03_matrimonio_vs_negocio", 158.6, 180.8, "Enamorate de tu negocio"),
    ("04_no_coquetear",          299.4, 318.5, "No coquetees con ideas nuevas"),
    ("05_cocacola_new_coke",     645.7, 675.4, "La marca: el caso New Coke"),
    ("06_migracion_caos",        787.4, 818.1, "La migracion que fue un caos"),
]


def run(cmd):
    print("   $", " ".join(str(c) for c in cmd[:2]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(f"[!] Fallo: {cmd[0]}")
    return r


def cortar_vertical(inicio, fin, destino):
    dur = fin - inicio
    vf = "crop=trunc(ih*9/16/2)*2:ih,scale=1080:1920,setsar=1"
    run([FFMPEG, "-y", "-ss", f"{inicio}", "-t", f"{dur}", "-i", str(VIDEO),
         "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(destino)])


def quitar_silencios(origen, destino):
    run([PY, "-m", "auto_editor", str(origen),
         "--edit", "audio:threshold=8%", "--margin", "0.1s",
         "-o", str(destino), "--no-open"])


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    for nombre, ini, fin, titulo in CLIPS:
        print(f"\n=== {nombre}  ({ini}s -> {fin}s)  {titulo}")
        vert = TMP / f"{nombre}_vert.mp4"
        final = SALIDA / f"{nombre}.mp4"

        cortar_vertical(ini, fin, vert)
        quitar_silencios(vert, final)
        print(f"   OK -> {final.name}  (sin subtitulos; los pone Editor_Sergio)")

    # limpiar intermedios (siempre por defecto)
    if TMP.exists():
        shutil.rmtree(TMP, ignore_errors=True)
        print(f"   Intermedios eliminados: {TMP}")

    print(f"\nListo. Clips (sin subs) en: {SALIDA}")


if __name__ == "__main__":
    main()

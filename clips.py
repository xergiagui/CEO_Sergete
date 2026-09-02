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
Si no se pasa --cortes, se busca en transcripciones/<video>/cortes.json.

Los subtitulos NO se queman aqui. Se anaden UNA sola vez en la edicion final
con la skill Editor_Sergio (b-roll + musica + subs), para no generarlos dos
veces ni acabar con subtitulos duplicados en pantalla.

Pipeline por clip:
  1) ffmpeg  -> recorte + crop vertical 1080x1920
  2) auto-editor (umbral 8%, margen 0.1s) -> quita silencios -> clip final
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

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


def cortar_vertical(video: Path, inicio, fin, destino):
    dur = float(fin) - float(inicio)
    vf = "crop=trunc(ih*9/16/2)*2:ih,scale=1080:1920,setsar=1"
    run([FFMPEG, "-y", "-ss", f"{inicio}", "-t", f"{dur}", "-i", str(video),
         "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(destino)])


def quitar_silencios(origen, destino):
    run([PY, "-m", "auto_editor", str(origen),
         "--edit", "audio:threshold=8%", "--margin", "0.1s",
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
    print(f"Video: {video}\nCortes: {cortes_path}  ({len(cortes)} clips)\n")

    for c in cortes:
        cn, ini, fin = c["nombre"], c["inicio"], c["fin"]
        titulo = c.get("titulo", "")
        print(f"\n=== {cn}  ({ini}s -> {fin}s)  {titulo}")
        vert = tmp / f"{cn}_vert.mp4"
        final = salida / f"{cn}.mp4"
        cortar_vertical(video, ini, fin, vert)
        quitar_silencios(vert, final)
        print(f"   OK -> {final.name}  (sin subtitulos; los pone Editor_Sergio)")

    if tmp.exists() and not args.keep_tmp:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"   Intermedios eliminados: {tmp}")

    print(f"\nListo. Clips (sin subs) en: {salida}")


if __name__ == "__main__":
    main()

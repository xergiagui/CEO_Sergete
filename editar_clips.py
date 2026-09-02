#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 4 — Edicion final con la skill Editor_Sergio (solo Fase C).

GENERICO: funciona con cualquier video. La imagen-gancho de cada clip se toma
del `hook_query` del cortes.json (el mismo que uso clips.py); si un clip no lo
trae, se deriva del nombre. Asi el flujo es 100% automatico sin tocar codigo.

Por cada clip de transcripciones/<video>/clips/ aplica:
  gancho (imagen libre online) + b-roll local (superposiciones/) + musica local
  (musicas/) + de-click + subtitulos palabra a palabra (una sola vez, enmascarando
  palabrotas).

Trabaja en una carpeta ASCII (whisper/_edit) para evitar problemas de rutas con
tildes en el filtro de subtitulos de ffmpeg. Salida en transcripciones/<video>/finales/.

Uso:
    python editar_clips.py "Mi Adicción"
    python editar_clips.py "input/video.mp4"
    python editar_clips.py "video" --cortes cortes.json
"""
import argparse
import json
import shutil
import sys
import traceback
from pathlib import Path

# La consola de Windows (cp1252) no puede imprimir '→' y otros chars que usa
# pipeline_core -> UnicodeEncodeError que aborta cada clip. Forzamos UTF-8 en la
# salida para que el flujo sea robusto al invocarse desde bash/venv (subagente).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / ".claude" / "skills" / "Editor_Sergio"))
import pipeline_core as pc  # noqa: E402

MUSIC = RAIZ / "musicas"
OVERLAYS = RAIZ / "superposiciones"
WORKROOT = RAIZ / "whisper" / "_edit"


def resolver_nombre(arg: str) -> str:
    """Nombre del video (para ubicar transcripciones/<nombre>/)."""
    p = Path(arg)
    return p.stem if p.suffix else arg


def cargar_hooks(cortes_path: Path) -> dict:
    """Mapa nombre_clip -> hook_query desde cortes.json (si existe)."""
    hooks = {}
    if cortes_path.exists():
        try:
            for c in json.loads(cortes_path.read_text(encoding="utf-8")):
                if c.get("hook_query"):
                    hooks[c["nombre"]] = c["hook_query"]
        except Exception:
            pass
    return hooks


def main():
    ap = argparse.ArgumentParser(description="Edicion final (Fase C) de los clips de un video.")
    ap.add_argument("video", help="Nombre en input/ o ruta al video.")
    ap.add_argument("--cortes", help="Ruta al cortes.json (por defecto transcripciones/<video>/cortes.json).")
    args = ap.parse_args()

    nombre = resolver_nombre(args.video)
    clips_dir = RAIZ / "transcripciones" / nombre / "clips"
    out = RAIZ / "transcripciones" / nombre / "finales"
    cortes_path = Path(args.cortes) if args.cortes else (RAIZ / "transcripciones" / nombre / "cortes.json")
    hooks = cargar_hooks(cortes_path)

    if not clips_dir.exists():
        raise SystemExit(f"[!] No hay clips en {clips_dir}. Ejecuta antes clips.py.")

    # cargar env.json (trae PEXELS_API_KEY para el mini-video de gancho)
    env = {}
    try:
        if pc.ENV_PATH.exists():
            env = json.loads(pc.ENV_PATH.read_text())
    except Exception:
        env = {}
    env.update({"MUSIC_DIR": str(MUSIC), "OVERLAYS_DIR": str(OVERLAYS)})
    out.mkdir(parents=True, exist_ok=True)
    if WORKROOT.exists():
        shutil.rmtree(WORKROOT, ignore_errors=True)

    clips = sorted(clips_dir.glob("*.mp4"))
    print(f"{len(clips)} clips a editar\n", flush=True)
    for clip in clips:
        name = clip.stem
        hook = hooks.get(name) or name.split("_", 1)[-1].replace("_", " ")
        print(f"=== {name}   gancho='{hook}'", flush=True)
        work = WORKROOT / name
        work.mkdir(parents=True, exist_ok=True)
        ascii_in = work / "in.mp4"
        shutil.copy(str(clip), str(ascii_in))
        out_tmp = work / "out.mp4"
        try:
            pc.burn_subs_and_music(
                ascii_in, MUSIC, out_tmp,
                lang="es", env=env, overlays_dir=OVERLAYS, hook_query=hook,
            )
            shutil.move(str(out_tmp), str(out / f"{name}.mp4"))
            print(f"   OK -> finales/{name}.mp4", flush=True)
        except Exception as e:
            traceback.print_exc()
            print(f"   [!] FALLO en {name}: {e}", flush=True)

    shutil.rmtree(WORKROOT, ignore_errors=True)
    print(f"\nListo. Finales en: {out}", flush=True)


if __name__ == "__main__":
    main()

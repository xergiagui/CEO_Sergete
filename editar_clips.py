#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 4 — Edicion final con la skill Editor_Sergio (solo Fase C).

Por cada clip de transcripciones/<video>/clips/ aplica:
  gancho (imagen libre online) + b-roll local (superposiciones/) + musica local
  (musicas/) + de-click + subtitulos palabra a palabra (una sola vez, enmascarando
  palabrotas).

Trabaja en una carpeta ASCII (whisper/_edit) para evitar problemas de rutas con
tildes en el filtro de subtitulos de ffmpeg. Salida en transcripciones/<video>/finales/.
"""
import shutil
import sys
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / ".claude" / "skills" / "Editor_Sergio"))
import pipeline_core as pc  # noqa: E402

VIDEO = "Mi Adicción"
CLIPS = RAIZ / "transcripciones" / VIDEO / "clips"
OUT = RAIZ / "transcripciones" / VIDEO / "finales"
MUSIC = RAIZ / "musicas"
OVERLAYS = RAIZ / "superposiciones"
WORKROOT = RAIZ / "whisper" / "_edit"

# Query de la imagen-gancho por clip: analizada para tener fuerte gancho visual
# y relacion clara con el contenido (en ingles -> mejor stock).
HOOKS = {
    "01_adiccion_emprendedores": "excited entrepreneur starting new project idea",
    "02_empresa_como_bebe":      "newborn baby crying held in hands",
    "03_matrimonio_vs_negocio":  "couple holding hands wedding rings love",
    "04_no_coquetear":           "many open doors choice temptation",
    "05_cocacola_new_coke":      "vintage coca cola glass bottle red",
    "06_migracion_caos":         "stressed man overwhelmed laptop office",
}


def main():
    # cargar env.json (trae PEXELS_API_KEY para el mini-video de gancho)
    env = {}
    try:
        if pc.ENV_PATH.exists():
            import json
            env = json.loads(pc.ENV_PATH.read_text())
    except Exception:
        env = {}
    env.update({"MUSIC_DIR": str(MUSIC), "OVERLAYS_DIR": str(OVERLAYS)})
    OUT.mkdir(parents=True, exist_ok=True)
    if WORKROOT.exists():
        shutil.rmtree(WORKROOT, ignore_errors=True)

    clips = sorted(CLIPS.glob("*.mp4"))
    print(f"{len(clips)} clips a editar\n", flush=True)
    for clip in clips:
        name = clip.stem
        hook = HOOKS.get(name, name.split("_", 1)[-1].replace("_", " "))
        print(f"=== {name}   gancho='{hook}'", flush=True)
        work = WORKROOT / name
        work.mkdir(parents=True, exist_ok=True)
        ascii_in = work / "in.mp4"
        shutil.copy(str(clip), str(ascii_in))
        out = work / "out.mp4"
        try:
            pc.burn_subs_and_music(
                ascii_in, MUSIC, out,
                lang="es", env=env, overlays_dir=OVERLAYS, hook_query=hook,
            )
            shutil.move(str(out), str(OUT / f"{name}.mp4"))
            print(f"   OK -> finales/{name}.mp4", flush=True)
        except Exception as e:
            traceback.print_exc()
            print(f"   [!] FALLO en {name}: {e}", flush=True)

    shutil.rmtree(WORKROOT, ignore_errors=True)
    print(f"\nListo. Finales en: {OUT}", flush=True)


if __name__ == "__main__":
    main()

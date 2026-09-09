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

Trabaja en una carpeta ASCII ÚNICA por proceso (whisper/_edit_XXXX via mkdtemp)
para evitar problemas de rutas con tildes en el filtro de subtitulos de ffmpeg y
para no pisar ediciones en paralelo. Salida en transcripciones/<video>/finales/.

Uso:
    python editar_clips.py "Mi Adicción"
    python editar_clips.py "input/video.mp4"
    python editar_clips.py "video" --cortes cortes.json
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
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
# Raíz ASCII bajo la que se crea el work dir ÚNICO por ejecución (ver main()).
# whisper-cli/ffmpeg abren rutas ANSI, así que el intermedio va bajo whisper/
# con nombre ASCII garantizado.
WORKBASE = RAIZ / "whisper"


def resolver_nombre(arg: str) -> str:
    """Nombre del video (para ubicar transcripciones/<nombre>/)."""
    p = Path(arg)
    return p.stem if p.suffix else arg


def resolver_env_supabase() -> dict:
    """Env con credenciales de Supabase para el banco de frases virales.

    Prioridad: 1) ~/.viral-pipeline/env.json (pc.ENV_PATH, el mismo que ya usa
    el pipeline y trae SUPABASE_URL/ANON_KEY + PEXELS). 2) fallback al .env de
    CEO_Sergete (carpeta hermana). Best-effort: devuelve {} si no hay nada.
    """
    env = {}
    try:
        if pc.ENV_PATH.exists():
            env = json.loads(pc.ENV_PATH.read_text(encoding="utf-8"))
    except Exception:
        env = {}
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY")):
        ceo_env = RAIZ.parent / "CEO_Sergete" / ".env"
        try:
            if ceo_env.exists():
                for line in ceo_env.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("SUPABASE_URL", "SUPABASE_ANON_KEY") and not env.get(k):
                        env[k] = v
        except Exception:
            pass
    return env


def guardar_frases_virales(nombre: str, cortes_path: Path,
                           source_url: str = None, env: dict = None) -> dict:
    """Lee cortes.json y guarda las frases virales en Supabase (best-effort).

    Por cada corte usa `frase_viral` (texto verbatim); si falta, cae al `titulo`
    y, en ultimo caso, al `hook_query`. Pasa tambien angle/virality/category/
    rationale/tags si el corte los trae. avatar_name = slug del video (nombre).
    Nunca lanza: si no hay env/Supabase o falla la red, avisa y continua. El
    dedup por phrase_hash en store_viral_phrases evita duplicados al re-ejecutar.
    """
    if env is None:
        env = resolver_env_supabase()
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY")):
        print("   [frases] sin credenciales Supabase -> no se guardan (best-effort).", flush=True)
        return {"ok": False, "reason": "sin Supabase"}
    if not cortes_path.exists():
        print(f"   [frases] no hay {cortes_path.name}; nada que guardar.", flush=True)
        return {"ok": False, "reason": "sin cortes.json"}
    try:
        cortes = json.loads(cortes_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"   [frases] no pude leer cortes.json ({e}); se omite.", flush=True)
        return {"ok": False, "reason": str(e)}

    phrases = []
    for c in (cortes or []):
        texto = (c.get("frase_viral") or c.get("titulo") or c.get("hook_query") or "").strip()
        if not texto:
            continue
        phrases.append({
            "phrase": texto,
            "category": c.get("category"),
            "angle": c.get("angle"),
            "virality": c.get("virality"),
            "rationale": c.get("rationale"),
            "tags": c.get("tags") or [],
        })
    if not phrases:
        print("   [frases] ningun corte trae frase_viral/titulo; nada que guardar.", flush=True)
        return {"ok": False, "reason": "sin frases"}

    try:
        res = pc.store_viral_phrases(env, phrases, source_url=source_url,
                                     lang="es", avatar=nombre)
    except Exception as e:  # blindaje extra: jamas rompe el pipeline
        print(f"   [frases] guardado fallo (ignorado): {e}", flush=True)
        return {"ok": False, "reason": str(e)}

    if res.get("ok"):
        print(f"   [frases] {res['stored']} frases virales guardadas en Supabase "
              f"(avatar={nombre}).", flush=True)
    else:
        print(f"   [frases] no guardado (best-effort): {res.get('reason')}", flush=True)
    return res


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


def cargar_cortes_meta(cortes_path: Path) -> dict:
    """Mapa nombre_clip -> corte (dict completo) desde cortes.json.

    Sirve para derivar por clip la `tipologia_musica` (mood explícito) y el
    texto del clip (`frase_viral`/`titulo`) con el que inferir el mood cuando no
    hay anotación. Devuelve {} si no hay cortes.json."""
    meta = {}
    if cortes_path.exists():
        try:
            for c in json.loads(cortes_path.read_text(encoding="utf-8")):
                if c.get("nombre"):
                    meta[c["nombre"]] = c
        except Exception:
            pass
    return meta


def main():
    ap = argparse.ArgumentParser(description="Edicion final (Fase C) de los clips de un video.")
    ap.add_argument("video", help="Nombre en input/ o ruta al video.")
    ap.add_argument("--cortes", help="Ruta al cortes.json (por defecto transcripciones/<video>/cortes.json).")
    ap.add_argument("--work-dir", help="Work dir ASCII para intermedios (por defecto uno único por proceso bajo whisper/). "
                                       "Si se suministra, NO se borra al terminar.")
    args = ap.parse_args()

    nombre = resolver_nombre(args.video)
    clips_dir = RAIZ / "transcripciones" / nombre / "clips"
    out = RAIZ / "transcripciones" / nombre / "finales"
    cortes_path = Path(args.cortes) if args.cortes else (RAIZ / "transcripciones" / nombre / "cortes.json")
    hooks = cargar_hooks(cortes_path)
    cortes_meta = cargar_cortes_meta(cortes_path)

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

    # CONCURRENCIA: el work dir debe ser ÚNICO por ejecución. Antes se usaba un
    # 'whisper/_edit' COMPARTIDO y se hacía rmtree al arrancar; con dos ediciones
    # en paralelo la segunda borraba los intermedios de la primera (carrera: una
    # edición se caía o se pisaba a media). Ahora cada proceso crea su propio dir
    # aislado (tempfile.mkdtemp bajo whisper/, nombre ASCII garantizado y único)
    # y solo limpia ESE al terminar; nunca un rmtree del dir global. Se puede
    # forzar con --work-dir / EDIT_WORK_DIR (debe ser ASCII y estar bajo la raíz).
    WORKBASE.mkdir(parents=True, exist_ok=True)
    supplied = args.work_dir or os.environ.get("EDIT_WORK_DIR")
    if supplied:
        workroot = Path(supplied)
        workroot.mkdir(parents=True, exist_ok=True)
        _work_es_propio = False  # dir suministrado: no lo borramos al final
    else:
        workroot = Path(tempfile.mkdtemp(prefix="_edit_", dir=str(WORKBASE)))
        _work_es_propio = True

    clips = sorted(clips_dir.glob("*.mp4"))
    print(f"{len(clips)} clips a editar\n", flush=True)
    for clip in clips:
        name = clip.stem
        hook = hooks.get(name) or name.split("_", 1)[-1].replace("_", " ")
        corte = cortes_meta.get(name, {})
        # Tipología de música explícita (mood) y texto del clip para inferirla.
        music_typology = corte.get("tipologia_musica")
        clip_text = (corte.get("frase_viral") or corte.get("titulo")
                     or hook or "").strip() or None
        print(f"=== {name}   gancho='{hook}'"
              + (f"   mood='{music_typology}'" if music_typology else ""), flush=True)
        work = workroot / name
        work.mkdir(parents=True, exist_ok=True)
        ascii_in = work / "in.mp4"
        shutil.copy(str(clip), str(ascii_in))
        out_tmp = work / "out.mp4"
        try:
            pc.burn_subs_and_music(
                ascii_in, MUSIC, out_tmp,
                lang="es", env=env, overlays_dir=OVERLAYS, hook_query=hook,
                music_typology=music_typology, clip_text=clip_text,
            )
            shutil.move(str(out_tmp), str(out / f"{name}.mp4"))
            print(f"   OK -> finales/{name}.mp4", flush=True)
        except Exception as e:
            traceback.print_exc()
            print(f"   [!] FALLO en {name}: {e}", flush=True)

    if _work_es_propio:
        shutil.rmtree(workroot, ignore_errors=True)
    print(f"\nListo. Finales en: {out}", flush=True)

    # --- Banco de frases virales (Supabase, best-effort) ---------------------
    # Al terminar la edicion guardamos las frases virales de este video en la
    # tabla viral_phrases para reutilizarlas mas adelante (historias, hooks...).
    inp = RAIZ / "input" / f"{nombre}.mp4"
    source_url = str(inp) if inp.exists() else str(args.video)
    guardar_frases_virales(nombre, cortes_path, source_url=source_url)


if __name__ == "__main__":
    main()

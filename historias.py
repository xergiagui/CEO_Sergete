"""
TheHistoria — generador de historias de Instagram (9:16), por PROYECTO.

Toma las FRASES virales del proyecto que TheEditor guarda en Supabase
(`viral_phrases` con `proyecto:<id>` en `tags` y used_in_story = false), les pone
un FONDO según la política de b-roll del proyecto (banco común, b-roll propio o
fondo liso), renderiza un MP4 vertical por frase y marca la frase como usada.
Proceso INDEPENDIENTE: se lanza a demanda, no forma parte de la descarga/edición.

Uso:
  python historias.py [--proyecto ID]          # N historias desde la BBDD
  python historias.py --n 5                    # 5 historias
  python historias.py --categoria dinero       # solo esa categoría
  python historias.py --min-virality 70        # solo frases con virality >= 70
  python historias.py --phrase "Tu texto"      # historia suelta (no toca la BBDD)
  python historias.py --no-marcar              # no marca used_in_story
  python historias.py --duracion 7             # segundos por historia

`--proyecto` se puede omitir si solo hay un proyecto; con varios es obligatorio.
Salida en salidas/<id>/<AAAAMMDD_HHMMSS>/. Ejecuta con el .venv de TheEditor.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import config
from lib.env import load_env, has_supabase
from lib.fondos import elegir_fondo, hay_fondos, origen_fondos
from lib.proyectos import Proyecto, ProyectoError, resolver
from lib.render import render_historia
from lib.supabase_phrases import fetch_unused_phrases, mark_used


def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen] or "historia").rstrip("-")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Genera historias IG a partir de frases virales.")
    p.add_argument("--proyecto", default=None,
                   help="id del proyecto (obligatorio si hay más de uno)")
    p.add_argument("--n", type=int, default=None,
                   help="nº de historias desde la BBDD (def. el del proyecto, o 5)")
    p.add_argument("--categoria", default=None, help="filtra por category")
    p.add_argument("--min-virality", type=int, default=None, help="virality mínima")
    p.add_argument("--phrase", default=None, help="frase suelta (no usa la BBDD)")
    p.add_argument("--duracion", type=float, default=None,
                   help="segundos por historia (def. el del proyecto, o 6)")
    p.add_argument("--orientation", default=None, choices=["vertical", "horizontal"],
                   help="fondo con esa orientación (si el catálogo lo tiene)")
    p.add_argument("--no-marcar", action="store_true", help="no marcar used_in_story")
    p.add_argument("--max-len", type=int, default=None,
                   help="OPCIONAL: descarta frases más largas que N caracteres. "
                        "Por defecto NO filtra: las frases largas se ajustan solas.")
    return p.parse_args(argv)


def _tanda_dir(proyecto: Proyecto) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = proyecto.salidas_dir / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def main(argv=None) -> int:
    # En consolas Windows (cp1252) los caracteres como '✓' o acentos rompen el
    # print. Forzamos UTF-8 en stdout/stderr de forma best-effort.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = _parse_args(argv)
    try:
        proyecto = resolver(args.proyecto)
    except ProyectoError as e:
        print(f"[!] {e}")
        return 2
    cfg = proyecto.seccion("historias")
    if cfg.get("activas") is False:
        print(f"[!] El proyecto «{proyecto.id}» no tiene las historias activas "
              f"(proyectos/{proyecto.id}/proyecto.json → historias.activas).")
        return 2
    print(f"[i] {proyecto.resumen()}")
    filtro = cfg.get("frases") if isinstance(cfg.get("frases"), dict) else {}
    duracion = args.duracion or cfg.get("duracion") or config.STORY_DURATION
    orientation = args.orientation or cfg.get("orientacion")

    # Supabase: frases (BBDD) y catálogo del banco común. Con --phrase y política
    # propio/ninguno no se usa para nada.
    env = load_env() if not args.phrase or proyecto.broll == "banco_comun" else {}

    # 1) Reunir las frases a renderizar (solo las del proyecto).
    if args.phrase:
        items = [{"id": None, "phrase": args.phrase}]
    else:
        if not has_supabase(env):
            print("[!] Sin credenciales de Supabase (revisa .env). No hay frases que leer.")
            print("    Puedes probar una frase suelta con:  --phrase \"tu texto\"")
            return 2
        items = fetch_unused_phrases(
            env, proyecto.etiqueta_frases,
            limit=args.n or cfg.get("n_por_defecto") or 5,
            categoria=args.categoria,
            categorias=filtro.get("categorias"),
            min_virality=(args.min_virality if args.min_virality is not None
                          else filtro.get("min_virality")),
            lang=filtro.get("lang"),
        )
        if not items:
            print(f"[i] No hay frases sin usar del proyecto (etiqueta «{proyecto.etiqueta_frases}») "
                  f"que cumplan el filtro. Nada que generar.")
            return 0

    if not hay_fondos(proyecto):
        print(f"[!] El proyecto «{proyecto.id}» (b-roll {proyecto.broll}) no tiene vídeos de "
              f"fondo en {origen_fondos(proyecto)}. Añádelos o cambia su política a «ninguno» "
              f"(fondo liso) en TheEditor/proyectos/{proyecto.id}/proyecto.json.")
        return 2

    out_dir = _tanda_dir(proyecto)
    usados_fondo: set = set()
    manifest = []

    print(f"[i] Generando {len(items)} historia(s) en {out_dir}")
    print(f"    fondos: {origen_fondos(proyecto)}")
    omitidas_largas = 0
    for idx, it in enumerate(items, 1):
        phrase = (it.get("phrase") or "").strip()
        if not phrase:
            continue
        # Filtro OPCIONAL por longitud (por defecto desactivado: el render ajusta
        # el tamaño de fuente para que cualquier frase larga quepa y sea legible).
        if args.max_len is not None and len(phrase) > args.max_len:
            omitidas_largas += 1
            print(f"  [{idx}] omitida por --max-len ({len(phrase)} > {args.max_len})")
            continue
        fondo, metodo = elegir_fondo(phrase, env, proyecto, usados=usados_fondo,
                                     want_orientation=orientation)
        if fondo is None and metodo != "liso":
            print(f"  [{idx}] sin fondos disponibles en {origen_fondos(proyecto)} — se omite")
            continue
        if fondo is not None:
            usados_fondo.add(fondo.name)

        out_mp4 = out_dir / f"{idx:02d}_{_slug(phrase)}.mp4"
        try:
            render_historia(fondo, phrase, out_mp4, duration=duracion,
                            color=proyecto.color_liso if fondo is None else None)
        except Exception as e:
            print(f"  [{idx}] ERROR al renderizar: {e}")
            continue

        marcada = False
        if it.get("id") and not args.no_marcar:
            marcada = mark_used(env, it["id"])

        nombre_fondo = fondo.name if fondo is not None else proyecto.color_liso
        print(f"  [{idx}] OK  fondo={nombre_fondo} ({metodo})  ->  {out_mp4.name}"
              + ("  [marcada]" if marcada else ""))
        manifest.append({
            "proyecto": proyecto.id,
            "phrase": phrase,
            "phrase_id": it.get("id"),
            "fondo": nombre_fondo,
            "metodo_fondo": metodo,
            "politica_broll": proyecto.broll,
            "salida": out_mp4.name,
            "marcada_usada": marcada,
            "virality": it.get("virality"),
            "longitud": len(phrase),
        })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[✓] {len(manifest)} historia(s) generada(s). Manifiesto: {out_dir / 'manifest.json'}"
          + (f"  ({omitidas_largas} omitidas por --max-len)" if omitidas_largas else ""))
    return 0 if manifest else 1


if __name__ == "__main__":
    sys.exit(main())

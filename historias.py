"""
TheHistoria — generador de historias de Instagram (9:16).

Toma las FRASES virales que TheEditor guarda en Supabase (`viral_phrases`,
used_in_story = false), les pone un FONDO del catálogo de b-roll compartido
(TheEditor/superposiciones/ · broll_assets), renderiza un MP4 vertical por frase
y marca la frase como usada. Proceso INDEPENDIENTE: se lanza a demanda, no forma
parte del flujo de descarga/edición.

Uso:
  python historias.py                         # N historias desde la BBDD (por defecto)
  python historias.py --n 5                    # 5 historias
  python historias.py --categoria dinero       # solo esa categoría
  python historias.py --min-virality 70        # solo frases con virality >= 70
  python historias.py --phrase "Tu texto"      # historia suelta (no toca la BBDD)
  python historias.py --no-marcar              # no marca used_in_story
  python historias.py --duracion 7             # segundos por historia

Ejecuta con el Python que tenga las deps (fastembed, httpx, Pillow,
imageio-ffmpeg). Reutiliza el .venv de TheEditor (ver README).
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
from lib.supabase_phrases import fetch_unused_phrases, mark_used
from lib.fondos import elegir_fondo
from lib.render import render_historia


def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen] or "historia").rstrip("-")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Genera historias IG a partir de frases virales.")
    p.add_argument("--n", type=int, default=5, help="nº de historias desde la BBDD (def. 5)")
    p.add_argument("--categoria", default=None, help="filtra por category")
    p.add_argument("--min-virality", type=int, default=None, help="virality mínima")
    p.add_argument("--phrase", default=None, help="frase suelta (no usa la BBDD)")
    p.add_argument("--duracion", type=float, default=config.STORY_DURATION, help="segundos por historia")
    p.add_argument("--orientation", default=None, choices=["vertical", "horizontal"],
                   help="fondo con esa orientación (si el catálogo lo tiene)")
    p.add_argument("--no-marcar", action="store_true", help="no marcar used_in_story")
    return p.parse_args(argv)


def _tanda_dir() -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = config.OUT_DIR / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def main(argv=None) -> int:
    args = _parse_args(argv)
    env = load_env()

    # 1) Reunir las frases a renderizar.
    if args.phrase:
        items = [{"id": None, "phrase": args.phrase}]
    else:
        if not has_supabase(env):
            print("[!] Sin credenciales de Supabase (revisa .env). No hay frases que leer.")
            print("    Puedes probar una frase suelta con:  --phrase \"tu texto\"")
            return 2
        items = fetch_unused_phrases(
            env, limit=args.n, categoria=args.categoria, min_virality=args.min_virality,
        )
        if not items:
            print("[i] No hay frases sin usar que cumplan el filtro. Nada que generar.")
            return 0

    if not config.FONDOS_DIR.is_dir():
        print(f"[!] No existe la carpeta de fondos: {config.FONDOS_DIR}")
        return 2

    out_dir = _tanda_dir()
    usados_fondo: set = set()
    manifest = []

    print(f"[i] Generando {len(items)} historia(s) en {out_dir}")
    for idx, it in enumerate(items, 1):
        phrase = (it.get("phrase") or "").strip()
        if not phrase:
            continue
        fondo, metodo = elegir_fondo(phrase, env, usados=usados_fondo,
                                     want_orientation=args.orientation)
        if fondo is None:
            print(f"  [{idx}] sin fondos disponibles — se omite")
            continue
        usados_fondo.add(fondo.name)

        out_mp4 = out_dir / f"{idx:02d}_{_slug(phrase)}.mp4"
        try:
            render_historia(fondo, phrase, out_mp4, duration=args.duracion)
        except Exception as e:
            print(f"  [{idx}] ERROR al renderizar: {e}")
            continue

        marcada = False
        if it.get("id") and not args.no_marcar:
            marcada = mark_used(env, it["id"])

        print(f"  [{idx}] OK  fondo={fondo.name} ({metodo})  ->  {out_mp4.name}"
              + ("  [marcada]" if marcada else ""))
        manifest.append({
            "phrase": phrase,
            "phrase_id": it.get("id"),
            "fondo": fondo.name,
            "metodo_fondo": metodo,
            "salida": out_mp4.name,
            "marcada_usada": marcada,
        })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[✓] {len(manifest)} historia(s) generada(s). Manifiesto: {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

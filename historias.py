"""
TheHistoria — generador de historias de Instagram (9:16), por PROYECTO.

Toma las FRASES virales del proyecto que TheEditor guarda en Supabase
(`viral_phrases` con `proyecto:<id>` en `tags` y used_in_story = false), les pone
un FONDO según la política de b-roll del proyecto (banco común, b-roll propio o
fondo liso) y renderiza un MP4 vertical por frase, con la fuente y los colores
del proyecto. Proceso INDEPENDIENTE: se lanza a demanda.

Las frases NO se marcan al generar (una tanda rechazada no gasta frases); se
marcan como usadas al APROBAR la tanda. Mientras una tanda está pendiente en
salidas/<id>/, sus frases no se repiten en otra.

Uso:
  python historias.py [--proyecto ID]          # N historias desde la BBDD
  python historias.py --n 5                    # 5 historias
  python historias.py --categoria dinero       # solo esa categoría
  python historias.py --min-virality 70        # solo frases con virality >= 70
  python historias.py --phrase "Tu texto"      # historia suelta (no toca la BBDD)
  python historias.py --duracion 7             # segundos por historia
  python historias.py --aprobar <tanda…> | --todas [--no-marcar] [--destino DIR]
      # OK: mueve los MP4 a CEO_Sergete/HISTORIAS/<id>/1. Pte publicar/ (nombre
      # único), marca sus frases como usadas, apunta el manifest en
      # salidas/<id>/_aprobadas.log y borra la tanda. --destino: solo pruebas.

`--proyecto` se puede omitir si solo hay un proyecto; con varios es obligatorio.
Salida en salidas/<id>/<AAAAMMDD_HHMMSS>/. Ejecuta con el .venv de TheEditor.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

import config
from lib.aprobar import nombre_unico, registrar
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
    p.add_argument("--no-marcar", action="store_true",
                   help="con --aprobar: no marca used_in_story (al generar nunca se marca)")
    p.add_argument("--aprobar", nargs="+", metavar="TANDA",
                   help="OK a estas tandas (nombre en salidas/<id>/ o ruta): mueve los MP4 "
                        "a HISTORIAS/<id>/1. Pte publicar/, marca sus frases y borra la tanda")
    p.add_argument("--todas", action="store_true",
                   help="OK a todas las tandas de historias pendientes del proyecto")
    p.add_argument("--destino", default=None,
                   help="PRUEBAS: carpeta destino alternativa para --aprobar")
    p.add_argument("--max-len", type=int, default=None,
                   help="OPCIONAL: descarta frases más largas que N caracteres. "
                        "Por defecto NO filtra: las frases largas se ajustan solas.")
    return p.parse_args(argv)


def _tanda_dir(proyecto: Proyecto) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = proyecto.salidas_dir / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tandas_pendientes(proyecto: Proyecto) -> list[Path]:
    """Tandas de historias (normales y especiales) en salidas/<id>/."""
    d = proyecto.salidas_dir
    if not d.is_dir():
        return []
    return sorted(t for t in d.iterdir()
                  if t.is_dir() and not t.name.startswith(("carrusel_", "_", "."))
                  and ((t / "manifest.json").exists() or any(t.glob("*.mp4"))))


def _manifest(tanda: Path) -> list[dict]:
    try:
        datos = json.loads((tanda / "manifest.json").read_text(encoding="utf-8"))
        return [m for m in datos if isinstance(m, dict)] if isinstance(datos, list) else []
    except Exception:
        return []


def _ids_pendientes(proyecto: Proyecto) -> set:
    """Frases ya puestas en tandas sin aprobar (para no repetirlas en otra)."""
    return {m["phrase_id"] for t in _tandas_pendientes(proyecto) for m in _manifest(t)
            if m.get("phrase_id")}


def _resolver_tanda(nombre: str, proyecto: Proyecto) -> Path | None:
    t = Path(nombre)
    for cand in ([t] if t.is_absolute() else [proyecto.salidas_dir / t.name, Path.cwd() / t]):
        if cand.is_dir():
            return cand.resolve()
    return None


def _aprobar(args, proyecto: Proyecto) -> int:
    """OK a tandas: mover MP4 (nombre único), marcar frases, log y borrar la tanda."""
    if args.todas:
        tandas = _tandas_pendientes(proyecto)
        if not tandas:
            print(f"[i] No hay tandas de historias pendientes en {proyecto.salidas_dir}.")
            return 0
    else:
        tandas = []
        for nombre in args.aprobar:
            t = _resolver_tanda(nombre, proyecto)
            if t is None:
                print(f"[!] No existe la tanda «{nombre}» en {proyecto.salidas_dir}.")
                return 2
            if t.parent != proyecto.salidas_dir.resolve() or t.name.startswith("carrusel_"):
                print(f"[!] «{nombre}» no es una tanda de historias de salidas/{proyecto.id}/ "
                      f"(los carruseles se aprueban con carruseles.py --aprobar).")
                return 2
            tandas.append(t)
    for t in tandas:
        ajenas = {m.get("proyecto") for m in _manifest(t)} - {proyecto.id, None}
        if ajenas:
            print(f"[!] La tanda {t.name} trae historias de otro proyecto ({', '.join(ajenas)}).")
            return 2

    a_marcar = [m["phrase_id"] for t in tandas for m in _manifest(t)
                if m.get("phrase_id") and not m.get("marcada_usada")]
    env = {}
    if a_marcar and not args.no_marcar:
        env = load_env()
        if not has_supabase(env):
            print(f"[!] Hay {len(a_marcar)} frase(s) que marcar y no hay credenciales de "
                  f"Supabase: no apruebo nada (o usa --no-marcar).")
            return 2

    destino = Path(args.destino).resolve() if args.destino else proyecto.historias_pte
    destino.mkdir(parents=True, exist_ok=True)
    log = proyecto.salidas_dir / config.APROBADAS_LOG
    total = 0
    for t in tandas:
        manifest = _manifest(t)
        movidos = []
        for mp4 in sorted(t.glob("*.mp4")):
            dst = nombre_unico(destino, mp4.name, sufijo=t.name)
            shutil.move(str(mp4), str(dst))
            movidos.append({"origen": mp4.name, "destino": dst.name})
        marcadas, fallidas = [], []
        for m in manifest:
            pid = m.get("phrase_id")
            if not pid or m.get("marcada_usada") or args.no_marcar:
                continue
            (marcadas if mark_used(env, pid) else fallidas).append(pid)
        registrar(log, {"proyecto": proyecto.id, "tanda": t.name, "destino": str(destino),
                        "archivos": movidos, "frases_marcadas": marcadas,
                        "frases_sin_marcar": fallidas, "no_marcar": bool(args.no_marcar),
                        "manifest": manifest})
        shutil.rmtree(t)
        total += len(movidos)
        print(f"  [OK] {t.name}: {len(movidos)} MP4 → {destino}"
              + (f" · {len(marcadas)} frase(s) marcada(s)" if marcadas else "")
              + (f" · [!] {len(fallidas)} sin marcar (ver log)" if fallidas else ""))
    print(f"[✓] {total} historia(s) aprobada(s) de {len(tandas)} tanda(s). Log: {log}")
    return 0


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
    if args.aprobar or args.todas:
        return _aprobar(args, proyecto)
    print(f"[i] {proyecto.resumen()}")
    for a in proyecto.avisos():
        print(f"[aviso] {a}")
    if proyecto.estilo_por_rellenar():
        print(f"[aviso] proyectos/{proyecto.id}/estilo.json sigue con `_rellenar`: revisa "
              f"las fuentes del proyecto.")
    estilo = proyecto.estilo_historia()
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
        n = args.n or cfg.get("n_por_defecto") or 5
        pendientes = _ids_pendientes(proyecto)
        items = fetch_unused_phrases(
            env, proyecto.etiqueta_frases,
            limit=n + len(pendientes),
            categoria=args.categoria,
            categorias=filtro.get("categorias"),
            min_virality=(args.min_virality if args.min_virality is not None
                          else filtro.get("min_virality")),
            lang=filtro.get("lang"),
        )
        items = [it for it in items if it.get("id") not in pendientes][:n]
        if not items:
            print(f"[i] No hay frases sin usar del proyecto (etiqueta «{proyecto.etiqueta_frases}») "
                  f"que cumplan el filtro"
                  + (f" ni estén ya en una tanda pendiente ({len(pendientes)})" if pendientes else "")
                  + ". Nada que generar.")
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
            render_historia(fondo, phrase, out_mp4, duration=duracion, estilo=estilo)
        except Exception as e:
            print(f"  [{idx}] ERROR al renderizar: {e}")
            continue

        nombre_fondo = fondo.name if fondo is not None else proyecto.color_liso
        print(f"  [{idx}] OK  fondo={nombre_fondo} ({metodo})  ->  {out_mp4.name}")
        manifest.append({
            "proyecto": proyecto.id,
            "phrase": phrase,
            "phrase_id": it.get("id"),
            "fondo": nombre_fondo,
            "metodo_fondo": metodo,
            "politica_broll": proyecto.broll,
            "salida": out_mp4.name,
            "marcada_usada": False,        # se marca al aprobar (--aprobar)
            "virality": it.get("virality"),
            "longitud": len(phrase),
        })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[✓] {len(manifest)} historia(s) generada(s). Manifiesto: {out_dir / 'manifest.json'}"
          + (f"  ({omitidas_largas} omitidas por --max-len)" if omitidas_largas else ""))
    if manifest:
        print(f"    Al dar OK: historias.py --proyecto {proyecto.id} --aprobar {out_dir.name} "
              f"(marca las frases; si se rechaza, borra la carpeta)")
    return 0 if manifest else 1


if __name__ == "__main__":
    sys.exit(main())

"""
TheHistoria — HISTORIAS ESPECIALES (vía aparte), por PROYECTO.

Genera historias de Instagram (9:16) a partir de TEXTOS que da el usuario por
parámetro (NO usa Supabase ni `viral_phrases`), con FONDOS propios del proyecto
en `proyectos/<id>/especiales/` (NO el banco común), elegidos por rotación/azar
sin repetir dentro de la tanda. Si esa carpeta está vacía, manda la política de
b-roll del proyecto (propio → su b-roll; ninguno → fondo liso). Deja una FRANJA
INFERIOR libre para el botón de IG: el texto se centra en la zona superior.

VARIACIONES: se generan N historias del mismo tema, cada una con un FONDO
distinto. Se pueden pasar VARIOS `--texto` (uno por variación); si hay menos
textos que variaciones, los textos se ciclan y varía el fondo. Con 1 solo texto
y N>1, todas comparten texto y cambia el fondo.

Uso:
  python historias_especiales.py [--proyecto ID] --texto "..." --variaciones 3
  python historias_especiales.py --texto "A" --texto "B" --variaciones 4 --duracion 5
  python historias_especiales.py --texto "..." --reserva-inferior 0.30

`--proyecto` se puede omitir si solo hay un proyecto. Salida en
salidas/<id>/especiales_<AAAAMMDD_HHMMSS>/. Ejecuta con el .venv de TheEditor.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import config
from lib.fondos_especiales import banco_especiales, seleccion_sin_repeticion
from lib.proyectos import Proyecto, ProyectoError, resolver
from lib.render import render_historia


def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen] or "historia").rstrip("-")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Genera HISTORIAS ESPECIALES (texto propio + fondos especiales del proyecto).")
    p.add_argument("--proyecto", default=None,
                   help="id del proyecto (obligatorio si hay más de uno)")
    p.add_argument("--texto", action="append", required=True, dest="textos",
                   help="texto de la historia. REPETIBLE: uno por variación. Al menos uno.")
    p.add_argument("--variaciones", type=int, default=None,
                   help="nº de historias del mismo tema, cada una con otro fondo "
                        "(def. el del proyecto, o 3)")
    p.add_argument("--duracion", type=float, default=None,
                   help="segundos por historia (def. el del proyecto, o 6)")
    p.add_argument("--reserva-inferior", type=float, default=None, dest="reserva_inferior",
                   help="fracción 0..0.6 de la altura reservada abajo para el botón "
                        "de IG (def. el del proyecto, o 0.25)")
    return p.parse_args(argv)


def _tanda_dir(proyecto: Proyecto) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = proyecto.salidas_dir / f"especiales_{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main(argv=None) -> int:
    # Forzar UTF-8 en stdout/stderr (acentos/símbolos en consolas Windows cp1252).
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
    cfg = proyecto.seccion("especiales")
    if cfg.get("activas") is False:
        print(f"[!] El proyecto «{proyecto.id}» no tiene las historias especiales activas "
              f"(proyectos/{proyecto.id}/proyecto.json → especiales.activas).")
        return 2
    print(f"[i] {proyecto.resumen()}")

    textos = [t.strip() for t in (args.textos or []) if t and t.strip()]
    if not textos:
        print("[!] Necesitas al menos un --texto con contenido.")
        return 2

    n = max(1, int(args.variaciones or cfg.get("variaciones") or 3))
    reserva = args.reserva_inferior
    if reserva is None:
        reserva = cfg.get("reserva_inferior", config.RESERVA_INFERIOR_ESPECIAL)
    reserva = max(0.0, min(0.6, float(reserva)))
    duracion = args.duracion or cfg.get("duracion") or config.STORY_DURATION

    fondos_banco, origen = banco_especiales(proyecto)
    if origen == "sin-fondos":
        print(f"[!] No hay vídeos para las especiales de «{proyecto.id}»: añade fondos en "
              f"{proyecto.especiales_dir}"
              + (f" o en {proyecto.broll_propio_dir}" if proyecto.broll == "propio" else "")
              + ".")
        return 2

    fondos = seleccion_sin_repeticion(fondos_banco, n) if fondos_banco else [None] * n

    out_dir = _tanda_dir(proyecto)
    manifest = []
    print(f"[i] Generando {n} variación(es) en {out_dir}")
    desc = {"especiales": f"{len(fondos_banco)} vídeo(s) de {proyecto.especiales_dir}",
            "broll-propio": f"{len(fondos_banco)} vídeo(s) del b-roll propio "
                            f"({proyecto.broll_propio_dir}), porque especiales/ está vacío",
            "liso": f"fondo liso {proyecto.color_liso} (especiales/ vacío y b-roll «ninguno»)"}
    print(f"    fondos: {desc[origen]} · reserva inferior: {reserva:.2f}")

    ok = 0
    for idx in range(1, n + 1):
        texto = textos[(idx - 1) % len(textos)]   # cicla los textos
        fondo = fondos[idx - 1]
        nombre_fondo = fondo.name if fondo is not None else proyecto.color_liso

        out_mp4 = out_dir / f"{idx:02d}_{_slug(texto)}.mp4"
        try:
            render_historia(fondo, texto, out_mp4, duration=duracion,
                            bottom_reserved_frac=reserva,
                            color=proyecto.color_liso if fondo is None else None)
        except Exception as e:
            print(f"  [{idx}] ERROR al renderizar (fondo={nombre_fondo}): {e}")
            continue

        ok += 1
        print(f"  [{idx}/{n}] OK  fondo={nombre_fondo}  ->  {out_mp4.name}")
        manifest.append({
            "proyecto": proyecto.id,
            "variacion": idx,
            "texto": texto,
            "fondo": nombre_fondo,
            "origen_fondo": origen,
            "salida": out_mp4.name,
            "reserva_inferior": reserva,
            "duracion": duracion,
        })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {ok}/{n} historia(s) especial(es) generada(s). "
          f"Manifiesto: {out_dir / 'manifest.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

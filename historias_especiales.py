"""
TheHistoria — HISTORIAS ESPECIALES (vía aparte).

Genera historias de Instagram (9:16) a partir de TEXTOS que da el usuario por
parámetro (NO usa Supabase ni `viral_phrases`), con FONDOS del banco propio
`BRells especiales/` (NO `superposiciones/`), elegidos por rotación/azar sin
repetir dentro de la tanda. Deja una FRANJA INFERIOR libre para el botón de IG:
el texto se centra en la zona superior (reserva inferior parametrizable).

VARIACIONES: se generan N historias del mismo tema, cada una con un FONDO
distinto. Se pueden pasar VARIOS `--texto` (uno por variación); si hay menos
textos que variaciones, los textos se ciclan y varía el fondo. Con 1 solo texto
y N>1, todas comparten texto y cambia el fondo.

Uso:
  python historias_especiales.py --texto "..." --variaciones 3
  python historias_especiales.py --texto "A" --texto "B" --variaciones 4 --duracion 5
  python historias_especiales.py --texto "..." --reserva-inferior 0.30

Ejecuta con el .venv de TheEditor (Pillow + imageio-ffmpeg). No instala nada.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import config
from lib.fondos_especiales import listar_fondos_especiales, seleccion_sin_repeticion
from lib.render import render_historia


def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen] or "historia").rstrip("-")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Genera HISTORIAS ESPECIALES (texto propio + fondo de BRells especiales/).")
    p.add_argument("--texto", action="append", required=True, dest="textos",
                   help="texto de la historia. REPETIBLE: uno por variación. Al menos uno.")
    p.add_argument("--variaciones", type=int, default=3,
                   help="nº de historias del mismo tema, cada una con otro fondo (def. 3)")
    p.add_argument("--duracion", type=float, default=config.STORY_DURATION,
                   help="segundos por historia (def. %(default)s)")
    p.add_argument("--reserva-inferior", type=float,
                   default=config.RESERVA_INFERIOR_ESPECIAL, dest="reserva_inferior",
                   help="fracción 0..0.6 de la altura reservada abajo para el botón "
                        "de IG (def. %(default)s)")
    return p.parse_args(argv)


def _tanda_dir() -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = config.OUT_DIR / f"especiales_{ts}"
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

    textos = [t.strip() for t in (args.textos or []) if t and t.strip()]
    if not textos:
        print("[!] Necesitas al menos un --texto con contenido.")
        return 2

    n = max(1, int(args.variaciones))
    reserva = max(0.0, min(0.6, float(args.reserva_inferior)))

    fondos_banco = listar_fondos_especiales()
    if not fondos_banco:
        print(f"[!] No hay vídeos en el banco de fondos especiales: "
              f"{config.FONDOS_ESPECIALES_DIR}")
        return 2

    fondos = seleccion_sin_repeticion(n)  # sin repetir dentro de la pasada

    out_dir = _tanda_dir()
    manifest = []
    print(f"[i] Generando {n} variación(es) en {out_dir}")
    print(f"    banco de fondos: {len(fondos_banco)} vídeo(s) · reserva inferior: {reserva:.2f}")

    ok = 0
    for idx in range(1, n + 1):
        texto = textos[(idx - 1) % len(textos)]   # cicla los textos
        fondo = fondos[idx - 1]

        out_mp4 = out_dir / f"{idx:02d}_{_slug(texto)}.mp4"
        try:
            render_historia(fondo, texto, out_mp4, duration=args.duracion,
                            bottom_reserved_frac=reserva)
        except Exception as e:
            print(f"  [{idx}] ERROR al renderizar (fondo={fondo.name}): {e}")
            continue

        ok += 1
        print(f"  [{idx}/{n}] OK  fondo={fondo.name}  ->  {out_mp4.name}")
        manifest.append({
            "variacion": idx,
            "texto": texto,
            "fondo": fondo.name,
            "salida": out_mp4.name,
            "reserva_inferior": reserva,
            "duracion": args.duracion,
        })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {ok}/{n} historia(s) especial(es) generada(s). "
          f"Manifiesto: {out_dir / 'manifest.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

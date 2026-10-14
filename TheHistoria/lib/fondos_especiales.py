"""
Selección de FONDOS para las HISTORIAS ESPECIALES (vía aparte).

Sin Supabase ni semántica: los fondos son los vídeos propios del proyecto en
`proyectos/<id>/especiales/` y se eligen por ROTACIÓN/azar SIN repetir dentro
de la tanda (hasta agotar el banco; si se piden más variaciones que fondos, se
vuelve a barajar).

Si `especiales/` está vacío, manda la política de b-roll del proyecto:
  propio       su b-roll propio (TheEditor/proyectos/<id>/recursos/broll/);
  ninguno      fondo liso de marca;
  banco_comun  error (las especiales nunca tiran del banco común).
"""
from __future__ import annotations

import random
from pathlib import Path

import config
from lib.fondos import listar_fondos_propios


def listar_fondos_especiales(proyecto) -> list[Path]:
    """Vídeos de proyectos/<id>/especiales/ (orden estable por nombre)."""
    d = proyecto.especiales_dir
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.suffix.lower() in config.VIDEO_EXTS and not p.name.startswith(".")
    )


def banco_especiales(proyecto) -> tuple[list[Path], str]:
    """(fondos, origen) según lo que haya y la política del proyecto.

    origen ∈ {"especiales", "broll-propio", "liso", "sin-fondos"}."""
    fondos = listar_fondos_especiales(proyecto)
    if fondos:
        return fondos, "especiales"
    if proyecto.broll == "propio":
        propios = listar_fondos_propios(proyecto)
        return (propios, "broll-propio") if propios else ([], "sin-fondos")
    if proyecto.broll == "ninguno":
        return [], "liso"
    return [], "sin-fondos"


def seleccion_sin_repeticion(fondos: list[Path], n: int, barajar: bool = True) -> list[Path]:
    """Devuelve `n` fondos SIN repetir dentro de una pasada por el banco.

    Si `n` supera el nº de fondos, se recorre el banco tantas veces como haga
    falta (cada pasada sin repetir); solo así puede repetirse un fondo entre
    pasadas distintas. Con `barajar=True` cada pasada va en orden aleatorio;
    con False mantiene el orden estable (rotación determinista).
    """
    if not fondos or n <= 0:
        return []
    out: list[Path] = []
    while len(out) < n:
        pasada = list(fondos)
        if barajar:
            random.shuffle(pasada)
        out.extend(pasada)
    return out[:n]

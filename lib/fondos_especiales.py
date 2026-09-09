"""
Selección de FONDOS para las HISTORIAS ESPECIALES (vía aparte).

A diferencia de `fondos.py`, aquí NO hay Supabase ni semántica: los fondos son
los vídeos propios de `config.FONDOS_ESPECIALES_DIR` ("BRells especiales/") y se
eligen por ROTACIÓN/azar SIN repetir dentro de la tanda (hasta agotar el banco;
si se piden más variaciones que fondos, se vuelve a barajar).
"""
from __future__ import annotations
import random
from pathlib import Path

import config


def listar_fondos_especiales() -> list[Path]:
    """Vídeos disponibles como fondo especial (orden estable por nombre)."""
    d = config.FONDOS_ESPECIALES_DIR
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.suffix.lower() in config.VIDEO_EXTS
    )


def seleccion_sin_repeticion(n: int, barajar: bool = True) -> list[Path]:
    """Devuelve `n` fondos SIN repetir dentro de una pasada por el banco.

    Si `n` supera el nº de fondos, se recorre el banco tantas veces como haga
    falta (cada pasada sin repetir); solo así puede repetirse un fondo entre
    pasadas distintas. Con `barajar=True` cada pasada va en orden aleatorio;
    con False mantiene el orden estable (rotación determinista).
    """
    fondos = listar_fondos_especiales()
    if not fondos or n <= 0:
        return []
    out: list[Path] = []
    while len(out) < n:
        pasada = list(fondos)
        if barajar:
            random.shuffle(pasada)
        out.extend(pasada)
    return out[:n]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 2 (parte SRT): genera un .srt revisado conservando los tiempos de cada
segmento. Limpia el texto dentro de cada cue: enmascara palabrotas, corrige
errores obvios de reconocimiento y normaliza marcas, sin fusionar segmentos.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
NOMBRE = "Mi Adicción"
SRC = RAIZ / "transcripciones" / NOMBRE / f"{NOMBRE}.srt"
DST = RAIZ / "transcripciones" / NOMBRE / "revisadas" / f"{NOMBRE} - revisado.srt"

# Reemplazos exactos (respetando mayus/minus tal cual aparecen)
REEMPLAZOS = [
    ("jodida", "j***"),                      # palabrota enmascarada
    ("Cloud Code", "Claude Code"),
    ("con tu cloud en cero coma", "con tu Claude, en cero coma,"),
    ("desde tu cloud", "desde tu Claude"),
    ("con tu propio cloud", "con tu propio Claude"),
    ("hoy en cloud", "hoy en día"),
    ("ganas terrenales terribles", "ganas terribles"),
    ("buena barra de entrada", "buena barrera de entrada"),
    ("clonify", "Clonify"),
]

TIEMPO = re.compile(r"^\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d$")


def limpiar(texto: str) -> str:
    for a, b in REEMPLAZOS:
        texto = texto.replace(a, b)
    # espacios antes de signos y dobles espacios
    texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto).strip()
    return texto


def main():
    lineas = SRC.read_text(encoding="utf-8").splitlines()
    salida = []
    for ln in lineas:
        if ln.strip().isdigit() or TIEMPO.match(ln.strip()) or ln.strip() == "":
            salida.append(ln)
        else:
            salida.append(limpiar(ln))
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text("\n".join(salida) + "\n", encoding="utf-8")
    print(f"OK -> {DST.name}")


if __name__ == "__main__":
    main()

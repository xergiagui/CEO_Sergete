"""
APROBAR (al dar OK): utilidades comunes de `historias.py --aprobar` y
`carruseles.py --aprobar`. Mover (no copiar) a la carpeta de publicación del
proyecto con un nombre que no pise nada y dejar constancia en un log jsonl.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


def nombre_unico(destino: Path, nombre: str, sufijo: str = "") -> Path:
    """`destino/nombre` si está libre; si no, `<stem>_<sufijo><ext>` y después
    `_2`, `_3`… (vale para archivos y carpetas)."""
    cand = destino / nombre
    if not cand.exists():
        return cand
    p = Path(nombre)
    stem, ext = (p.stem, p.suffix) if p.suffix and len(p.suffix) <= 5 else (nombre, "")
    base = f"{stem}_{sufijo}" if sufijo else stem
    cand = destino / f"{base}{ext}"
    k = 2
    while cand.exists():
        cand = destino / f"{base}_{k}{ext}"
        k += 1
    return cand


def registrar(log: Path, entrada: dict) -> None:
    """Añade una línea JSON a `log` (con la fecha de aprobación)."""
    entrada = {"aprobada": dt.datetime.now().isoformat(timespec="seconds"), **entrada}
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

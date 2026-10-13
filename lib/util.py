"""Utilidades comunes: consola UTF-8, JSON, normalización de texto."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path


def forzar_utf8() -> None:
    """La consola de Windows usa cp1252 y rompe con tildes/emojis."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def leer_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def escribir_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos, espacios simples. Para comparar copys."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9#ñ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normalizar_hashtag(tag: str) -> str:
    """'Ventas' / '#Ventas ' -> '#ventas'. No quita tildes (IG las admite)."""
    t = (tag or "").strip().lower()
    if t and not t.startswith("#"):
        t = "#" + t
    return t

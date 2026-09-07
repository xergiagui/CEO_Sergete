"""
Embeddings de texto — EL MISMO modelo con el que TheEditor indexó `broll_assets`
y `viral_phrases` (paraphrase-multilingual-MiniLM-L12-v2, 384d, local, fastembed).

Usarlo permite casar una FRASE con el FONDO más afín del catálogo vía la RPC
`match_broll`. Best-effort: si fastembed no está disponible, quien llame cae a
selección de fondo al azar.
"""
from __future__ import annotations

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding  # import perezoso (dep pesada)
        _model = TextEmbedding(model_name=config.EMBED_MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    """Vector 384d del texto. Lanza si fastembed no está instalado."""
    vec = next(iter(_get_model().embed([text])))
    return [float(x) for x in vec]

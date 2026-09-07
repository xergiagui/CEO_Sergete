"""
Selección del FONDO para una historia.

Reutiliza EL MISMO banco que TheEditor: los vídeos de `TheEditor/superposiciones/`
catalogados en Supabase (`broll_assets`, con embedding + orientación). Para cada
frase, casa por afinidad semántica con la RPC `match_broll` y coge el fondo más
afín; si no hay Supabase/embeddings o nada supera el umbral, elige uno al azar.

Espejo de la lógica de pipeline_core.broll_match_filename (TheEditor), adaptado
a fondos de historias.
"""
from __future__ import annotations
import random
from pathlib import Path
from typing import Optional

import httpx

import config
from lib.env import supabase_headers, has_supabase

_aviso_cache: Optional[set] = None


def listar_fondos_locales() -> list[Path]:
    """Vídeos disponibles como fondo en superposiciones/ (orden estable)."""
    d = config.FONDOS_DIR
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.suffix.lower() in config.VIDEO_EXTS
    )


def _avisos(env: dict) -> set:
    """Filenames con tag 'aviso*' (marca/persona/calidad) → evitar. Cacheado."""
    global _aviso_cache
    if _aviso_cache is not None:
        return _aviso_cache
    out: set = set()
    url = env.get("SUPABASE_URL", "").rstrip("/")
    if has_supabase(env):
        try:
            r = httpx.get(
                f"{url}/rest/v1/broll_assets",
                params={"select": "filename,logical_tags"},
                headers=supabase_headers(env),
                timeout=20,
            )
            if r.status_code == 200:
                for row in r.json():
                    tags = row.get("logical_tags") or []
                    if any(str(t).startswith("aviso") for t in tags):
                        out.add(row["filename"])
        except Exception:
            pass
    _aviso_cache = out
    return out


def _match_filename(
    phrase: str, env: dict, exclude: set,
    want_orientation: Optional[str] = None, k: int = 8,
) -> Optional[str]:
    """Filename del fondo semánticamente más afín a la frase (o None)."""
    url = env.get("SUPABASE_URL", "").rstrip("/")
    if not has_supabase(env) or not (phrase or "").strip():
        return None
    try:
        from lib.embeddings import embed_text
        body = {
            "query_embedding": embed_text(phrase),
            "match_count": k,
            "want_orientation": want_orientation,
        }
        r = httpx.post(
            f"{url}/rest/v1/rpc/match_broll",
            headers=supabase_headers(env),
            json=body,
            timeout=20,
        )
        if r.status_code != 200:
            return None
        avisos = _avisos(env)
        for row in r.json():  # ordenados por similitud desc
            fn = row.get("filename")
            if not fn or fn in exclude or fn in avisos:
                continue
            if (row.get("similarity") or 0) >= config.FONDO_SIMILARITY_THRESHOLD:
                return fn
            return None  # el mejor no llega al umbral → mejor azar
    except Exception:
        return None
    return None


def elegir_fondo(
    phrase: str, env: dict, usados: Optional[set] = None,
    want_orientation: Optional[str] = None,
) -> tuple[Optional[Path], str]:
    """Devuelve (ruta_del_fondo, metodo) para la frase.

    metodo ∈ {'semantico', 'azar', 'sin-fondos'}. `usados` evita repetir fondos
    dentro de la misma tanda.
    """
    usados = usados or set()
    disponibles = listar_fondos_locales()
    if not disponibles:
        return None, "sin-fondos"

    por_nombre = {p.name: p for p in disponibles}

    fn = _match_filename(phrase, env, exclude=usados, want_orientation=want_orientation)
    if fn and fn in por_nombre:
        return por_nombre[fn], "semantico"

    # Azar entre los no usados (o entre todos si ya se agotaron).
    libres = [p for p in disponibles if p.name not in usados] or disponibles
    return random.choice(libres), "azar"

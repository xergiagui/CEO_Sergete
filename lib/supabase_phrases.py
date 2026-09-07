"""
Acceso a la tabla `viral_phrases` de Supabase (el banco de frases que TheEditor
va poblando al analizar virales). TheHistoria LEE de aquí las frases sin usar y,
tras generar la historia, marca `used_in_story = true` para no repetir.

Esquema de la tabla: TheLanding/supabase/viral_phrases.sql
Todo vía REST + anon key (RLS da select/insert/update solo sobre esta tabla).
"""
from __future__ import annotations
from typing import Optional

import httpx

from lib.env import supabase_headers


def fetch_unused_phrases(
    env: dict,
    limit: int = 10,
    categoria: Optional[str] = None,
    min_virality: Optional[int] = None,
) -> list[dict]:
    """Devuelve frases con used_in_story = false, ordenadas por viralidad desc.

    Filtros opcionales: `categoria` (igualdad exacta) y `min_virality`.
    Best-effort: si Supabase no responde, devuelve [].
    """
    url = env.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        return []
    params = {
        "select": "id,phrase,category,angle,tags,virality,source_platform,lang",
        "used_in_story": "eq.false",
        "order": "virality.desc.nullslast,created_at.desc",
        "limit": str(limit),
    }
    if categoria:
        params["category"] = f"eq.{categoria}"
    if min_virality is not None:
        params["virality"] = f"gte.{min_virality}"
    try:
        r = httpx.get(
            f"{url}/rest/v1/viral_phrases",
            params=params,
            headers=supabase_headers(env),
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def mark_used(env: dict, phrase_id: str) -> bool:
    """Marca una frase como ya utilizada en una historia. Best-effort."""
    url = env.get("SUPABASE_URL", "").rstrip("/")
    if not url or not phrase_id:
        return False
    headers = dict(supabase_headers(env))
    headers["Prefer"] = "return=minimal"
    try:
        r = httpx.patch(
            f"{url}/rest/v1/viral_phrases",
            params={"id": f"eq.{phrase_id}"},
            headers=headers,
            json={"used_in_story": True},
            timeout=20,
        )
        return r.status_code < 400
    except Exception:
        return False

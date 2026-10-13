"""
Acceso a la tabla `viral_phrases` de Supabase (el banco de frases que TheEditor
va poblando al analizar virales). TheHistoria LEE de aquí las frases sin usar
DEL PROYECTO (`tags` contiene `proyecto:<id>`) y, tras generar la historia, marca
`used_in_story = true` para no repetir. Nunca se leen frases de otro proyecto.

Esquema de la tabla: TheLanding/supabase/viral_phrases.sql
Todo vía REST + anon key (RLS da select/insert/update solo sobre esta tabla).
"""
from __future__ import annotations
from typing import Optional

import httpx

from lib.env import supabase_headers


def _lista_pg(valores: list[str]) -> str:
    """Valores entre comillas para los filtros de PostgREST (`cs.{…}`, `in.(…)`)."""
    return ",".join('"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'
                    for v in valores)


def fetch_unused_phrases(
    env: dict,
    etiqueta_proyecto: str,
    limit: int = 10,
    categoria: Optional[str] = None,
    min_virality: Optional[int] = None,
    categorias: Optional[list[str]] = None,
    lang: Optional[str] = None,
) -> list[dict]:
    """Frases DEL PROYECTO con used_in_story = false, por viralidad desc.

    `etiqueta_proyecto` (obligatoria, p. ej. «proyecto:mongemalo») debe estar en
    `tags`. Filtros opcionales: `categoria` (igualdad exacta; manda sobre
    `categorias`), `categorias` (cualquiera de la lista), `min_virality` y `lang`.
    Best-effort: si Supabase no responde, devuelve [].
    """
    url = env.get("SUPABASE_URL", "").rstrip("/")
    if not url or not etiqueta_proyecto:
        return []
    params = {
        "select": "id,phrase,category,angle,tags,virality,source_platform,lang",
        "used_in_story": "eq.false",
        "tags": "cs.{" + _lista_pg([etiqueta_proyecto]) + "}",
        "order": "virality.desc.nullslast,created_at.desc",
        "limit": str(limit),
    }
    if categoria:
        params["category"] = f"eq.{categoria}"
    elif categorias:
        params["category"] = "in.(" + _lista_pg(categorias) + ")"
    if min_virality is not None:
        params["virality"] = f"gte.{min_virality}"
    if lang:
        params["lang"] = f"eq.{lang}"
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

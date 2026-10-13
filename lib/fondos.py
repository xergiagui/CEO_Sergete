"""
Selección del FONDO de una historia según la POLÍTICA DE B-ROLL del proyecto
(TheEditor/proyectos/<id>/proyecto.json → recursos.broll):

  banco_comun  el MISMO banco que TheEditor: `TheEditor/superposiciones/`,
               catalogado en Supabase (`broll_assets`). Casa la frase con la RPC
               `match_broll` y coge el más afín; si no hay Supabase/embeddings o
               nada supera el umbral, al azar. Con `internet: false` se excluyen
               los clips bajados de internet (prefijo `pexels_`).
  propio       SOLO `TheEditor/proyectos/<id>/recursos/broll/`. Semántica LOCAL
               si hay `_indice.json` (sin Supabase ni el catálogo común); si no,
               al azar. Nunca toca el banco común.
  ninguno      sin vídeo: fondo liso del color de marca (metodo "liso").

Devuelve (ruta | None, metodo) con metodo ∈ {semantico, semantico-local, azar,
liso, sin-fondos}.
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Optional

import httpx

import config
from lib.env import has_supabase, supabase_headers

_aviso_cache: Optional[set] = None
_indice_cache: dict = {}
_emb_texto_cache: dict = {}


def _videos(d: Path, recursivo: bool = False) -> list[Path]:
    if not d.is_dir():
        return []
    it = d.rglob("*") if recursivo else d.iterdir()
    return sorted(p for p in it
                  if p.is_file() and p.suffix.lower() in config.VIDEO_EXTS
                  and not p.name.startswith(("_", ".")))


# ------------------------------------------------------------ banco común
def listar_fondos_locales(internet: bool = True) -> list[Path]:
    """Vídeos del banco común (superposiciones/), sin los de internet si se pide."""
    fondos = _videos(config.FONDOS_DIR)
    if not internet:
        fondos = [p for p in fondos if not p.name.lower().startswith(config.PREFIJOS_INTERNET)]
    return fondos


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
    """Filename del fondo del banco común más afín a la frase (o None)."""
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


def _elegir_banco_comun(phrase, env, usados, want_orientation, internet):
    disponibles = listar_fondos_locales(internet)
    if not disponibles:
        return None, "sin-fondos"
    por_nombre = {p.name: p for p in disponibles}
    fn = _match_filename(phrase, env, exclude=usados, want_orientation=want_orientation)
    if fn and fn in por_nombre:
        return por_nombre[fn], "semantico"
    libres = [p for p in disponibles if p.name not in usados] or disponibles
    return random.choice(libres), "azar"


# ------------------------------------------------------------ b-roll propio
def listar_fondos_propios(proyecto) -> list[Path]:
    """Vídeos de TheEditor/proyectos/<id>/recursos/broll/ (incluye subcarpetas)."""
    return _videos(proyecto.broll_propio_dir, recursivo=True)


_CLAVES_ARCHIVO = ("archivo", "filename", "file", "nombre", "ruta", "path")
_CLAVES_TEXTO = ("descripcion", "description", "texto", "tema", "tags", "logical_tags",
                 "etiquetas", "keywords")


def _entradas_indice(data) -> list[dict]:
    """Admite lista de entradas, {items|assets|clips|broll|archivos: […]} o
    {archivo: entrada}. Cada entrada: archivo + embedding y/o texto descriptivo."""
    if isinstance(data, dict):
        for k in ("items", "assets", "clips", "broll", "archivos", "videos"):
            if isinstance(data.get(k), list):
                return [x for x in data[k] if isinstance(x, dict)]
        out = []
        for k, v in data.items():
            if str(k).startswith("_"):
                continue
            out.append(dict(v, archivo=v.get("archivo", k)) if isinstance(v, dict)
                       else {"archivo": k, "texto": v})
        return out
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def _texto_entrada(e: dict) -> str:
    partes = []
    for k in _CLAVES_TEXTO:
        v = e.get(k)
        if isinstance(v, str):
            partes.append(v)
        elif isinstance(v, list):
            partes.append(", ".join(str(x) for x in v))
    return ". ".join(p for p in partes if p.strip())


def _cargar_indice(base: Path) -> list[tuple[str, list[float] | None, str, dict]]:
    """(nombre_relativo, embedding|None, texto, entrada) del `_indice.json`."""
    f = base / "_indice.json"
    if not f.exists():
        return []
    key = (str(f), f.stat().st_mtime)
    if key in _indice_cache:
        return _indice_cache[key]
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for e in _entradas_indice(data):
        nombre = next((str(e[k]) for k in _CLAVES_ARCHIVO if e.get(k)), "")
        if not nombre:
            continue
        emb = e.get("embedding") or e.get("vector")
        emb = [float(x) for x in emb] if isinstance(emb, list) and emb else None
        out.append((nombre.replace("\\", "/"), emb, _texto_entrada(e), e))
    _indice_cache[key] = out
    return out


def _coseno(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return -1.0
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else -1.0


def _match_propio(phrase: str, proyecto, disponibles: list[Path], usados: set,
                  want_orientation: Optional[str], internet: bool) -> Optional[Path]:
    """Fondo propio más afín según `_indice.json` (embeddings locales) o None."""
    base = proyecto.broll_propio_dir
    indice = _cargar_indice(base)
    if not indice or not (phrase or "").strip():
        return None
    por_rel = {p.relative_to(base).as_posix(): p for p in disponibles}
    por_nombre = {p.name: p for p in disponibles}
    if not internet:
        # El modelo de embeddings solo se lee de la caché local: nada de red.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    try:
        from lib.embeddings import embed_text
        q = embed_text(phrase)
        mejor, mejor_sim = None, -1.0
        for nombre, emb, texto, e in indice:
            p = por_rel.get(nombre) or por_nombre.get(Path(nombre).name)
            if p is None or p.name in usados:
                continue
            tags = e.get("logical_tags") or e.get("tags") or []
            if isinstance(tags, list) and any(str(t).startswith("aviso") for t in tags):
                continue
            ori = e.get("orientation") or e.get("orientacion")
            if want_orientation and ori and ori != want_orientation:
                continue
            if emb is None:
                if not texto:
                    continue
                if texto not in _emb_texto_cache:
                    _emb_texto_cache[texto] = embed_text(texto)
                emb = _emb_texto_cache[texto]
            sim = _coseno(q, emb)
            if sim > mejor_sim:
                mejor, mejor_sim = p, sim
        if mejor is not None and mejor_sim >= config.FONDO_SIMILARITY_THRESHOLD:
            return mejor
    except Exception:
        return None
    return None


def _elegir_propio(phrase, proyecto, usados, want_orientation, internet):
    disponibles = listar_fondos_propios(proyecto)
    if not disponibles:
        return None, "sin-fondos"
    p = _match_propio(phrase, proyecto, disponibles, usados, want_orientation, internet)
    if p is not None:
        return p, "semantico-local"
    libres = [p for p in disponibles if p.name not in usados] or disponibles
    return random.choice(libres), "azar"


# ------------------------------------------------------------ entrada
def elegir_fondo(
    phrase: str, env: dict, proyecto, usados: Optional[set] = None,
    want_orientation: Optional[str] = None,
) -> tuple[Optional[Path], str]:
    """(ruta_del_fondo, metodo) para la frase según la política del proyecto.

    `usados` evita repetir fondos dentro de la misma tanda.
    """
    usados = usados or set()
    if proyecto.broll == "ninguno":
        return None, "liso"
    if proyecto.broll == "propio":
        return _elegir_propio(phrase, proyecto, usados, want_orientation, proyecto.internet)
    return _elegir_banco_comun(phrase, env, usados, want_orientation, proyecto.internet)


def hay_fondos(proyecto) -> bool:
    """¿Tiene el proyecto de dónde sacar fondos? (`ninguno` siempre: fondo liso)."""
    if proyecto.broll == "ninguno":
        return True
    if proyecto.broll == "propio":
        return bool(listar_fondos_propios(proyecto))
    return bool(listar_fondos_locales(proyecto.internet))


def origen_fondos(proyecto) -> str:
    """Texto para el log/errores: de dónde salen los fondos del proyecto."""
    if proyecto.broll == "ninguno":
        return f"fondo liso {proyecto.color_liso}"
    if proyecto.broll == "propio":
        return str(proyecto.broll_propio_dir)
    return str(config.FONDOS_DIR) + ("" if proyecto.internet else " (sin clips de internet)")

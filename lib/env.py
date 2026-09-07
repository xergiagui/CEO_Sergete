"""
Carga de credenciales (Supabase) para TheHistoria.

Busca en este orden (el primero que exista gana), sin subir nunca secretos a git:
  1. TheHistoria/.env            (dotenv KEY=VALUE, propio del departamento)
  2. CEO_Sergete/.env            (el .env compartido del centro de mando)
  3. ~/.viral-pipeline/env.json  (env del pipeline de TheEditor, formato JSON)

Devuelve un dict con al menos SUPABASE_URL y SUPABASE_ANON_KEY si están.
Best-effort: si no hay credenciales, devuelve lo que encuentre (posiblemente {})
y quien llame decide (p. ej. modo local sin Supabase).
"""
from __future__ import annotations
import json
from pathlib import Path

import config


def _parse_dotenv(path: Path) -> dict:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def load_env() -> dict:
    env: dict = {}

    candidates_dotenv = [
        config.PROJECT_ROOT / ".env",
        config.CEO_ROOT / ".env",
    ]
    for p in candidates_dotenv:
        if p.exists():
            try:
                env.update(_parse_dotenv(p))
                break
            except Exception:
                pass

    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_ANON_KEY"):
        editor_env = Path.home() / ".viral-pipeline" / "env.json"
        if editor_env.exists():
            try:
                data = json.loads(editor_env.read_text(encoding="utf-8"))
                for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
                    env.setdefault(k, data.get(k))
            except Exception:
                pass

    return env


def supabase_headers(env: dict) -> dict:
    key = env.get("SUPABASE_ANON_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def has_supabase(env: dict) -> bool:
    return bool(env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY"))

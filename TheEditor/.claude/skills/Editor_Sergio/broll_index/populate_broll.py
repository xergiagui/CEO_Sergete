#!/usr/bin/env python3
"""Sube (upsert) los 70 registros de broll_final.json a la tabla
public.broll_assets de Supabase, usando la key anon de TheLanding/.env.local.
Requiere que broll_assets.sql ya se haya ejecutado (tabla + policies anon)."""
import json, sys
from pathlib import Path
import httpx

ENV = Path(r"C:\Users\ico858\Desktop\PruebasIA\TheLanding\.env.local")
HERE = Path(__file__).resolve().parent

def read_env(path):
    d = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d

env = read_env(ENV)
URL = env["SUPABASE_URL"].rstrip("/")
KEY = env["SUPABASE_ANON_KEY"]
recs = json.loads((HERE/"broll_final.json").read_text(encoding="utf-8"))

# pgvector acepta la representación textual "[a,b,c]"
rows = []
for r in recs:
    row = dict(r)
    row["embedding"] = "[" + ",".join(str(x) for x in r["embedding"]) + "]"
    row.pop("idx", None)
    rows.append(row)

endpoint = f"{URL}/rest/v1/broll_assets?on_conflict=filename"
headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}

BATCH = 20
ok = 0
with httpx.Client(timeout=60) as c:
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        r = c.post(endpoint, headers=headers, json=chunk)
        if r.status_code >= 400:
            print(f"  ERR lote {i//BATCH+1}: HTTP {r.status_code}\n     {r.text[:500]}")
            sys.exit(1)
        ok += len(chunk)
        print(f"  OK lote {i//BATCH+1}: {len(chunk)} filas (acumulado {ok})")

# verificación: contar filas
r = httpx.get(f"{URL}/rest/v1/broll_assets?select=count",
              headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                       "Prefer": "count=exact"}, timeout=30)
print(f"\nSubidas {ok} filas. Conteo remoto: {r.headers.get('content-range')}")

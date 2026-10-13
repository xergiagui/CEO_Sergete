#!/usr/bin/env python3
"""Genera embeddings (384d) del search_text de cada b-roll con
paraphrase-multilingual-MiniLM-L12-v2 (fastembed). Output: broll_final.json."""
import json
from pathlib import Path
import sys
import warnings
from fastembed import TextEmbedding

warnings.filterwarnings("ignore", message=".*mean pooling.*")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_core import _fastembed_cache_dir  # caché en whisper/models/fastembed

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
HERE = Path(__file__).resolve().parent
recs = json.loads((HERE/"broll_records.json").read_text(encoding="utf-8"))

print(f"Cargando modelo {MODEL} ...")
emb = TextEmbedding(model_name=MODEL, cache_dir=_fastembed_cache_dir())
texts = [r["search_text"] for r in recs]
print(f"Embebiendo {len(texts)} textos ...")
vecs = list(emb.embed(texts))
for r, v in zip(recs, vecs):
    r["embedding"] = [round(float(x), 6) for x in v]

dim = len(recs[0]["embedding"])
(HERE/"broll_final.json").write_text(
    json.dumps(recs, ensure_ascii=False), encoding="utf-8")
print(f"OK: {len(recs)} registros con embedding de {dim} dims -> broll_final.json")
assert dim == 384, f"dim inesperada {dim}"

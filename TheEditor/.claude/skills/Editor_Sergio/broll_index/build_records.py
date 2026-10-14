#!/usr/bin/env python3
"""Fusiona metadatos técnicos (broll_tech.json) + semánticos (sem/sem_*.json)
por idx y construye el search_text de cada clip. Output: broll_records.json."""
import json, glob, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
tech = {}
for tf in sorted(glob.glob(str(HERE/"broll_tech*.json"))):
    for r in json.loads(Path(tf).read_text(encoding="utf-8")):
        tech[r["idx"]] = r

sem = {}
for f in sorted(glob.glob(str(HERE/"sem"/"sem_*.json"))):
    for r in json.loads(Path(f).read_text(encoding="utf-8")):
        sem[r["idx"]] = r

records = []
for idx in sorted(tech):
    t = tech[idx]
    s = sem.get(idx)
    if not s:
        print(f"  ⚠ idx {idx} ({t['filename']}) SIN metadatos semánticos")
        continue
    # sanity: los filenames deben coincidir
    if s["filename"] != t["filename"]:
        print(f"  ⚠ idx {idx}: filename semántico '{s['filename']}' != técnico '{t['filename']}'")
    objects = s.get("objects", [])
    actions = s.get("actions", [])
    mood = s.get("mood", [])
    concepts = s.get("concepts", [])
    tags = s.get("logical_tags", [])
    name_clean = os.path.splitext(t["filename"])[0].replace("_", " ")
    search_text = (
        f"{name_clean}. {s.get('description','')} "
        f"Escenario: {s.get('setting','')}. "
        f"Objetos: {', '.join(objects)}. "
        f"Acciones: {', '.join(actions)}. "
        f"Tono: {', '.join(mood)}. "
        f"Temas: {', '.join(concepts)}. "
        f"Categoría: {s.get('category','')}. "
        f"Etiquetas: {', '.join(tags)}."
    )
    records.append({
        "filename": t["filename"],
        "abs_path": t["abs_path"],
        "category": s.get("category"),
        "logical_tags": tags,
        "duration": t["duration"],
        "width": t["width"],
        "height": t["height"],
        # orientación: fiarse de la visual (la técnica falla con rotación iPhone)
        "orientation": s.get("orientation") or t["orientation"],
        "fps": t["fps"],
        "has_audio": t["has_audio"],
        "description": s.get("description"),
        "objects": objects,
        "setting": s.get("setting"),
        "actions": actions,
        "mood": mood,
        "concepts": concepts,
        "search_text": " ".join(search_text.split()),
    })

(HERE/"broll_records.json").write_text(
    json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

# resumen
from collections import Counter
orient = Counter(r["orientation"] for r in records)
warn = sum(1 for r in records if any("aviso" in t for t in r["logical_tags"]))
print(f"OK: {len(records)} registros -> broll_records.json")
print(f"  orientacion: {dict(orient)}")
print(f"  con aviso (marca/persona/calidad): {warn}")
print("  ejemplo search_text[0]:")
print("   ", records[0]["search_text"][:200], "...")

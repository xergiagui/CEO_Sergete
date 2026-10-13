#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Índice semántico LOCAL del b-roll propio de un proyecto (recursos.broll = propio).

Sirve para casar cada frase del clip con el b-roll del proyecto por significado,
sin Supabase ni el catálogo común: todo queda en
proyectos/<id>/recursos/broll/_indice.json y se calcula con el MISMO modelo de
embeddings que el catálogo común (fastembed, paraphrase-multilingual-MiniLM-L12-v2).
Sin índice, el render pone el b-roll propio al azar sin repetir dentro del clip.

Flujo (3 pasos, como el catálogo común):
  1) python indexar_broll.py --proyecto <id> --frames
       -> recursos/broll/_frames/<clip>.jpg (3 fotogramas: 20/50/80 %) y
          recursos/broll/_descripciones.json con una entrada por clip nuevo.
  2) El editor (LLM) mira cada montaje y escribe en _descripciones.json qué se ve:
       {"<ruta relativa del clip>": {"descripcion": "...", "logical_tags": []}}
     (o solo el texto). Una etiqueta que empiece por «aviso» (aviso-marca-ajena,
     aviso-persona-identificable, aviso-marca-agua, aviso-baja-calidad) lo excluye.
  3) python indexar_broll.py --proyecto <id>
       -> _indice.json (embedding de «nombre + descripción» por clip).
Es idempotente: se puede relanzar al añadir o quitar clips. Un clip sin
descripción se indexa por su nombre de archivo (con aviso).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / ".claude" / "skills" / "Editor_Sergio"))
import pipeline_core as pc  # noqa: E402
import proyecto  # noqa: E402

DESCRIPCIONES = "_descripciones.json"
FRAMES = "_frames"


def _leer_json(p: Path, defecto):
    if not p.exists():
        return defecto
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"[!] {p} no es un JSON válido: {e}")


def _entrada(v) -> dict:
    """Normaliza una descripción: texto suelto o {descripcion, logical_tags}."""
    if isinstance(v, dict):
        return {"descripcion": str(v.get("descripcion") or v.get("description") or "").strip(),
                "logical_tags": [str(t) for t in (v.get("logical_tags") or v.get("tags") or [])]}
    return {"descripcion": str(v or "").strip(), "logical_tags": []}


def extraer_frames(clips: dict, broll_dir: Path) -> int:
    ff = pc.get_ffmpeg_exe()
    out_dir = broll_dir / FRAMES
    out_dir.mkdir(exist_ok=True)
    hechos = 0
    for rel, path in clips.items():
        dest = out_dir / (rel.replace("/", "__") + ".jpg")
        if dest.exists():
            continue
        try:
            dur = pc._get_duration(path, ff)
        except Exception:
            dur = 0.0
        ts = [max(dur * f, 0.0) for f in (0.2, 0.5, 0.8)] if dur > 0 else [0, 0, 0]
        cmd = [ff, "-y"]
        for t in ts:
            cmd += ["-ss", f"{t:.2f}", "-i", str(path)]
        cmd += ["-filter_complex",
                "[0:v]scale=-2:360,setsar=1[a];[1:v]scale=-2:360,setsar=1[b];"
                "[2:v]scale=-2:360,setsar=1[c];[a][b][c]hstack=inputs=3[v]",
                "-map", "[v]", "-frames:v", "1", "-q:v", "4", str(dest)]
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        if r.returncode == 0 and dest.exists():
            hechos += 1
        else:
            print(f"   [frames] no pude extraer {rel}")
    return hechos


def main():
    ap = argparse.ArgumentParser(description="Índice semántico local del b-roll propio.")
    proyecto.add_argumento(ap)
    ap.add_argument("--frames", action="store_true",
                    help="Paso 1: montajes en _frames/ + plantilla de _descripciones.json (sin indexar).")
    args = ap.parse_args()
    p = proyecto.abrir(args.proyecto, "indexar_broll", log=False)
    if p.recursos["broll"] != "propio":
        raise SystemExit(f"[!] El proyecto «{p.id}» usa b-roll «{p.recursos['broll']}»: el índice "
                         f"local es solo para b-roll propio (el banco común usa broll_assets).")
    broll_dir = p.overlays_dir
    broll_dir.mkdir(parents=True, exist_ok=True)
    clips = pc.list_overlays_recursive(broll_dir)
    if not clips:
        raise SystemExit(f"[!] No hay vídeos en {broll_dir}.")
    desc_path = broll_dir / DESCRIPCIONES
    descripciones = _leer_json(desc_path, {})

    if args.frames:
        n = extraer_frames(clips, broll_dir)
        nuevos = [rel for rel in clips if rel not in descripciones]
        for rel in nuevos:
            descripciones[rel] = {"descripcion": "", "logical_tags": []}
        desc_path.write_text(json.dumps(descripciones, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        print(f"{len(clips)} clips · {n} montajes nuevos en {broll_dir / FRAMES}\n"
              f"{len(nuevos)} entradas nuevas en {desc_path}: describe cada clip y lanza sin --frames.")
        return

    archivos, sin_desc, avisos = [], [], 0
    textos = []
    for rel in clips:
        e = _entrada(descripciones.get(rel))
        nombre = Path(rel).stem.replace("_", " ").replace("-", " ")
        if not e["descripcion"]:
            sin_desc.append(rel)
        if any(t.startswith("aviso") for t in e["logical_tags"]):
            avisos += 1
        texto = f"{nombre}. {e['descripcion']}".strip()
        archivos.append({"archivo": rel, "descripcion": e["descripcion"] or nombre,
                         "logical_tags": e["logical_tags"]})
        textos.append(texto)
    print(f"Embebiendo {len(textos)} clips con {pc._EMBED_MODEL_NAME} (local)...")
    vecs = list(pc._get_embed_model().embed(textos))
    for a, v in zip(archivos, vecs):
        a["embedding"] = [round(float(x), 6) for x in v]
    dim = len(archivos[0]["embedding"])
    indice = {"modelo": pc._EMBED_MODEL_NAME, "dim": dim, "archivos": archivos}
    out = broll_dir / pc.INDICE_BROLL
    out.write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    print(f"OK -> {out}  ({len(archivos)} clips, {dim} dims, {avisos} con aviso)")
    if sin_desc:
        print(f"AVISO: {len(sin_desc)} sin descripción (indexados por el nombre): "
              + ", ".join(sin_desc[:10]) + (" …" if len(sin_desc) > 10 else ""))


if __name__ == "__main__":
    main()

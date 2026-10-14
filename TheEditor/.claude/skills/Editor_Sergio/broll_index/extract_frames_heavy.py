#!/usr/bin/env python3
"""Igual que extract_frames.py pero para los clips OMITIDOS (los más pesados):
procesa vids[70:] en orden ascendente de tamaño -> idx 71..92.
Output: frames/ (mismos) + broll_tech_heavy.json"""
import json, re, subprocess, unicodedata
from pathlib import Path
_RAIZ = Path(__file__).resolve().parents[4]  # TheEditor
import sys as _sys
_sys.path.insert(0, str(_RAIZ))
import herramientas  # ffmpeg común de TheEditor

FF = herramientas.exigir_ffmpeg()
SRC = Path(r"C:\Users\ico858\Desktop\PruebasIA\TheEditor\superposiciones")
OUT = Path(__file__).resolve().parent
FRAMES = OUT / "frames"; FRAMES.mkdir(exist_ok=True)
SKIP_FIRST = 70

def slugify(name, i):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w]+", "-", s).strip("-").lower()
    return f"{i:02d}__{s[:40]}"

def probe(path):
    r = subprocess.run([FF, "-i", str(path), "-hide_banner"],
                       capture_output=True, text=True, errors="replace")
    e = r.stderr; dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", e)
    if m: dur = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
    w = h = 0; fps = 0.0
    mv = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", e)
    if mv: w, h = int(mv.group(1)), int(mv.group(2))
    mf = re.search(r"([\d.]+)\s*fps", e)
    if mf: fps = round(float(mf.group(1)), 3)
    has_audio = bool(re.search(r"Stream #\d+:\d+.*: Audio:", e))
    rot = 0
    mr = re.search(r"rotat(?:e|ion)\s*[:=]\s*(-?\d+)", e)
    if mr: rot = abs(int(mr.group(1))) % 180
    if rot == 90: w, h = h, w
    orient = "vertical" if h >= w else "horizontal"
    return dur, w, h, fps, has_audio, orient

def frame_at(path, t, out_jpg):
    subprocess.run([FF, "-y", "-ss", f"{t:.2f}", "-i", str(path),
                    "-frames:v", "1", "-vf", "scale=-2:360", "-q:v", "3", str(out_jpg)],
                   capture_output=True, text=True)
    return out_jpg.exists() and out_jpg.stat().st_size > 1000

def montage(path, dur, out_jpg):
    tmps = []; fracs = [0.2, 0.5, 0.8] if dur > 1 else [0.1, 0.3, 0.5]
    for k, fr in enumerate(fracs):
        t = max(0.1, dur * fr)
        tj = out_jpg.with_name(out_jpg.stem + f"_f{k}.jpg")
        if frame_at(path, t, tj): tmps.append(tj)
    if not tmps: return False
    if len(tmps) == 1: tmps[0].replace(out_jpg); return True
    inputs = []
    for tj in tmps: inputs += ["-i", str(tj)]
    n = len(tmps)
    filt = "".join(f"[{i}:v]" for i in range(n)) + f"hstack=inputs={n}"
    subprocess.run([FF, "-y", *inputs, "-filter_complex", filt, "-q:v", "3", str(out_jpg)],
                   capture_output=True, text=True)
    for tj in tmps: tj.unlink(missing_ok=True)
    return out_jpg.exists()

vids = [p for p in SRC.iterdir() if p.is_file() and p.suffix.lower() in (".mov", ".mp4")]
vids.sort(key=lambda p: p.stat().st_size)
heavy = vids[SKIP_FIRST:]
print(f"{len(vids)} total; proceso los {len(heavy)} pesados (idx 71..{70+len(heavy)}).")

records = []
for j, p in enumerate(heavy):
    idx = SKIP_FIRST + 1 + j
    slug = slugify(p.stem, idx)
    mj = FRAMES / f"{slug}.jpg"
    dur, w, h, fps, has_audio, orient = probe(p)
    ok = montage(p, dur, mj)
    records.append({"idx": idx, "filename": p.name, "abs_path": str(p),
        "size_mb": round(p.stat().st_size/1048576, 1), "duration": round(dur, 2),
        "width": w, "height": h, "orientation": orient, "fps": fps,
        "has_audio": has_audio, "montage": str(mj) if ok else None})
    print(f"  [{idx}] {p.name} | {dur:.1f}s {w}x{h} {orient} | {'OK' if ok else 'SIN FRAMES'}")

(OUT / "broll_tech_heavy.json").write_text(
    json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"OK: {len(records)} registros -> broll_tech_heavy.json")

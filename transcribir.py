#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 1 del flujo — Transcripción (solo sirve para ELEGIR los cortes).

Convierte el audio a WAV 16 kHz mono y lo transcribe con whisper.cpp (100 %
local). Modelo: `whisper/models/ggml-large-v3-turbo*.bin` si existe (más
rápido); si no, `ggml-large-v3.bin`. Sin DTW: los tiempos por palabra los saca
después faster-whisper sobre cada clip (editar_clips.py), y aquí basta el
tiempo por frase.

Trabaja por PROYECTO (`--proyecto <id>`, ver proyecto.py): lee del buzón
proyectos/<id>/input/ y escribe en proyectos/<id>/transcripciones/<nombre>/:
    - <nombre>.cortes.txt -> LO QUE LEE EL EDITOR (LLM) para elegir los cortes:
                             cabecera (duración + nº de clips sugerido) y una
                             línea por frase «[612.3–618.9] texto»; una línea
                             en blanco marca una pausa de más de 1,5 s.
    - <nombre>.txt / .srt / .json -> texto plano, subtítulos y JSON de whisper.

Vídeos largos: si el audio supera --umbral-min (def 35) se trocea en fragmentos
de ~--chunk-min (def 10). Cada corte cae en el SILENCIO más cercano (±30 s) para
no partir palabras; si no hay silencio, el fragmento se alarga 2 s (solape) y
se descartan los segmentos repetidos. Después se fusionan los formatos.

Uso:
    python transcribir.py --proyecto mongemalo              -> todo su input/
    python transcribir.py --proyecto mongemalo "video.mp4"  -> uno de su input/
    python transcribir.py --proyecto mongemalo "C:/ruta/v.mp4"   (cualquier ruta)
    python transcribir.py --proyecto x "video.mp4" --forzar   -> aunque ya esté hecho
    python transcribir.py --cortes-txt "C:/…/video.json" [--salida <dir>]
        -> solo (re)genera <video>.cortes.txt desde un JSON de whisper.cpp
Si solo hay un proyecto, --proyecto se puede omitir.

Se SALTA lo que ya está transcrito (transcripciones/<nombre>/<nombre>.txt) o ya
aprobado y archivado (_Historico/<id>/<nombre>/), salvo con --forzar. Si a lo ya
transcrito le falta el .cortes.txt, se genera sin volver a transcribir.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import herramientas
import proyecto

RAIZ = Path(__file__).resolve().parent
EXTENSIONES = {".mp4", ".mkv", ".mov", ".m4v", ".avi", ".webm", ".m4a", ".mp3", ".wav",
               ".flac", ".ogg", ".aac"}

FFMPEG = herramientas.FFMPEG
WHISPER_CLI = RAIZ / "whisper" / "bin" / "whisper-cli.exe"
MODELOS_DIR = RAIZ / "whisper" / "models"


def _modelo() -> Path:
    """large-v3-turbo si está descargado (no se descarga nada); si no, large-v3."""
    turbo = sorted(MODELOS_DIR.glob("ggml-large-v3-turbo*.bin"))
    return turbo[0] if turbo else MODELOS_DIR / "ggml-large-v3.bin"


MODELO = _modelo()

# Troceo automático de vídeos largos (evita que whisper se corte por el límite
# de tiempo de las tareas en segundo plano).
UMBRAL_TROCEO_MIN = 35   # a partir de esta duración (min) se trocea
CHUNK_MIN = 10           # duración (min) de cada fragmento
VENTANA_SILENCIO = 30.0  # s alrededor del corte nominal donde buscar un silencio
SOLAPE = 2.0             # s de solape si no hay silencio cerca

# cortes.txt
PAUSA_LARGA = 1.5        # s: pausa que se marca con una línea en blanco
FRASE_MAX = 20.0         # s: una «frase» sin puntuación se parte a este tamaño
_FIN_FRASE = re.compile(r"[.?!…][\"'»”)\]]*$")


def run(cmd, cwd=None):
    try:
        return herramientas.ejecutar(cmd, cwd=cwd)
    except RuntimeError as e:
        raise SystemExit(f"[!] {e}")


def a_wav_16k_mono(origen: Path, destino: Path):
    """Convierte a WAV 16 kHz mono PCM (lo que espera whisper.cpp)."""
    run([FFMPEG, "-y", "-i", str(origen), "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", str(destino)])


def _ms_a_ts(ms: int) -> str:
    """Milisegundos -> 'HH:MM:SS,mmm' (formato SRT / whisper)."""
    h, ms = divmod(int(ms), 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def whisper_cli(wav_rel: str, out_rel: str, idioma: str, formatos):
    """whisper.cpp sobre un WAV (rutas RELATIVAS ASCII, cwd=RAIZ). Sin DTW."""
    cmd = [str(WHISPER_CLI),
           "-m", Path(os.path.relpath(MODELO, RAIZ)).as_posix(),
           "-f", wav_rel,
           "-l", idioma,
           "-t", str(max(4, os.cpu_count() or 4))]
    if "txt" in formatos:
        cmd.append("-otxt")
    if "srt" in formatos:
        cmd.append("-osrt")
    if "json" in formatos:
        cmd.append("-oj")
    cmd += ["-of", out_rel]
    run(cmd, cwd=str(RAIZ))


def escribir_srt(destino: Path, segmentos: list):
    """.srt con el formato de whisper.cpp (CRLF, línea en blanco entre bloques)."""
    lineas = []
    for i, s in enumerate(segmentos, 1):
        lineas.append(str(i))
        lineas.append(f"{s['timestamps']['from']} --> {s['timestamps']['to']}")
        lineas.append(s["text"])
        lineas.append("")
    destino.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8", newline="")


def escribir_txt(destino: Path, segmentos: list):
    """.txt con el formato de whisper.cpp (una frase por línea, CRLF)."""
    lineas = [s["text"].strip() for s in segmentos]
    destino.write_text("\r\n".join(lineas) + "\r\n", encoding="utf-8", newline="")


# ------------------------------------------------------------------ cortes.txt
def clips_sugeridos(dur_s: float) -> int:
    """1 clip cada ~3 min, mínimo 3 y máximo 6."""
    return int(min(6, max(3, round(dur_s / 180.0))))


def _mmss(s: float) -> str:
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def _trozos_de_frase(segs: list) -> list[tuple[float, float, str]]:
    """(inicio, fin, texto) por frase: un segmento de whisper con varias frases
    se parte en su puntuación, repartiendo su tiempo según la longitud."""
    out = []
    for s in segs:
        a, b = s["offsets"]["from"] / 1000.0, s["offsets"]["to"] / 1000.0
        t = re.sub(r"\s+", " ", s["text"]).strip()
        partes = [x for x in re.split(r"(?<=[.?!…])\s+", t) if x]
        total = sum(len(x) for x in partes) or 1
        cur = a
        for x in partes:
            fin = cur + (b - a) * len(x) / total
            out.append((round(cur, 2), round(fin, 2), x))
            cur = fin
    return out


def escribir_cortes_txt(segmentos: list, destino: Path, nombre: str, dur_s: float | None = None) -> int:
    """<video>.cortes.txt: lo único que lee el editor (LLM) para elegir cortes.
    Devuelve el nº de frases."""
    segs = [s for s in segmentos if (s.get("text") or "").strip()]
    if dur_s is None:
        dur_s = max((s["offsets"]["to"] for s in segs), default=0) / 1000.0
    lineas, cur, ultimo_fin, n = [], None, None, 0

    def volcar():
        nonlocal cur, n
        if cur:
            lineas.append(f"[{cur[0]:.1f}–{cur[1]:.1f}] {cur[2]}")
            n += 1
        cur = None

    for a, b, t in _trozos_de_frase(segs):
        if ultimo_fin is not None and a - ultimo_fin > PAUSA_LARGA:
            volcar()
            lineas.append("")
        if cur is None:
            cur = [a, b, t]
        else:
            cur[1], cur[2] = b, f"{cur[2]} {t}"
        ultimo_fin = b
        if _FIN_FRASE.search(t) or cur[1] - cur[0] >= FRASE_MAX:
            volcar()
    volcar()
    cab = [f"# {nombre} · duración {_mmss(dur_s)} ({dur_s:.0f} s) · clips sugeridos: "
           f"{clips_sugeridos(dur_s)} (1 cada 3 min, mín. 3, máx. 6)",
           "# Una línea por frase: [inicio–fin] texto, en segundos del vídeo. "
           "Línea en blanco = pausa de más de 1,5 s.", ""]
    destino.write_text("\n".join(cab + lineas) + "\n", encoding="utf-8")
    return n


def cortes_txt_desde_json(json_path: Path, destino: Path | None = None) -> tuple[Path, int]:
    """(Re)genera <video>.cortes.txt desde un JSON de whisper.cpp."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    stem = Path(json_path).stem
    destino = Path(destino) if destino else Path(json_path).parent
    destino.mkdir(parents=True, exist_ok=True)
    out = destino / f"{stem}.cortes.txt"
    n = escribir_cortes_txt(data.get("transcription") or [], out, stem)
    return out, n


# ------------------------------------------------------------------ troceo
def _silencios(wav: Path) -> list[float]:
    """Puntos medios de los silencios del audio (≥ 0,4 s a −35 dB)."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(wav),
                        "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ini = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r.stderr)]
    fin = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r.stderr)]
    return [(a + b) / 2 for a, b in zip(ini, fin)]


def _tramos(dur: float, chunk: float, silencios: list[float]) -> list[tuple[float, float]]:
    """[(inicio, fin)] de cada fragmento: cortes en el silencio más cercano al
    corte nominal; sin silencio cerca, el fragmento se alarga SOLAPE s."""
    n = max(1, round(dur / chunk))
    bordes, solapes = [0.0], []
    for k in range(1, n):
        nominal = k * dur / n
        cands = [m for m in silencios if abs(m - nominal) <= VENTANA_SILENCIO and m > bordes[-1] + 60]
        if cands:
            bordes.append(min(cands, key=lambda m: abs(m - nominal)))
            solapes.append(0.0)
        else:
            bordes.append(nominal)
            solapes.append(SOLAPE)
    bordes.append(dur)
    solapes.append(0.0)
    return [(bordes[i], min(dur, bordes[i + 1] + solapes[i])) for i in range(n)]


def transcribir(origen: Path, idioma: str = "es",
                umbral_seg: float = UMBRAL_TROCEO_MIN * 60,
                chunk_seg: float = CHUNK_MIN * 60,
                work_dir: Path | None = None,
                salida: Path | None = None) -> str:
    """Transcribe `origen` en <salida>/<stem>/. Devuelve la línea de resumen."""
    if salida is None:
        raise ValueError("falta la carpeta de salida (transcripciones/ del proyecto)")
    print(f"\n=> Paso 1 — Transcribiendo: {origen.name}  (modelo {MODELO.name})")
    base = Path(salida) / origen.stem
    base.mkdir(parents=True, exist_ok=True)

    # whisper-cli usa fopen ANSI: las tildes de la ruta lo rompen. Trabajamos en
    # un dir ASCII ÚNICO por proceso bajo whisper/ (seguro en paralelo) y pasamos
    # rutas RELATIVAS con cwd=RAIZ; luego se mueve a `base`.
    base_work = RAIZ / "whisper"
    base_work.mkdir(parents=True, exist_ok=True)
    if work_dir is not None:
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        _work_es_propio = False  # dir suministrado: no lo borramos al final
    else:
        work = Path(tempfile.mkdtemp(prefix="_work_", dir=str(base_work)))
        _work_es_propio = True
    work_rel = Path(os.path.relpath(work, RAIZ)).as_posix()
    wav = work / "audio.wav"

    print("   [1/2] convirtiendo a WAV 16 kHz mono...")
    a_wav_16k_mono(origen, wav)
    dur = herramientas.duracion(wav)
    trozos = 1

    if dur <= umbral_seg:
        print("   [2/2] whisper.cpp (una pasada)...")
        whisper_cli(f"{work_rel}/audio.wav", f"{work_rel}/out", idioma,
                    formatos=("txt", "srt", "json"))
        for ext in (".txt", ".srt", ".json"):
            src = work / f"out{ext}"
            if src.exists():
                shutil.move(str(src), str(base / f"{origen.stem}{ext}"))
        data = json.loads((base / f"{origen.stem}.json").read_text(encoding="utf-8"))
        segmentos = data.get("transcription") or []
    else:
        tramos = _tramos(dur, chunk_seg, _silencios(wav))
        trozos = len(tramos)
        print(f"   [2/2] audio largo ({dur/60:.1f} min > {umbral_seg/60:.0f} min): "
              f"{trozos} fragmentos cortados en silencios...")
        template = None
        segmentos = []
        limite = 0.0           # fin del último segmento aceptado (s)
        for i, (a, b) in enumerate(tramos):
            chunk_wav = work / "chunk.wav"
            run([FFMPEG, "-y", "-ss", f"{a:.3f}", "-i", str(wav),
                 "-t", f"{b - a:.3f}", "-c", "copy", str(chunk_wav)])
            print(f"      - fragmento {i+1}/{trozos} ({a/60:.1f}–{b/60:.1f} min)...")
            whisper_cli(f"{work_rel}/chunk.wav", f"{work_rel}/cout", idioma, formatos=("json",))
            data = json.loads((work / "cout.json").read_text(encoding="utf-8"))
            if template is None:
                template = data
            corte_sig = tramos[i + 1][0] if i + 1 < trozos else float("inf")
            for s in data.get("transcription", []):
                ia = s["offsets"]["from"] + int(round(a * 1000))
                ib = s["offsets"]["to"] + int(round(a * 1000))
                if ia / 1000.0 < limite - 0.2:      # repetido por el solape
                    continue
                if ia / 1000.0 >= corte_sig:        # lo transcribe el fragmento siguiente
                    continue
                ns = dict(s)
                ns["offsets"] = {"from": ia, "to": ib}
                ns["timestamps"] = {"from": _ms_a_ts(ia), "to": _ms_a_ts(ib)}
                segmentos.append(ns)
                limite = max(limite, ib / 1000.0)
            for p in (chunk_wav, work / "cout.json"):
                p.unlink(missing_ok=True)

        template = template or {"transcription": []}
        template["transcription"] = segmentos
        (base / f"{origen.stem}.json").write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        escribir_srt(base / f"{origen.stem}.srt", segmentos)
        escribir_txt(base / f"{origen.stem}.txt", segmentos)

    n = escribir_cortes_txt(segmentos, base / f"{origen.stem}.cortes.txt", origen.stem, dur)
    if _work_es_propio:
        shutil.rmtree(work, ignore_errors=True)
    print(f"   OK -> {base}/")
    return (f"OK {origen.name} · {_mmss(dur)} · {trozos} trozo(s) · {n} frases · "
            f"sugeridos {clips_sugeridos(dur)} clips -> {base / (origen.stem + '.cortes.txt')}")


def ya_hecho(p, ruta: Path) -> str | None:
    """Motivo para saltar `ruta` (ya transcrita o ya aprobada) o None."""
    stem = ruta.stem
    if (p.transcripciones_dir / stem / f"{stem}.txt").exists():
        return f"ya transcrito en transcripciones/{stem}/"
    arch = p.archivado(stem)
    if arch:
        return f"ya aprobado y archivado en {arch}"
    return None


def main():
    parser = argparse.ArgumentParser(description="Paso 1 — Transcripción con whisper.cpp")
    parser.add_argument("archivo", nargs="?",
                        help="Archivo concreto (opcional): nombre en el input/ del proyecto o ruta")
    proyecto.add_argumento(parser)
    proyecto.add_salida(parser)
    parser.add_argument("--idioma", default=None,
                        help="Código de idioma (def: el del proyecto, si no 'es')")
    parser.add_argument("--umbral-min", type=float, default=UMBRAL_TROCEO_MIN,
                        help=f"Duración (min) a partir de la cual se trocea (def: {UMBRAL_TROCEO_MIN})")
    parser.add_argument("--chunk-min", type=float, default=CHUNK_MIN,
                        help=f"Duración (min) de cada fragmento al trocear (def: {CHUNK_MIN})")
    parser.add_argument("--work-dir", default=os.environ.get("WHISPER_WORK_DIR"),
                        help="Directorio intermedio (ASCII, bajo la raíz). Por defecto uno ÚNICO "
                             "por ejecución (seguro en paralelo).")
    parser.add_argument("--forzar", action="store_true",
                        help="Transcribir aunque ya esté en transcripciones/ o en _Historico/.")
    parser.add_argument("--cortes-txt", metavar="JSON", default=None,
                        help="Solo (re)genera <video>.cortes.txt desde un JSON de whisper.cpp.")
    parser.add_argument("--salida", default=None,
                        help="Con --cortes-txt: carpeta donde escribirlo (por defecto, la del JSON).")
    args = parser.parse_args()

    if args.cortes_txt:      # no transcribe: no hace falta proyecto
        for s in (sys.stdout, sys.stderr):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        out, n = cortes_txt_desde_json(Path(args.cortes_txt), args.salida)
        print(f"OK {out} · {n} frases")
        return

    p = proyecto.abrir(args.proyecto, "transcribir", quiet=args.quiet)
    entrada, salida = p.input_dir, p.transcripciones_dir
    idioma = args.idioma or p.idioma
    herramientas.exigir_ffmpeg()
    if not WHISPER_CLI.exists():
        raise SystemExit(f"[!] No existe whisper-cli: {WHISPER_CLI}")
    if not MODELO.exists():
        raise SystemExit(f"[!] No existe el modelo: {MODELO}")

    if args.archivo:
        a = Path(args.archivo)
        objetivos = [entrada / a if (not a.is_absolute() and len(a.parts) == 1
                                     and (entrada / a).exists()) else a]
    else:
        entrada.mkdir(parents=True, exist_ok=True)
        objetivos = sorted(f for f in entrada.iterdir()
                           if f.is_file() and f.suffix.lower() in EXTENSIONES)
    if not objetivos:
        raise SystemExit(f"[!] No hay archivos para transcribir en {entrada}")

    work_dir = Path(args.work_dir) if args.work_dir else None
    saltados = 0
    for ruta in objetivos:
        if not ruta.exists():
            proyecto.decir(f"FALTA {ruta}")
            continue
        motivo = None if args.forzar else ya_hecho(p, ruta)
        if motivo:
            saltados += 1
            extra = ""
            j = p.transcripciones_dir / ruta.stem / f"{ruta.stem}.json"
            ct = j.with_name(f"{ruta.stem}.cortes.txt")
            if j.exists() and not ct.exists():
                cortes_txt_desde_json(j)
                extra = " (cortes.txt generado)"
            proyecto.decir(f"= {ruta.name}: {motivo} -> salto{extra}")
            continue
        proyecto.decir(transcribir(ruta, idioma, args.umbral_min * 60, args.chunk_min * 60,
                                   work_dir, salida=salida))
    proyecto.decir(f"RESUMEN: {len(objetivos) - saltados} transcrito(s) · {saltados} saltado(s) · "
                   f"lee solo <video>.cortes.txt para elegir los cortes")


if __name__ == "__main__":
    main()

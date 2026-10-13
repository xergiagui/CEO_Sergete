#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validación por script ANTES de renderizar (la usan clips.py, editar_clips.py y
procesar_batch_clip.py; también a mano con `clips.py --validar` y
`procesar_batch_clip.py --validar-ganchos`).

cortes.json (vía 1), por corte:
  - `nombre` con [a-z0-9_]+ y único;
  - `inicio` < `fin`, dentro de la duración del vídeo, sin solapes y con una
    duración de 15 a 90 s.
Gancho de texto (`gancho_texto` en cortes.json o el valor de ganchos.json):
  - como mucho 2 líneas (el MISMO cálculo que el render) y 50 caracteres;
  - `¿` si hay `?` y `¡` si hay `!`; sin emojis;
  - sus cifras salen en el texto del clip;
  - no es la primera frase literal del clip.
ganchos.json (vía 2): sus claves coinciden con los clips de la carpeta.

Un gancho vacío no es un error: el clip sale sin gancho (aviso).
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
NOMBRE_RE = re.compile(r"[a-z0-9_]+")
DUR_MIN, DUR_MAX = 15.0, 90.0
GANCHO_MAX_CAR = 50
GANCHO_MAX_LINEAS = 2

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U0001F1E6-\U0001F1FF☀-➿"
                    "⌀-⏿⬀-⯿️‍]")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_NUMEROS_EN_LETRA = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80,
    "noventa": 90, "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
    "quinientos": 500, "mil": 1000, "millon": 1000000, "millones": 1000000,
}


def _norm(t: str) -> str:
    """Minúsculas, sin tildes ni puntuación, espacios colapsados."""
    t = unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def _cifras(t: str) -> set[str]:
    """Cifras de un texto como dígitos sin separadores («10.000» -> «10000»)."""
    return {re.sub(r"[.,]", "", n) for n in _NUM.findall(t or "")}


def _cifras_en_letra(t: str) -> set[str]:
    return {str(_NUMEROS_EN_LETRA[w]) for w in _norm(t).split() if w in _NUMEROS_EN_LETRA}


def _primera_frase(t: str) -> str:
    for parte in re.split(r"(?<=[.?!…])\s+", (t or "").strip()):
        if parte.strip():
            return parte
    return ""


def lineas_gancho(texto: str) -> list[str]:
    """Reparto en líneas del render (pipeline_core.hook_text_lines)."""
    skill = RAIZ / ".claude" / "skills" / "Editor_Sergio"
    if str(skill) not in sys.path:
        sys.path.insert(0, str(skill))
    import pipeline_core as pc
    return pc.hook_text_lines(texto)


def validar_gancho(texto: str, texto_clip: str | None = None) -> tuple[list[str], list[str]]:
    """(errores, avisos) de un gancho de texto no vacío."""
    err, av = [], []
    t = (texto or "").strip()
    if not t:
        return err, av
    lineas = lineas_gancho(t)
    if len(lineas) > GANCHO_MAX_LINEAS:
        err.append(f"gancho en {len(lineas)} líneas (máx. {GANCHO_MAX_LINEAS}): «{' / '.join(lineas)}»")
    if len(t) > GANCHO_MAX_CAR:
        err.append(f"gancho de {len(t)} caracteres (máx. {GANCHO_MAX_CAR})")
    if "?" in t and "¿" not in t:
        err.append("falta «¿» (hay «?»)")
    if "!" in t and "¡" not in t:
        err.append("falta «¡» (hay «!»)")
    if _EMOJI.search(t):
        err.append("lleva emojis")
    if texto_clip is None:
        av.append("no hay texto del clip: sin comprobar cifras ni primera frase")
        return err, av
    faltan = sorted(c for c in _cifras(t)
                    if c not in _cifras(texto_clip) and c not in _cifras_en_letra(texto_clip))
    if faltan:
        err.append(f"cifra(s) {', '.join(faltan)} que no salen en el clip")
    ng, nf, nt = _norm(t), _norm(_primera_frase(texto_clip)), _norm(texto_clip)
    if ng and (ng == nf or (len(ng.split()) >= 4 and nt.startswith(ng))):
        err.append("repite literal la primera frase del clip")
    return err, av


def texto_en_tramo(json_whisper: Path, inicio: float, fin: float) -> str | None:
    """Texto de la transcripción (JSON de whisper.cpp) entre inicio y fin (s)."""
    try:
        data = json.loads(Path(json_whisper).read_text(encoding="utf-8"))
    except Exception:
        return None
    partes = []
    for s in data.get("transcription") or []:
        a, b = s["offsets"]["from"] / 1000.0, s["offsets"]["to"] / 1000.0
        if inicio - 0.5 <= (a + b) / 2 <= fin + 0.5:
            partes.append(s.get("text", "").strip())
    return " ".join(p for p in partes if p) or None


def validar_cortes(cortes, duracion: float | None = None, json_whisper: Path | None = None,
                   gancho_texto: bool = True) -> list[tuple[str | None, str, str]]:
    """[(nombre o None, 'error'|'aviso', mensaje)] de un cortes.json ya leído."""
    out = []
    if not isinstance(cortes, list) or not cortes:
        return [(None, "error", "cortes.json debe ser una lista no vacía de cortes")]
    vistos = set()
    tramos = []
    for i, c in enumerate(cortes):
        if not isinstance(c, dict):
            out.append((None, "error", f"corte #{i} no es un objeto"))
            continue
        n = c.get("nombre")
        if not isinstance(n, str) or not NOMBRE_RE.fullmatch(n):
            out.append((n if isinstance(n, str) else None, "error",
                        f"corte #{i}: nombre «{n}» no válido (solo [a-z0-9_])"))
        elif n in vistos:
            out.append((n, "error", "nombre repetido"))
        vistos.add(n)
        try:
            a, b = float(c["inicio"]), float(c["fin"])
        except (KeyError, TypeError, ValueError):
            out.append((n, "error", "falta inicio o fin numérico"))
            continue
        if a < 0 or a >= b:
            out.append((n, "error", f"inicio {a} debe ser ≥ 0 y menor que fin {b}"))
            continue
        if duracion and b > duracion + 0.5:
            out.append((n, "error", f"fin {b} pasa de la duración del vídeo ({duracion:.1f} s)"))
        if not (DUR_MIN <= b - a <= DUR_MAX):
            out.append((n, "error", f"dura {b - a:.1f} s (de {DUR_MIN:.0f} a {DUR_MAX:.0f} s)"))
        tramos.append((a, b, n))
        g = (c.get("gancho_texto") or "").strip() if gancho_texto else ""
        if gancho_texto and not g:
            out.append((n, "aviso", "sin gancho_texto: sale sin gancho"))
        elif g:
            texto = texto_en_tramo(json_whisper, a, b) if json_whisper else None
            e, av = validar_gancho(g, texto)
            out += [(n, "error", m) for m in e] + [(n, "aviso", m) for m in av]
    tramos.sort()
    for (a0, b0, n0), (a1, b1, n1) in zip(tramos, tramos[1:]):
        if a1 < b0 - 0.01:
            out.append((n1, "error", f"se solapa con «{n0}» ({a1} < {b0})"))
    return out


def validar_ganchos(ganchos, clips: list[str], textos: dict[str, str]) -> list[tuple[str | None, str, str]]:
    """Valida un ganchos.json ya leído contra los clips (nombres sin extensión)."""
    from proyecto import sin_extension
    out = []
    if not isinstance(ganchos, dict):
        return [(None, "error", "ganchos.json debe ser un objeto {\"<clip>.mp4\": \"texto\"}")]
    claves = {}
    for k, v in ganchos.items():
        stem = sin_extension(k)
        if stem not in clips:
            out.append((stem, "error", f"la clave «{k}» no coincide con ningún clip"))
            continue
        if isinstance(v, dict):
            v = v.get("gancho_texto") or v.get("texto") or ""
        if not isinstance(v, str):
            out.append((stem, "error", f"«{k}»: el gancho debe ser texto"))
            continue
        claves[stem] = v.strip()
    for c in clips:
        if c not in claves:
            out.append((c, "aviso", "sin entrada en ganchos.json: sale sin gancho"))
        elif not claves[c]:
            out.append((c, "aviso", "gancho vacío: sale sin gancho"))
        else:
            e, av = validar_gancho(claves[c], textos.get(c))
            out += [(c, "error", m) for m in e] + [(c, "aviso", m) for m in av]
    return out


def informar(res, que: str, solo: set[str] | None = None, decir=print) -> bool:
    """Imprime errores y avisos (filtrados a `solo` si se da). True si no hay errores."""
    res = [r for r in res if solo is None or r[0] is None or r[0] in solo]
    errores = [r for r in res if r[1] == "error"]
    avisos = [r for r in res if r[1] == "aviso"]
    for n, nivel, m in errores + avisos:
        decir(f"{'ERROR' if nivel == 'error' else 'aviso'} {n or que}: {m}")
    decir(f"VALIDACIÓN {que}: {'OK' if not errores else 'NO'} · {len(errores)} error(es) · "
          f"{len(avisos)} aviso(s)")
    return not errores

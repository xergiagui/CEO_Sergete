"""
Contexto de cada clip a partir de lo que ya generó TheEditor.

El clip final `finales/<nombre>.mp4` corresponde a la entrada de `cortes.json`
con ese `nombre` (título, frase viral, ángulo, categoría, motivo...). Además
se extrae de la transcripción (.srt) lo que se dice entre `inicio` y `fin`, que
es la mejor base para escribir un copy pegado al clip.
"""
from __future__ import annotations

import re
from pathlib import Path

import config
from lib.util import leer_json

CAMPOS_CORTE = ("titulo", "frase_viral", "angle", "category", "rationale", "inicio", "fin")


def _indexar() -> dict[str, list[tuple[Path, dict]]]:
    """nombre_clip -> [(cortes.json, entrada), ...] en todas las fuentes."""
    indice: dict[str, list[tuple[Path, dict]]] = {}
    for base in config.FUENTES_METADATOS:
        if not base.exists():
            continue
        for cortes in base.glob("*/cortes.json"):
            try:
                entradas = leer_json(cortes)
            except Exception:
                continue
            for e in entradas if isinstance(entradas, list) else []:
                if isinstance(e, dict) and e.get("nombre"):
                    indice.setdefault(e["nombre"], []).append((cortes, e))
    return indice


def _seg(ts: str) -> float:
    h, m, rest = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _fragmento_srt(carpeta: Path, inicio: float, fin: float) -> str:
    srts = sorted(carpeta.glob("*.srt"))
    if not srts:
        return ""
    texto = srts[0].read_text(encoding="utf-8-sig", errors="replace")
    trozos = []
    for bloque in re.split(r"\n\s*\n", texto):
        m = re.search(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", bloque)
        if not m:
            continue
        a, b = _seg(m.group(1)), _seg(m.group(2))
        if b >= inicio and a <= fin:
            lineas = bloque.split("\n")[2:]
            trozos.append(" ".join(l.strip() for l in lineas if l.strip()))
    frag = " ".join(trozos)
    if len(frag) > config.MAX_CHARS_TRANSCRIPCION:
        frag = frag[: config.MAX_CHARS_TRANSCRIPCION].rsplit(" ", 1)[0] + " […]"
    return frag


class BuscadorMetadatos:
    def __init__(self):
        self.indice = _indexar()

    def contexto(self, clip: Path | str) -> dict:
        """Contexto del clip o {'aviso': ...} si no hay metadatos."""
        nombre = Path(clip).stem
        candidatos = self.indice.get(nombre, [])
        if not candidatos:
            return {"aviso": "Sin cortes.json para este clip: escribe el copy viendo el vídeo o desde el banco."}

        # Si el nombre se repite en varios vídeos, el cortes.json más reciente.
        candidatos.sort(key=lambda c: c[0].stat().st_mtime, reverse=True)
        cortes, entrada = candidatos[0]
        ctx = {k: entrada[k] for k in CAMPOS_CORTE if k in entrada}
        ctx["video_carpeta"] = cortes.parent.name
        ctx["fuente"] = str(cortes)
        if "inicio" in entrada and "fin" in entrada:
            frag = _fragmento_srt(cortes.parent, float(entrada["inicio"]), float(entrada["fin"]))
            if frag:
                ctx["transcripcion"] = frag
        if len(candidatos) > 1:
            ctx["aviso"] = (f"Nombre repetido en {len(candidatos)} cortes.json; se usa el más reciente. "
                            "Revisa que el contexto cuadra con el clip.")
        return ctx

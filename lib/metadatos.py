"""
Contexto de cada clip a partir de lo que ya generó TheEditor, SOLO en las carpetas
del proyecto (proyecto.json → carpetas.contexto; por defecto
`TheEditor/proyectos/<id>/transcripciones/` y `_Historico/<id>/`). Cada carpeta
tiene una subcarpeta por vídeo:

  largos    <video>/cortes.json + <video>.srt
            El clip final `finales/<nombre>.mp4` es la entrada de cortes.json con ese
            `nombre` (título, frase viral, ángulo, categoría…); de la transcripción
            (.srt) se extrae lo que se dice entre `inicio` y `fin`.
  clipping  <carpeta>/textos/<clip>.txt (+ <carpeta>/ganchos.json)
            Lo que escribe procesar_batch_clip.py: la transcripción del clip entero y,
            si existe, el gancho de texto que se le quemó.

Durante la transición también se mira la ruta antigua `TheEditor/transcripciones/`
(sin proyecto), solo si el clip no sale en las del proyecto y con un aviso.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import config
from lib.util import leer_json

CAMPOS_CORTE = ("titulo", "frase_viral", "gancho_texto", "angle", "category", "rationale", "inicio", "fin")


@dataclass
class Candidato:
    carpeta: Path            # carpeta del vídeo (o de la tanda de clipping)
    fuente: Path             # cortes.json o textos/<clip>.txt
    entrada: dict | None     # entrada de cortes.json (largos) o None (clipping)
    transicion: bool         # viene de la ruta antigua sin proyecto

    @property
    def mtime(self) -> float:
        try:
            return self.fuente.stat().st_mtime
        except OSError:
            return 0.0


def _indexar(proyecto) -> dict[str, list[Candidato]]:
    """nombre_clip (sin extensión) -> candidatos en las carpetas de contexto del proyecto."""
    indice: dict[str, list[Candidato]] = {}
    for base, transicion in proyecto.carpetas_contexto():
        if not base.exists():
            continue
        for cortes in base.glob("*/cortes.json"):
            try:
                entradas = leer_json(cortes)
            except Exception:
                continue
            for e in entradas if isinstance(entradas, list) else []:
                if isinstance(e, dict) and e.get("nombre"):
                    nombre = Path(str(e["nombre"])).stem if str(e["nombre"]).lower().endswith(".mp4") else str(e["nombre"])
                    indice.setdefault(nombre, []).append(Candidato(cortes.parent, cortes, e, transicion))
        for txt in base.glob("*/textos/*.txt"):
            indice.setdefault(txt.stem, []).append(Candidato(txt.parent.parent, txt, None, transicion))
    return indice


def _seg(ts: str) -> float:
    h, m, rest = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _recortar(frag: str) -> str:
    frag = re.sub(r"\s+", " ", frag).strip()
    if len(frag) > config.MAX_CHARS_TRANSCRIPCION:
        frag = frag[: config.MAX_CHARS_TRANSCRIPCION].rsplit(" ", 1)[0] + " […]"
    return frag


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
    return _recortar(" ".join(trozos))


def _gancho_clipping(carpeta: Path, nombre: str) -> str:
    """Gancho de texto quemado en un clip de clipping (ganchos.json de su carpeta), si lo hay."""
    gj = carpeta / "ganchos.json"
    if not gj.exists():
        return ""
    try:
        data = leer_json(gj)
    except Exception:
        return ""
    for k, v in (data.items() if isinstance(data, dict) else []):
        if Path(str(k)).stem.strip().lower() == nombre.lower() or str(k).strip().lower() == nombre.lower():
            if isinstance(v, dict):
                v = v.get("gancho_texto") or v.get("texto")
            return str(v or "").strip()
    return ""


class BuscadorMetadatos:
    def __init__(self, proyecto):
        self.proyecto = proyecto
        self.indice = _indexar(proyecto)

    def candidatos(self, nombre: str) -> list[Candidato]:
        """Los del proyecto; los de la ruta antigua solo si no hay ninguno. Más reciente primero."""
        todos = self.indice.get(Path(nombre).stem if nombre.lower().endswith(tuple(config.EXT_VIDEO)) else nombre, [])
        propios = [c for c in todos if not c.transicion]
        elegidos = propios or todos
        return sorted(elegidos, key=lambda c: c.mtime, reverse=True)

    def _resolver(self, nombre: str) -> tuple[Candidato | None, list[Candidato], bool]:
        """(candidato elegido, todos, ambiguo). En clipping, con el nombre en varias carpetas
        distintas NO se elige ninguno (los nombres tipo «Luis 1» se repiten en cada carpeta)."""
        cands = self.candidatos(nombre)
        if not cands:
            return None, [], False
        carpetas = {c.carpeta.name.lower() for c in cands}
        ambiguo = len(carpetas) > 1
        if ambiguo and all(c.entrada is None for c in cands):
            return None, cands, True
        # largos: el cortes.json más reciente (lo de clipping solo si no hay cortes.json)
        con_cortes = [c for c in cands if c.entrada is not None]
        return (con_cortes or cands)[0], cands, ambiguo

    def origen(self, nombre: str) -> str | None:
        """Carpeta del vídeo de origen del clip (para el calendario) o None si no se sabe."""
        elegido, _, ambiguo = self._resolver(nombre)
        if elegido is None or (ambiguo and elegido.entrada is None):
            return None
        return elegido.carpeta.name

    def contexto(self, clip: Path | str) -> dict:
        """Contexto del clip o {'aviso': ...} si no hay metadatos."""
        nombre = Path(clip).stem
        elegido, cands, ambiguo = self._resolver(nombre)
        if not cands:
            return {"aviso": "Sin contexto (ni cortes.json ni textos/<clip>.txt en las carpetas del proyecto): "
                             "escribe el copy viendo el vídeo o desde el banco."}
        if elegido is None:
            lista = ", ".join(sorted({c.carpeta.name for c in cands}))
            return {"aviso": f"El nombre «{nombre}» está en {len(cands)} carpetas de clipping ({lista}): no se "
                             "sabe de cuál es. Pide al CEO la carpeta de origen o una línea sobre el clip.",
                    "candidatos": sorted({str(c.fuente) for c in cands})}

        avisos = []
        if elegido.entrada is not None:  # largos: cortes.json + .srt
            e = elegido.entrada
            ctx = {k: e[k] for k in CAMPOS_CORTE if k in e}
            ctx["video_carpeta"] = elegido.carpeta.name
            ctx["fuente"] = str(elegido.fuente)
            if "inicio" in e and "fin" in e:
                frag = _fragmento_srt(elegido.carpeta, float(e["inicio"]), float(e["fin"]))
                if frag:
                    ctx["transcripcion"] = frag
        else:  # clipping: textos/<clip>.txt (+ ganchos.json)
            ctx = {"video_carpeta": elegido.carpeta.name, "fuente": str(elegido.fuente)}
            texto = elegido.fuente.read_text(encoding="utf-8-sig", errors="replace")
            if texto.strip():
                ctx["transcripcion"] = _recortar(texto)
            gancho = _gancho_clipping(elegido.carpeta, nombre)
            if gancho:
                ctx["gancho_texto"] = gancho
        if ambiguo:
            avisos.append(f"Nombre repetido en {len(cands)} sitios; se usa el más reciente "
                          f"({elegido.carpeta.name}). Revisa que el contexto cuadra con el clip.")
        if elegido.transicion:
            avisos.append("Contexto sacado de la ruta antigua TheEditor/transcripciones (sin proyecto).")
        if avisos:
            ctx["aviso"] = " ".join(avisos)
        return ctx

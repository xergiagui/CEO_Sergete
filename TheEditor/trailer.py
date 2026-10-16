#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modo tráiler: clips 9:16 montados SOLO con material oficial (un tráiler ya
vertical + su póster), sin b-roll, sin música añadida y sin recortar silencios.

Se activa por proyecto con `proyecto.json → "modo": "trailer"` y su bloque
`"trailer": {…}` (hoy, `wicker`). Los demás proyectos no pasan por aquí.

Por clip (una entrada de cortes.json):
  1) uno o varios TRAMOS del tráiler, montados en orden con corte seco de imagen
     y micro-fundidos de audio (sin quitar silencios: el ritmo es el del tráiler);
  2) GANCHO de texto LITERAL de su tipo (A–E, `trailer.tipos`), grande, del
     fotograma 0 a los `gancho.duracion_s` (3 s), con salida suave;
  3) SUBTÍTULOS de los diálogos (`trailer.dialogos`, texto revisado y en
     segundos del tráiler), que esquivan el gancho y las zonas protegidas
     (rótulos oficiales: no se tapan);
  4) CTA fija LITERAL (`trailer.cta.texto`) sobre el póster oficial, con
     fundido de entrada y el remate musical del propio tráiler (`cta.audio`);
  5) audio: solo el original, ganancia estática hacia `loudness.lufs` y
     limitador; nada de música, TTS ni voz en off;
  6) PORTADA `<clip>.portada.jpg` (1080x1920) sobre un fotograma del propio
     clip con uno de los títulos LITERALES de `trailer.portadas`.
Deja un manifiesto `clips/<clip>.render.json` (+ los PNG del gancho y la CTA)
que usa qc.py para comprobar el clip ya exportado.

Esquema de un corte (cortes.json, lista):
    {"nombre": "a_marido_de_mimbre",     # empieza por la letra del tipo + "_"
     "tipo": "A",
     "tramos": [[42.54, 81.04]],          # segundos del tráiler (o "inicio"/"fin")
     "portada_titulo": "WICKER: el marido perfecto es de MIMBRE 🧺",
     "portada_t": 77.5,                   # segundo del tráiler (dentro de un tramo)
     "portada_pos": "abajo",              # arriba | centro | abajo (opcional)
     "gancho_pos": "arriba",              # arriba | abajo (opcional)
     "momento": "…", "por_que": "…"}      # texto libre (plan y revisión)
`gancho_texto` no hace falta: sale del tipo (si se pone, tiene que ser el literal).
Un tramo puede ser {"inicio": a, "fin": b, "fuente": "<alias>", "x": 0.5} para
tomarlo de otra versión del tráiler (`trailer.fuentes`), recortada a 9:16
centrada en `x` (fracción del ancho).
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import herramientas
import proyecto

RAIZ = Path(__file__).resolve().parent
W, H = 1080, 1920
NOMBRE_RE = re.compile(r"[a-z0-9_]+")
POS_VALIDAS = ("arriba", "centro", "abajo")
# Centro del título de portada según portada_pos y la franja que puede ocupar.
CENTRO_PORTADA = {"arriba": 640, "centro": 960, "abajo": 1290}
BANDA_PORTADA = {"arriba": (400, 880), "centro": (740, 1180), "abajo": (1060, 1520)}

DEFECTOS = {
    "gancho": {"duracion_s": 3.0, "fundido_s": 0.25, "pos": "arriba", "y_arriba": 380,
               "y_abajo_fin": 1560, "tam_max": 92, "tam_min": 58, "max_lineas": 4,
               "ancho_max": 900},
    "cta": {"duracion_s": 4.0, "fundido_s": 0.30, "audio": None,
            "poster_ancho": 640, "poster_y": 200},
    "subtitulos": {"tam": 60, "y_fin": 1500, "ancho_max": 860, "max_lineas": 2,
                   "retencion_s": 0.30, "min_s": 0.70, "solape_min_s": 0.25},
    "portada": {"tam_max": 104, "tam_min": 64, "max_lineas": 4, "ancho_max": 900},
    "fundido_audio_s": 0.06,
    "duracion": {"min": 15.0, "max": 90.0},
    "loudness": {"lufs": -14.0, "limite": 0.89, "ganancia_max_db": 8.0},
    "zona_segura": {"y0": 230, "y1": 1600},
    "tolerancia_frase_s": 0.12,
}

# Variación de Fraunces (ejes por nombre) para cada uso.
VAR_GANCHO = {"Optical Size": 72, "Weight": 760, "Softness": 40, "Wonky": 0}
VAR_ACENTO = {"Optical Size": 72, "Weight": 900, "Softness": 40, "Wonky": 0}
VAR_SUBS = {"Optical Size": 36, "Weight": 640, "Softness": 20, "Wonky": 0}
VAR_CTA_TIT = {"Optical Size": 144, "Weight": 900, "Softness": 30, "Wonky": 0}
VAR_CTA = {"Optical Size": 48, "Weight": 760, "Softness": 30, "Wonky": 0}

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U0001F1E6-\U0001F1FF\u2600-\u27BF"
                    "\u2300-\u23FF\u2B00-\u2BFF\uFE0F\u200D]")
_PUNT = "¿¡«»\"'“”‘’()[].,;:!?…—–-"
# No se deja ninguna de estas al final de una línea si hay otro reparto con las mismas líneas.
_PALABRAS_DEBILES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
                     "a", "y", "e", "o", "u", "en", "con", "por", "para", "que", "se", "lo",
                     "le", "su", "sus", "mi", "tu", "ni", "si", "sin", "tan", "muy"}


class ErrorTrailer(RuntimeError):
    """Configuración o corte del modo tráiler no válidos."""


# ============================================================ configuración
def activo(p) -> bool:
    return str((p.cfg or {}).get("modo") or "").strip().lower() == "trailer"


def _fusion(base: dict, extra: dict | None) -> dict:
    out = json.loads(json.dumps(base))
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _fusion(out[k], v)
        else:
            out[k] = v
    return out


def _color(hexa: str) -> tuple[int, int, int]:
    h = str(hexa or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ErrorTrailer(f"color «{hexa}» no es #rrggbb")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@dataclass
class Config:
    p: object
    raw: dict
    fuente: Path
    fuentes: dict          # alias -> Path (versiones alternativas del tráiler)
    dialogos_path: Path | None
    poster: Path
    tipografia: dict       # texto, emoji (Path)
    marca: dict            # fondo, texto, acento (rgb)
    tipos: dict            # "A" -> {"gancho": str, "lineas": [...]?}
    portadas: list         # títulos literales
    portadas_lineas: dict  # título -> reparto en líneas (opcional)
    cta: dict
    gancho: dict
    subs: dict
    portada: dict
    zonas: list            # [{"nombre", "t": (a, b), "caja": (x0, y0, x1, y1), "prensa"}]
    evitar: list           # [{"t": (a, b), "motivo", "donde": ["portada", "gancho", ...]}]
    acento_palabras: list
    fundido_audio: float
    duracion: dict
    loudness: dict
    zona_segura: dict
    tol_frase: float

    @property
    def fps(self) -> str:
        return fps_de(self.fuente) or "24000/1001"


def config(p) -> Config:
    """Bloque `trailer` del proyecto, resuelto y comprobado (rutas que existen)."""
    t = (p.cfg or {}).get("trailer")
    if not isinstance(t, dict):
        raise ErrorTrailer(f"proyectos/{p.id}/proyecto.json: modo «trailer» sin bloque «trailer».")
    c = _fusion(DEFECTOS, t)

    def ruta(rel, que, obligatoria=True) -> Path | None:
        if not rel:
            if obligatoria:
                raise ErrorTrailer(f"trailer.{que}: falta la ruta")
            return None
        r = Path(rel)
        r = r if r.is_absolute() else (p.dir / r)
        if not r.exists():
            if obligatoria:
                raise ErrorTrailer(f"trailer.{que}: no existe {r}")
            return None
        return r

    fuente = ruta(c.get("fuente"), "fuente")
    fuentes = {}
    for alias, rel in (c.get("fuentes") or {}).items():
        if str(alias).startswith("_"):
            continue
        fuentes[alias] = ruta(rel, f"fuentes.{alias}")
    tip = c.get("tipografia") or {}
    tdir = Path(tip.get("dir") or "recursos/fuentes")
    tdir = tdir if tdir.is_absolute() else (p.dir / tdir)
    tipografia = {}
    for k in ("texto", "emoji"):
        if not tip.get(k):
            raise ErrorTrailer(f"trailer.tipografia.{k}: falta el archivo de la fuente")
        f = tdir / tip[k]
        if not f.exists():
            raise ErrorTrailer(f"trailer.tipografia.{k}: no existe {f}")
        tipografia[k] = f
    marca = {k: _color((c.get("marca") or {}).get(k)) for k in ("fondo", "texto", "acento")}
    tipos = {}
    for k, v in (c.get("tipos") or {}).items():
        if str(k).startswith("_"):
            continue
        v = v if isinstance(v, dict) else {"gancho": v}
        if not str(v.get("gancho") or "").strip():
            raise ErrorTrailer(f"trailer.tipos.{k}: falta «gancho»")
        lin = v.get("lineas")
        if lin and " ".join(lin) != v["gancho"]:
            raise ErrorTrailer(f"trailer.tipos.{k}.lineas no reproduce el gancho literal")
        tipos[str(k).upper()] = {"gancho": v["gancho"], "lineas": lin}
    if not tipos:
        raise ErrorTrailer("trailer.tipos: no hay ningún tipo de clip")
    portadas, portadas_lineas = [], {}
    for x in c.get("portadas") or []:
        tit = x.get("titulo") if isinstance(x, dict) else x
        if not str(tit or "").strip():
            continue
        portadas.append(tit)
        lin = x.get("lineas") if isinstance(x, dict) else None
        if lin:
            if " ".join(lin) != tit:
                raise ErrorTrailer(f"trailer.portadas: las lineas de «{tit}» no reproducen el título")
            portadas_lineas[tit] = lin
    cta = c["cta"]
    if not str(cta.get("texto") or "").strip():
        raise ErrorTrailer("trailer.cta.texto: falta la CTA literal")
    if cta.get("lineas") and " ".join(cta["lineas"]) != cta["texto"]:
        raise ErrorTrailer("trailer.cta.lineas no reproduce la CTA literal")
    zonas = []
    for z in c.get("zonas_protegidas") or []:
        zonas.append({"nombre": z.get("nombre", "rótulo"), "t": tuple(map(float, z["t"])),
                      "caja": tuple(map(int, z["caja"])), "prensa": bool(z.get("prensa"))})
    evitar = []
    for z in c.get("evitar") or []:
        evitar.append({"t": tuple(map(float, z["t"])), "motivo": z.get("motivo", ""),
                       "donde": list(z.get("donde") or ["todo"])})
    return Config(
        p=p, raw=c, fuente=fuente, fuentes=fuentes,
        dialogos_path=ruta(c.get("dialogos"), "dialogos", obligatoria=False),
        poster=ruta(c.get("poster"), "poster"), tipografia=tipografia, marca=marca,
        tipos=tipos, portadas=portadas, portadas_lineas=portadas_lineas, cta=cta,
        gancho=c["gancho"],
        subs=c["subtitulos"], portada=c["portada"], zonas=zonas, evitar=evitar,
        acento_palabras=[str(x) for x in (c.get("acento_palabras") or [])],
        fundido_audio=float(c["fundido_audio_s"]), duracion=c["duracion"],
        loudness=c["loudness"], zona_segura=c["zona_segura"],
        tol_frase=float(c["tolerancia_frase_s"]))


def describir(p) -> str:
    """Una línea para `proyecto.py ver`."""
    try:
        c = config(p)
    except ErrorTrailer as e:
        return f"[!] {e}"
    return (f"fuente {c.fuente.name} · tipos {''.join(sorted(c.tipos))} · gancho "
            f"{c.gancho['duracion_s']:g} s · CTA {c.cta['duracion_s']:g} s · "
            f"{len(c.portadas)} títulos de portada · {len(c.zonas)} zonas protegidas · "
            f"fuentes {c.tipografia['texto'].name} + {c.tipografia['emoji'].name}")


def fps_de(video: Path) -> str | None:
    if not herramientas.FFPROBE or not Path(video).exists():
        return None
    r = subprocess.run([herramientas.FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    v = (r.stdout or "").strip()
    return v if re.fullmatch(r"\d+/\d+", v) else None


# ============================================================ diálogos
def cargar_dialogos(c: Config) -> list[dict]:
    if not c.dialogos_path:
        return []
    data = json.loads(c.dialogos_path.read_text(encoding="utf-8"))
    lineas = data.get("lineas") if isinstance(data, dict) else data
    out = []
    for d in lineas or []:
        t0, t1, tx = float(d["t0"]), float(d["t1"]), str(d["texto"]).strip()
        if tx and t1 > t0:
            out.append({"t0": t0, "t1": t1, "texto": tx})
    return sorted(out, key=lambda d: d["t0"])


# ============================================================ cortes
def cargar_cortes(ruta: Path) -> list[dict]:
    if not ruta.exists():
        raise SystemExit(f"[!] Falta {ruta}: escribe cortes.json (esquema en la cabecera de "
                         f"trailer.py) leyendo <video>.cortes.txt y reglas.md.")
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"[!] {ruta} no es un JSON válido: {e}")
    if isinstance(data, dict) and isinstance(data.get("clips"), list):
        data = data["clips"]           # el plan de una tanda también vale
    if not isinstance(data, list) or not data:
        raise SystemExit(f"[!] {ruta} debe ser una lista no vacía de cortes.")
    return data


def tramos_de(corte: dict) -> list[dict]:
    """[{"a", "b", "fuente" (alias o None), "x"}] en el orden del montaje."""
    raw = corte.get("tramos")
    if raw is None and "inicio" in corte and "fin" in corte:
        raw = [[corte["inicio"], corte["fin"]]]
    out = []
    for t in raw or []:
        if isinstance(t, dict):
            out.append({"a": float(t["inicio"]), "b": float(t["fin"]),
                        "fuente": t.get("fuente"), "x": float(t.get("x", 0.5))})
        else:
            out.append({"a": float(t[0]), "b": float(t[1]), "fuente": None, "x": 0.5})
    return out


def _solapa(a0, a1, b0, b1) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _cajas_solapan(c1, c2) -> bool:
    return not (c1[2] <= c2[0] or c2[2] <= c1[0] or c1[3] <= c2[1] or c2[3] <= c1[1])


def duracion_total(c: Config, tramos: list[dict]) -> float:
    main = sum(t["b"] - t["a"] for t in tramos)
    return main - float(c.cta["fundido_s"]) + float(c.cta["duracion_s"])


def gancho_de(c: Config, corte: dict) -> str:
    tipo = str(corte.get("tipo") or "").upper()
    return c.tipos.get(tipo, {}).get("gancho", "")


def _zona_fuente_a_salida(segs, t0, t1):
    """Intervalos de SALIDA en que se ve el intervalo [t0, t1] del tráiler."""
    out = []
    for s in segs:
        ov0, ov1 = max(t0, s["a"]), min(t1, s["b"])
        if ov1 > ov0:
            out.append((ov0 - s["a"] + s["o"], ov1 - s["a"] + s["o"]))
    return out


def validar_cortes(c: Config, cortes, dur_fuente: float | None,
                   dialogos: list[dict]) -> list[tuple[str | None, str, str]]:
    """[(nombre o None, 'error'|'aviso', mensaje)] (mismo formato que validar.py)."""
    out = []
    if not isinstance(cortes, list) or not cortes:
        return [(None, "error", "cortes.json debe ser una lista no vacía de cortes")]
    vistos = set()
    gdur = float(c.gancho["duracion_s"])
    for i, corte in enumerate(cortes):
        if not isinstance(corte, dict):
            out.append((None, "error", f"corte #{i} no es un objeto"))
            continue
        n = corte.get("nombre")
        if not isinstance(n, str) or not NOMBRE_RE.fullmatch(n):
            out.append((n if isinstance(n, str) else None, "error",
                        f"corte #{i}: nombre «{n}» no válido (solo [a-z0-9_])"))
            n = n if isinstance(n, str) else f"#{i}"
        elif n in vistos:
            out.append((n, "error", "nombre repetido"))
        vistos.add(n)
        tipo = str(corte.get("tipo") or "").upper()
        if tipo not in c.tipos:
            out.append((n, "error", f"tipo «{corte.get('tipo')}» no válido "
                                    f"({' | '.join(sorted(c.tipos))})"))
        elif not n.startswith(f"{tipo.lower()}_"):
            out.append((n, "error", f"el nombre tiene que empezar por «{tipo.lower()}_» "
                                    f"(contrato con TheCopy)"))
        g = corte.get("gancho_texto")
        if g is not None and tipo in c.tipos and g != c.tipos[tipo]["gancho"]:
            out.append((n, "error", f"gancho_texto no es el literal del tipo {tipo}: "
                                    f"«{c.tipos[tipo]['gancho']}» (quítalo y sale solo)"))
        for k, ok in (("gancho_pos", ("arriba", "abajo")), ("portada_pos", POS_VALIDAS)):
            if corte.get(k) and corte[k] not in ok:
                out.append((n, "error", f"{k} «{corte[k]}» no válido ({' | '.join(ok)})"))
        try:
            trs = tramos_de(corte)
        except (KeyError, TypeError, ValueError, IndexError):
            out.append((n, "error", "tramos mal escritos: [[inicio, fin], …] en segundos"))
            continue
        if not trs:
            out.append((n, "error", "sin tramos (tramos: [[inicio, fin], …])"))
            continue
        ok_tramos = True
        for j, t in enumerate(trs):
            if t["fuente"] and t["fuente"] not in c.fuentes:
                out.append((n, "error", f"tramo {j + 1}: fuente «{t['fuente']}» no está en "
                                        f"trailer.fuentes ({', '.join(c.fuentes) or 'ninguna'})"))
                ok_tramos = False
            if t["a"] < 0 or t["b"] <= t["a"]:
                out.append((n, "error", f"tramo {j + 1}: {t['a']}–{t['b']} no válido"))
                ok_tramos = False
                continue
            if t["b"] - t["a"] < 0.5:
                out.append((n, "error", f"tramo {j + 1} de {t['b'] - t['a']:.2f} s (mín. 0,5 s)"))
            if dur_fuente and t["b"] > dur_fuente + 0.01:
                out.append((n, "error", f"tramo {j + 1}: fin {t['b']} pasa de la fuente "
                                        f"({dur_fuente:.2f} s)"))
            for d in dialogos:      # no partir una frase por la mitad
                for borde in (t["a"], t["b"]):
                    if d["t0"] + c.tol_frase < borde < d["t1"] - c.tol_frase:
                        out.append((n, "error", f"tramo {j + 1} corta la frase «{d['texto']}» "
                                                f"({d['t0']:.2f}–{d['t1']:.2f}) en {borde:.2f}"))
            for z in c.evitar:
                if "todo" in z["donde"] and _solapa(t["a"], t["b"], *z["t"]) > 0:
                    out.append((n, "error", f"tramo {j + 1} entra en {z['t'][0]}–{z['t'][1]} "
                                            f"({z['motivo']})"))
        for j, t in enumerate(trs):
            for k, u in enumerate(trs[j + 1:], j + 1):
                if _solapa(t["a"], t["b"], u["a"], u["b"]) > 0.01:
                    out.append((n, "error", f"los tramos {j + 1} y {k + 1} se solapan "
                                            f"(se repetiría material dentro del clip)"))
        if not ok_tramos:
            continue
        total = duracion_total(c, trs)
        lo, hi = float(c.duracion["min"]), float(c.duracion["max"])
        if not (lo <= total <= hi):
            out.append((n, "error", f"dura {total:.1f} s con la CTA (de {lo:.0f} a {hi:.0f} s)"))
        # el gancho (0–3 s) no puede ir sobre un plano vetado para el gancho
        segs, o = [], 0.0
        for t in trs:
            segs.append({**t, "o": o})
            o += t["b"] - t["a"]
        for z in c.evitar:
            if "gancho" in z["donde"] or "todo" in z["donde"]:
                for s0, s1 in _zona_fuente_a_salida(segs, *z["t"]):
                    if s0 < gdur:
                        out.append((n, "error", f"el gancho (0–{gdur:g} s) cae sobre "
                                                f"{z['t'][0]}–{z['t'][1]} ({z['motivo']})"))
        embargo = str(c.raw.get("embargo_prensa") or "")
        fecha = str(corte.get("fecha") or "")
        for z in c.zonas:
            if z["prensa"] and any(_solapa(t["a"], t["b"], *z["t"]) > 0 for t in trs):
                if embargo and fecha and fecha[:10] > embargo[:10]:
                    continue                # se publica después del embargo: sin problema
                out.append((n, "aviso" if not fecha else "error",
                            f"lleva {z['nombre']} (prensa: embargo hasta {embargo or 'la fecha del briefing'})"
                            + ("" if fecha else "; pon «fecha» para comprobarlo")))
        # portada
        tit = corte.get("portada_titulo")
        if not tit:
            out.append((n, "error", "falta portada_titulo (uno de trailer.portadas, literal)"))
        elif tit not in c.portadas:
            out.append((n, "error", f"portada_titulo «{tit}» no es uno de los títulos literales "
                                    f"de trailer.portadas"))
        pt = corte.get("portada_t")
        if pt is None:
            out.append((n, "aviso", "sin portada_t: la portada usa el centro del tramo más largo"))
        else:
            try:
                pt = float(pt)
            except (TypeError, ValueError):
                out.append((n, "error", "portada_t debe ser un número (segundo del tráiler)"))
                pt = None
            if pt is not None and not any(t["a"] <= pt <= t["b"] - 0.05 for t in trs):
                out.append((n, "error", f"portada_t {pt} no está dentro de ningún tramo del clip "
                                        f"(la portada sale de un fotograma del propio clip)"))
            if pt is not None:
                banda = BANDA_PORTADA.get(corte.get("portada_pos") or "abajo", BANDA_PORTADA["abajo"])
                for z in c.zonas:
                    if z["t"][0] <= pt <= z["t"][1] and \
                            _cajas_solapan((0, banda[0], W, banda[1]), z["caja"]):
                        out.append((n, "error", f"la portada (portada_t {pt}, {corte.get('portada_pos') or 'abajo'}) "
                                                f"taparía el rótulo oficial «{z['nombre']}»: otro fotograma o "
                                                f"otra portada_pos"))
                for z in c.evitar:
                    if ("portada" in z["donde"] or "todo" in z["donde"]) and \
                            z["t"][0] <= pt <= z["t"][1]:
                        out.append((n, "error", f"portada_t {pt} cae en {z['t'][0]}–{z['t'][1]} "
                                                f"({z['motivo']})"))
        if tipo == "D" and dialogos:
            if not any("cama" in d["texto"].lower() and
                       any(_solapa(t["a"], t["b"], d["t0"], d["t1"]) > 0.3 for t in trs)
                       for d in dialogos):
                out.append((n, "error", "un clip D tiene que contener el diálogo de la cama"))
    return out


# ============================================================ tipografía
def _es_emoji(ch: str) -> bool:
    return bool(_EMOJI.fullmatch(ch))


def _quitar_variantes(s: str) -> str:
    return s.replace("\uFE0F", "").replace("\u200D", "")


class Tipografia:
    """Fraunces (variable) para el texto + Noto Color Emoji (CBDT) para los emojis."""

    def __init__(self, c: Config):
        self.texto = c.tipografia["texto"]
        self.emoji = c.tipografia["emoji"]
        self._cache = {}
        self._ecache = {}
        self._efont = None

    def fuente(self, tam: int, var: dict):
        from PIL import ImageFont
        key = (tam, tuple(sorted(var.items())))
        if key not in self._cache:
            f = ImageFont.truetype(str(self.texto), tam)
            try:
                ejes = f.get_variation_axes()
                vals = []
                for e in ejes:
                    nombre = e.get("name")
                    nombre = nombre.decode() if isinstance(nombre, bytes) else str(nombre)
                    v = var.get(nombre, e.get("default"))
                    vals.append(max(e["minimum"], min(e["maximum"], v)))
                f.set_variation_by_axes(vals)
            except Exception:
                pass          # fuente estática: se usa tal cual
            self._cache[key] = f
        return self._cache[key]

    def emoji_img(self, ch: str, alto: int):
        from PIL import Image, ImageDraw, ImageFont
        key = (ch, alto)
        if key not in self._ecache:
            if self._efont is None:
                self._efont = ImageFont.truetype(str(self.emoji), 109)
            lienzo = Image.new("RGBA", (220, 180), (0, 0, 0, 0))
            ImageDraw.Draw(lienzo).text((10, 10), ch, font=self._efont, embedded_color=True)
            bbox = lienzo.getbbox()
            if not bbox:
                raise ErrorTrailer(f"la fuente de emojis no tiene «{ch}» (U+{ord(ch):04X})")
            im = lienzo.crop(bbox)
            ancho = max(1, round(im.width * alto / im.height))
            self._ecache[key] = im.resize((ancho, alto), Image.LANCZOS)
        return self._ecache[key]


@dataclass
class Estilo:
    tam_max: int
    tam_min: int
    max_lineas: int
    ancho_max: int
    var: dict
    var_acento: dict
    color: tuple
    acento: tuple
    interlineado: float = 1.14
    trazo: int = 0                 # contorno (px) para texto sin panel
    trazo_color: tuple = (12, 30, 33)
    sombra: bool = False
    acentuar_mayus: bool = True
    lineas: list | None = None     # reparto manual (literal)


def _segmentos(palabra: str) -> list[tuple[str, str]]:
    """[('t'|'e', texto)]: trozos de texto y emojis de una palabra."""
    out = []
    for ch in palabra:
        k = "e" if _es_emoji(ch) else "t"
        if ch in ("\uFE0F", "\u200D"):
            continue
        if out and out[-1][0] == k and k == "t":
            out[-1] = (k, out[-1][1] + ch)
        else:
            out.append((k, ch))
    return out


def _mayus_enfasis(core: str, texto: str) -> bool:
    letras = [ch for ch in texto if ch.isalpha()]
    mayus = sum(1 for ch in letras if ch.isupper())
    if letras and mayus / len(letras) > 0.6:      # texto todo en mayúsculas (CTA)
        return False
    return len(core) >= 2 and core.isalpha() and core.isupper()


def _unidades(texto: str) -> list[list[str]]:
    """Palabras agrupadas en unidades que no se parten: un emoji va con la palabra
    anterior; «—», «+», «=» van con la siguiente."""
    palabras = [w for w in texto.split(" ") if w]
    unidades: list[list[str]] = []
    pegar_sig = False
    for w in palabras:
        solo_emoji = all(_es_emoji(ch) for ch in w)
        if solo_emoji and unidades and not pegar_sig:
            unidades[-1].append(w)
        elif pegar_sig and unidades:
            unidades[-1].append(w)
        else:
            unidades.append([w])
        pegar_sig = w in ("—", "–", "+", "=", "-")
    return unidades


class Maqueta:
    """Texto repartido en líneas con su tamaño de letra; sabe dibujarse."""

    def __init__(self, tipo: Tipografia, texto: str, est: Estilo, c: Config):
        self.tipo, self.texto, self.est, self.c = tipo, texto, est, c
        self.tam, self.lineas = self._ajustar()

    # -- medidas
    def _fuentes(self, tam):
        return self.tipo.fuente(tam, self.est.var), self.tipo.fuente(tam, self.est.var_acento)

    def _piezas(self, palabra: str, tam: int):
        """[(kind, texto, color, fuente|None, ancho)] de una palabra."""
        f, fa = self._fuentes(tam)
        out = []
        core = palabra.strip(_PUNT)
        acento = (core.upper() in [x.upper() for x in self.c.acento_palabras]
                  or (self.est.acentuar_mayus and _mayus_enfasis(core, self.texto)))
        for k, s in _segmentos(palabra):
            if k == "e":
                im = self.tipo.emoji_img(s, round(tam * 0.92))
                out.append(("e", s, None, None, im.width))
                continue
            if acento and core:
                i = s.find(core) if core in s else -1
                if i >= 0:
                    for parte, col, fu in ((s[:i], self.est.color, f), (core, self.est.acento, fa),
                                           (s[i + len(core):], self.est.color, f)):
                        if parte:
                            out.append(("t", parte, col, fu, fu.getlength(parte)))
                    continue
            out.append(("t", s, self.est.color, f, f.getlength(s)))
        return out

    def _ancho_palabra(self, w, tam):
        return sum(p[4] for p in self._piezas(w, tam))

    def _ancho_linea(self, palabras, tam):
        f, _ = self._fuentes(tam)
        esp = f.getlength(" ")
        return sum(self._ancho_palabra(w, tam) for w in palabras) + esp * max(0, len(palabras) - 1)

    def _repartir(self, tam):
        """Reparto: el mínimo de líneas que cabe; entre esos, el que no deja un
        artículo o una preposición al final de línea y, luego, el más equilibrado."""
        if self.est.lineas:
            lin = [l.split(" ") for l in self.est.lineas]
            return lin if max(self._ancho_linea(l, tam) for l in lin) <= self.est.ancho_max else None
        from itertools import combinations
        uds = _unidades(self.texto)
        n = len(uds)
        anchos = {}

        def ancho(i, j):
            if (i, j) not in anchos:
                anchos[(i, j)] = self._ancho_linea([w for u in uds[i:j] for w in u], tam)
            return anchos[(i, j)]

        def floja(j):            # la línea que acaba en la unidad j-1 termina en palabra débil
            ult = uds[j - 1][-1].strip(_PUNT).lower()
            return ult in _PALABRAS_DEBILES
        for k in range(1, min(self.est.max_lineas, n) + 1):
            mejor = None
            for cortes in combinations(range(1, n), k - 1):
                b = (0,) + cortes + (n,)
                anch = max(ancho(b[i], b[i + 1]) for i in range(k))
                if anch > self.est.ancho_max:
                    continue
                clave = (sum(floja(b[i + 1]) for i in range(k - 1)), anch)
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, b)
            if mejor:
                b = mejor[1]
                return [[w for u in uds[b[i]:b[i + 1]] for w in u] for i in range(k)]
        return None

    def _ajustar(self):
        for tam in range(self.est.tam_max, self.est.tam_min - 1, -2):
            lin = self._repartir(tam)
            if lin:
                return tam, lin
        lin = self._repartir(self.est.tam_min)
        if not lin:
            raise ErrorTrailer(f"«{self.texto}» no cabe en {self.est.max_lineas} líneas ni a "
                               f"{self.est.tam_min} px")
        return self.est.tam_min, lin

    @property
    def paso(self) -> int:
        return round(self.tam * self.est.interlineado)

    def tamano(self) -> tuple[int, int]:
        f, _ = self._fuentes(self.tam)
        asc, desc = f.getmetrics()
        ancho = max(self._ancho_linea(l, self.tam) for l in self.lineas)
        alto = self.paso * (len(self.lineas) - 1) + asc + desc
        return math.ceil(ancho), math.ceil(alto)

    def textos_lineas(self) -> list[str]:
        return [" ".join(l) for l in self.lineas]

    def dibujar(self, img, x_centro: int, y_top: int) -> tuple[int, int, int, int]:
        """Dibuja centrado en x_centro desde y_top; devuelve la caja (x0, y0, x1, y1)."""
        from PIL import Image, ImageDraw, ImageFilter
        f, _ = self._fuentes(self.tam)
        asc, desc = f.getmetrics()
        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        emojis = []
        x_min, x_max = 10 ** 9, -1
        for li, palabras in enumerate(self.lineas):
            ancho = self._ancho_linea(palabras, self.tam)
            x = x_centro - ancho / 2.0
            x_min, x_max = min(x_min, x), max(x_max, x + ancho)
            base = y_top + asc + li * self.paso
            esp = f.getlength(" ")
            for wi, w in enumerate(palabras):
                for k, s, col, fu, an in self._piezas(w, self.tam):
                    if k == "e":
                        im = self.tipo.emoji_img(s, round(self.tam * 0.92))
                        emojis.append((im, round(x), round(base + desc * 0.30 - im.height)))
                    else:
                        d.text((x, base), s, font=fu, fill=col + (255,), anchor="ls",
                               stroke_width=self.est.trazo,
                               stroke_fill=(self.est.trazo_color + (255,)) if self.est.trazo else None)
                    x += an
                if wi < len(palabras) - 1:
                    x += esp
        if self.est.sombra:
            sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sombra.putalpha(capa.getchannel("A").point(lambda v: int(v * 0.55)))
            sombra = sombra.filter(ImageFilter.GaussianBlur(6))
            img.alpha_composite(sombra, (0, 4))
        img.alpha_composite(capa)
        for im, ex, ey in emojis:
            img.alpha_composite(im, (ex, ey))
        alto = self.paso * (len(self.lineas) - 1) + asc + desc
        return (int(x_min), int(y_top), int(math.ceil(x_max)), int(y_top + alto))


def _panel(img, caja, c: Config, radio=30, alfa=0.92):
    """Panel con el azul verdoso del póster y un filete crema fino (estilo cuento)."""
    from PIL import ImageDraw
    from PIL import Image
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle(caja, radius=radio, fill=c.marca["fondo"] + (round(255 * alfa),))
    ins = 9
    d.rounded_rectangle((caja[0] + ins, caja[1] + ins, caja[2] - ins, caja[3] - ins),
                        radius=max(4, radio - ins), outline=c.marca["texto"] + (150,), width=2)
    img.alpha_composite(capa)


def _estilo_gancho(c: Config, lineas=None, portada=False) -> Estilo:
    g = c.portada if portada else c.gancho
    return Estilo(tam_max=int(g["tam_max"]), tam_min=int(g["tam_min"]),
                  max_lineas=int(g["max_lineas"]), ancho_max=int(g["ancho_max"]),
                  var=VAR_GANCHO, var_acento=VAR_ACENTO, color=c.marca["texto"],
                  acento=c.marca["acento"], interlineado=1.13, lineas=lineas)


def render_tarjeta_texto(c: Config, tipo: Tipografia, texto: str, destino: Path, *,
                         y_top: int | None = None, y_centro: int | None = None,
                         y_fin: int | None = None, lineas=None, portada=False,
                         fondo=None) -> dict:
    """Texto en panel (gancho o título de portada) sobre un lienzo 1080x1920.
    Sin `fondo`, PNG transparente. Devuelve {caja, lineas, tam}."""
    from PIL import Image
    m = Maqueta(tipo, texto, _estilo_gancho(c, lineas, portada), c)
    tw, th = m.tamano()
    pad_x, pad_y = 46, 34
    alto = th + 2 * pad_y
    if y_top is None:
        y_top = (y_centro - alto // 2) if y_centro is not None else (y_fin - alto)
    caja = (W // 2 - tw // 2 - pad_x, y_top, W // 2 + (tw + 1) // 2 + pad_x, y_top + alto)
    img = (fondo.convert("RGBA") if fondo is not None else Image.new("RGBA", (W, H), (0, 0, 0, 0)))
    _panel(img, caja, c)
    m.dibujar(img, W // 2, y_top + pad_y)
    if destino.suffix.lower() in (".jpg", ".jpeg"):
        img.convert("RGB").save(destino, quality=92, subsampling=0)
    else:
        img.save(destino)
    return {"caja": list(caja), "lineas": m.textos_lineas(), "tam": m.tam}


def render_subtitulo(c: Config, tipo: Tipografia, texto: str, destino: Path, y_fin: int) -> dict:
    """Subtítulo recortado a su caja (PNG con alfa) para superponer en (x, y)."""
    from PIL import Image
    s = c.subs
    est = Estilo(tam_max=int(s["tam"]), tam_min=int(s["tam"]) - 10,
                 max_lineas=int(s["max_lineas"]), ancho_max=int(s["ancho_max"]),
                 var=VAR_SUBS, var_acento=VAR_SUBS, color=c.marca["texto"],
                 acento=c.marca["texto"], interlineado=1.16, trazo=5, sombra=True,
                 acentuar_mayus=False)
    m = Maqueta(tipo, texto, est, c)
    tw, th = m.tamano()
    margen = 16
    lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y_top = y_fin - th
    caja = m.dibujar(lienzo, W // 2, y_top)
    recorte = (max(0, caja[0] - margen), max(0, caja[1] - margen),
               min(W, caja[2] + margen), min(H, caja[3] + margen + 8))
    lienzo.crop(recorte).save(destino)
    return {"x": recorte[0], "y": recorte[1], "caja": list(recorte), "lineas": m.textos_lineas(),
            "tam": m.tam}


def render_cta(c: Config, tipo: Tipografia, destino: Path) -> dict:
    """Cartela final: fondo de marca + póster oficial entero + CTA literal."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), c.marca["fondo"] + (255,))
    poster = Image.open(c.poster).convert("RGB")
    pw = int(c.cta["poster_ancho"])
    ph = round(poster.height * pw / poster.width)
    poster = poster.resize((pw, ph), Image.LANCZOS)
    px, py = (W - pw) // 2, int(c.cta["poster_y"])
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle((px + 6, py + 14, px + pw + 6, py + ph + 14), fill=(0, 0, 0, 120))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(14)))
    img.paste(poster, (px, py))
    ImageDraw.Draw(img).rectangle((px - 3, py - 3, px + pw + 2, py + ph + 2),
                                  outline=c.marca["texto"] + (255,), width=3)
    texto = c.cta["texto"]
    lineas = c.cta.get("lineas")
    y = py + ph + 46
    cajas = []
    if lineas:
        # 1.ª línea (la del título) más grande; el resto, el cuerpo de la CTA.
        primera = Maqueta(tipo, lineas[0], Estilo(118, 80, 1, 960, VAR_CTA_TIT, VAR_CTA_TIT,
                                                   c.marca["texto"], c.marca["acento"],
                                                   acentuar_mayus=False, lineas=[lineas[0]]), c)
        cajas.append(primera.dibujar(img, W // 2, y))
        y = cajas[-1][3] + 14
        resto = Maqueta(tipo, " ".join(lineas[1:]), Estilo(66, 46, len(lineas) - 1, 960, VAR_CTA,
                                                         VAR_CTA, c.marca["texto"],
                                                         c.marca["acento"], interlineado=1.18,
                                                         acentuar_mayus=False,
                                                         lineas=lineas[1:]), c)
        cajas.append(resto.dibujar(img, W // 2, y))
        reparto = primera.textos_lineas() + resto.textos_lineas()
    else:
        m = Maqueta(tipo, texto, Estilo(80, 46, 4, 960, VAR_CTA, VAR_CTA_TIT, c.marca["texto"],
                                        c.marca["acento"], acentuar_mayus=False), c)
        cajas.append(m.dibujar(img, W // 2, y))
        reparto = m.textos_lineas()
    if " ".join(reparto) != texto:
        raise ErrorTrailer("la CTA dibujada no es la literal")
    caja = [min(b[0] for b in cajas), cajas[0][1], max(b[2] for b in cajas), cajas[-1][3]]
    img.convert("RGB").save(destino)
    return {"caja_texto": caja, "lineas": reparto, "poster": [px, py, px + pw, py + ph]}


# ============================================================ plan del clip
def planificar(c: Config, corte: dict, dialogos: list[dict]) -> dict:
    trs = tramos_de(corte)
    segs, o = [], 0.0
    for t in trs:
        segs.append({**t, "o": round(o, 4)})
        o += t["b"] - t["a"]
    t_main = o
    fcta = float(c.cta["fundido_s"])
    cta_t0 = t_main - fcta
    total = cta_t0 + float(c.cta["duracion_s"])
    s = c.subs
    subs = []
    for sg in segs:
        for d in dialogos:
            ov = _solapa(d["t0"], d["t1"], sg["a"], sg["b"])
            if ov < float(s["solape_min_s"]) and ov < 0.9 * (d["t1"] - d["t0"]):
                continue
            a = max(d["t0"], sg["a"]) - sg["a"] + sg["o"]
            b = min(d["t1"] + float(s["retencion_s"]), sg["b"]) - sg["a"] + sg["o"]
            subs.append({"t0": a, "t1": b, "texto": d["texto"],
                         "fuente_t": [d["t0"], d["t1"]]})
    subs.sort(key=lambda x: x["t0"])
    for i, sb in enumerate(subs):
        if i + 1 < len(subs):
            sb["t1"] = min(sb["t1"], subs[i + 1]["t0"] - 0.04)
        sb["t1"] = min(sb["t1"], cta_t0)
        if sb["t1"] - sb["t0"] < float(s["min_s"]):
            sb["t1"] = min(sb["t0"] + float(s["min_s"]),
                           subs[i + 1]["t0"] - 0.04 if i + 1 < len(subs) else cta_t0)
    subs = [x for x in subs if x["t1"] - x["t0"] >= 0.3]
    return {"segs": segs, "t_main": t_main, "cta_t0": cta_t0, "total": total, "subs": subs}


def _zonas_activas(c: Config, segs, t0, t1):
    """Zonas protegidas visibles en algún momento de [t0, t1] de SALIDA."""
    out = []
    for z in c.zonas:
        for a, b in _zona_fuente_a_salida(segs, *z["t"]):
            if _solapa(a, b, t0, t1) > 0:
                out.append(z)
                break
    return out


# ============================================================ render
def _ffmpeg() -> str:
    return herramientas.exigir_ffmpeg()


def _loudness(cmd_base: list[str]) -> float | None:
    """Loudness integrado (LUFS) de la mezcla de audio de `cmd_base` (sin salida)."""
    r = subprocess.run(cmd_base + ["-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr or "")
    return float(m[-1]) if m else None


def _entradas_y_grafo_audio(c: Config, plan: dict, fps: str):
    """Entradas (tramos + audio de la CTA) y grafo de audio común a la medida y al render."""
    fa = c.fundido_audio
    entradas, grafo, etiquetas = [], [], []
    for i, sg in enumerate(plan["segs"]):
        src = c.fuentes[sg["fuente"]] if sg["fuente"] else c.fuente
        d = sg["b"] - sg["a"]
        entradas += ["-ss", f"{sg['a']:.3f}", "-t", f"{d:.3f}", "-i", str(src)]
        fin = plan["segs"][-1] is sg
        fo = max(fa, 0.2) if fin else fa
        grafo.append(f"[{i}:a]aresample=48000,asetpts=PTS-STARTPTS,"
                     f"afade=t=in:st=0:d={fa:.3f},afade=t=out:st={max(0, d - fo):.3f}:d={fo:.3f}[a{i}]")
        etiquetas.append(f"[a{i}]")
    n = len(plan["segs"])
    grafo.append("".join(etiquetas) + f"concat=n={n}:v=0:a=1[amain]")
    cta_a = c.cta.get("audio")
    if cta_a:
        a, b = float(cta_a[0]), float(cta_a[1])
        dur_cta = min(b - a, float(c.cta["duracion_s"]))
        entradas += ["-ss", f"{a:.3f}", "-t", f"{dur_cta:.3f}", "-i", str(c.fuente)]
        k = n
        ms = int(round(plan["cta_t0"] * 1000))
        grafo.append(f"[{k}:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.04,"
                     f"afade=t=out:st={max(0, dur_cta - 0.5):.3f}:d=0.5,adelay={ms}|{ms}[acta]")
        grafo.append("[amain][acta]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
                     f"apad=whole_dur={plan['total']:.3f}[amix]")
    else:
        grafo.append(f"[amain]apad=whole_dur={plan['total']:.3f}[amix]")
    return entradas, grafo


def render_clip(c: Config, corte: dict, dialogos: list[dict], out_mp4: Path,
                out_portada: Path, clips_dir: Path, work: Path) -> dict:
    """Renderiza un clip + su portada y escribe clips/<clip>.render.json."""
    tipo_txt = Tipografia(c)
    nombre = corte["nombre"]
    tipo = str(corte["tipo"]).upper()
    plan = planificar(c, corte, dialogos)
    fps = c.fps
    work.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    zs = c.zona_segura

    # --- gancho (literal del tipo), del fotograma 0 a gdur
    gdur, gfade = float(c.gancho["duracion_s"]), float(c.gancho["fundido_s"])
    gancho = c.tipos[tipo]["gancho"]
    gpos = corte.get("gancho_pos") or c.gancho.get("pos") or "arriba"
    g_png = clips_dir / f"{nombre}.gancho.png"
    if gpos == "abajo":
        ginfo = render_tarjeta_texto(c, tipo_txt, gancho, g_png, y_fin=int(c.gancho["y_abajo_fin"]),
                                     lineas=c.tipos[tipo].get("lineas"))
    else:
        ginfo = render_tarjeta_texto(c, tipo_txt, gancho, g_png, y_top=int(c.gancho["y_arriba"]),
                                     lineas=c.tipos[tipo].get("lineas"))
    gcaja = ginfo["caja"]
    avisos = []
    for z in _zonas_activas(c, plan["segs"], 0, gdur + gfade):
        if _cajas_solapan(gcaja, z["caja"]):
            raise ErrorTrailer(f"el gancho taparía el rótulo oficial «{z['nombre']}»")

    # --- subtítulos (esquivan gancho, zonas protegidas y la zona insegura de IG)
    subs_out = []
    for i, sb in enumerate(plan["subs"]):
        png = work / f"sub_{i:02d}.png"
        y_fin = int(c.subs["y_fin"])
        info = render_subtitulo(c, tipo_txt, sb["texto"], png, y_fin)
        obstaculos = [z["caja"] for z in _zonas_activas(c, plan["segs"], sb["t0"], sb["t1"])]
        if sb["t0"] < gdur + gfade:
            obstaculos.append(gcaja)
        x0, y0, x1, y1 = info["caja"]
        # desplazamientos verticales a probar: su sitio, encima o debajo de cada obstáculo
        desplazamientos = [0]
        for ob in sorted(obstaculos, key=lambda b: b[1]):
            desplazamientos += [(ob[1] - 20) - y1, (ob[3] + 20) - y0]
        elegido = None
        for dy in desplazamientos:
            cj = (x0, y0 + dy, x1, y1 + dy)
            if cj[1] < zs["y0"] or cj[3] > zs["y1"] + 40:
                continue
            if not any(_cajas_solapan(cj, ob) for ob in obstaculos):
                elegido = cj
                break
        if elegido is None:
            avisos.append(f"subtítulo «{sb['texto']}» sin hueco libre: va en su sitio")
            elegido = (x0, y0, x1, y1)
        subs_out.append({**sb, "png": png, "x": elegido[0], "y": elegido[1],
                         "caja": list(elegido), "lineas": info["lineas"]})

    # --- CTA (cartela con el póster)
    cta_png = clips_dir / f"{nombre}.cta.png"
    cta_info = render_cta(c, tipo_txt, cta_png)

    # --- audio: medida de loudness y ganancia estática
    ff = _ffmpeg()
    entradas, grafo_a = _entradas_y_grafo_audio(c, plan, fps)
    medir = [ff, "-hide_banner", "-nostats", *entradas, "-filter_complex",
             ";".join(grafo_a) + ";[amix]ebur128=framelog=quiet[aout]", "-map", "[aout]"]
    lufs = _loudness(medir)
    lo = c.loudness
    gan = 0.0 if lufs is None else max(-float(lo["ganancia_max_db"]),
                                       min(float(lo["ganancia_max_db"]), float(lo["lufs"]) - lufs))

    # --- vídeo
    n = len(plan["segs"])
    grafo_v = []
    for i, sg in enumerate(plan["segs"]):
        src = c.fuentes[sg["fuente"]] if sg["fuente"] else c.fuente
        sw, sh = herramientas.dimensiones(src)
        if herramientas.es_vertical(sw, sh):
            enc = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        else:
            cw = int(sh * 9 / 16) // 2 * 2
            x = int(min(max(sg["x"] * sw - cw / 2, 0), sw - cw)) // 2 * 2
            enc = f"crop={cw}:{sh}:{x}:0,scale={W}:{H}"
        grafo_v.append(f"[{i}:v]{enc},setsar=1,fps={fps},format=yuv420p,setpts=PTS-STARTPTS[v{i}]")
    grafo_v.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]")
    extra = []
    k0 = n + (1 if c.cta.get("audio") else 0)
    k = k0
    extra += ["-loop", "1", "-framerate", fps, "-t", f"{gdur + gfade + 0.1:.3f}", "-i", str(g_png)]
    grafo_v.append(f"[{k}:v]format=rgba,fade=t=out:st={gdur:.3f}:d={gfade:.3f}:alpha=1[g]")
    grafo_v.append("[vc][g]overlay=0:0:eof_action=pass:format=auto[v_g]")
    ultimo = "v_g"
    k += 1
    for i, sb in enumerate(subs_out):
        dur_in = sb["t1"] + 0.1
        extra += ["-loop", "1", "-framerate", fps, "-t", f"{dur_in:.3f}", "-i", str(sb["png"])]
        fd = 0.08
        grafo_v.append(f"[{k}:v]format=rgba,fade=t=in:st={sb['t0']:.3f}:d={fd}:alpha=1,"
                       f"fade=t=out:st={max(sb['t0'], sb['t1'] - fd):.3f}:d={fd}:alpha=1[s{i}]")
        grafo_v.append(f"[{ultimo}][s{i}]overlay={sb['x']}:{sb['y']}:eof_action=pass:"
                       f"enable='between(t,{sb['t0']:.3f},{sb['t1']:.3f})':format=auto[vs{i}]")
        ultimo = f"vs{i}"
        k += 1
    cta_dur = float(c.cta["duracion_s"])
    extra += ["-loop", "1", "-framerate", fps, "-t", f"{cta_dur:.3f}", "-i", str(cta_png)]
    grafo_v.append(f"[{k}:v]format=yuv420p,setsar=1,fps={fps},settb=AVTB[card]")
    grafo_v.append(f"[{ultimo}]format=yuv420p,settb=AVTB[vm]")
    grafo_v.append(f"[vm][card]xfade=transition=fade:duration={float(c.cta['fundido_s']):.3f}:"
                   f"offset={plan['cta_t0']:.3f}[vout]")
    grafo = grafo_a + [f"[amix]volume={gan:.2f}dB,alimiter=limit={float(lo['limite'])}:level=0:"
                       f"attack=5:release=50,aresample=48000[aout]"] + grafo_v
    tmp = work / "out.mp4"
    cmd = [ff, "-y", "-hide_banner", *entradas, *extra, "-filter_complex", ";".join(grafo),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{plan['total']:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-b:v", "10M", "-maxrate", "12M",
           "-bufsize", "24M", "-pix_fmt", "yuv420p", "-r", fps,
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-map_metadata", "-1", "-metadata:s:a:0", "language=spa",
           "-movflags", "+faststart", str(tmp)]
    herramientas.ejecutar(cmd, cola=3000)
    shutil.move(str(tmp), str(out_mp4))

    # --- portada
    port = render_portada(c, tipo_txt, corte, plan, out_portada, work)

    manifiesto = {
        "nombre": nombre, "tipo": tipo, "fuente": str(c.fuente), "fps": fps,
        "tramos": [{"inicio": s["a"], "fin": s["b"], "salida": s["o"],
                    "fuente": s["fuente"] or "principal", "x": s["x"]} for s in plan["segs"]],
        "duracion": round(plan["total"], 3),
        "gancho": {"texto": gancho, "t0": 0.0, "t1": gdur, "fundido": gfade, "caja": gcaja,
                   "lineas": ginfo["lineas"], "tam": ginfo["tam"], "png": str(g_png)},
        "subtitulos": [{"t0": round(s["t0"], 3), "t1": round(s["t1"], 3), "texto": s["texto"],
                        "caja": s["caja"], "lineas": s["lineas"]} for s in subs_out],
        "cta": {"texto": c.cta["texto"], "t0": round(plan["cta_t0"], 3),
                "t_lleno": round(plan["cta_t0"] + float(c.cta["fundido_s"]), 3),
                "t1": round(plan["total"], 3), "png": str(cta_png), **cta_info,
                "audio": c.cta.get("audio")},
        "audio": {"lufs_mezcla": lufs, "ganancia_db": round(gan, 2),
                  "limite": float(lo["limite"]), "fundido_s": c.fundido_audio},
        "portada": port,
        "zonas": [{"nombre": z["nombre"], "t": list(z["t"]), "caja": list(z["caja"])}
                  for z in c.zonas],
        "avisos": avisos,
    }
    (clips_dir / f"{nombre}.render.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifiesto


def _fuente_y_t(plan: dict, t_fuente: float, c: Config):
    for s in plan["segs"]:
        if s["a"] <= t_fuente <= s["b"]:
            src = c.fuentes[s["fuente"]] if s["fuente"] else c.fuente
            return src, s, t_fuente - s["a"] + s["o"]
    return None, None, None


def render_portada(c: Config, tipo_txt: Tipografia, corte: dict, plan: dict,
                   destino: Path, work: Path) -> dict:
    from PIL import Image
    pt = corte.get("portada_t")
    if pt is None:
        s = max(plan["segs"], key=lambda x: x["b"] - x["a"])
        pt = (s["a"] + s["b"]) / 2
    pt = float(pt)
    src, seg, t_salida = _fuente_y_t(plan, pt, c)
    if src is None:
        raise ErrorTrailer(f"portada_t {pt} fuera de los tramos del clip")
    frame = work / "portada_src.png"
    sw, sh = herramientas.dimensiones(src)
    if herramientas.es_vertical(sw, sh):
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    else:
        cw = int(sh * 9 / 16) // 2 * 2
        x = int(min(max(seg["x"] * sw - cw / 2, 0), sw - cw)) // 2 * 2
        vf = f"crop={cw}:{sh}:{x}:0,scale={W}:{H}"
    herramientas.ejecutar([_ffmpeg(), "-y", "-v", "error", "-ss", f"{pt:.3f}", "-i", str(src),
                           "-frames:v", "1", "-vf", vf, str(frame)])
    fondo = Image.open(frame).convert("RGBA")
    titulo = corte.get("portada_titulo") or ""
    pos = corte.get("portada_pos") or "abajo"
    info = render_tarjeta_texto(c, tipo_txt, titulo, destino, y_centro=CENTRO_PORTADA[pos],
                                portada=True, fondo=fondo,
                                lineas=c.portadas_lineas.get(titulo))
    return {"ruta": str(destino), "titulo": titulo, "t_fuente": pt,
            "t_clip": round(t_salida, 3), "pos": pos, **info}


# ============================================================ QC (lo llama qc.py)
def _frame_rgb(mp4: Path, t: float):
    import numpy as np
    r = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(mp4),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    if a.size != W * H * 3:
        return None
    return a.reshape(H, W, 3).astype(np.int16)


def _parecido_png(frame, png: Path, solo_opaco=True) -> float | None:
    """Diferencia media (0–255) entre el fotograma y los píxeles opacos del PNG."""
    import numpy as np
    from PIL import Image
    if frame is None or not png.exists():
        return None
    im = np.asarray(Image.open(png).convert("RGBA")).astype(np.int16)
    if im.shape[0] != H or im.shape[1] != W:
        return None
    mask = im[..., 3] >= 250 if solo_opaco else np.ones(im.shape[:2], bool)
    if mask.sum() < 50:
        return None
    return float(np.abs(frame[mask] - im[..., :3][mask]).mean())


def _audio_mono(cmd_in: list[str], sr=8000):
    import numpy as np
    r = subprocess.run([_ffmpeg(), "-v", "error", *cmd_in, "-ac", "1", "-ar", str(sr),
                        "-f", "s16le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def _correlacion_audio(mp4: Path, man: dict, c: Config) -> tuple[float | None, float | None]:
    """(mediana, p10) de la correlación por ventanas de 1 s entre el audio del clip
    y los tramos originales del tráiler (≈1 = solo audio original; una música o una
    voz añadidas la bajan). Alinea cada tramo antes (retardo del códec AAC)."""
    import numpy as np
    sr = 8000
    out = _audio_mono(["-i", str(mp4)], sr).astype(np.float64)
    cors = []
    for tr in man["tramos"]:
        src = c.fuentes.get(tr["fuente"], c.fuente) if tr["fuente"] != "principal" else c.fuente
        d = tr["fin"] - tr["inicio"]
        ref = _audio_mono(["-ss", f"{tr['inicio']:.3f}", "-t", f"{d:.3f}", "-i", str(src)],
                          sr).astype(np.float64)
        o = int(round(tr["salida"] * sr))
        m = 600                                    # ±75 ms de margen para alinear
        seg = out[max(0, o - m):o + len(ref) + m]
        pre = o - max(0, o - m)
        if len(seg) < len(ref) // 2 or len(ref) < sr:
            continue
        # retardo global del tramo por correlación cruzada (FFT)
        n = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
        xc = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)
        lags = np.r_[np.arange(0, pre + m + 1), np.arange(n - m, n)] if pre + m + 1 < n - m else []
        if not len(lags):
            continue
        k = int(lags[np.argmax(xc[lags])])
        desp = k if k <= pre + m else k - n          # índice de seg donde empieza ref
        w = sr
        for i in range(int(0.3 * sr), len(ref) - w - int(0.3 * sr), w):
            b = ref[i:i + w]
            j = desp + i
            if j < 0 or j + w > len(seg) or np.sqrt((b ** 2).mean()) < 10 ** (-45 / 20):
                continue
            a = seg[j:j + w]
            den = float(np.sqrt((a ** 2).sum() * (b ** 2).sum()))
            if den > 0:
                cors.append(float((a * b).sum()) / den)
    if not cors:
        return None, None
    cors.sort()
    return float(np.median(cors)), float(cors[int(0.1 * (len(cors) - 1))])


def _negros_fuente(man: dict, c: Config) -> list[tuple[float, float]]:
    """Negros que ya trae el tráiler en los tramos del clip, en tiempo de SALIDA."""
    out = []
    for tr in man["tramos"]:
        src = c.fuentes.get(tr["fuente"], c.fuente) if tr["fuente"] != "principal" else c.fuente
        d = tr["fin"] - tr["inicio"]
        r = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-ss", f"{tr['inicio']:.3f}",
                            "-t", f"{d:.3f}", "-i", str(src), "-vf", "scale=270:-2,blackdetect=d=0.1",
                            "-an", "-f", "null", "-"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        for a, b in re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", r.stderr or ""):
            out.append((float(a) + tr["salida"], float(b) + tr["salida"]))
    return out


_MARCAS = re.compile(r"capcut|vn video|inshot|kinemaster|splice|filmora|canva|"
                     r"videoleap|tiktok|bytedance|watermark", re.I)


def qc_clip(p, mp4: Path, dur: float) -> dict:
    """Comprobaciones del modo tráiler sobre un final ya exportado.
    {'fallos': [...], 'avisos': [...], 'ok': [...], 'portada': Path|None,
     'frames': [(etiqueta, t)], 'silencio_desde': t}"""
    out = {"fallos": [], "avisos": [], "ok": [], "portada": None, "frames": [],
           "silencio_desde": None, "congelado_desde": None, "negros_fuente": []}
    try:
        c = config(p)
    except ErrorTrailer as e:
        out["fallos"].append(f"config tráiler: {e}")
        return out
    base = mp4.parent.parent
    man_p = base / "clips" / f"{mp4.stem}.render.json"
    if not man_p.exists():
        out["fallos"].append(f"sin manifiesto {man_p.name} (¿renderizado fuera de trailer.py?)")
        return out
    man = json.loads(man_p.read_text(encoding="utf-8"))
    tipo = man.get("tipo")
    # nombre y textos literales
    if tipo not in c.tipos or not mp4.stem.startswith(f"{str(tipo).lower()}_"):
        out["fallos"].append(f"nombre/tipo: «{mp4.stem}» no empieza por «{str(tipo).lower()}_»")
    if man["gancho"]["texto"] != c.tipos.get(tipo, {}).get("gancho"):
        out["fallos"].append("el gancho no es el literal del briefing")
    if man["cta"]["texto"] != c.cta["texto"] or " ".join(man["cta"]["lineas"]) != c.cta["texto"]:
        out["fallos"].append("la CTA no es la literal del briefing")
    lo, hi = float(c.duracion["min"]), float(c.duracion["max"])
    if not (lo <= dur <= hi):
        out["fallos"].append(f"dura {dur:.1f} s (de {lo:.0f} a {hi:.0f})")
    # gancho visible del fotograma 0 a los 3 s
    g_png = Path(man["gancho"]["png"])
    t1 = float(man["gancho"]["t1"])
    difs = [_parecido_png(_frame_rgb(mp4, t), g_png) for t in (0.0, t1 / 2, t1 - 0.06)]
    if any(d is None for d in difs) or max(difs) > 22:
        out["fallos"].append("gancho NO visible entero de 0 a "
                             f"{t1:g} s (dif. {['¿?' if d is None else round(d) for d in difs]})")
    else:
        out["ok"].append(f"gancho literal 0–{t1:g} s")
    # CTA al final, el tiempo suficiente
    cta_png = Path(man["cta"]["png"])
    t_lleno, t_fin = float(man["cta"]["t_lleno"]), float(man["cta"]["t1"])
    visible = t_fin - t_lleno
    difs = [_parecido_png(_frame_rgb(mp4, t), cta_png, solo_opaco=False)
            for t in (t_lleno + 0.1, (t_lleno + t_fin) / 2, dur - 0.1)]
    if any(d is None for d in difs) or max(difs) > 12:
        out["fallos"].append(f"CTA no visible al final (dif. {['¿?' if d is None else round(d) for d in difs]})")
    elif visible < 3.0:
        out["fallos"].append(f"CTA solo {visible:.1f} s entera (mín. 3 s)")
    else:
        out["ok"].append(f"CTA literal {visible:.1f} s")
    # subtítulos y gancho fuera de las zonas protegidas (rótulos oficiales)
    choques = []
    segs = [{"a": t["inicio"], "b": t["fin"], "o": t["salida"]} for t in man["tramos"]]
    for sb in man["subtitulos"]:
        for z in _zonas_activas(c, segs, sb["t0"], sb["t1"]):
            if _cajas_solapan(sb["caja"], z["caja"]):
                choques.append(f"«{sb['texto']}» sobre «{z['nombre']}»")
        if sb["t0"] < t1 + float(man["gancho"]["fundido"]) and \
                _cajas_solapan(sb["caja"], man["gancho"]["caja"]):
            choques.append(f"«{sb['texto']}» sobre el gancho")
    if choques:
        out["fallos"].append("choques: " + "; ".join(choques[:3]))
    else:
        out["ok"].append(f"{len(man['subtitulos'])} subtítulos sin choques")
    # audio original (correlación con el tráiler) => sin música ni voces añadidas
    med, p10 = _correlacion_audio(mp4, man, c)
    if med is None:
        out["avisos"].append("audio: no se pudo medir la correlación")
    elif med < 0.97 or p10 < 0.92:
        # (calibrado: el original da ~0,99/0,98; con un fondo añadido a -11 dB, 0,97/0,86)
        out["fallos"].append(f"audio no coincide con el original (corr. med {med:.3f}, p10 "
                             f"{p10:.3f}): ¿música o voz añadidas?")
    elif med < 0.985:
        out["avisos"].append(f"audio: correlación con el original algo baja (med {med:.3f}, "
                             f"p10 {p10:.3f}): escúchalo")
    else:
        out["ok"].append(f"audio original (corr. {med:.3f}/{p10:.3f})")
    # sin marcas de agua de editores (metadatos) y audio etiquetado en español
    r = subprocess.run([herramientas.FFPROBE, "-v", "error", "-show_entries",
                        "format_tags:stream_tags", "-of", "json", str(mp4)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tags = r.stdout or ""
    if _MARCAS.search(tags):
        out["fallos"].append("metadatos de un editor externo (marca de agua)")
    else:
        out["ok"].append("sin marcas de editores")
    if '"language": "spa"' not in tags:
        out["avisos"].append("audio sin etiqueta de idioma «spa»")
    # portada
    port = Path(man["portada"]["ruta"])
    port = port if port.exists() else mp4.with_name(f"{mp4.stem}.portada.jpg")
    if not port.exists():
        out["fallos"].append("falta la portada")
    else:
        from PIL import Image
        with Image.open(port) as im:
            if im.size != (W, H):
                out["fallos"].append(f"portada {im.size[0]}x{im.size[1]}≠1080x1920")
        if man["portada"]["titulo"] not in c.portadas:
            out["fallos"].append("título de portada no literal")
        else:
            out["ok"].append("portada")
        out["portada"] = port
    out["frames"] = [("0 s", 0.0), (f"{t1 - 0.1:.1f} s", t1 - 0.1), ("final", dur - 0.3)]
    # Lo que no es un defecto: la cola de la CTA puede ir en silencio, la cartela
    # es fija (congelado) y los negros que ya trae el tráiler oficial.
    out["silencio_desde"] = float(man["cta"]["t0"]) + 1.0
    out["congelado_desde"] = float(man["cta"]["t0"]) - 0.3
    out["negros_fuente"] = _negros_fuente(man, c)
    if out["negros_fuente"]:
        out["ok"].append(f"{len(out['negros_fuente'])} negro(s) del propio tráiler (no cuentan)")
    for a in man.get("avisos") or []:
        out["avisos"].append(a)
    return out


# ============================================================ CLI (desde clips.py / editar_clips.py)
def _nombre_video(arg: str) -> str:
    pth = Path(arg)
    return pth.stem if pth.suffix.lower() in proyecto.EXT_VIDEO else pth.name


def validar_cli(p, video_arg: str, cortes_path: Path | None, solo) -> bool:
    c = config(p)
    nombre = _nombre_video(video_arg)
    base = p.transcripciones_dir / nombre
    cortes = cargar_cortes(cortes_path or (base / "cortes.json"))
    dialogos = cargar_dialogos(c)
    res = validar_cortes(c, cortes, herramientas.duracion(c.fuente), dialogos)
    import validar
    nombres = [x.get("nombre") for x in cortes if isinstance(x, dict)]
    sel = proyecto.filtrar_solo(nombres, solo, "corte") if solo else None
    return validar.informar(res, "cortes.json", solo=sel, decir=proyecto.decir)


def editar_cli(p, args) -> int:
    """editar_clips.py en modo tráiler: valida, renderiza finales + portadas."""
    import validar
    try:
        c = config(p)
    except ErrorTrailer as e:
        raise SystemExit(f"[!] {e}")
    nombre = _nombre_video(args.video)
    base = p.transcripciones_dir / nombre
    cortes_path = Path(args.cortes) if args.cortes else (base / "cortes.json")
    cortes = cargar_cortes(cortes_path)
    dialogos = cargar_dialogos(c)
    if not dialogos:
        proyecto.decir("AVISO: sin trailer.dialogos: los clips salen sin subtítulos")
    nombres = [x.get("nombre") for x in cortes if isinstance(x, dict)]
    solo = proyecto.filtrar_solo(nombres, args.solo, "corte") if args.solo else None
    res = validar_cortes(c, cortes, herramientas.duracion(c.fuente), dialogos)
    if not validar.informar(res, "cortes.json", solo=solo or set(nombres), decir=proyecto.decir):
        raise SystemExit("[!] cortes.json tiene errores en los clips a renderizar: corrígelos y relanza.")
    out = base / "finales"
    clips_dir = base / "clips"
    out.mkdir(parents=True, exist_ok=True)
    proyecto.decir(f"Modo tráiler: fuente {c.fuente.name} · sin b-roll, sin música añadida, "
                   f"sin recorte de silencios")
    work_base = RAIZ / "whisper"
    work_base.mkdir(parents=True, exist_ok=True)
    workroot = Path(args.work_dir) if args.work_dir else Path(
        tempfile.mkdtemp(prefix="_trailer_", dir=str(work_base)))
    hechos, fallos = 0, []
    try:
        for corte in cortes:
            n = corte["nombre"]
            if solo is not None and n not in solo:
                continue
            print(f"=== {n}", flush=True)
            try:
                if getattr(args, "solo_portada", False):
                    # Corrección de la portada sola: ni vídeo ni audio se tocan.
                    man_p = clips_dir / f"{n}.render.json"
                    if not man_p.exists() or not (out / f"{n}.mp4").exists():
                        raise ErrorTrailer("no hay render previo de este clip: lánzalo sin --solo-portada")
                    man = json.loads(man_p.read_text(encoding="utf-8"))
                    (workroot / n).mkdir(parents=True, exist_ok=True)
                    man["portada"] = render_portada(c, Tipografia(c), corte,
                                                    planificar(c, corte, dialogos),
                                                    out / f"{n}.portada.jpg", workroot / n)
                    man_p.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
                    hechos += 1
                    proyecto.decir(f"OK {n}.portada.jpg · «{man['portada']['titulo']}» "
                                   f"({' / '.join(man['portada']['lineas'])})")
                    continue
                man = render_clip(c, corte, dialogos, out / f"{n}.mp4", out / f"{n}.portada.jpg",
                                  clips_dir, workroot / n)
                hechos += 1
                tr = " + ".join(f"{t['inicio']:.1f}–{t['fin']:.1f}" for t in man["tramos"])
                proyecto.decir(f"OK {n}.mp4 · {man['duracion']:.0f} s · tipo {man['tipo']} · tramos "
                               f"{tr} · {len(man['subtitulos'])} subtítulos · audio "
                               f"{man['audio']['ganancia_db']:+.1f} dB · portada «{man['portada']['titulo']}»"
                               + (f" · avisos: {'; '.join(man['avisos'])}" if man["avisos"] else ""))
            except Exception as e:
                fallos.append(n)
                import traceback
                traceback.print_exc(file=sys.stdout)
                proyecto.decir(f"FALLO {n}.mp4 · {herramientas.describir_error(e)} (detalle en el log)")
    finally:
        if not args.work_dir:
            shutil.rmtree(workroot, ignore_errors=True)
    proyecto.decir(f"RESUMEN: {hechos} OK · {len(fallos)} fallo(s)"
                   + (f" ({', '.join(fallos)})" if fallos else "") + f" -> {out}")
    proyecto.decir(f"QC: .venv\\Scripts\\python.exe qc.py --proyecto {p.id} \"{nombre}\"  "
                   f"(y mira finales/_qc.jpg)")
    return 1 if fallos else 0

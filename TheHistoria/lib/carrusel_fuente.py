"""
CARRUSELES · material para escribir el plan, en el menor nº de tokens.

  fuente_compacta  `carruseles.py --fuente <video|ruta>`: texto de la
                   transcripción en párrafos SIN tiempos (del `.txt`; nunca del
                   `.json` de Whisper) + títulos y frases de su `cortes.json` +
                   clips para la portada. También admite un `articulo.md` de
                   TheTextos (o su carpeta).
  listado          `carruseles.py --listar`: carruseles del proyecto (plan / en
                   salidas / en REVISADOS / publicado) y vídeos de `_Historico`
                   con cuántos carruseles tiene cada uno.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

import config
from lib.carrusel_plan import resolver_ruta
from lib.proyectos import Proyecto, ProyectoError, es_ajeno, es_propio

_RE_TIEMPO = re.compile(r"^\s*\[?\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\s*-->\s*"
                        r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\]?\s*")
_RE_CARRUSEL = re.compile(r"^carrusel_(\d{8}-\d{4})_(.+)$")
PARRAFO_CHARS = 650


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(config.PRUEBAS_IA.resolve()).as_posix()
    except ValueError:
        return str(p)


def _bajo(path: Path, raiz: Path) -> bool:
    try:
        path.resolve().relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


# ------------------------------------------------------------------ fuente
def resolver_fuente(arg: str, proyecto: Proyecto) -> Path:
    """Ruta (absoluta, relativa a PruebasIA/TheHistoria) o nombre de vídeo/artículo
    del proyecto (exacto o aproximado) en _Historico, TheEditor o TheTextos."""
    p = Path(arg)
    for cand in ([p] if p.is_absolute() else
                 [config.PRUEBAS_IA / p, config.PROJECT_ROOT / p, Path.cwd() / p]):
        if cand.exists():
            if es_ajeno(cand, proyecto) and not es_propio(cand, proyecto):
                raise ProyectoError(f"{arg} es material de OTRO proyecto: no se mezclan proyectos.")
            return cand
    bases = [proyecto.historico_dir, proyecto.transcripciones_dir, proyecto.textos_dir]
    dirs = [d for b in bases if b.is_dir() for d in sorted(b.iterdir()) if d.is_dir()]
    exactos = [d for d in dirs if d.name == arg]
    if exactos:
        return exactos[0]
    q = _plano(arg)
    aprox = [d for d in dirs if q and q in _plano(d.name)]
    if len(aprox) == 1:
        return aprox[0]
    if len(aprox) > 1:
        raise ProyectoError(f"«{arg}» encaja con varias fuentes: "
                            + "; ".join(_rel(d) for d in aprox) + ". Afina el nombre.")
    disp = [d.name for d in dirs]
    raise ProyectoError(f"no encuentro «{arg}» en el material de «{proyecto.id}». "
                        f"Disponibles: {' | '.join(disp) or '(ninguno)'}.")


def _parrafos(texto: str) -> str:
    """Líneas de Whisper → párrafos de ~PARRAFO_CHARS cortados en fin de frase."""
    lineas = [_RE_TIEMPO.sub("", l).strip() for l in texto.splitlines()]
    plano = " ".join(l for l in lineas if l)
    frases = re.split(r"(?<=[.!?…])\s+", plano)
    out, cur = [], ""
    for f in frases:
        cur = f"{cur} {f}".strip()
        if len(cur) >= PARRAFO_CHARS:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return "\n\n".join(out)


def _srt_a_texto(srt: str) -> str:
    return "\n".join(l for l in srt.splitlines()
                     if l.strip() and not l.strip().isdigit() and "-->" not in l)


def _leer(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _articulo(md: Path) -> str:
    s = _leer(md)
    titulo = ""
    if s.startswith("---"):
        fin = s.find("\n---", 3)
        if fin != -1:
            cab, s = s[3:fin], s[fin + 4:]
            m = re.search(r"(?mi)^title\s*:\s*[\"']?(.+?)[\"']?\s*$", cab)
            titulo = m.group(1) if m else ""
    return (f"Título: {titulo}\n\n" if titulo else "") + s.strip()


def _cortes(d: Path) -> list[str]:
    f = d / "cortes.json"
    if not f.exists():
        return []
    try:
        datos = json.loads(_leer(f))
    except Exception:
        return ["(cortes.json ilegible)"]
    if isinstance(datos, dict):
        datos = datos.get("cortes") or datos.get("clips") or []
    out = []
    for c in datos if isinstance(datos, list) else []:
        if not isinstance(c, dict):
            continue
        linea = f"- {c.get('nombre', '?')}: {c.get('titulo', '')}".rstrip(": ")
        if c.get("frase_viral"):
            linea += f" — «{c['frase_viral']}»"
        if c.get("gancho_texto"):
            linea += f" (gancho: «{c['gancho_texto']}»)"
        out.append(linea)
    return out


def fuente_compacta(path: Path, proyecto: Proyecto) -> tuple[str, str, str]:
    """(texto para imprimir, fuente.tipo sugerido, fuente.ruta)."""
    if path.is_file() and path.suffix.lower() == ".md":
        return _articulo(path), "articulo", _rel(path)
    if path.is_dir() and (path / "articulo.md").exists():
        return _articulo(path / "articulo.md"), "articulo", _rel(path / "articulo.md")
    d = path if path.is_dir() else path.parent
    if d.name in ("clips", "finales", "textos"):
        d = d.parent
    partes = []
    txt = d / f"{d.name}.txt"
    txts = [txt] if txt.exists() else sorted(d.glob("*.txt"))
    extractos = sorted((d / "textos").glob("*.txt")) if (d / "textos").is_dir() else []
    if txts:
        for t in txts:
            if len(txts) > 1:
                partes.append(f"## {t.stem}")
            partes.append(_parrafos(_leer(t)))
    elif extractos:
        for t in extractos:
            partes.append(f"## {t.stem}\n{_parrafos(_leer(t))}")
    elif sorted(d.glob("*.srt")):
        partes.append(_parrafos(_srt_a_texto(_leer(sorted(d.glob("*.srt"))[0]))))
    else:
        partes.append("(sin transcripción .txt/.srt en la carpeta)")
    cortes = _cortes(d)
    if cortes:
        partes.append("## Cortes (cortes.json)\n" + "\n".join(cortes))
    clips = sorted(p for p in (d / "clips").glob("*") if p.suffix.lower() in config.VIDEO_EXTS) \
        if (d / "clips").is_dir() else []
    if clips:
        partes.append("## Clips (para `portada_fondo`; elige el fotograma con "
                      "--candidatos-portada)\n" + "\n".join(f"- {_rel(c)}" for c in clips))
    return "\n\n".join(partes), "video", _rel(d)


# ------------------------------------------------------------------ listado
def _leer_json(p: Path) -> dict | None:
    try:
        d = json.loads(_leer(p))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def carruseles(proyecto: Proyecto) -> list[dict]:
    """Un registro por slug con su estado más avanzado:
    plan < en salidas < en REVISADOS < publicado."""
    fuentes = [("plan", 0, p) for p in sorted(proyecto.planes_dir.glob("*.json"))
               if not p.name.startswith("_")]
    for estado, rango, base in (("en salidas", 1, proyecto.salidas_dir),
                                ("en REVISADOS", 2, proyecto.revisados_pte),
                                ("publicado", 3, proyecto.revisados_publicados)):
        if base.is_dir():
            fuentes += [(estado, rango, d / "carrusel.json") for d in sorted(base.iterdir())
                        if d.is_dir() and (d / "carrusel.json").exists()]
    por_slug: dict[str, dict] = {}
    for estado, rango, f in fuentes:
        datos = _leer_json(f)
        if not datos or (datos.get("proyecto") and datos["proyecto"] != proyecto.id):
            continue
        slug = datos.get("slug") or f.stem
        if rango == 0:
            fecha = dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        else:
            m = _RE_CARRUSEL.match(f.parent.name)
            fecha = (datos.get("creado") or "")[:10] or (
                f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]}" if m else "?")
        fuente = datos.get("fuente") if isinstance(datos.get("fuente"), dict) else {}
        reg = {"slug": slug, "tema": datos.get("tema", ""), "formula": datos.get("formula", ""),
               "fuente_tipo": fuente.get("tipo", ""), "fuente_ruta": fuente.get("ruta", ""),
               "fecha": fecha, "estado": estado, "rango": rango,
               "carpeta": "" if rango == 0 else f.parent.name}
        previo = por_slug.get(slug)
        if previo is None or rango >= previo["rango"]:
            if previo and not reg["tema"]:
                reg["tema"] = previo["tema"]
            por_slug[slug] = reg
    return sorted(por_slug.values(), key=lambda r: (r["fecha"], r["slug"]), reverse=True)


def listado(proyecto: Proyecto) -> str:
    regs = carruseles(proyecto)
    lineas = [f"Carruseles de «{proyecto.id}» ({len(regs)}; más recientes primero):"]
    for r in regs:
        fuente = Path(r["fuente_ruta"]).name if r["fuente_ruta"] else r["fuente_tipo"] or "?"
        lineas.append(f"  {r['fecha']} · {r['estado']:<12} · {r['slug']} · {r['formula']} · "
                      f"«{r['tema']}» · fuente: {fuente}")
    if not regs:
        lineas.append("  (ninguno)")

    def cuantos(d: Path) -> int:
        return sum(1 for r in regs if r["fuente_ruta"]
                   and _bajo(resolver_ruta(r["fuente_ruta"], None), d))

    for titulo, base in ((f"Vídeos de _Historico/{proyecto.id}", proyecto.historico_dir),
                         (f"En curso en TheEditor/proyectos/{proyecto.id}/transcripciones",
                          proyecto.transcripciones_dir)):
        dirs = [d for d in base.iterdir() if d.is_dir()] if base.is_dir() else []
        if not dirs and base == proyecto.transcripciones_dir:
            continue
        dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        lineas.append(f"\n{titulo} ({len(dirs)}; más recientes primero):")
        for d in dirs:
            fecha = dt.datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d")
            n = cuantos(d)
            lineas.append(f"  {fecha} · {d.name} · {n} carrusel{'es' if n != 1 else ''}")
        if not dirs:
            lineas.append("  (ninguno)")
    return "\n".join(lineas)

"""
CARRUSELES: piezas que genera TheHistoria. Cada una es una CARPETA:

  <carpeta_carrusel>/
    01.jpg … NN.jpg     slides (1080×1350), en orden
    carrusel.json       {"tipo": "carrusel", "proyecto", "slug", "tema", "formula",
                         "objetivo", "pilar", "fuente": {"tipo", "ruta", "credito"},
                         "slides": [{"n", "rol", "titulo", "texto"}], "creado"}
    _vista.jpg          hoja de contacto (se ignora: todo lo que empieza por "_")
    <carpeta>.txt       lo escribe TheCopy al registrar: el texto listo para pegar

Al dar OK, el CEO mueve la carpeta entera a la carpeta *pendiente* del proyecto.
El nombre de la pieza en el registro es el NOMBRE DE LA CARPETA.

Los textos de las slides pueden llevar **marcado** (destacado en dorado en la
imagen): se quita al usarlos como contexto o para comparar con el caption. Las
slides pueden traer campos opcionales (numero, puntos, peticion) y el plan un
portada_fondo: se usan `puntos` y `peticion` como contexto; el resto se ignora.
"""
from __future__ import annotations

import re
from pathlib import Path

import config
from lib.util import leer_json


def es_carrusel(carpeta: Path) -> bool:
    """Carpeta con carrusel.json y al menos una slide."""
    carpeta = Path(carpeta)
    return carpeta.is_dir() and (carpeta / config.CARRUSEL_JSON).is_file() and bool(slides(carpeta))


def slides(carpeta: Path) -> list[Path]:
    """Imágenes de las slides en orden (sin _vista.jpg ni nada que empiece por "_")."""
    return sorted(f for f in Path(carpeta).iterdir()
                  if f.is_file() and f.suffix.lower() in config.EXT_IMAGEN and not f.name.startswith("_"))


def carruseles_en(carpeta: Path | None, recursivo: bool = False) -> list[Path]:
    if not carpeta or not Path(carpeta).exists():
        return []
    if recursivo:
        dirs = {j.parent for j in Path(carpeta).rglob(config.CARRUSEL_JSON)}
    else:
        dirs = {d for d in Path(carpeta).iterdir() if d.is_dir()}
    return sorted(d for d in dirs if es_carrusel(d))


def leer_json_carrusel(carpeta: Path) -> dict:
    try:
        data = leer_json(Path(carpeta) / config.CARRUSEL_JSON)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def sin_marcado(texto) -> str:
    """'8 filtros contra **clientes tóxicos**' → '8 filtros contra clientes tóxicos'."""
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: m.group(1), str(texto or ""), flags=re.S)
    return re.sub(r"\s+", " ", t.replace("**", "")).strip()


def _slides(data: dict) -> list[dict]:
    sl = [s for s in (data.get("slides") or []) if isinstance(s, dict)]
    return sorted(sl, key=lambda s: s.get("n") if isinstance(s.get("n"), (int, float)) else 0)


def gancho_slide1(data: dict) -> str:
    """Título de la slide 1 sin marcado (el gancho que el caption tiene que repetir)."""
    sl = _slides(data)
    if not sl:
        return ""
    return sin_marcado(sl[0].get("titulo") or sl[0].get("texto") or "")


def contexto(carpeta: Path, proyecto) -> dict:
    """Contexto de un carrusel para la tanda (lo que dice carrusel.json + avisos del contrato)."""
    carpeta = Path(carpeta)
    data = leer_json_carrusel(carpeta)
    imgs = slides(carpeta)
    avisos = []
    if not data:
        return {"aviso": f"{config.CARRUSEL_JSON} ilegible o vacío: revisa la carpeta.", "n_imagenes": len(imgs)}
    if data.get("tipo") not in (None, "carrusel"):
        avisos.append(f"tipo = '{data.get('tipo')}' (se esperaba 'carrusel').")
    if data.get("proyecto") and data["proyecto"] != proyecto.id:
        avisos.append(f"carrusel.json dice proyecto '{data['proyecto']}', no '{proyecto.id}'.")
    if data.get("formula") and data["formula"] not in config.FORMULAS_CARRUSEL:
        avisos.append(f"fórmula '{data['formula']}' desconocida ({', '.join(config.FORMULAS_CARRUSEL)}).")
    sl = _slides(data)
    if sl and len(sl) != len(imgs):
        avisos.append(f"{len(sl)} slides en carrusel.json y {len(imgs)} imágenes en la carpeta.")
    if len(imgs) < 2:
        avisos.append(f"solo {len(imgs)} imagen(es): un carrusel necesita al menos 2.")
    for cid in ("objetivo", "pilar"):
        campo = proyecto.campo(cid)
        if campo and data.get(cid) and proyecto.canon_valor(campo, data[cid]) is None:
            avisos.append(f"{cid} = '{data[cid]}' no es válido ({', '.join(proyecto.valores_campo(campo) or {})}).")

    ctx = {k: data[k] for k in ("tema", "formula", "objetivo", "pilar", "slug", "fuente", "creado") if k in data}
    if ctx.get("tema"):
        ctx["tema"] = sin_marcado(ctx["tema"])
    ctx["n_imagenes"] = len(imgs)
    ctx["gancho_slide1"] = gancho_slide1(data)
    ctx["slides"] = []
    for s in sl:
        d = {k: s[k] for k in ("n", "rol") if s.get(k) not in (None, "")}
        for k in ("titulo", "texto", "peticion"):
            if s.get(k):
                d[k] = sin_marcado(s[k])
        if isinstance(s.get("puntos"), list) and s["puntos"]:
            d["puntos"] = [sin_marcado(x) for x in s["puntos"]]
        ctx["slides"].append(d)
    # Texto de las slides: cuenta como "literal de la pieza" en la auditoría (repetir el gancho
    # de la slide 1 en el caption es obligatorio).
    ctx["texto_slides"] = " ".join(
        ". ".join([d.get("titulo", ""), d.get("texto", ""), *d.get("puntos", []), d.get("peticion", "")])
        for d in ctx["slides"]).strip()
    if avisos:
        ctx["aviso"] = " ".join(avisos)
    return ctx


def formula(carpeta: Path | None) -> str | None:
    if not carpeta or not Path(carpeta).is_dir():
        return None
    return leer_json_carrusel(carpeta).get("formula") or None


def fuente(carpeta: Path | None) -> dict:
    if not carpeta or not Path(carpeta).is_dir():
        return {}
    f = leer_json_carrusel(carpeta).get("fuente")
    return f if isinstance(f, dict) else {}

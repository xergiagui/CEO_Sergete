"""
El `.txt` listo para pegar, por plataforma:
  Reel     → junto al MP4, con el mismo nombre (01_x.mp4 → 01_x.txt).
  Carrusel → DENTRO de su carpeta, como <carpeta>.txt.

Se genera SIEMPRE desde el registro Excel (todas las filas de esa pieza), así
que refleja todas las plataformas aunque se hayan registrado en tandas
distintas. Viaja con la pieza al moverla de «pte Publicar» a «Publicados».
"""
from __future__ import annotations

import re
from pathlib import Path


def ruta_txt(ruta: Path | str, formato: str | None = None) -> Path:
    """Dónde va el .txt de una pieza. `formato` hace falta si la ruta ya no existe."""
    ruta = Path(ruta)
    es_carpeta = ruta.is_dir() if ruta.exists() else (formato == "carrusel")
    return ruta / f"{ruta.name}.txt" if es_carpeta else ruta.with_suffix(".txt")


def escribir(proyecto, ruta: Path, filas: list[dict]) -> Path | None:
    if not filas or not Path(ruta).exists():
        return None
    ruta = Path(ruta)
    filas = [f for f in filas if f.get("Estado") != "Descartado"] or filas
    primera = filas[0]
    nombre = ruta.name if ruta.is_dir() else ruta.stem
    formato = primera.get("Formato") or ("Carrusel" if ruta.is_dir() else "Reel")
    lineas = [f"{primera.get('ID')} · {nombre} · {formato} · {proyecto.nombre}"]
    for campo in proyecto.campos_extra():
        val = primera.get(campo["columna"])
        if val:
            lineas.append(f"{campo['columna']}: {val}")

    orden = {p: i for i, p in enumerate(proyecto.conf.get("plataformas") or {})}
    for f in sorted(filas, key=lambda f: orden.get(_pid(proyecto, f.get("Plataforma")), 99)):
        lineas += ["", f"────────── {str(f.get('Plataforma') or '').upper()} ──────────"]
        if f.get("Título"):
            lineas += [f"Título: {f['Título']}", ""]
        lineas.append(str(f.get("Texto para pegar") or "").strip())
        lineas += _checklist(proyecto, _pid(proyecto, f.get("Plataforma")), nombre, str(f.get("Copy") or ""))

    destino = ruta_txt(ruta)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def _checklist(proyecto, pid: str | None, nombre: str, copy: str) -> list[str]:
    """Checklist de publicación (NO es parte del caption), si la plataforma la define:
    proyecto.json → plataformas.<p>.checklist_publicacion = {titulo, lineas: ["... {clip} {ubicacion}"],
    ubicacion: {por_defecto, ciudades}}. {ubicacion} = la ciudad que nombre el caption o la de por defecto."""
    chk = (proyecto.plataforma(pid).get("checklist_publicacion") if pid else None) or {}
    if not chk.get("lineas"):
        return []
    ub = chk.get("ubicacion") or {}
    ciudad = next((c for c in ub.get("ciudades") or [] if re.search(rf"\b{re.escape(c)}\b", copy, re.IGNORECASE)),
                  ub.get("por_defecto") or "")
    out = ["", f"── {chk.get('titulo') or 'CHECKLIST DE PUBLICACIÓN (no forma parte del caption)'} ──"]
    out += [f"[ ] {l.format(clip=nombre, ubicacion=ciudad)}" for l in chk["lineas"]]
    return out


def _pid(proyecto, nombre_plat) -> str | None:
    for pid in proyecto.conf.get("plataformas") or {}:
        if proyecto.nombre_plataforma(pid) == nombre_plat:
            return pid
    return None

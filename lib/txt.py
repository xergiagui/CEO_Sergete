"""
El `.txt` listo para pegar, por plataforma:
  Reel     → junto al MP4, con el mismo nombre (01_x.mp4 → 01_x.txt).
  Carrusel → DENTRO de su carpeta, como <carpeta>.txt.

Se genera SIEMPRE desde el registro Excel (todas las filas de esa pieza), así
que refleja todas las plataformas aunque se hayan registrado en tandas
distintas. Viaja con la pieza al moverla de «pte Publicar» a «Publicados».
"""
from __future__ import annotations

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

    destino = ruta_txt(ruta)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def _pid(proyecto, nombre_plat) -> str | None:
    for pid in proyecto.conf.get("plataformas") or {}:
        if proyecto.nombre_plataforma(pid) == nombre_plat:
            return pid
    return None

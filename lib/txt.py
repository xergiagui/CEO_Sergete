"""
`<clip>.txt` junto a cada MP4: el texto listo para pegar, por plataforma.

Se genera SIEMPRE desde el registro Excel (todas las filas de ese clip), así
que refleja todas las plataformas aunque se hayan registrado en tandas
distintas. Viaja con el vídeo al moverlo de «pte Publicar» a «Publicados».
"""
from __future__ import annotations

from pathlib import Path


def escribir(proyecto, ruta_mp4: Path, filas: list[dict]) -> Path | None:
    if not filas or not Path(ruta_mp4).exists():
        return None
    filas = [f for f in filas if f.get("Estado") != "Descartado"] or filas
    primera = filas[0]
    lineas = [f"{primera.get('ID')} · {Path(ruta_mp4).stem} · {proyecto.nombre}"]
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

    destino = Path(ruta_mp4).with_suffix(".txt")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def _pid(proyecto, nombre_plat) -> str | None:
    for pid in proyecto.conf.get("plataformas") or {}:
        if proyecto.nombre_plataforma(pid) == nombre_plat:
            return pid
    return None

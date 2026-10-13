"""
Carga de un PROYECTO (cliente/marca) desde `proyectos/<id>/`.

Cada proyecto es autocontenido:
  proyecto.json     reglas: tono, CTA, carpetas, plataformas, campos propios
  ofertas.json      productos/ofertas a los que puede apuntar un copy
  hashtags.json     fijos por plataforma + banco temático
  banco_copys.json  copys de referencia (tono) y de reserva
  fuentes/          documentos originales de los que salió todo lo anterior
  registro_<id>.xlsx  el registro clip ↔ copy ↔ hashtags (lo crea el script)
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import config
from lib.util import leer_json, escribir_json, normalizar_hashtag

ARCHIVOS = ("proyecto.json", "ofertas.json", "hashtags.json", "banco_copys.json")


class ErrorProyecto(Exception):
    pass


def _ruta(p: str) -> Path:
    """Rutas de proyecto.json: absolutas o relativas a PruebasIA/."""
    path = Path(p)
    return path if path.is_absolute() else (config.PRUEBAS_IA / path)


class Proyecto:
    def __init__(self, pid: str):
        self.dir = config.PROYECTOS_DIR / pid
        if pid.startswith("_") or not (self.dir / "proyecto.json").exists():
            raise ErrorProyecto(
                f"No existe el proyecto '{pid}'. Disponibles: {', '.join(listar()) or '(ninguno)'}")
        faltan = [a for a in ARCHIVOS if not (self.dir / a).exists()]
        if faltan:
            raise ErrorProyecto(f"Al proyecto '{pid}' le faltan: {', '.join(faltan)}")

        self.conf = leer_json(self.dir / "proyecto.json")
        self.ofertas = leer_json(self.dir / "ofertas.json")
        self.hashtags = leer_json(self.dir / "hashtags.json")
        self.banco = leer_json(self.dir / "banco_copys.json")

        self.id = self.conf.get("id") or pid
        self.nombre = self.conf.get("nombre") or pid
        self.prefijo_id = self.conf.get("prefijo_id") or pid[:2].upper()
        self._comprobar()

    # ---------- validación de la configuración ----------
    def _comprobar(self) -> None:
        errores = []
        plats = self.conf.get("plataformas") or {}
        if not plats:
            errores.append("proyecto.json no define 'plataformas'.")
        if not self.plataformas_activas():
            errores.append("No hay ninguna plataforma con \"activa\": true.")
        for pid in self.plataformas_activas():
            for tag in self.fijos(pid):
                if not re.fullmatch(r"#[^\s#]+", tag):
                    errores.append(f"hashtags.json: fijo inválido en {pid}: '{tag}'")
        for campo in self.campos_extra():
            if "id" not in campo or "columna" not in campo:
                errores.append(f"campos_extra mal definido: {campo}")
        if errores:
            raise ErrorProyecto(f"Configuración de '{self.id}' incorrecta:\n  - " + "\n  - ".join(errores))

    # ---------- plataformas ----------
    def plataformas_activas(self) -> list[str]:
        return [p for p, c in (self.conf.get("plataformas") or {}).items() if c.get("activa")]

    def plataforma(self, pid: str) -> dict:
        try:
            return self.conf["plataformas"][pid]
        except KeyError:
            raise ErrorProyecto(f"La plataforma '{pid}' no está definida en {self.id}/proyecto.json")

    def nombre_plataforma(self, pid: str) -> str:
        return self.plataforma(pid).get("nombre") or pid.capitalize()

    # ---------- hashtags ----------
    def fijos(self, pid: str) -> list[str]:
        return [normalizar_hashtag(t) for t in (self.hashtags.get("fijos") or {}).get(pid, [])]

    def banco_tematico(self) -> dict[str, list[str]]:
        return {tema: [normalizar_hashtag(t) for t in tags]
                for tema, tags in (self.hashtags.get("tematicos") or {}).items()
                if not tema.startswith("_")}

    def pool_tematico(self) -> set[str]:
        return {t for tags in self.banco_tematico().values() for t in tags}

    # ---------- campos propios del proyecto (p. ej. Oferta) ----------
    def campos_extra(self) -> list[dict]:
        return self.conf.get("campos_extra") or []

    def valores_campo(self, campo: dict) -> dict[str, str] | None:
        """{valor_id: nombre_legible} o None si el campo es texto libre."""
        if campo.get("valores") == "ofertas":
            vals = {o["id"]: o["nombre"] for o in self.ofertas.get("ofertas", [])}
            gen = self.ofertas.get("generico")
            if gen:
                vals[gen.get("id", "generico")] = gen.get("nombre", "Genérico")
            return vals
        if isinstance(campo.get("valores"), list):
            return {v: v for v in campo["valores"]}
        return None

    # ---------- carpetas / registro ----------
    @property
    def carpeta_pendiente(self) -> Path | None:
        p = (self.conf.get("carpetas") or {}).get("pendiente")
        return _ruta(p) if p else None

    @property
    def carpeta_publicado(self) -> Path | None:
        p = (self.conf.get("carpetas") or {}).get("publicado")
        return _ruta(p) if p else None

    @property
    def registro_path(self) -> Path:
        return self.dir / (self.conf.get("registro") or f"registro_{self.id}.xlsx")


def listar() -> list[str]:
    if not config.PROYECTOS_DIR.exists():
        return []
    return sorted(d.name for d in config.PROYECTOS_DIR.iterdir()
                  if d.is_dir() and not d.name.startswith("_") and (d / "proyecto.json").exists())


def crear(pid: str, nombre: str, prefijo: str | None = None) -> Path:
    """Da de alta un proyecto nuevo copiando la plantilla."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", pid):
        raise ErrorProyecto("El id del proyecto debe ir en minúsculas, sin espacios (ej. 'mi_marca').")
    destino = config.PROYECTOS_DIR / pid
    if destino.exists():
        raise ErrorProyecto(f"Ya existe el proyecto '{pid}'.")
    shutil.copytree(config.PLANTILLA_DIR, destino)
    conf_path = destino / "proyecto.json"
    conf = leer_json(conf_path)
    conf["id"] = pid
    conf["nombre"] = nombre
    conf["prefijo_id"] = (prefijo or re.sub(r"[^A-Z]", "", nombre.upper())[:3] or pid[:2]).upper()
    conf["registro"] = f"registro_{pid}.xlsx"
    escribir_json(conf_path, conf)
    return destino

"""
Carga de un PROYECTO (cliente/marca) desde `proyectos/<id>/`.

Cada proyecto es autocontenido:
  proyecto.json     reglas: tono, CTA, carpetas, plataformas, campos propios
  ofertas.json      productos/ofertas a los que puede apuntar un copy
  hashtags.json     fijos por plataforma + banco temático (por tamaño: nicho/medio/amplio)
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

# Tamaño de un hashtag por nº de publicaciones (estimado: la API no lo da).
#   nicho < 50k · medio 50k–500k · amplio > 500k
TAMANOS = ("nicho", "medio", "amplio")
RE_TAG = re.compile(r"#[^\s#]+")


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
        self._tamanos, self._conflictos_tamano = self._indexar_tamanos()
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
                if not RE_TAG.fullmatch(tag):
                    errores.append(f"hashtags.json: fijo inválido en {pid}: '{tag}'")
        for campo in self.campos_extra():
            if "id" not in campo or "columna" not in campo:
                errores.append(f"campos_extra mal definido: {campo}")
        # banco temático: formato antiguo (tema → lista) o nuevo (tema → {nicho/medio/amplio: lista})
        for tema, val in (self.hashtags.get("tematicos") or {}).items():
            if tema.startswith("_"):
                continue
            if isinstance(val, dict):
                raras = [k for k in val if k not in TAMANOS and not k.startswith("_")]
                if raras:
                    errores.append(f"hashtags.json: tema '{tema}' con tamaños desconocidos {raras} "
                                   f"(usa {', '.join(TAMANOS)}).")
            elif not isinstance(val, list):
                errores.append(f"hashtags.json: tema '{tema}' debe ser una lista o {{nicho/medio/amplio: lista}}.")
        for tema, tags in self.banco_tematico().items():
            malos = [t for t in tags if not RE_TAG.fullmatch(t) or t != t.lower()]
            if malos:
                errores.append(f"hashtags.json: etiquetas mal formadas en '{tema}': {' '.join(malos)}")
        for tag, tam in (self.hashtags.get("tamano_fijos") or {}).items():
            if tam not in TAMANOS:
                errores.append(f"hashtags.json: tamano_fijos['{tag}'] = '{tam}' (usa {', '.join(TAMANOS)}).")
        for tag, tams in self._conflictos_tamano.items():
            errores.append(f"hashtags.json: {tag} aparece con tamaños distintos ({', '.join(sorted(tams))}).")
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

    def banco_por_tamano(self) -> dict[str, dict[str, list[str]]]:
        """tema → {nicho: [...], medio: [...], amplio: [...], sin_tamano: [...]}.

        Acepta los dos formatos de `tematicos` en hashtags.json:
          antiguo: "tema": ["#a", "#b"]                      (todo queda en sin_tamano)
          nuevo:   "tema": {"nicho": [...], "medio": [...], "amplio": [...]}
        """
        out: dict[str, dict[str, list[str]]] = {}
        for tema, val in (self.hashtags.get("tematicos") or {}).items():
            if tema.startswith("_"):
                continue
            grupos = {k: [] for k in (*TAMANOS, "sin_tamano")}
            if isinstance(val, dict):
                for tam in TAMANOS:
                    grupos[tam] = [normalizar_hashtag(t) for t in val.get(tam) or []]
            elif isinstance(val, list):
                grupos["sin_tamano"] = [normalizar_hashtag(t) for t in val]
            out[tema] = grupos
        return out

    def banco_tematico(self) -> dict[str, list[str]]:
        """tema → etiquetas (sin distinguir tamaño), en los dos formatos."""
        return {tema: [t for k in (*TAMANOS, "sin_tamano") for t in g[k]]
                for tema, g in self.banco_por_tamano().items()}

    def pool_tematico(self) -> set[str]:
        return {t for tags in self.banco_tematico().values() for t in tags}

    def _indexar_tamanos(self) -> tuple[dict[str, str], dict[str, set[str]]]:
        """{etiqueta: tamaño} del banco (formato nuevo) + `tamano_fijos`; y los conflictos."""
        mapa: dict[str, str] = {}
        vistos: dict[str, set[str]] = {}
        for g in self.banco_por_tamano().values():
            for tam in TAMANOS:
                for t in g[tam]:
                    vistos.setdefault(t, set()).add(tam)
        for t, tam in (self.hashtags.get("tamano_fijos") or {}).items():
            vistos.setdefault(normalizar_hashtag(t), set()).add(tam)
        conflictos = {t: s for t, s in vistos.items() if len(s) > 1}
        for t, s in vistos.items():
            if len(s) == 1:
                mapa[t] = next(iter(s))
        return mapa, conflictos

    def tamano_hashtag(self, tag: str) -> str | None:
        """'nicho' | 'medio' | 'amplio' (ESTIMADO, según hashtags.json) o None si no se conoce."""
        return self._tamanos.get(normalizar_hashtag(tag))

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

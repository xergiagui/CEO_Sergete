"""
PROYECTOS: cada cuenta o cliente de contenido es independiente.

Configuración de cada uno en `proyectos/<id>/` (fuente de verdad):
  proyecto.json   historias sí/no, filtro de frases, nº de historias, crédito…
  estilo.json     maquetación (fuentes, tamaños, márgenes, posiciones)
  especiales/     fondos de las historias especiales (vídeos propios)
  planes/         planes de carrusel
  reglas.md       reglas propias del proyecto (recursos, fuentes, crédito…)
`proyectos/_plantilla/` es la base de los nuevos (no cuenta como proyecto).

La IDENTIDAD (cuenta_ig, voz, emojis_max, palabras prohibidas y colores de marca)
sale de CEO_Sergete/proyectos.json → `identidad` (fuente única; no se copia). Si
falta, se usan valores neutros con aviso.

Regla común de elección (`--proyecto <id>`): si se omite y solo hay un proyecto
se usa ese; si hay varios, ERROR con la lista. Nunca se mezclan proyectos.

La POLÍTICA DE RECURSOS (b-roll `banco_comun` | `propio` | `ninguno`, `internet`…)
se lee de TheEditor/proyectos/<id>/proyecto.json → `recursos` (no se duplica).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import config


class ProyectoError(Exception):
    """Proyecto inexistente, ambiguo o mal configurado (mensaje para el usuario)."""


def _leer_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ProyectoError(f"JSON ilegible en {path} ({e.msg}, línea {e.lineno}).")
    if not isinstance(data, dict):
        raise ProyectoError(f"{path} debe ser un objeto JSON.")
    return data


def ids_disponibles() -> list[str]:
    """Proyectos de TheHistoria (carpetas de proyectos/, sin `_plantilla`)."""
    d = config.PROYECTOS_DIR
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir()
                  if p.is_dir() and p.name != config.PLANTILLA_ID
                  and not p.name.startswith((".", "__")))


def registro_ceo() -> dict[str, dict]:
    """Índice común de CEO_Sergete/proyectos.json → {id: entrada}. Best-effort."""
    try:
        data = json.loads(config.CEO_PROYECTOS_JSON.read_text(encoding="utf-8"))
        return {p["id"]: p for p in data.get("proyectos") or [] if isinstance(p, dict) and p.get("id")}
    except Exception:
        return {}


def _normalizar_recursos(raw: dict, origen: str) -> dict:
    """{broll, internet, …} con `broll` en BROLL_POLITICAS e `internet` booleano.

    Tolera `broll` como texto o como objeto ({"politica"|"modo"|"tipo": …}) e
    `internet` como booleano u objeto (solo es True si TODO lo que declara es True).
    Si falta `internet`, se toma False (lo más restrictivo)."""
    out = dict(raw or {})
    broll = out.get("broll")
    if isinstance(broll, dict):
        broll = broll.get("politica") or broll.get("modo") or broll.get("tipo")
    broll = str(broll or "").strip().lower()
    if broll not in config.BROLL_POLITICAS:
        raise ProyectoError(f"política de b-roll «{broll or '(vacía)'}» no válida en {origen} "
                            f"(opciones: {' | '.join(config.BROLL_POLITICAS)}).")
    internet = out.get("internet")
    if isinstance(internet, dict):
        valores = [v for k, v in internet.items() if not str(k).startswith("_")]
        internet = bool(valores) and all(bool(v) for v in valores)
    out["broll"] = broll
    out["internet"] = bool(internet) if internet is not None else False
    return out


@dataclass
class Proyecto:
    id: str
    dir: Path
    cfg: dict
    recursos: dict
    origen_recursos: str
    ceo: dict = field(default_factory=dict)
    editor: dict = field(default_factory=dict)   # TheEditor/proyectos/<id>/proyecto.json

    # --- datos generales
    @property
    def nombre(self) -> str:
        return self.cfg.get("nombre") or self.ceo.get("nombre") or self.id

    @property
    def tipo(self) -> str:
        return self.ceo.get("tipo") or self.editor.get("tipo") or self.cfg.get("tipo") or "?"

    def seccion(self, nombre: str) -> dict:
        v = self.cfg.get(nombre)
        return v if isinstance(v, dict) else {}

    # --- carpetas del proyecto
    @property
    def salidas_dir(self) -> Path:
        return config.OUT_DIR / self.id

    @property
    def estilo_path(self) -> Path:
        return self.dir / (self.seccion("carruseles").get("estilo") or "estilo.json")

    @property
    def planes_dir(self) -> Path:
        return self.dir / "planes"

    @property
    def especiales_dir(self) -> Path:
        return self.dir / "especiales"

    # --- publicación (CEO_Sergete) y fuentes del proyecto
    @property
    def historias_pte(self) -> Path:
        return Path(str(config.HISTORIAS_PTE).format(id=self.id))

    @property
    def reels_pte(self) -> Path:
        return Path(str(config.REELS_PTE).format(id=self.id))

    @property
    def reels_publicados(self) -> Path:
        return Path(str(config.REELS_PUBLICADOS).format(id=self.id))

    @property
    def historico_dir(self) -> Path:
        return config.HISTORICO_DIR / self.id

    @property
    def transcripciones_dir(self) -> Path:
        return config.EDITOR_PROYECTOS_DIR / self.id / "transcripciones"

    @property
    def textos_dir(self) -> Path:
        return config.TEXTOS_DIR / self.id

    @property
    def credito_defecto(self) -> str:
        """`fuente.credito` por defecto de los carruseles de vídeo (proyecto.json)."""
        return str(self.seccion("carruseles").get("credito") or "").strip()

    # --- frases y recursos
    @property
    def etiqueta_frases(self) -> str:
        return config.ETIQUETA_PROYECTO.format(id=self.id)

    @property
    def broll(self) -> str:
        return self.recursos["broll"]

    @property
    def internet(self) -> bool:
        return self.recursos["internet"]

    @property
    def broll_propio_dir(self) -> Path:
        return config.EDITOR_PROYECTOS_DIR / self.id / "recursos" / "broll"

    # --- identidad (CEO_Sergete/proyectos.json → identidad; fuente única)
    @property
    def identidad(self) -> dict:
        v = self.ceo.get("identidad")
        return v if isinstance(v, dict) else {}

    @property
    def marca(self) -> dict:
        """Colores {fondo, texto, acento, texto_suave, detalle} de `identidad.marca`
        (neutros si faltan). Los matices se derivan si la identidad no los trae."""
        m = self.identidad.get("marca")
        m = m if isinstance(m, dict) else {}
        out = {k: _hex(m.get(k)) or config.MARCA_NEUTRA[k] for k in ("fondo", "texto", "acento")}
        out["texto_suave"] = _hex(m.get("texto_suave")) or _mezcla(
            out["texto"], out["fondo"], config.MEZCLA_TEXTO_SUAVE)
        out["detalle"] = _hex(m.get("detalle")) or _mezcla(
            out["texto"], out["fondo"], config.MEZCLA_DETALLE)
        return out

    @property
    def handle(self) -> str:
        h = str(self.identidad.get("cuenta_ig") or "").strip()
        return ("@" + h.lstrip("@")) if h else ""

    @property
    def emojis_max(self) -> int:
        voz = self.identidad.get("voz") if isinstance(self.identidad.get("voz"), dict) else {}
        try:
            return max(0, int(voz.get("emojis_max", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def avisos(self) -> list[str]:
        """Avisos de configuración (identidad incompleta)."""
        out = []
        if not self.identidad:
            out.append(f"«{self.id}» no tiene `identidad` en CEO_Sergete/proyectos.json: "
                       f"uso valores neutros (colores grises, sin handle, 0 emojis).")
        else:
            if not isinstance(self.identidad.get("marca"), dict):
                out.append("la identidad no trae `marca`: uso colores neutros.")
            if not self.handle:
                out.append("la identidad no trae `cuenta_ig`: no se pinta el handle.")
        return out

    @property
    def color_liso(self) -> str:
        """Fondo liso: `fondo_liso` del proyecto.json o `identidad.marca.fondo`."""
        return _hex(self.cfg.get("fondo_liso")) or self.marca["fondo"]

    # --- estilo (maquetación del proyecto + identidad)
    def estilo_crudo(self, path: Path | None = None) -> dict:
        """estilo.json tal cual ({} si no existe)."""
        path = Path(path) if path else self.estilo_path
        return _leer_json(path) if path.exists() else {}

    def estilo(self, path: Path | None = None) -> dict:
        """Maquetación de estilo.json + `colores`, `handle` y `emojis_max` de la
        identidad (si el estilo aún los trae, manda la identidad)."""
        path = Path(path) if path else self.estilo_path
        if not path.exists():
            raise FileNotFoundError(2, "no existe", str(path))
        e = _leer_json(path)
        e["colores"] = self.marca
        e["handle"] = self.handle
        e["emojis_max"] = self.emojis_max
        return e

    def estilo_historia(self) -> dict:
        """Fuente y colores de las historias (normales y especiales)."""
        try:
            fuentes = self.estilo_crudo().get("fuentes") or {}
        except ProyectoError:
            fuentes = {}
        fuente = config.FONTS_DIR / (fuentes.get("titulo") or config.FUENTE_HISTORIA)
        if not fuente.exists():
            fuente = config.FONTS_DIR / config.FUENTE_HISTORIA
        m = self.marca
        return {"fuente": fuente, "fondo": self.color_liso, "velo": m["fondo"],
                "texto": m["texto"]}

    def estilo_por_rellenar(self) -> bool:
        try:
            return bool(self.estilo_crudo().get("_rellenar"))
        except ProyectoError:
            return False

    def raices_propias(self) -> list[Path]:
        """Carpetas con material del proyecto (portadas de carrusel, fondos)."""
        raices = [
            self.dir,
            config.HISTORICO_DIR / self.id,
            config.EDITOR_PROYECTOS_DIR / self.id,
            config.DESCARGA_ROOT / "descargas" / self.id,
            config.CEO_ROOT / "REELS" / self.id,
            config.CEO_ROOT / "HISTORIAS" / self.id,
        ]
        if self.broll == "banco_comun":
            raices.append(config.FONDOS_DIR)
        # Extras opt-in del proyecto (relativos a PruebasIA), p. ej. carpetas de
        # trabajo de TheEditor que aún no van por proyecto.
        for extra in self.seccion("carruseles").get("material_extra") or []:
            raices.append(config.PRUEBAS_IA / extra)
        return raices

    def raices_ajenas(self) -> list[Path]:
        """Carpetas de OTROS proyectos conocidos (para no mezclar)."""
        otros = (set(ids_disponibles()) | set(registro_ceo())) - {self.id}
        out = []
        for o in sorted(otros):
            out += [config.PROYECTOS_DIR / o, config.HISTORICO_DIR / o,
                    config.EDITOR_PROYECTOS_DIR / o, config.DESCARGA_ROOT / "descargas" / o,
                    config.TEXTOS_DIR / o, config.OUT_DIR / o]
        return out

    def resumen(self) -> str:
        return (f"proyecto «{self.id}» ({self.tipo}) · b-roll {self.broll} · "
                f"internet {'sí' if self.internet else 'no'} · política: {self.origen_recursos}")


def _hex(c) -> str:
    """'#rrggbb' válido o ''."""
    c = str(c or "").strip()
    if len(c) == 7 and c.startswith("#"):
        try:
            int(c[1:], 16)
            return c.lower()
        except ValueError:
            pass
    return ""


def _mezcla(c1: str, c2: str, t: float) -> str:
    """Color de `c1` desplazado una fracción `t` hacia `c2`."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _dentro(path: Path, raiz: Path) -> bool:
    try:
        path.resolve().relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


def es_propio(path: Path, proyecto: Proyecto) -> bool:
    return any(_dentro(path, r) for r in proyecto.raices_propias())


def es_ajeno(path: Path, proyecto: Proyecto) -> bool:
    return any(_dentro(path, r) for r in proyecto.raices_ajenas())


def proyecto_de_ruta(path: Path) -> str | None:
    """id del proyecto si `path` está dentro de proyectos/<id>/ de TheHistoria."""
    try:
        rel = path.resolve().relative_to(config.PROYECTOS_DIR.resolve())
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def leer_editor(pid: str) -> dict:
    """TheEditor/proyectos/<id>/proyecto.json ({} si aún no existe)."""
    f = config.EDITOR_PROYECTOS_DIR / pid / "proyecto.json"
    return _leer_json(f) if f.exists() else {}


def cargar_recursos(pid: str, cfg: dict, editor: dict | None = None) -> tuple[dict, str]:
    """Política de recursos: TheEditor manda; si aún no la tiene, respaldo."""
    editor = leer_editor(pid) if editor is None else editor
    if isinstance(editor.get("recursos"), dict):
        origen = "TheEditor/proyectos/%s/proyecto.json" % pid
        return _normalizar_recursos(editor["recursos"], origen), origen
    if isinstance(cfg.get("recursos_respaldo"), dict):
        origen = "respaldo de TheHistoria (TheEditor aún no la define)"
        return _normalizar_recursos(cfg["recursos_respaldo"], origen), origen
    origen = "la más restrictiva por defecto (nadie la define)"
    return _normalizar_recursos(config.RECURSOS_RESPALDO, origen), origen


def cargar(pid: str) -> Proyecto:
    d = config.PROYECTOS_DIR / pid
    f = d / "proyecto.json"
    if not f.exists():
        raise ProyectoError(f"el proyecto «{pid}» no tiene {f.relative_to(config.PROJECT_ROOT)} "
                            f"(cópialo de proyectos/{config.PLANTILLA_ID}/).")
    cfg = _leer_json(f)
    if cfg.get("id") and cfg["id"] != pid:
        raise ProyectoError(f"proyectos/{pid}/proyecto.json dice id «{cfg['id']}»: debe ser «{pid}» "
                            f"(¿falta sustituir <id> de la plantilla?).")
    editor = leer_editor(pid)
    recursos, origen = cargar_recursos(pid, cfg, editor)
    return Proyecto(pid, d, cfg, recursos, origen, registro_ceo().get(pid, {}), editor)


def resolver(pid: str | None) -> Proyecto:
    """Regla común: `--proyecto` explícito, o el único que haya; si hay varios, error."""
    ids = ids_disponibles()
    if pid:
        pid = pid.strip()
        if pid == config.PLANTILLA_ID or pid not in ids:
            raise ProyectoError(f"no existe el proyecto «{pid}» en TheHistoria/proyectos/. "
                                f"Disponibles: {', '.join(ids) or '(ninguno)'}.")
        return cargar(pid)
    if not ids:
        raise ProyectoError(f"no hay ningún proyecto en TheHistoria/proyectos/ "
                            f"(crea uno desde {config.PLANTILLA_ID}/).")
    if len(ids) > 1:
        raise ProyectoError(f"hay {len(ids)} proyectos ({', '.join(ids)}): indica cuál con "
                            f"--proyecto <id>.")
    return cargar(ids[0])

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proyectos de TheEditor (cuentas o clientes de contenido).

Cada proyecto vive en `proyectos/<id>/` (fuente de verdad):

    proyecto.json     tipo, idioma, recursos (política), encuadre, silencios,
                      gancho y frases
    reglas.md         reglas de edición propias del proyecto
    input/            buzón (vídeos largos, o clips ya cortados por subcarpetas)
    transcripciones/  trabajo y salidas (<video>/{clips,finales,cortes.json…})
    logs/             logs de cada ejecución
    recursos/broll/   recursos/musica/   recursos/sfx/   (si tiene recursos propios)

`proyectos/_plantilla/` es la base de los nuevos (pensada para clipping).

Elección del proyecto (`--proyecto <id>` en todos los scripts): si se omite y
solo hay un proyecto (sin contar `_plantilla`), se usa ese; si hay varios, error
con la lista. Nunca se mezcla material de proyectos distintos.

Política de recursos (`proyecto.json → recursos`), la hace cumplir el código:
    broll          banco_comun | propio | ninguno
    musica         banco_comun | propia | ninguna
    internet       true | false   (false: nada de Pexels, imágenes libres ni
                                   catálogo común; guarda en pipeline_core)
    gancho_visual  pexels | ninguno   (pexels exige internet: true)
    gancho_texto   true | false
    guardar_frases true | false   (viral_phrases con la etiqueta proyecto:<id>)

Salida de los scripts: con `--quiet` (por defecto cuando la salida NO es una
terminal, p. ej. un agente) la consola solo recibe una línea por vídeo/clip y el
RESUMEN (`decir()`); el detalle completo va al log de proyectos/<id>/logs/.
`--verbose` lo enseña todo.

CLI:
    python proyecto.py                       -> lista los proyectos y su política
    python proyecto.py ver <id>              -> política resuelta + recursos + reglas.md
    python proyecto.py nuevo <id> --nombre "Nombre" [--tipo clipping|largos]
    python proyecto.py aprobar <id> --video "<video|carpeta>" [--clips a.mp4,b.mp4]
                               [--cerrar] [--destino-pruebas <dir>]
        -> mueve los finales aprobados a CEO_Sergete/REELS/<id>/1. pte Publicar/
           y, si finales/ queda vacío (o con --cerrar), archiva transcripciones/<v>/
           en PruebasIA/_Historico/<id>/<v>/ (sin _prep/) y la fuente de input/ en
           …/<v>/_fuente/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PROYECTOS_DIR = RAIZ / "proyectos"
PLANTILLA = "_plantilla"
BANCO_BROLL = RAIZ / "superposiciones"     # banco común de b-roll
BANCO_MUSICA = RAIZ / "musicas"            # banco común de música
SKILL_DIR = RAIZ / ".claude" / "skills" / "Editor_Sergio"
PRUEBAS_IA = RAIZ.parent
HISTORICO = PRUEBAS_IA / "_Historico"                # aprobados: <id>/<video>/
REELS = PRUEBAS_IA / "CEO_Sergete" / "REELS"  # <id>/1. pte Publicar/
PTE_PUBLICAR = "1. pte Publicar"
EXT_VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4a", ".mp3", ".wav")
EXT_CLIPS = (".mp4", ".mov", ".m4v", ".mkv")   # clips ya cortados (vía 2)
EXT_MUSICA = (".mp3", ".wav", ".m4a")
EXT_BROLL = (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")
SUELTOS = "_sueltos"                           # lote de los clips sueltos en input/

# Modos de encuadre del batch (vía 2); alias -> modo.
MODOS_ENCUADRE = ("right", "left", "center", "auto", "auto-right", "follow")
_ALIAS_MODO = {"izq": "left", "centro": "center", "auto-derecha": "auto-right"}

TIPOS = ("largos", "clipping")
BROLL = ("banco_comun", "propio", "ninguno")
MUSICA = ("banco_comun", "propia", "ninguna")
GANCHO_VISUAL = ("pexels", "ninguno")

# Si a un proyecto le falta alguna clave de `recursos`, se toma lo más
# restrictivo (nada de fuera) y se avisa.
RECURSOS_RESTRICTIVOS = {
    "broll": "propio", "musica": "propia", "internet": False,
    "gancho_visual": "ninguno", "gancho_texto": True, "guardar_frases": False,
}
SILENCIOS_DEFECTO = {"umbral": "6%", "margen": "0.15s"}
MODO_ENCUADRE_DEFECTO = "right"           # el de siempre del batch


class ProyectoError(SystemExit):
    """Error de proyecto: en un script sale con el mensaje; capturable."""


def normalizar_modo(modo, origen: str = "MODO") -> str:
    """Modo de encuadre válido (right|left|center|auto|auto-right|follow o una
    fracción 0–1, p. ej. 0.81). Un modo desconocido es un error, nunca `follow`
    en silencio."""
    m = str(modo or "").strip().lower()
    m = _ALIAS_MODO.get(m, m)
    if m in MODOS_ENCUADRE:
        return m
    try:
        f = float(m)
        if 0.0 <= f <= 1.0:
            return m
    except ValueError:
        pass
    raise ProyectoError(f"[!] {origen} «{modo}» no es válido: "
                        f"{' | '.join(MODOS_ENCUADRE)} | <fracción 0–1>.")


def _ids_en_disco() -> list[str]:
    if not PROYECTOS_DIR.is_dir():
        return []
    return sorted(d.name for d in PROYECTOS_DIR.iterdir()
                  if d.is_dir() and d.name != PLANTILLA and (d / "proyecto.json").exists())


def listar() -> list[str]:
    """Ids de los proyectos (subcarpetas con proyecto.json, sin _plantilla)."""
    return _ids_en_disco()


@dataclass
class Proyecto:
    id: str
    dir: Path
    cfg: dict
    recursos: dict

    # ------------------------------------------------------------ datos
    @property
    def nombre(self) -> str:
        return self.cfg.get("nombre") or self.id

    @property
    def tipo(self) -> str:
        return self.cfg.get("tipo") or "largos"

    @property
    def idioma(self) -> str:
        return self.cfg.get("idioma") or "es"

    @property
    def input_dir(self) -> Path:
        return self.dir / "input"

    @property
    def transcripciones_dir(self) -> Path:
        return self.dir / "transcripciones"

    @property
    def logs_dir(self) -> Path:
        return self.dir / "logs"

    @property
    def recursos_dir(self) -> Path:
        return self.dir / "recursos"

    @property
    def historico_dir(self) -> Path:
        return HISTORICO / self.id

    def archivado(self, nombre: str) -> Path | None:
        """Carpeta de _Historico/<id>/<nombre>/ si ese vídeo o lote ya se aprobó."""
        nombre = (nombre or "").strip()
        if not nombre:
            return None
        d = self.historico_dir / nombre
        return d if d.is_dir() else None

    # ------------------------------------------------------------ política
    @property
    def internet(self) -> bool:
        return bool(self.recursos["internet"])

    @property
    def gancho_texto(self) -> bool:
        return bool(self.recursos["gancho_texto"])

    @property
    def guardar_frases(self) -> bool:
        return bool(self.recursos["guardar_frases"])

    @property
    def usa_gancho_visual(self) -> bool:
        """Mini-vídeo de Pexels al inicio (vía 1 y vía 3)."""
        return self.recursos["gancho_visual"] == "pexels" and self.internet

    @property
    def overlays_dir(self) -> Path | None:
        b = self.recursos["broll"]
        if b == "banco_comun":
            return BANCO_BROLL
        if b == "propio":
            return self.recursos_dir / "broll"
        return None

    @property
    def music_dir(self) -> Path | None:
        m = self.recursos["musica"]
        if m == "banco_comun":
            return BANCO_MUSICA
        if m == "propia":
            return self.recursos_dir / "musica"
        return None

    @property
    def broll_indice(self) -> Path | None:
        if self.recursos["broll"] != "propio":
            return None
        p = self.recursos_dir / "broll" / "_indice.json"
        return p if p.exists() else None

    def politica_render(self, sin_broll: bool = False, sin_musica: bool = False) -> dict | None:
        """Política para `pipeline_core.burn_subs_and_music(recursos=…)`.

        None si es la de siempre (banco común + internet): así MongeMalo pasa
        exactamente por el mismo camino que antes de haber proyectos.
        `sin_broll` / `sin_musica` (--sin-broll / --sin-musica): solo esta ejecución.
        """
        r = dict(self.recursos)
        if sin_broll:
            r["broll"] = "ninguno"
        if sin_musica:
            r["musica"] = "ninguna"
        if r["broll"] == "banco_comun" and r["musica"] == "banco_comun" and r["internet"]:
            return None
        return {
            "broll": r["broll"],
            "musica": r["musica"],
            "internet": bool(r["internet"]),
            "broll_indice": self.broll_indice,
            # click de entrada del b-roll: el de siempre con música del banco
            # común; si no, solo el del proyecto (recursos/sfx/).
            "sfx_dirs": None if r["musica"] == "banco_comun" else [self.recursos_dir / "sfx"],
        }

    # ------------------------------------------------------------ recursos en disco
    def contar_recursos(self) -> dict:
        """{'broll': n, 'musica': n} de lo que permite la política (None = no aplica)."""
        out = {"broll": None, "musica": None}
        d = self.overlays_dir
        if d is not None:
            if not d.is_dir():
                out["broll"] = 0
            elif self.recursos["broll"] == "propio":   # con subcarpetas; lo que empieza por _ fuera
                out["broll"] = sum(1 for f in d.rglob("*") if f.is_file()
                                   and f.suffix.lower() in EXT_BROLL
                                   and not any(x.startswith(("_", ".")) for x in f.relative_to(d).parts))
            else:
                out["broll"] = sum(1 for f in d.iterdir()
                                   if f.is_file() and f.suffix.lower() in EXT_BROLL)
        m = self.music_dir
        if m is not None:
            out["musica"] = sum(1 for f in m.rglob("*") if f.is_file()
                                and f.suffix.lower() in EXT_MUSICA) if m.is_dir() else 0
        return out

    def comprobar_recursos(self, sin_broll: bool = False, sin_musica: bool = False) -> str:
        """Cuenta los recursos según la política y PARA si falta b-roll o música
        (salvo --sin-broll / --sin-musica). Devuelve la línea de resumen."""
        n = self.contar_recursos()
        faltan = []
        if n["broll"] == 0 and not sin_broll:
            faltan.append(f"b-roll ({self.overlays_dir})")
        if n["musica"] == 0 and not sin_musica:
            faltan.append(f"música ({self.music_dir})")
        if faltan:
            flags = " ".join(f for f, k in (("--sin-broll", "b-roll"), ("--sin-musica", "música"))
                             if any(x.startswith(k) for x in faltan))
            raise ProyectoError(f"[!] «{self.id}»: no hay {' ni '.join(faltan)}. Añade los "
                                f"recursos o relanza con {flags}.")
        b = ("no" if sin_broll or n["broll"] is None else
             f"{n['broll']} ({self.recursos['broll']}"
             + (", índice" if self.broll_indice else "") + ")")
        m = ("no" if sin_musica or n["musica"] is None else
             f"{n['musica']} ({self.recursos['musica']})")
        return f"Recursos: b-roll {b} · música {m}"

    # ------------------------------------------------------------ frases
    @property
    def etiqueta(self) -> str:
        return f"proyecto:{self.id}"

    def etiquetas_frases(self, tags=()) -> list[str]:
        """tags de la frase + etiquetas extra del proyecto + proyecto:<id>."""
        out = [str(t) for t in (tags or [])]
        extra = (self.cfg.get("frases") or {}).get("etiquetas_extra") or []
        for t in list(extra) + [self.etiqueta]:
            if t and t not in out:
                out.append(str(t))
        return out

    # ------------------------------------------------------------ encuadre y silencios
    def modo_de_carpeta(self, carpeta: str | None) -> str | None:
        """Modo EXPLÍCITO de una carpeta (`encuadre.carpetas`) o None."""
        mapa = (self.cfg.get("encuadre") or {}).get("carpetas") or {}
        if carpeta:
            for k, v in mapa.items():
                if k.strip().lower() == carpeta.strip().lower() and str(v).strip():
                    return normalizar_modo(v, f"proyecto.json → encuadre.carpetas «{k}»")
        return None

    def modo_encuadre(self, carpeta: str | None = None) -> str:
        """Modo del batch para una carpeta: mapa del proyecto o su modo por defecto."""
        enc = self.cfg.get("encuadre") or {}
        return self.modo_de_carpeta(carpeta) or normalizar_modo(
            enc.get("modo_por_defecto") or MODO_ENCUADRE_DEFECTO,
            "proyecto.json → encuadre.modo_por_defecto")

    @property
    def silencios(self) -> dict:
        s = dict(SILENCIOS_DEFECTO)
        s.update({k: str(v) for k, v in (self.cfg.get("silencios") or {}).items()
                  if k in SILENCIOS_DEFECTO and v not in (None, "")})
        return s

    @property
    def gancho_duracion(self) -> float | None:
        v = (self.cfg.get("gancho") or {}).get("texto_duracion_s")
        try:
            return float(v) if v else None
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------ red y logs
    def aplicar_red(self) -> None:
        """Sin internet: bloquea la red de recursos del proceso (guarda de
        pipeline_core) y obliga a cargar los modelos (Whisper, fastembed) solo
        de la caché local, sin consultar Hugging Face."""
        if self.internet:
            return
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        if "huggingface_hub" in sys.modules:   # ya importado: forzar también
            try:
                sys.modules["huggingface_hub"].constants.HF_HUB_OFFLINE = True
            except Exception:
                pass
        pc = _pipeline_core()
        if pc is not None:
            pc.bloquear_red_recursos(f"el proyecto «{self.id}» tiene internet=false")

    def iniciar_log(self, nombre: str, quiet: bool = False) -> Path:
        """Duplica stdout/stderr en proyectos/<id>/logs/<nombre>_<fecha>.log.
        Con `quiet`, stdout solo va al log (la consola recibe lo de `decir()`)."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        path = self.logs_dir / f"{nombre}_{dt.datetime.now():%Y%m%d-%H%M%S}.log"
        fh = open(path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _Tee(sys.stdout, fh, mudo=quiet)
        sys.stderr = _Tee(sys.stderr, fh)
        return path

    def resumen(self) -> str:
        r = self.recursos
        return (f"Proyecto: {self.id} ({self.tipo}) · b-roll {r['broll']} · música {r['musica']} · "
                f"internet {'sí' if r['internet'] else 'NO'} · gancho visual {r['gancho_visual']} · "
                f"gancho texto {'sí' if r['gancho_texto'] else 'no'} · "
                f"frases {'sí' if r['guardar_frases'] else 'no'}")


class _Tee:
    """stdout/stderr -> consola + log. `mudo`: solo al log (salida --quiet)."""

    def __init__(self, stream, fh, mudo: bool = False):
        self._s, self._fh, self.mudo = stream, fh, mudo

    def write(self, s):
        if self._fh is not None:
            try:
                self._fh.write(s)
            except Exception:
                pass
        return len(s) if self.mudo else self._s.write(s)

    def consola(self, s):
        """Siempre a la consola (y al log), también en modo --quiet."""
        if self._fh is not None:
            try:
                self._fh.write(s)
            except Exception:
                pass
        self._s.write(s)
        self._s.flush()

    def flush(self):
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:
                pass
        self._s.flush()

    def isatty(self):
        return False if self.mudo else self._s.isatty()

    def __getattr__(self, k):
        return getattr(self._s, k)


def decir(msg: str = "") -> None:
    """Línea para quien lanza el script (el LLM): sale SIEMPRE en consola, también
    con --quiet, y queda en el log. Úsala para la línea por clip y el RESUMEN."""
    out = sys.stdout
    if isinstance(out, _Tee):
        out.consola(f"{msg}\n")
    else:
        print(msg, flush=True)


def es_quiet() -> bool:
    return isinstance(sys.stdout, _Tee) and sys.stdout.mudo


def add_salida(ap: argparse.ArgumentParser) -> None:
    """--quiet / --verbose. Por defecto, --quiet si la salida no es una terminal."""
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quiet", dest="quiet", action="store_true", default=None,
                   help="Una línea por clip + RESUMEN (detalle en el log). Por defecto si la "
                        "salida no es una terminal.")
    g.add_argument("--verbose", dest="quiet", action="store_false",
                   help="Todo el detalle también en la consola.")


def _silenciar_ruido() -> None:
    """Fuera barras de progreso y avisos de librerías (no aportan nada al LLM)."""
    os.environ.setdefault("TQDM_DISABLE", "1")
    import warnings
    warnings.filterwarnings("ignore", message=".*mean pooling.*")
    warnings.filterwarnings("ignore", message=".*progress bars.*")


def _pipeline_core():
    """pipeline_core (el mismo módulo que usan los scripts) o None."""
    if "pipeline_core" in sys.modules:
        return sys.modules["pipeline_core"]
    if str(SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(SKILL_DIR))
    try:
        import pipeline_core  # noqa: F401
        return sys.modules["pipeline_core"]
    except Exception:
        return None


def _normalizar_recursos(pid: str, raw: dict) -> dict:
    raw = {k: v for k, v in (raw or {}).items() if not str(k).startswith("_")}
    faltan = [k for k in RECURSOS_RESTRICTIVOS if k not in raw]
    if faltan:
        print(f"[proyecto] AVISO: a «{pid}» le falta en recursos {', '.join(faltan)}: "
              f"se usa lo más restrictivo.")
    r = dict(RECURSOS_RESTRICTIVOS)
    r.update({k: raw[k] for k in RECURSOS_RESTRICTIVOS if k in raw})
    r["broll"] = str(r["broll"]).strip().lower()
    r["musica"] = str(r["musica"]).strip().lower()
    r["gancho_visual"] = str(r["gancho_visual"]).strip().lower()
    for k in ("internet", "gancho_texto", "guardar_frases"):
        if not isinstance(r[k], bool):
            raise ProyectoError(f"[!] proyectos/{pid}/proyecto.json: recursos.{k} debe ser true o false.")
    for k, ok in (("broll", BROLL), ("musica", MUSICA), ("gancho_visual", GANCHO_VISUAL)):
        if r[k] not in ok:
            raise ProyectoError(f"[!] proyectos/{pid}/proyecto.json: recursos.{k} = «{r[k]}» "
                                f"no es válido (opciones: {' | '.join(ok)}).")
    if r["gancho_visual"] == "pexels" and not r["internet"]:
        raise ProyectoError(f"[!] proyectos/{pid}/proyecto.json: gancho_visual «pexels» "
                            f"exige internet: true.")
    return r


def cargar(pid: str) -> Proyecto:
    d = PROYECTOS_DIR / pid
    f = d / "proyecto.json"
    if not f.exists():
        raise ProyectoError(f"[!] No existe el proyecto «{pid}» ({f}).")
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        raise ProyectoError(f"[!] {f} no es un JSON válido: {e}")
    if cfg.get("id") and cfg["id"] != pid:
        print(f"[proyecto] AVISO: {f} dice id «{cfg['id']}»; manda la carpeta («{pid}»).")
    if cfg.get("tipo") and cfg["tipo"] not in TIPOS:
        raise ProyectoError(f"[!] {f}: tipo «{cfg['tipo']}» no válido ({' | '.join(TIPOS)}).")
    return Proyecto(pid, d, cfg, _normalizar_recursos(pid, cfg.get("recursos")))


def resolver(pid: str | None = None) -> Proyecto:
    """Regla común: --proyecto explícito; si falta y solo hay uno, ese; si hay
    varios, error con la lista."""
    ids = listar()
    if pid:
        pid = pid.strip()
        if pid == PLANTILLA:
            raise ProyectoError("[!] _plantilla no es un proyecto: cópiala con «proyecto.py nuevo <id>».")
        if pid not in ids:
            raise ProyectoError(f"[!] No existe el proyecto «{pid}». Proyectos: "
                                f"{', '.join(ids) or '(ninguno)'}.")
        return cargar(pid)
    if not ids:
        raise ProyectoError(f"[!] No hay proyectos en {PROYECTOS_DIR}. Crea uno con "
                            f"«proyecto.py nuevo <id> --nombre ...».")
    if len(ids) > 1:
        raise ProyectoError(f"[!] Hay varios proyectos ({', '.join(ids)}): indica "
                            f"--proyecto <id>.")
    return cargar(ids[0])


def add_argumento(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--proyecto", default=None,
                    help="Id del proyecto (proyectos/<id>/). Obligatorio si hay varios.")


def abrir(pid: str | None, script: str, log: bool = True, quiet: bool | None = None) -> Proyecto:
    """Resuelve el proyecto, aplica su política de red y abre el log del script.

    `quiet` None = automático: --quiet si stdout no es una terminal (solo en los
    scripts con log; los cortos sin log lo enseñan todo)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if quiet is None:
        try:
            quiet = log and not sys.stdout.isatty()
        except Exception:
            quiet = bool(log)
    _silenciar_ruido()
    p = resolver(pid)
    p.aplicar_red()
    if log:
        ruta = p.iniciar_log(script, quiet=quiet)
        decir(f"{p.resumen()} · log {ruta}")
    else:
        if quiet:
            sys.stdout = _Tee(sys.stdout, None, mudo=True)
        decir(p.resumen())
    return p


# ---------------------------------------------------------------- ayudas de los scripts
def sin_extension(nombre: str) -> str:
    """«clip 3.mp4» / «IMG_1.MOV» -> «clip 3» / «IMG_1» (solo extensiones de vídeo)."""
    x = str(nombre or "").strip()
    for ext in EXT_CLIPS:
        if x.lower().endswith(ext):
            return x[: -len(ext)].strip()
    return x


def filtrar_solo(nombres: list[str], solo: list[str] | None, que: str = "clip") -> set[str] | None:
    """Nombres pedidos con --solo (sin .mp4) que existen; error si alguno no.
    None si no hay --solo (= todos)."""
    if not solo:
        return None
    pedidos = []
    for s in solo:
        for x in str(s).split(","):
            x = sin_extension(x)
            if x:
                pedidos.append(x)
    faltan = [x for x in pedidos if x not in nombres]
    if faltan:
        raise ProyectoError(f"[!] --solo: no hay ningún {que} «{', '.join(faltan)}». "
                         f"Disponibles: {', '.join(nombres) or '(ninguno)'}")
    return set(pedidos)


def silencios_cli(sil: dict, umbral: str | None, margen: str | None) -> dict:
    """Silencios de esta ejecución: los del proyecto, con --umbral/--margen
    encima. Nunca se escriben en proyecto.json."""
    out = dict(sil)
    if umbral:
        out["umbral"] = umbral if str(umbral).endswith("%") else f"{umbral}%"
    if margen:
        out["margen"] = margen if str(margen).endswith("s") else f"{margen}s"
    return out


# ---------------------------------------------------------------- CLI
def _sustituir(carpeta: Path, pid: str, nombre: str) -> None:
    for f in carpeta.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".json", ".md", ".txt"):
            t = f.read_text(encoding="utf-8")
            n = t.replace("<id>", pid).replace("<Nombre>", nombre)
            if n != t:
                f.write_text(n, encoding="utf-8")


def _cmd_nuevo(a) -> int:
    pid = a.id
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", pid):
        raise ProyectoError("[!] El id va en minúsculas, sin espacios ni tildes (p. ej. «clientex»).")
    destino = PROYECTOS_DIR / pid
    if destino.exists():
        raise ProyectoError(f"[!] Ya existe {destino}.")
    shutil.copytree(PROYECTOS_DIR / PLANTILLA, destino)
    _sustituir(destino, pid, a.nombre)
    if a.tipo:
        f = destino / "proyecto.json"
        cfg = json.loads(f.read_text(encoding="utf-8"))
        cfg["tipo"] = a.tipo
        f.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {destino}\n  Rellena proyecto.json (recursos, encuadre) y reglas.md; "
          f"deja el b-roll en recursos/broll/ y la música en recursos/musica/.")
    return 0


def _nombre_unico(destino: Path, nombre: str) -> Path:
    """destino/nombre, o destino/<stem>_2.mp4, _3… si ya existe."""
    dst = destino / nombre
    k = 2
    while dst.exists():
        dst = destino / f"{Path(nombre).stem}_{k}{Path(nombre).suffix}"
        k += 1
    return dst


def _fuente_en_input(p: Proyecto, v: str) -> Path | None:
    """El vídeo largo input/<v>.<ext> o la carpeta de extractos input/<v>/."""
    d = p.input_dir / v
    if d.is_dir():
        return d
    for ext in EXT_VIDEO:
        f = p.input_dir / f"{v}{ext}"
        if f.is_file():
            return f
    return None


def _cmd_aprobar(a) -> int:
    """Mueve los finales aprobados a REELS y, al cerrar, archiva el vídeo."""
    p = cargar(a.id)
    v = (a.video or "").strip().rstrip("/\\")
    if v.lower().endswith(".mp4"):
        v = v[:-4]
    base = p.transcripciones_dir / v
    fin = base / "finales"
    if not base.is_dir():
        arch = p.archivado(v)
        raise ProyectoError(f"[!] No existe {base}" + (f" (ya está archivado en {arch})." if arch else "."))
    disponibles = sorted(f.name for f in fin.glob("*.mp4")) if fin.is_dir() else []

    if a.clips:
        pedidos = []
        for x in a.clips.split(","):
            x = x.strip()
            if x:
                pedidos.append(x if x.lower().endswith(".mp4") else f"{x}.mp4")
        faltan = [x for x in pedidos if x not in disponibles]
        if faltan:
            raise ProyectoError(f"[!] No están en {fin}: {', '.join(faltan)}. "
                                f"Finales: {', '.join(disponibles) or '(ninguno)'}.")
    else:
        pedidos = list(disponibles)
    if not pedidos and not a.cerrar:
        raise ProyectoError(f"[!] No hay finales que aprobar en {fin} (usa --cerrar para archivar).")

    pruebas = Path(a.destino_pruebas).resolve() if a.destino_pruebas else None
    reels = (pruebas / "REELS") if pruebas else REELS
    historico = (pruebas / "_Historico") if pruebas else HISTORICO
    destino = reels / p.id / PTE_PUBLICAR
    hist = historico / p.id / v
    restantes = [x for x in disponibles if x not in pedidos]
    cerrar = bool(a.cerrar or not restantes)
    if v == SUELTOS and hist.exists():          # cada tanda de sueltos, su archivo
        hist = historico / p.id / f"{SUELTOS}_{dt.datetime.now():%Y%m%d-%H%M}"
    if cerrar and hist.exists():
        raise ProyectoError(f"[!] Ya existe {hist}: no archivo encima. Revísalo antes "
                            f"(no se ha movido nada).")
    if pruebas:
        print(f"[aprobar] MODO PRUEBA: destino {pruebas} (ni REELS ni _Historico reales).")

    destino.mkdir(parents=True, exist_ok=True)
    for name in pedidos:
        dst = _nombre_unico(destino, name)
        if dst.name != name:
            print(f"[aprobar] AVISO: ya había un «{name}» en {destino}: se guarda como «{dst.name}».")
        shutil.move(str(fin / name), str(dst))
        print(f"[aprobar] {name} -> {dst}")
    print(f"[aprobar] {len(pedidos)} clip(s) en {destino}")

    if not cerrar:
        print(f"[aprobar] Quedan {len(restantes)} final(es) en {fin}: {', '.join(restantes)}. "
              f"No se archiva (usa --cerrar para archivar igualmente).")
    else:
        prep = base / "_prep"
        if prep.exists():
            shutil.rmtree(prep, ignore_errors=True)
            print("[aprobar] _prep/ borrado")
        tmp = base / "clips" / "_tmp"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        hist.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(base), str(hist))
        print(f"[aprobar] archivado: {base} -> {hist}")
        fuente = _fuente_en_input(p, v)
        if v == SUELTOS:
            sueltos = sorted(f for f in p.input_dir.iterdir()
                             if f.is_file() and f.suffix.lower() in EXT_CLIPS) if p.input_dir.is_dir() else []
            (hist / "_fuente").mkdir(parents=True, exist_ok=True)
            for f in sueltos:
                shutil.move(str(f), str(hist / "_fuente" / f.name))
            print(f"[aprobar] fuente: {len(sueltos)} clip(s) sueltos de input/ -> {hist / '_fuente'}")
        elif fuente is None:
            print(f"[aprobar] (no hay fuente de «{v}» en {p.input_dir}: nada que archivar)")
        elif fuente.is_dir():
            shutil.move(str(fuente), str(hist / "_fuente"))
            print(f"[aprobar] fuente: {fuente} -> {hist / '_fuente'}")
        else:
            (hist / "_fuente").mkdir(parents=True, exist_ok=True)
            shutil.move(str(fuente), str(hist / "_fuente" / fuente.name))
            print(f"[aprobar] fuente: {fuente.name} -> {hist / '_fuente'}")

    if pedidos:
        print(f"\nSiguiente (TheCopy): copys.py pendientes --proyecto {p.id}"
              + ("   [prueba: TheCopy no verá estos clips]" if pruebas else ""))
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Proyectos de TheEditor.")
    sub = ap.add_subparsers(dest="cmd")
    v = sub.add_parser("ver", help="política resuelta, recursos y reglas.md de un proyecto")
    v.add_argument("id")
    n = sub.add_parser("nuevo", help="crea proyectos/<id>/ desde _plantilla")
    n.add_argument("id")
    n.add_argument("--nombre", required=True)
    n.add_argument("--tipo", choices=TIPOS, default=None)
    ok = sub.add_parser("aprobar", help="mueve finales aprobados a REELS y archiva el vídeo")
    ok.add_argument("id")
    ok.add_argument("--video", required=True, help="Vídeo (vía 1) o carpeta de extractos (vía 2).")
    ok.add_argument("--clips", default=None,
                    help="Clips aprobados separados por comas (por defecto, todos los finales).")
    ok.add_argument("--cerrar", action="store_true",
                    help="Archiva el vídeo aunque queden finales sin aprobar.")
    ok.add_argument("--destino-pruebas", default=None,
                    help="Raíz de prueba en vez de REELS y _Historico reales.")
    a = ap.parse_args()
    if a.cmd == "nuevo":
        return _cmd_nuevo(a)
    if a.cmd == "aprobar":
        return _cmd_aprobar(a)
    if a.cmd == "ver":
        # Todo lo que el editor necesita del proyecto en UNA llamada: política
        # resuelta, recursos en disco y su reglas.md.
        p = cargar(a.id)
        n = p.contar_recursos()
        print(p.resumen())
        print(f"  carpeta      {p.dir}")
        print(f"  b-roll       {p.overlays_dir or '-'}"
              + (f"  ({n['broll']} vídeos)" if n["broll"] is not None else "")
              + (f"  (índice: {p.broll_indice.name})" if p.broll_indice else ""))
        print(f"  música       {p.music_dir or '-'}"
              + (f"  ({n['musica']} audios)" if n["musica"] is not None else ""))
        print(f"  encuadre     por defecto «{p.modo_encuadre()}»; carpetas: "
              f"{(p.cfg.get('encuadre') or {}).get('carpetas') or '-'}")
        print(f"  silencios    {p.silencios}")
        print(f"  gancho texto {p.gancho_duracion or 2.5} s · frases etiqueta {p.etiqueta}")
        reglas = p.dir / "reglas.md"
        print(f"\n--- {reglas.relative_to(RAIZ).as_posix()} ---")
        print(reglas.read_text(encoding="utf-8").strip() if reglas.exists() else "(no hay reglas.md)")
        return 0
    for pid in listar():
        print(cargar(pid).resumen())
    return 0


if __name__ == "__main__":
    sys.exit(main())

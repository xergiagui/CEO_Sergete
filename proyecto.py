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

CLI:
    python proyecto.py                       -> lista los proyectos y su política
    python proyecto.py ver <id>              -> configuración resuelta
    python proyecto.py nuevo <id> --nombre "Nombre" [--tipo clipping|largos]
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

TIPOS = ("largos", "clipping")
BROLL = ("banco_comun", "propio", "ninguno")
MUSICA = ("banco_comun", "propia", "ninguna")
GANCHO_VISUAL = ("pexels", "ninguno")

# Si a un proyecto le falta alguna clave de `recursos`, se toma lo más
# restrictivo (nada de fuera) y se avisa.
RECURSOS_RESTRICTIVOS = {
    "broll": "propio", "musica": "propia", "internet": False,
    "gancho_visual": "ninguno", "gancho_texto": True, "guardar_frases": True,
}
SILENCIOS_DEFECTO = {"umbral": "6%", "margen": "0.15s"}
MODO_ENCUADRE_DEFECTO = "right"           # el de siempre del batch


class ProyectoError(SystemExit):
    """Error de proyecto: en un script sale con el mensaje; capturable."""


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

    def politica_render(self) -> dict | None:
        """Política para `pipeline_core.burn_subs_and_music(recursos=…)`.

        None si es la de siempre (banco común + internet): así MongeMalo pasa
        exactamente por el mismo camino que antes de haber proyectos.
        """
        r = self.recursos
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
    def modo_encuadre(self, carpeta: str | None = None) -> str:
        """Modo del batch para una carpeta: mapa del proyecto o su modo por defecto."""
        enc = self.cfg.get("encuadre") or {}
        mapa = enc.get("carpetas") or {}
        if carpeta:
            for k, v in mapa.items():
                if k.strip().lower() == carpeta.strip().lower() and str(v).strip():
                    return str(v).strip().lower()
        return str(enc.get("modo_por_defecto") or MODO_ENCUADRE_DEFECTO).strip().lower()

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

    def iniciar_log(self, nombre: str) -> Path:
        """Duplica stdout/stderr en proyectos/<id>/logs/<nombre>_<fecha>.log."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        path = self.logs_dir / f"{nombre}_{dt.datetime.now():%Y%m%d-%H%M%S}.log"
        fh = open(path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _Tee(sys.stdout, fh)
        sys.stderr = _Tee(sys.stderr, fh)
        return path

    def resumen(self) -> str:
        r = self.recursos
        return (f"Proyecto: {self.id} ({self.tipo}) · b-roll {r['broll']} · música {r['musica']} · "
                f"internet {'sí' if r['internet'] else 'NO'} · gancho visual {r['gancho_visual']} · "
                f"gancho texto {'sí' if r['gancho_texto'] else 'no'} · "
                f"frases {'sí' if r['guardar_frases'] else 'no'}")


class _Tee:
    def __init__(self, stream, fh):
        self._s, self._fh = stream, fh

    def write(self, s):
        try:
            self._fh.write(s)
        except Exception:
            pass
        return self._s.write(s)

    def flush(self):
        try:
            self._fh.flush()
        except Exception:
            pass
        self._s.flush()

    def __getattr__(self, k):
        return getattr(self._s, k)


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


def abrir(pid: str | None, script: str, log: bool = True) -> Proyecto:
    """Resuelve el proyecto, aplica su política de red y abre el log del script."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    p = resolver(pid)
    p.aplicar_red()
    if log:
        ruta = p.iniciar_log(script)
        print(f"{p.resumen()}\n[log] {ruta}", flush=True)
    else:
        print(p.resumen(), flush=True)
    return p


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


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Proyectos de TheEditor.")
    sub = ap.add_subparsers(dest="cmd")
    v = sub.add_parser("ver", help="configuración resuelta de un proyecto")
    v.add_argument("id")
    n = sub.add_parser("nuevo", help="crea proyectos/<id>/ desde _plantilla")
    n.add_argument("id")
    n.add_argument("--nombre", required=True)
    n.add_argument("--tipo", choices=TIPOS, default=None)
    a = ap.parse_args()
    if a.cmd == "nuevo":
        return _cmd_nuevo(a)
    if a.cmd == "ver":
        p = cargar(a.id)
        print(p.resumen())
        print(f"  carpeta      {p.dir}")
        print(f"  b-roll       {p.overlays_dir or '-'}"
              + (f"  (índice: {p.broll_indice.name})" if p.broll_indice else ""))
        print(f"  música       {p.music_dir or '-'}")
        print(f"  encuadre     por defecto «{p.modo_encuadre()}»; carpetas: "
              f"{(p.cfg.get('encuadre') or {}).get('carpetas') or '-'}")
        print(f"  silencios    {p.silencios}")
        print(f"  frases       etiqueta {p.etiqueta}")
        return 0
    for pid in listar():
        print(cargar(pid).resumen())
    return 0


if __name__ == "__main__":
    sys.exit(main())

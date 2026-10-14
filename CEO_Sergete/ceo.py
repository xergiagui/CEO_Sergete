"""
CEO_Sergete — órdenes diarias sin lanzar subagentes.

Solo coordina: llama a las órdenes de los departamentos (TheCopy, TheHistoria,
TheEditor) y resume. No duplica su lógica. Para todo lo que necesita criterio
(escribir copys, elegir cortes, planes de carrusel…) sigue mandando el subagente.

  py ceo.py hoy      [--proyecto id] [--fecha AAAA-MM-DD]   ¿qué publico hoy? (todos los activos)
  py ceo.py semana   [--proyecto id] [--semana AAAA-Www]    plan de la semana (marca ATRASADOS)
  py ceo.py huecos   --proyecto id                           carruseles que faltan, descontando los pendientes de OK
  py ceo.py aprobar clips     --proyecto id --video "<v>" [--clips a.mp4,b.mp4] [--cerrar]
  py ceo.py aprobar carrusel  --proyecto id "<carpeta>"
  py ceo.py aprobar historias --proyecto id (<tanda> … | --todas)
  py ceo.py estado   [--proyecto id]                         qué queda PENDIENTE y qué hay en cada bandeja

Al aprobar clips o carruseles, después hay que lanzar el subagente `copy`
(copy + hashtags + calendario): ceo.py lo recuerda al terminar.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CEO = Path(__file__).resolve().parent
RAIZ = CEO.parent
PROYECTOS = CEO / "proyectos.json"
DEP = {d["id"]: (CEO / d["ruta_relativa"]).resolve()
       for d in json.loads((CEO / "departamentos.json").read_text(encoding="utf-8"))["departamentos"]}
PY_COPY = DEP["copy"] / ".venv" / "Scripts" / "python.exe"
PY_EDITOR = DEP["editor"] / ".venv" / "Scripts" / "python.exe"   # también lo usa TheHistoria
MAX_CARRUSELES_SEMANA = 2


def registro() -> list[dict]:
    return json.loads(PROYECTOS.read_text(encoding="utf-8"))["proyectos"]


def proyectos_objetivo(pid: str | None, solo_activos: bool = True) -> list[str]:
    todos = registro()
    ids = [p["id"] for p in todos]
    if pid:
        if pid not in ids:
            sys.exit(f"No existe el proyecto «{pid}». Proyectos: {', '.join(ids)}")
        return [pid]
    return [p["id"] for p in todos if not solo_activos or p.get("estado") == "activo"]


def exigir_uno(pid: str | None) -> str:
    if pid:
        return proyectos_objetivo(pid)[0]
    activos = proyectos_objetivo(None)
    if len(activos) == 1:
        return activos[0]
    sys.exit(f"Indica --proyecto ({', '.join(activos)}).")


def correr(cmd: list, cwd: Path, capturar: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], cwd=cwd, text=True, encoding="utf-8",
                          errors="replace", capture_output=capturar)


# --------------------------------------------------------------------------- órdenes
def cmd_hoy(a) -> int:
    rc = 0
    for pid in proyectos_objetivo(a.proyecto):
        print(f"══ {pid} ══", flush=True)
        extra = ["--fecha", a.fecha] if a.fecha else []
        rc |= correr([PY_COPY, "copys.py", "calendario", "hoy", "--proyecto", pid] + extra, DEP["copy"]).returncode
    return rc


def cmd_semana(a) -> int:
    rc = 0
    for pid in proyectos_objetivo(a.proyecto):
        print(f"══ {pid} ══", flush=True)
        extra = ["--semana", a.semana] if a.semana else []
        rc |= correr([PY_COPY, "copys.py", "calendario", "ver", "--proyecto", pid] + extra, DEP["copy"]).returncode
    return rc


def carruseles_pendientes_ok(pid: str) -> list[str]:
    salidas = DEP["historia"] / "salidas" / pid
    return sorted(p.name for p in salidas.glob("carrusel_*") if p.is_dir()) if salidas.exists() else []


def cmd_huecos(a) -> int:
    pid = exigir_uno(a.proyecto)
    r = correr([PY_COPY, "copys.py", "calendario", "planificar", "--proyecto", pid, "--simular", "--json"],
               DEP["copy"], capturar=True)
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError:
        print(r.stdout + r.stderr)
        return 1
    if "aviso" in datos or "error" in datos:
        print(datos.get("aviso") or datos.get("error"))
        return 0 if "aviso" in datos else 1
    pendientes = carruseles_pendientes_ok(pid)
    libres = len(pendientes)            # los pendientes de OK cubren huecos en orden
    print(f"Huecos de {pid} (simulación; no se escribe nada). Carruseles pendientes de OK: {len(pendientes)}"
          + (f" ({', '.join(pendientes)})" if pendientes else ""))
    total_a_hacer = 0
    for semana, f in datos.get("faltan", {}).items():
        cubre = min(libres, f["carruseles"])
        libres -= cubre
        hacer = min(MAX_CARRUSELES_SEMANA, f["carruseles"] - cubre)
        total_a_hacer += hacer
        print(f"  {semana}: faltan {f['carruseles']} carrusel(es) · {f['reels']} Reel(s) · {f['cualquiera']} pieza(s) "
              f"cualquiera · {f['historias']} historia(s) → hacer {hacer} carrusel(es)")
    print(f"HACER_CARRUSELES={total_a_hacer}")
    return 0


def cmd_aprobar(a) -> int:
    pid = exigir_uno(a.proyecto)
    if a.que == "clips":
        if not a.video:
            sys.exit("Falta --video.")
        cmd = [PY_EDITOR, "proyecto.py", "aprobar", pid, "--video", a.video]
        cmd += (["--clips", a.clips] if a.clips else []) + (["--cerrar"] if a.cerrar else [])
        print(flush=True)
        rc = correr(cmd, DEP["editor"]).returncode
    elif a.que == "carrusel":
        if len(a.objetivos) != 1:
            sys.exit("Indica una carpeta de carrusel.")
        rc = correr([PY_EDITOR, "carruseles.py", "--aprobar", a.objetivos[0], "--proyecto", pid],
                    DEP["historia"]).returncode
    else:  # historias
        if not a.objetivos and not a.todas:
            sys.exit("Indica las tandas o --todas.")
        cmd = [PY_EDITOR, "historias.py", "--proyecto", pid, "--aprobar"] + a.objetivos + (["--todas"] if a.todas else [])
        rc = correr(cmd, DEP["historia"]).returncode
    if rc == 0 and a.que in ("clips", "carrusel"):
        print(f"\nSiguiente: subagente `copy` con el proyecto «{pid}» (copy + hashtags + calendario).")
    return rc


# Marcas de «sin rellenar» (el «<id>» de las rutas plantilla de TheCopy es legítimo).
PENDIENTE = re.compile(r'PENDIENTE|<Nombre>|<cuenta>|"_rellenar":\s*true')
VIDEO = {".mp4", ".mov", ".m4v", ".mkv"}


def cmd_estado(a) -> int:
    for pid in proyectos_objetivo(a.proyecto, solo_activos=False):
        p = next(x for x in registro() if x["id"] == pid)
        print(f"══ {pid} · {p.get('nombre')} · {p.get('tipo')} · estado: {p.get('estado')} ══")
        # 1) lo que falta rellenar
        faltan = []
        for clave, valor in (p.get("identidad") or {}).items():
            if PENDIENTE.search(json.dumps(valor, ensure_ascii=False)):
                faltan.append(f"proyectos.json → identidad.{clave}")
        if not p.get("identidad"):
            faltan.append("proyectos.json → identidad (no existe)")
        for dep_id, raiz in DEP.items():
            carpeta = raiz / "proyectos" / pid
            if not carpeta.is_dir():
                continue
            for f in sorted(carpeta.rglob("*")):
                if f.suffix.lower() in (".json", ".md") and f.is_file() and "auditorias" not in f.parts:
                    if PENDIENTE.search(f.read_text(encoding="utf-8", errors="replace")):
                        faltan.append(str(f.relative_to(RAIZ)))
        print("  Pendiente de rellenar:" if faltan else "  Nada pendiente de rellenar.")
        for f in faltan:
            print(f"    - {f}")
        # 2) bandejas
        def contar(c: Path, patron: str = "*") -> int:
            return sum(1 for _ in c.glob(patron)) if c.exists() else 0
        rev = CEO / "REVISADOS" / pid / "1. pte Publicar"
        his = CEO / "HISTORIAS" / pid / "1. Pte publicar"
        sal = DEP["historia"] / "salidas" / pid
        inp = DEP["editor"] / "proyectos" / pid / "input"
        print(f"  Pte publicar: {contar(rev, '*.mp4')} Reel(s) y {sum(1 for d in rev.glob('carrusel_*') if d.is_dir()) if rev.exists() else 0} carrusel(es)"
              f" · historias: {contar(his, '*.mp4')}")
        print(f"  Pendiente de OK en TheHistoria: {len(carruseles_pendientes_ok(pid))} carrusel(es), "
              f"{sum(1 for d in sal.iterdir() if d.is_dir() and not d.name.startswith('carrusel_')) if sal.exists() else 0} tanda(s) de historias")
        n_vid = sum(1 for x in inp.iterdir() if x.suffix.lower() in VIDEO) if inp.exists() else 0
        n_dir = sum(1 for x in inp.iterdir() if x.is_dir()) if inp.exists() else 0
        print(f"  Buzón del editor (input/): {n_vid} vídeo(s) suelto(s) y {n_dir} carpeta(s) de clips")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Órdenes diarias del CEO (sin subagentes).")
    sub = ap.add_subparsers(dest="orden", required=True)
    h = sub.add_parser("hoy"); h.add_argument("--proyecto"); h.add_argument("--fecha")
    s = sub.add_parser("semana"); s.add_argument("--proyecto"); s.add_argument("--semana")
    u = sub.add_parser("huecos"); u.add_argument("--proyecto")
    ap_ = sub.add_parser("aprobar")
    ap_.add_argument("que", choices=["clips", "carrusel", "historias"])
    ap_.add_argument("objetivos", nargs="*", help="carpeta de carrusel o tandas de historias")
    ap_.add_argument("--proyecto")
    ap_.add_argument("--video")
    ap_.add_argument("--clips")
    ap_.add_argument("--cerrar", action="store_true")
    ap_.add_argument("--todas", action="store_true")
    e = sub.add_parser("estado"); e.add_argument("--proyecto")
    a = ap.parse_args()
    return {"hoy": cmd_hoy, "semana": cmd_semana, "huecos": cmd_huecos,
            "aprobar": cmd_aprobar, "estado": cmd_estado}[a.orden](a)


if __name__ == "__main__":
    sys.exit(main())

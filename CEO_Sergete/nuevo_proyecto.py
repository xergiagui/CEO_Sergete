"""
CEO_Sergete — da de alta un PROYECTO nuevo en todos los departamentos.

Solo coordina (no duplica código de los departamentos):
  1. añade el proyecto a `proyectos.json` con estado «alta»;
  2. copia `proyectos/_plantilla/` de cada departamento a `proyectos/<id>/`
     (TheCopy usa su propia orden `copys.py nuevo-proyecto`, que lee el registro);
  3. crea las carpetas de datos comunes (publicar, historias, histórico,
     descargas y el buzón y los recursos del editor).

Lo específico de cada proyecto (tono, ofertas, hashtags, recursos, reglas,
estilo, perfil…) lo rellenan después los subagentes de cada departamento.
Es idempotente: lo que ya existe no se toca.

  py nuevo_proyecto.py <id> --nombre "Nombre" --tipo clipping|largos
                       [--cuenta @cuenta] [--prefijo XX] [--simular]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CEO = Path(__file__).resolve().parent
RAIZ = CEO.parent                       # PruebasIA
REGISTRO = CEO / "proyectos.json"
DEPARTAMENTOS = CEO / "departamentos.json"
TEXTO = {".json", ".md", ".txt"}        # archivos donde se sustituyen <id> y <Nombre>


def carpetas_datos(pid: str) -> list[Path]:
    return [
        CEO / "REELS" / pid / "1. pte Publicar",
        CEO / "REELS" / pid / "2. Publicados",
        CEO / "HISTORIAS" / pid / "1. Pte publicar",
        CEO / "HISTORIAS" / pid / "2. Publicadas",
        RAIZ / "_Historico" / pid,
        RAIZ / "TheDescarga" / "descargas" / pid,
    ]
    # (las carpetas de TheEditor —input, recursos…— las crea su propia orden de alta)


def sustituir(carpeta: Path, pid: str, nombre: str, cuenta: str) -> None:
    for f in carpeta.rglob("*"):
        if f.is_file() and f.suffix.lower() in TEXTO:
            t = f.read_text(encoding="utf-8")
            n = t.replace("<id>", pid).replace("<Nombre>", nombre)
            if cuenta:
                n = n.replace("@<cuenta>", cuenta)
            if n != t:
                f.write_text(n, encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Alta de un proyecto en todos los departamentos.")
    ap.add_argument("id")
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--tipo", required=True, choices=["clipping", "largos"])
    ap.add_argument("--cuenta", default="")
    ap.add_argument("--prefijo", default="")
    ap.add_argument("--descripcion", default="PENDIENTE")
    ap.add_argument("--plataformas", default="instagram", help="separadas por comas")
    ap.add_argument("--formatos", default="reels", help="reels,carruseles,historias")
    ap.add_argument("--simular", action="store_true", help="enseña lo que haría sin tocar nada")
    a = ap.parse_args()

    pid = a.id
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", pid):
        sys.exit("El id va en minúsculas, sin espacios ni tildes (p. ej. «clientex»).")
    hacer = not a.simular
    hechos, saltados, fallos = [], [], []

    # 1) registro (antes que las plantillas: copys.py nuevo-proyecto lee de aquí nombre, tipo y prefijo)
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))
    if any(p["id"] == pid for p in reg["proyectos"]):
        saltados.append("proyectos.json: ya estaba")
    else:
        lista = lambda t: [x.strip() for x in t.split(",") if x.strip()]
        reg["proyectos"].append({
            "id": pid, "nombre": a.nombre, "tipo": a.tipo, "estado": "alta",
            "descripcion": a.descripcion, "cuenta_ig": a.cuenta, "plataformas": lista(a.plataformas),
            "prefijo_id": a.prefijo, "recursos": "PENDIENTE (TheEditor/proyectos/%s/proyecto.json → recursos)" % pid,
            "formatos": lista(a.formatos), "alta": dt.date.today().isoformat(),
            # Fuente única de la identidad (la leen TheCopy, TheHistoria y ThePerfil).
            "identidad": {
                "cuenta_ig": a.cuenta, "landing": "PENDIENTE", "afiliado": "",
                "posicionamiento": "PENDIENTE",
                "voz": {"persona": "PENDIENTE", "tono": "PENDIENTE", "idioma": "es-ES", "emojis_max": 3},
                "transparencia_afiliacion": False, "no_suplantar": "", "palabras_prohibidas": [],
                "marca": {"fondo": "PENDIENTE", "texto": "PENDIENTE", "acento": "PENDIENTE"},
            },
        })
        if hacer:
            REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hechos.append("proyectos.json: entrada nueva (estado «alta»)")

    # 2) plantillas de los departamentos. Los que tienen orden de alta propia la
    #    usan (ponen bien el tipo, el prefijo…); el resto copia su _plantilla.
    ordenes_propias = {
        "copy": ["copys.py", "nuevo-proyecto", pid, "--nombre", a.nombre, "--tipo", a.tipo]
                + (["--prefijo", a.prefijo] if a.prefijo else []),
        "editor": ["proyecto.py", "nuevo", pid, "--nombre", a.nombre, "--tipo", a.tipo],
    }
    deps = json.loads(DEPARTAMENTOS.read_text(encoding="utf-8"))["departamentos"]
    for d in deps:
        raiz_dep = (CEO / d["ruta_relativa"]).resolve()
        if d["id"] in ordenes_propias:
            destino = raiz_dep / "proyectos" / pid
            if (destino / "proyecto.json").exists():
                saltados.append(f"{d['nombre']}: ya existe")
                continue
            cmd = [str(raiz_dep / ".venv" / "Scripts" / "python.exe")] + ordenes_propias[d["id"]]
            if hacer:
                r = subprocess.run(cmd, cwd=raiz_dep, capture_output=True, text=True, encoding="utf-8")
                if r.returncode != 0:
                    fallos.append(f"{d['nombre']}: «{' '.join(ordenes_propias[d['id']][:2])}» falló:\n{r.stdout}{r.stderr}")
                    continue
            hechos.append(f"{d['nombre']}: {' '.join(ordenes_propias[d['id']][:2])}")
            continue
        plantilla = raiz_dep / "proyectos" / "_plantilla"
        if not plantilla.is_dir():
            continue
        destino = raiz_dep / "proyectos" / pid
        if destino.exists():
            saltados.append(f"{d['nombre']}: ya existe")
            continue
        if hacer:
            shutil.copytree(plantilla, destino)
            sustituir(destino, pid, a.nombre, a.cuenta)
        hechos.append(f"{d['nombre']}: proyectos/{pid}/ (desde _plantilla)")

    # 3) carpetas de datos comunes
    for c in carpetas_datos(pid):
        if c.exists():
            continue
        if hacer:
            c.mkdir(parents=True, exist_ok=True)
        hechos.append(f"carpeta {c.relative_to(RAIZ)}")

    print(("SIMULACIÓN · " if a.simular else "") + f"Proyecto «{pid}» ({a.tipo})")
    for h in hechos:
        print(f"  + {h}")
    for s in saltados:
        print(f"  = {s}")
    print("\nFalta rellenar (lo hacen los subagentes; ver «Añadir un proyecto» en CLAUDE.md):")
    print(f"  editor   TheEditor/proyectos/{pid}/proyecto.json (recursos, encuadre) + reglas.md; recursos en recursos/broll y recursos/musica")
    print(f"  copy     TheCopy/proyectos/{pid}/ (tono, ofertas, hashtags, CTA, plataformas, calendario)")
    print(f"  historia TheHistoria/proyectos/{pid}/ (estilo de carruseles, historias sí/no)")
    print(f"  perfil   captura del perfil → ThePerfil/proyectos/{pid}/")
    print(f"  textos   TheTextos/proyectos/{pid}/ (solo si habrá blog)")
    print(f"  CEO      proyectos.json → «identidad» (cuenta, landing, voz, palabras prohibidas, marca) y estado → activo")
    for f in fallos:
        print(f"\n[ERROR] {f}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())

"""
ThePerfil — valida una propuesta de perfil de Instagram antes de entregarla.

Comprueba los límites de la plataforma (nombre ≤ 30, bio ≤ 150 caracteres,
nombres de destacadas cortos) y las reglas del proyecto (`perfil.json`):
transparencia de afiliación, palabras prohibidas y emojis.

Solo usa la librería estándar: `py validar_perfil.py ...` (no necesita .venv).

Ejemplos:
  py validar_perfil.py --proyecto mongemalo --nombre "Sergio | Ventas y copywriting" ^
      --bio "Línea 1\\nLínea 2\\nLínea 3" --destacada "Empieza aquí" --destacada "Cursos"
  py validar_perfil.py --proyecto mongemalo --json propuesta.json
      (propuesta.json = {"nombre": "...", "bio": "...", "destacadas": ["..."]})

Código de salida: 0 sin errores, 1 con errores.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
MAX_NOMBRE = 30
MAX_BIO = 150
MAX_DESTACADA = 15  # a partir de aquí se corta en el perfil

RE_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U00002B00-\U00002BFF️]"
)


def cargar_perfil(pid: str) -> dict:
    ruta = RAIZ / "proyectos" / pid / "perfil.json"
    if not ruta.exists():
        sys.exit(f"No existe {ruta}. Proyectos: "
                 + ", ".join(p.name for p in (RAIZ / "proyectos").iterdir()
                             if p.is_dir() and not p.name.startswith("_")))
    return json.loads(ruta.read_text(encoding="utf-8"))


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def validar(perfil: dict, nombre: str | None, bio: str | None, destacadas: list[str]) -> tuple[list[str], list[str]]:
    errores, avisos = [], []
    reglas = perfil.get("reglas") or {}
    max_emojis = reglas.get("emojis_max_bio", 3)

    if nombre is not None:
        n = len(nombre)
        print(f"Nombre ({n}/{MAX_NOMBRE}): {nombre}")
        if n > MAX_NOMBRE:
            errores.append(f"Nombre: {n}/{MAX_NOMBRE} caracteres. Demasiado largo.")
        elif n < 8:
            avisos.append(f"Nombre: {n} caracteres. Añade una palabra clave que la gente busque.")
        claves = [normalizar(k) for k in reglas.get("palabras_clave_nombre", [])]
        if claves and not any(k in normalizar(nombre) for k in claves):
            avisos.append("Nombre: no lleva ninguna palabra clave del proyecto "
                          f"({', '.join(reglas.get('palabras_clave_nombre', []))}). Es el campo que indexa el buscador.")

    if bio is not None:
        bio = bio.replace("\\n", "\n")
        n = len(bio)
        if n > MAX_BIO:
            errores.append(f"Bio: {n}/{MAX_BIO} caracteres (los saltos de línea cuentan). Se cortaría.")
        lineas = [l for l in bio.split("\n") if l.strip()]
        if len(lineas) > 4:
            avisos.append(f"Bio: {len(lineas)} líneas; más de 4 se ve como un muro de texto.")
        emojis = RE_EMOJI.findall(bio)
        if len(emojis) > max_emojis:
            errores.append(f"Bio: {len(emojis)} emojis (máx. {max_emojis} en este proyecto).")
        bn = normalizar(bio)
        for p in reglas.get("palabras_prohibidas", []):
            if normalizar(p) in bn:
                errores.append(f"Bio: contiene «{p}» (prohibido en este proyecto: promete resultados o confunde).")
        if reglas.get("transparencia_afiliacion"):
            marcas = [normalizar(m) for m in reglas.get("marcas_afiliacion", ["afiliad"])]
            if not any(m in bn for m in marcas):
                errores.append("Bio: falta la transparencia de afiliación (p. ej. «afiliado independiente»).")
        if bio.strip() == bio.strip().upper() and any(c.isalpha() for c in bio):
            avisos.append("Bio: todo en mayúsculas.")
        print(f"Bio ({n}/{MAX_BIO}):\n  " + "\n  ".join(bio.split("\n")))

    for d in destacadas:
        if len(d) > MAX_DESTACADA:
            avisos.append(f"Destacada «{d}»: {len(d)} caracteres; a partir de {MAX_DESTACADA} se corta.")
    if destacadas and not (3 <= len(destacadas) <= 6):
        avisos.append(f"Destacadas: {len(destacadas)}; lo recomendable son 4–6 (las 3–4 primeras se ven sin deslizar).")

    return errores, avisos


def main() -> int:
    # La consola de Windows usa cp1252: sin esto, «↓» o las tildes rompen la salida.
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Valida una propuesta de perfil de Instagram.")
    ap.add_argument("--proyecto", required=True)
    ap.add_argument("--nombre")
    ap.add_argument("--bio", help="usa \\n para los saltos de línea")
    ap.add_argument("--destacada", action="append", default=[])
    ap.add_argument("--json", help="archivo con {nombre, bio, destacadas}")
    a = ap.parse_args()

    nombre, bio, destacadas = a.nombre, a.bio, list(a.destacada)
    if a.json:
        d = json.loads(Path(a.json).read_text(encoding="utf-8"))
        nombre = d.get("nombre", nombre)
        bio = d.get("bio", bio)
        destacadas = d.get("destacadas", destacadas)

    errores, avisos = validar(cargar_perfil(a.proyecto), nombre, bio, destacadas)
    for e in errores:
        print(f"ERROR  {e}")
    for w in avisos:
        print(f"AVISO  {w}")
    print("OK" if not errores else f"{len(errores)} error(es)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

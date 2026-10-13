"""
CARRUSELES · auditoría de estilo con el auditor de TheCopy (paso opcional).

No se importa ni se copia código de TheCopy: se lanza su CLI con su propio
.venv, una vez por slide, con todo el texto que se pinta en ella:

  <TheCopy>/.venv/Scripts/python.exe <TheCopy>/copys.py auditar --solo-estilo
      --json --texto "<texto>" [--proyecto <id>]

Contrato: stdout = lista JSON de {nivel, regla, fragmento, mensaje}; código de
salida 0 si no hay errores. Solo AVISA (no bloquea el render). Si TheCopy no
está o la orden aún no existe/no responde con JSON, se avisa y se sigue.
"""
from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import config
from lib.carrusel_plan import quitar_marcas, textos_de_slide


class AuditorNoDisponible(Exception):
    pass


def disponible() -> tuple[bool, str]:
    if not config.THECOPY_CLI.exists():
        return False, f"no existe {config.THECOPY_CLI}"
    if not config.THECOPY_PY.exists():
        return False, f"no existe el .venv de TheCopy ({config.THECOPY_PY})"
    return True, ""


def texto_auditable(slide: dict) -> str:
    """Lo que se pinta en la slide, sin marcado, un campo por línea."""
    return "\n".join(quitar_marcas(t).strip() for _, t in textos_de_slide(slide))


def _parse(stdout: str):
    s = (stdout or "").strip()
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find("["), s.rfind("]")
        if a != -1 and b > a:
            return json.loads(s[a:b + 1])
        raise


def auditar_texto(texto: str, proyecto: str | None = None, timeout: int = 90) -> list[dict]:
    cmd = [str(config.THECOPY_PY), str(config.THECOPY_CLI), "auditar", "--solo-estilo",
           "--json", "--texto", texto]
    if proyecto:
        cmd += ["--proyecto", proyecto]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        r = subprocess.run(cmd, capture_output=True, cwd=str(config.THECOPY_ROOT), env=env,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AuditorNoDisponible(f"el auditor no respondió en {timeout} s")
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace").strip()
    if r.returncode not in (0, 1):
        ultima = (err.splitlines() or [out.strip()[:200]])[-1]
        raise AuditorNoDisponible(f"la orden devolvió {r.returncode}: {ultima}")
    try:
        datos = _parse(out)
    except Exception:
        raise AuditorNoDisponible("la salida no es una lista JSON "
                                  "(¿aún no existe `auditar --solo-estilo --json`?)")
    if isinstance(datos, dict):                       # tolera {"hallazgos": [...]}
        datos = datos.get("hallazgos") or datos.get("resultados") or []
    if not isinstance(datos, list):
        raise AuditorNoDisponible("la salida JSON no es una lista")
    return [h for h in datos if isinstance(h, dict)]


def auditar_slides(slides: list[dict], proyecto: str | None = None
                   ) -> tuple[bool, str, dict[int, list[dict]]]:
    """Audita cada slide. Devuelve (ok, motivo_si_no, {n: hallazgos})."""
    ok, motivo = disponible()
    if not ok:
        return False, motivo, {}
    trabajos = [(s.get("n", i), texto_auditable(s)) for i, s in enumerate(slides, 1)
                if isinstance(s, dict)]
    trabajos = [(n, t) for n, t in trabajos if t.strip()]
    if not trabajos:
        return True, "", {}
    res: dict[int, list[dict]] = {}
    try:
        # La primera sola: si la orden no existe, se sabe sin lanzar el resto.
        n0, t0 = trabajos[0]
        res[n0] = auditar_texto(t0, proyecto)
        with ThreadPoolExecutor(max_workers=4) as ex:
            futuros = {n: ex.submit(auditar_texto, t, proyecto) for n, t in trabajos[1:]}
            for n, fut in futuros.items():
                res[n] = fut.result()
    except AuditorNoDisponible as e:
        return False, str(e), {}
    return True, "", res

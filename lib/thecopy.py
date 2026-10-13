"""
CONTRATOS con TheCopy (proceso aparte con su propio .venv; no se importa ni se
copia su código). Dos órdenes:

  campos   copys.py campos --json --proyecto <id>
           → {"formulas": [...], "objetivos": [...], "pilares": [...],
              "formula_objetivos": {formula: [objetivos]}}
           Listas válidas del plan de carrusel (fuente única: TheCopy). Se guarda
           la última respuesta en `.cache/campos_<id>.json`; si TheCopy no
           responde, se usa esa caché y, si tampoco hay, las listas de respaldo
           de `lib/carrusel_plan.py`.

  auditar  copys.py auditar --solo-estilo --json --proyecto <id> --stdin
           stdin = lista JSON de textos (uno por slide)
           → lista JSON de {i, nivel, regla, fragmento, mensaje}; `i` = índice
             (desde 0) del texto en la lista. Con `--proyecto` aplica palabras
             prohibidas, primera persona y emojis de la identidad.
           UNA llamada para todo el carrusel. Si la orden aún no admite
           `--stdin`, se vuelve a la llamada por slide (`--texto`) y se avisa.
           Solo informa: no bloquea el render.
"""
from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import config
from lib.carrusel_plan import CAMPOS_RESPALDO, quitar_marcas, textos_de_slide

_campos_mem: dict[str, tuple[dict, str]] = {}


class NoDisponible(Exception):
    pass


def disponible() -> tuple[bool, str]:
    if not config.THECOPY_CLI.exists():
        return False, f"no existe {config.THECOPY_CLI}"
    if not config.THECOPY_PY.exists():
        return False, f"no existe el .venv de TheCopy ({config.THECOPY_PY})"
    return True, ""


def _run(args: list[str], entrada: str | None = None, timeout: int = 90
         ) -> tuple[int, str, str]:
    ok, motivo = disponible()
    if not ok:
        raise NoDisponible(motivo)
    cmd = [str(config.THECOPY_PY), str(config.THECOPY_CLI), *args]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        r = subprocess.run(cmd, capture_output=True, cwd=str(config.THECOPY_ROOT), env=env,
                           timeout=timeout,
                           input=entrada.encode("utf-8") if entrada is not None else None)
    except subprocess.TimeoutExpired:
        raise NoDisponible(f"TheCopy no respondió en {timeout} s")
    return (r.returncode, r.stdout.decode("utf-8", "replace"),
            r.stderr.decode("utf-8", "replace").strip())


def _json(stdout: str, abre: str = "[", cierra: str = "]"):
    s = (stdout or "").strip()
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find(abre), s.rfind(cierra)
        if a != -1 and b > a:
            return json.loads(s[a:b + 1])
        raise


def _ultima(err: str, out: str) -> str:
    linea = ((err.splitlines() or [out.strip()[:200]]) or [""])[-1]
    if "invalid choice" in linea or "unrecognized arguments" in linea:
        return "TheCopy aún no tiene esa orden/opción"
    return linea[:160]


# ------------------------------------------------------------------ campos
def _ids(valores) -> list[str]:
    out = []
    for v in valores or []:
        if isinstance(v, dict):
            v = v.get("id") or v.get("valor") or v.get("nombre")
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return out


def _normalizar_campos(d: dict) -> dict:
    if not isinstance(d, dict):
        raise ValueError("no es un objeto JSON")
    out = {"formulas": _ids(d.get("formulas")), "objetivos": _ids(d.get("objetivos")),
           "pilares": _ids(d.get("pilares"))}
    if not all(out.values()):
        raise ValueError("faltan fórmulas, objetivos o pilares")
    fo = d.get("formula_objetivos") or {}
    out["formula_objetivos"] = {f: _ids(v if isinstance(v, list) else [v])
                                for f, v in fo.items() if isinstance(f, str)}
    return out


def campos(pid: str) -> tuple[dict, str]:
    """(campos, origen). origen = «TheCopy» | «caché (…)» | «respaldo (…)»."""
    if pid in _campos_mem:
        return _campos_mem[pid]
    cache = config.CACHE_DIR / f"campos_{pid}.json"
    try:
        rc, out, err = _run(["campos", "--json", "--proyecto", pid], timeout=60)
        if rc != 0:
            raise NoDisponible(f"`copys.py campos` devolvió {rc}: {_ultima(err, out)}")
        datos = _normalizar_campos(_json(out, "{", "}"))
        try:
            config.CACHE_DIR.mkdir(exist_ok=True)
            cache.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
        res = (datos, "TheCopy")
    except (NoDisponible, ValueError, json.JSONDecodeError) as e:
        motivo = str(e) or "respuesta ilegible"
        try:
            res = (_normalizar_campos(json.loads(cache.read_text(encoding="utf-8"))),
                   f"caché de la última respuesta de TheCopy ({motivo})")
        except Exception:
            res = (CAMPOS_RESPALDO, f"listas de respaldo de TheHistoria ({motivo})")
    _campos_mem[pid] = res
    return res


def resumen_campos(c: dict) -> str:
    fo = c.get("formula_objetivos") or {}
    formulas = " · ".join(f"{f} ({'/'.join(fo[f])})" if fo.get(f) else f
                          for f in c["formulas"])
    return (f"fórmula (objetivo): {formulas}\n"
            f"objetivos: {' | '.join(c['objetivos'])}\n"
            f"pilares: {' | '.join(c['pilares'])}")


# ------------------------------------------------------------------ auditoría
def texto_auditable(slide: dict) -> str:
    """Lo que se pinta en la slide, sin marcado, un campo por línea."""
    return "\n".join(quitar_marcas(t).strip() for _, t in textos_de_slide(slide))


def _hallazgos(datos) -> list[dict]:
    if isinstance(datos, dict):                       # tolera {"hallazgos": [...]}
        datos = datos.get("hallazgos") or datos.get("resultados") or []
    if not isinstance(datos, list):
        raise NoDisponible("la salida JSON no es una lista")
    return [h for h in datos if isinstance(h, dict)]


def _auditar_lote(textos: list[str], pid: str | None) -> list[dict]:
    args = ["auditar", "--solo-estilo", "--json", "--stdin"]
    if pid:
        args += ["--proyecto", pid]
    rc, out, err = _run(args, entrada=json.dumps(textos, ensure_ascii=False), timeout=120)
    if rc not in (0, 1):
        raise NoDisponible(f"la orden devolvió {rc}: {_ultima(err, out)}")
    try:
        return _hallazgos(_json(out))
    except NoDisponible:
        raise
    except Exception:
        raise NoDisponible("la salida no es una lista JSON")


def _auditar_texto(texto: str, pid: str | None) -> list[dict]:
    args = ["auditar", "--solo-estilo", "--json", "--texto", texto]
    if pid:
        args += ["--proyecto", pid]
    rc, out, err = _run(args)
    if rc not in (0, 1):
        raise NoDisponible(f"la orden devolvió {rc}: {_ultima(err, out)}")
    try:
        return _hallazgos(_json(out))
    except NoDisponible:
        raise
    except Exception:
        raise NoDisponible("la salida no es una lista JSON "
                           "(¿aún no existe `auditar --solo-estilo --json`?)")


def auditar_slides(slides: list[dict], pid: str | None
                   ) -> tuple[bool, str, dict[int, list[dict]], str]:
    """Audita todas las slides. Devuelve (ok, motivo_si_no, {n: hallazgos}, aviso).

    `aviso` no vacío = se usó la llamada por slide porque el contrato `--stdin`
    aún no responde."""
    ok, motivo = disponible()
    if not ok:
        return False, motivo, {}, ""
    trabajos = [(s.get("n", i), texto_auditable(s)) for i, s in enumerate(slides, 1)
                if isinstance(s, dict)]
    trabajos = [(n, t) for n, t in trabajos if t.strip()]
    if not trabajos:
        return True, "", {}, ""
    res: dict[int, list[dict]] = {n: [] for n, _ in trabajos}
    try:
        for h in _auditar_lote([t for _, t in trabajos], pid):
            i = h.get("i")
            if isinstance(i, int) and 0 <= i < len(trabajos):
                res[trabajos[i][0]].append(h)
        return True, "", res, ""
    except NoDisponible as e:
        aviso = (f"el contrato `auditar --stdin` aún no responde ({e}); "
                 f"vuelvo a una llamada por slide")
    try:
        n0, t0 = trabajos[0]                 # la primera sola: si falla, no lanzo el resto
        res[n0] = _auditar_texto(t0, pid)
        with ThreadPoolExecutor(max_workers=4) as ex:
            futuros = {n: ex.submit(_auditar_texto, t, pid) for n, t in trabajos[1:]}
            for n, fut in futuros.items():
                res[n] = fut.result()
    except NoDisponible as e:
        return False, str(e), {}, aviso
    return True, "", res, aviso

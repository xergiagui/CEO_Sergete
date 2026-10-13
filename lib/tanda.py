"""
TANDA = el JSON de trabajo de una orden de copys.

1) `copy.py pendientes` crea el esqueleto: un bloque por clip con su contexto
   (cortes.json + transcripción) y huecos vacíos por cada plataforma activa.
2) El subagente `copy` (LLM) rellena los huecos: tema, campos propios
   (p. ej. oferta), y por plataforma copy (+ título si aplica) y hashtags
   TEMÁTICOS. Los fijos los añade el script: no hay que escribirlos.
3) `copy.py registrar` valida todo y, si está bien, escribe Excel + .txt.

Esquema de cada clip:
{
  "clip": "01_nombre.mp4",
  "ruta": "C:\\...\\01_nombre.mp4",
  "contexto": {...},                 # solo lectura, lo pone el script
  "tema": "",                        # resumen corto del clip (columna Tema)
  "extra": {"oferta": ""},           # campos_extra del proyecto
  "plataformas": {                   # solo las que le faltan a ese clip
    "instagram": {"copy": "", "hashtags": []},
    "youtube":   {"titulo": "", "copy": "", "hashtags": []}
  }
}
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from lib.util import normalizar, normalizar_hashtag

RE_HASHTAG = re.compile(r"#[^\s#]+")


def hueco_plataforma(conf_plat: dict) -> dict:
    h = {}
    if conf_plat.get("requiere_titulo"):
        h["titulo"] = ""
    h["copy"] = ""
    h["hashtags"] = []
    return h


def esqueleto(proyecto, clips: list[tuple[Path, dict, list[str]]]) -> dict:
    """clips: [(ruta_mp4, contexto, plataformas_que_faltan)]"""
    return {
        "proyecto": proyecto.id,
        "creada": dt.datetime.now().isoformat(timespec="seconds"),
        "instrucciones": (
            "Rellena tema, extra y, por plataforma, copy (+titulo si aparece) y hashtags TEMÁTICOS "
            "(solo los temáticos: los fijos los añade el script). Reglas en proyectos/"
            f"{proyecto.id}/proyecto.json. Luego: copys.py registrar --entrada <este archivo>"),
        "clips": [
            {
                "clip": ruta.name,
                "ruta": str(ruta),
                "contexto": ctx,
                "tema": "",
                "extra": {c["id"]: "" for c in proyecto.campos_extra()},
                "plataformas": {p: hueco_plataforma(proyecto.plataforma(p)) for p in plats},
            }
            for ruta, ctx, plats in clips
        ],
    }


def hashtags_finales(proyecto, pid: str, tematicos: list[str]) -> list[str]:
    """Fijos de la plataforma + temáticos, sin duplicados y en ese orden."""
    out = []
    for t in proyecto.fijos(pid) + [normalizar_hashtag(t) for t in tematicos]:
        if t and t not in out:
            out.append(t)
    return out


def texto_para_pegar(proyecto, pid: str, bloque: dict) -> str:
    conf = proyecto.plataforma(pid)
    tags = " ".join(hashtags_finales(proyecto, pid, bloque.get("hashtags") or []))
    plantilla = conf.get("formato_texto") or "{copy}\n\n{hashtags}"
    return plantilla.format(copy=(bloque.get("copy") or "").strip(), hashtags=tags,
                            titulo=(bloque.get("titulo") or "").strip()).strip()


def validar(proyecto, tanda: dict, copys_existentes: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    """Devuelve (errores, avisos). Con errores no se registra nada.

    copys_existentes: {plataforma: {copy normalizado: clip}} ya registrados, para no repetir.
    """
    errores, avisos = [], []
    if tanda.get("proyecto") != proyecto.id:
        errores.append(f"La tanda es del proyecto '{tanda.get('proyecto')}', no de '{proyecto.id}'.")
    clips = tanda.get("clips") or []
    if not clips:
        errores.append("La tanda no tiene clips.")
    pool = proyecto.pool_tematico()
    vistos: dict[str, set[str]] = {}

    for c in clips:
        et = c.get("clip") or "(sin nombre)"
        if not c.get("clip"):
            errores.append("Hay un clip sin nombre.")
        if not (c.get("tema") or "").strip():
            errores.append(f"[{et}] falta 'tema'.")
        ruta = c.get("ruta")
        if not ruta or not Path(ruta).exists():
            avisos.append(f"[{et}] el MP4 no está en '{ruta}': se registra igual pero sin .txt ni enlace.")

        for campo in proyecto.campos_extra():
            val = ((c.get("extra") or {}).get(campo["id"]) or "").strip()
            permitidos = proyecto.valores_campo(campo)
            if campo.get("obligatorio") and not val:
                errores.append(f"[{et}] falta '{campo['id']}'"
                               + (f" (valores: {', '.join(permitidos)})" if permitidos else "") + ".")
            elif val and permitidos and val not in permitidos:
                errores.append(f"[{et}] '{campo['id']}' = '{val}' no es válido. Usa: {', '.join(permitidos)}.")

        plats = c.get("plataformas") or {}
        if not plats:
            errores.append(f"[{et}] no tiene ninguna plataforma.")
        for pid, b in plats.items():
            ep = f"[{et} · {pid}]"
            if pid not in (proyecto.conf.get("plataformas") or {}):
                errores.append(f"{ep} plataforma no definida en el proyecto.")
                continue
            if not proyecto.plataforma(pid).get("activa"):
                avisos.append(f"{ep} la plataforma no está activa en el proyecto (se registra igual).")
            conf = proyecto.plataforma(pid)
            copy = (b.get("copy") or "").strip()

            # --- título (YouTube) ---
            if conf.get("requiere_titulo"):
                tit = (b.get("titulo") or "").strip()
                if not tit:
                    errores.append(f"{ep} falta 'titulo'.")
                elif conf.get("titulo_max") and len(tit) > conf["titulo_max"]:
                    errores.append(f"{ep} título de {len(tit)} caracteres (máx. {conf['titulo_max']}).")

            # --- copy ---
            if not copy:
                errores.append(f"{ep} falta 'copy'.")
                continue
            if RE_HASHTAG.search(copy):
                errores.append(f"{ep} el copy lleva hashtags dentro; van en su campo 'hashtags'.")
            if conf.get("cta_obligatorio"):
                pats = conf.get("cta_patrones") or []
                if pats and not any(re.search(p, copy, re.IGNORECASE) for p in pats):
                    ej = conf.get("cta_ejemplo") or " | ".join(pats)
                    errores.append(f"{ep} el copy no lleva CTA (p. ej. «{ej}»).")
            rec = conf.get("copy_recomendado")
            if rec and not (rec[0] <= len(copy) <= rec[1]):
                avisos.append(f"{ep} copy de {len(copy)} caracteres (recomendado {rec[0]}–{rec[1]}).")

            # --- hashtags ---
            reglas = conf.get("hashtags") or {}
            tem_raw = b.get("hashtags") or []
            if isinstance(tem_raw, str):
                tem_raw = tem_raw.split()
            tem = [normalizar_hashtag(t) for t in tem_raw if str(t).strip()]
            fijos = proyecto.fijos(pid)
            malos = [t for t in tem if not RE_HASHTAG.fullmatch(t) or t != t.lower()]
            if malos:
                errores.append(f"{ep} hashtags mal formados (sin espacios, en minúsculas): {' '.join(malos)}")
            tem = [t for t in tem if t not in fijos]
            if len(set(tem)) != len(tem):
                errores.append(f"{ep} hashtags temáticos repetidos.")
            mn, mx = reglas.get("tematicos_min", 0), reglas.get("tematicos_max", 30)
            if not (mn <= len(tem) <= mx):
                errores.append(f"{ep} {len(tem)} hashtags temáticos; deben ser entre {mn} y {mx} "
                               f"(los fijos {' '.join(fijos)} ya se añaden solos).")
            fuera = [t for t in tem if pool and t not in pool]
            if fuera:
                avisos.append(f"{ep} hashtags fuera del banco temático (se aceptan): {' '.join(fuera)}")
            total = len(hashtags_finales(proyecto, pid, tem))
            if reglas.get("max_total") and total > reglas["max_total"]:
                errores.append(f"{ep} {total} hashtags en total (máx. {reglas['max_total']}).")
            b["hashtags"] = tem  # normalizados

            # --- longitud total ---
            texto = texto_para_pegar(proyecto, pid, b)
            if conf.get("max_caracteres") and len(texto) > conf["max_caracteres"]:
                errores.append(f"{ep} texto de {len(texto)} caracteres (máx. {conf['max_caracteres']}).")

            # --- no repetir copy ---
            n = normalizar(copy)
            if n in vistos.setdefault(pid, set()):
                errores.append(f"{ep} copy repetido dentro de la misma tanda.")
            vistos[pid].add(n)
            otro = copys_existentes.get(pid, {}).get(n)
            if otro and otro.lower() != et.lower():
                errores.append(f"{ep} este copy ya está registrado para {otro}; escribe uno distinto.")

    return errores, avisos

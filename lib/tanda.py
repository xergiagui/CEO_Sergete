"""
TANDA = el JSON de trabajo de una orden de copys.

1) `copys.py pendientes` crea el esqueleto: un bloque por clip con su contexto
   (cortes.json + transcripción) y huecos vacíos por cada plataforma activa.
2) El subagente `copy` (LLM) rellena los huecos: tema, campos propios
   (p. ej. oferta), y por plataforma copy (+ título si aplica) y hashtags
   TEMÁTICOS. Los fijos los añade el script: no hay que escribirlos.
   `copys.py auditar --entrada <tanda>` revisa el estilo antes de registrar.
3) `copys.py registrar` valida todo (incluida la auditoría) y, si está bien,
   escribe Excel + .txt.

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

import config
from lib import auditoria
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
            "(solo los temáticos: los fijos los añade el script; nº y tamaños en proyecto.json → "
            "plataformas.<p>.hashtags, banco por tamaño en hashtags.json, últimos usados con "
            f"copys.py hashtags). Reglas del copy en proyectos/{proyecto.id}/proyecto.json. "
            "Antes de registrar: copys.py auditar --entrada <este archivo> y corrige los avisos de "
            "estilo reescribiendo (solo se dejan si la frase es literal del clip). "
            "Luego: copys.py registrar --entrada <este archivo> --simular, y sin --simular."),
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


def tematicos_de(proyecto, pid: str, hashtags) -> frozenset[str]:
    """Conjunto de temáticos (sin los fijos actuales de la plataforma) de una lista o texto de hashtags."""
    if isinstance(hashtags, str):
        hashtags = RE_HASHTAG.findall(hashtags)
    fijos = set(proyecto.fijos(pid))
    return frozenset(t for t in (normalizar_hashtag(str(x)) for x in hashtags or []) if t and t not in fijos)


def texto_para_pegar(proyecto, pid: str, bloque: dict) -> str:
    conf = proyecto.plataforma(pid)
    tags = " ".join(hashtags_finales(proyecto, pid, bloque.get("hashtags") or []))
    plantilla = conf.get("formato_texto") or "{copy}\n\n{hashtags}"
    return plantilla.format(copy=(bloque.get("copy") or "").strip(), hashtags=tags,
                            titulo=(bloque.get("titulo") or "").strip()).strip()


def validar(proyecto, tanda: dict, copys_existentes: dict[str, dict[str, str]],
            recientes: dict[str, list[tuple[str, frozenset[str]]]] | None = None) -> tuple[list[str], list[str]]:
    """Devuelve (errores, avisos). Con errores no se registra nada.

    copys_existentes: {plataforma: {copy normalizado: clip}} ya registrados, para no repetir.
    recientes: {plataforma: [(clip, temáticos), ...]} registrados, en orden de alta, para la
               rotación de hashtags (se miran los últimos `rotacion_ultimos`).
    """
    errores, avisos = [], []
    if tanda.get("proyecto") != proyecto.id:
        errores.append(f"La tanda es del proyecto '{tanda.get('proyecto')}', no de '{proyecto.id}'.")
    clips = tanda.get("clips") or []
    if not clips:
        errores.append("La tanda no tiene clips.")
    pool = proyecto.pool_tematico()
    recientes = recientes or {}
    vistos: dict[str, set[str]] = {}
    sets_tanda: dict[str, dict[frozenset[str], str]] = {}

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

            # --- auditoría (lib/auditoria.py · referencias/auditoria_copy.md) ---
            for h in auditoria.auditar(copy, conf, c.get("contexto"), proyecto.nombre_plataforma(pid)):
                if h.nivel == "error":
                    errores.append(f"{ep} {h.mensaje}")
                elif h.nivel == "aviso":
                    avisos.append(f"{ep} estilo: {h.mensaje}")
                # "literal": frase literal del clip → se permite, no se avisa

            # --- hashtags ---
            errores_h, avisos_h, tem = _validar_hashtags(proyecto, pid, b, pool, et, recientes, sets_tanda)
            errores += [f"{ep} {e}" for e in errores_h]
            avisos += [f"{ep} {a}" for a in avisos_h]
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


def _validar_hashtags(proyecto, pid: str, bloque: dict, pool: set[str], clip: str,
                      recientes: dict[str, list[tuple[str, frozenset[str]]]],
                      sets_tanda: dict[str, dict[frozenset[str], str]]) -> tuple[list[str], list[str], list[str]]:
    """Reglas de hashtags de una plataforma (proyecto.json → plataformas.<p>.hashtags).

    Claves admitidas (todas opcionales):
      tematicos_min / tematicos_max   nº de temáticos (sin contar los fijos)
      total_min / total_max           nº total contando los fijos ('max_total' = alias antiguo)
      amplios_max                     máx. de etiquetas amplias (ERROR)          · cuentan fijos
      nicho_min                       mín. recomendado de etiquetas de nicho (AVISO) · cuentan fijos
      rotacion_ultimos                nº de registros recientes con los que no repetir conjunto
    Los tamaños salen de hashtags.json (ESTIMADOS); sin tamaño conocido = aviso.
    Devuelve (errores, avisos, temáticos normalizados).
    """
    errores, avisos = [], []
    reglas = proyecto.plataforma(pid).get("hashtags") or {}
    tem_raw = bloque.get("hashtags") or []
    if isinstance(tem_raw, str):
        tem_raw = tem_raw.split()
    tem = [normalizar_hashtag(t) for t in tem_raw if str(t).strip()]
    fijos = proyecto.fijos(pid)
    malos = [t for t in tem if not RE_HASHTAG.fullmatch(t) or t != t.lower()]
    if malos:
        errores.append(f"hashtags mal formados (sin espacios, en minúsculas): {' '.join(malos)}")
    tem = [t for t in tem if t not in fijos]
    if len(set(tem)) != len(tem):
        errores.append("hashtags temáticos repetidos.")
        tem = list(dict.fromkeys(tem))

    mn, mx = reglas.get("tematicos_min", 0), reglas.get("tematicos_max", 30)
    if not (mn <= len(tem) <= mx):
        errores.append(f"{len(tem)} hashtags temáticos; deben ser entre {mn} y {mx} "
                       f"(los fijos {' '.join(fijos) or '(ninguno)'} ya se añaden solos).")

    finales = hashtags_finales(proyecto, pid, tem)
    tmin = reglas.get("total_min")
    tmax = reglas.get("total_max") or reglas.get("max_total")
    if (tmin and len(finales) < tmin) or (tmax and len(finales) > tmax):
        rango = f"entre {tmin} y {tmax}" if tmin and tmax else (f"mín. {tmin}" if tmin else f"máx. {tmax}")
        errores.append(f"{len(finales)} hashtags en total contando los fijos ({' '.join(finales)}); "
                       f"deben ser {rango}.")

    # --- tamaños (estimados en hashtags.json) ---
    usa_tamanos = "amplios_max" in reglas or "nicho_min" in reglas
    fuera = [t for t in tem if pool and t not in pool]
    if fuera:
        avisos.append(f"hashtags fuera del banco temático (se aceptan"
                      + ("; tamaño desconocido, verifícalo en el buscador de IG" if usa_tamanos else "")
                      + f"): {' '.join(fuera)}")
    if usa_tamanos:
        tam = {t: proyecto.tamano_hashtag(t) for t in finales}
        sin_tam = [t for t in finales if tam[t] is None and t not in fuera]
        if sin_tam:
            avisos.append(f"hashtags sin tamaño conocido en hashtags.json: {' '.join(sin_tam)}")
        amplios = [t for t in finales if tam[t] == "amplio"]
        if "amplios_max" in reglas and len(amplios) > reglas["amplios_max"]:
            errores.append(f"{len(amplios)} hashtags amplios ({' '.join(amplios)}); máx. {reglas['amplios_max']}. "
                           "Cambia alguno por uno de nicho o medio.")
        nichos = [t for t in finales if tam[t] == "nicho"]
        nmin = reglas.get("nicho_min")
        if nmin and len(nichos) < nmin:
            if nichos:
                avisos.append(f"solo {len(nichos)} de nicho contando los fijos ({' '.join(nichos)}); "
                              f"recomendado mín. {nmin}: añade o cambia uno por otro de nicho.")
            else:
                avisos.append(f"ninguna etiqueta de nicho (recomendado mín. {nmin}): las de nicho son las que posicionan.")

    # --- rotación: no repetir el mismo conjunto de temáticos ---
    conjunto = frozenset(tem)
    if conjunto:
        en_tanda = sets_tanda.setdefault(pid, {})
        if conjunto in en_tanda and en_tanda[conjunto].lower() != clip.lower():
            avisos.append(f"mismo conjunto de temáticos que {en_tanda[conjunto]} en esta tanda: rótalos.")
        en_tanda.setdefault(conjunto, clip)
        n = int(reglas.get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0)
        previos = [(c, s) for c, s in recientes.get(pid, []) if c.lower() != clip.lower()][-n:] if n else []
        repetido = next((c for c, s in reversed(previos) if s == conjunto), None)
        if repetido:
            avisos.append(f"mismo conjunto de temáticos que {repetido} (entre los {n} últimos registrados "
                          f"en {proyecto.nombre_plataforma(pid)}): rótalos.")
    return errores, avisos, tem

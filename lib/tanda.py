"""
TANDA = el JSON de trabajo de una orden de copys. Las REGLAS no van aquí: están en
`copys.py brief --proyecto <id>` (un solo sitio).

1) `copys.py pendientes` crea el esqueleto: un bloque por pieza (Reel = MP4 o
   carrusel = carpeta con carrusel.json) con su contexto mínimo y huecos por cada
   plataforma activa que admita ese formato. Prerrellena lo que puede: `tema` (título
   del corte o tema del carrusel), `extra.oferta` (sugerida cruzando ofertas[].temas
   con la categoría y lo que se dice) y `hashtags_temas` (temas del banco que encajan).
2) El subagente `copy` (LLM) revisa lo sugerido y rellena el resto: campos propios
   (objetivo, pilar) y, por plataforma, copy (+ título si aplica). Hashtags: deja
   `hashtags` vacío y `registrar` elige un conjunto válido y rotado de `hashtags_temas`;
   solo se escriben para forzar alguno (si van menos de los mínimos, se completan).
3) `copys.py registrar --entrada <tanda> [--simular] [--planificar] [--estricto]` valida
   todo (incluida la auditoría) y, si está bien, escribe Excel + .txt.

Esquema de cada pieza:
{
  "clip": "01_nombre.mp4",           # Reel: nombre del MP4 · carrusel: nombre de la carpeta
  "formato": "reel",                 # "reel" | "carrusel" (sin clave = reel, tandas antiguas)
  "ruta": "C:\\...\\01_nombre.mp4",    # MP4 o carpeta del carrusel
  "contexto": {...},                 # solo lectura, lo pone el script
  "tema": "",                        # resumen corto (columna Tema)
  "extra": {"oferta": "", "objetivo": "", "pilar": ""},   # campos_extra del proyecto
  "hashtags_temas": ["ventas"],      # temas del banco para los hashtags automáticos
  "plataformas": {                   # solo las que le faltan y admiten el formato
    "instagram": {"copy": "", "hashtags": []},
    "youtube":   {"titulo": "", "copy": "", "hashtags": []}
  }
}
"""
from __future__ import annotations

import datetime as dt
import itertools
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


def esqueleto(proyecto, piezas: list[dict]) -> dict:
    """piezas: [{"ruta": Path, "contexto": dict, "plataformas": [pid], "formato": "reel"|"carrusel",
                 "tema": str (opcional), "extra": {campo: valor} (opcional)}]"""
    clips = []
    for pz in piezas:
        ctx = pz.get("contexto") or {}
        extra = {c["id"]: (pz.get("extra") or {}).get(c["id"]) or "" for c in proyecto.campos_extra()}
        if "oferta" in extra and not extra["oferta"]:
            extra["oferta"] = sugerir_oferta(proyecto, ctx)
        clips.append({
            "clip": Path(pz["ruta"]).name,
            "formato": pz.get("formato") or "reel",
            "ruta": str(pz["ruta"]),
            "contexto": ctx,
            "tema": pz.get("tema") or str(ctx.get("titulo") or ctx.get("tema") or ""),
            "extra": extra,
            "hashtags_temas": sugerir_temas(proyecto, ctx),
            "plataformas": {p: hueco_plataforma(proyecto.conf_formato(p, pz.get("formato") or "reel"))
                            for p in pz["plataformas"]},
        })
    return {
        "proyecto": proyecto.id,
        "creada": dt.datetime.now().isoformat(timespec="seconds"),
        "instrucciones": f"Reglas y formato: copys.py brief --proyecto {proyecto.id}. Después: copys.py registrar "
                         "--entrada <esta tanda> --simular y, limpio, --planificar.",
        "clips": clips,
    }


# ---------------------------------------------------------------- sugerencias
_STOP = {"de", "del", "la", "el", "los", "las", "y", "en", "sin", "con", "por", "para", "a", "un", "una"}


def _coincide(palabra: str, token: str) -> bool:
    """Misma palabra, singular/plural o la misma raíz larga (≥ 6 letras en común)."""
    if palabra == token or palabra + "s" == token or token + "s" == palabra:
        return True
    if palabra + "es" == token or token + "es" == palabra:
        return True
    n = 0
    for a, b in zip(palabra, token):
        if a != b:
            break
        n += 1
    return n >= 6


def _aparece(termino: str, texto: str, tokens: set[str]) -> bool:
    """`termino` (normalizado) en `texto` (normalizado): frase exacta o todas sus palabras con contenido."""
    if not termino or not texto:
        return False
    if f" {termino} " in f" {texto} ":
        return True
    palabras = [w for w in termino.split() if w not in _STOP and len(w) >= 4]
    return bool(palabras) and all(any(_coincide(w, t) for t in tokens) for w in palabras)


def _textos(ctx: dict) -> tuple[str, str, str, set[str], set[str]]:
    cat = normalizar(str(ctx.get("category") or ""))
    cab = normalizar(" ".join(str(ctx.get(k) or "") for k in ("titulo", "frase_viral", "gancho_texto",
                                                               "tema", "gancho_slide1")))
    cuerpo = normalizar(str(ctx.get("transcripcion") or ""))
    return cat, cab, cuerpo, set(cab.split()), set(cuerpo.split())


def sugerir_oferta(proyecto, ctx: dict) -> str:
    """Id de la oferta cuyos `temas` más encajan con la categoría, el título/frase y la transcripción
    del clip ("" si no hay una clara: lo decide el subagente). Solo una sugerencia."""
    ofertas = [o for o in (proyecto.ofertas.get("ofertas") or []) if o.get("id")]
    if not ofertas or not ctx or ctx.get("aviso") and not ctx.get("transcripcion"):
        return ""
    cat, cab, cuerpo, t_cab, t_cuerpo = _textos(ctx)
    puntos = []
    for o in ofertas:
        sc, distintos = 0, 0
        for t in o.get("temas") or []:
            tn = normalizar(str(t))
            hit = 0
            if tn and tn == cat:
                hit += 1
            if _aparece(tn, cab, t_cab):
                hit += 2
            elif _aparece(tn, cuerpo, t_cuerpo):
                hit += 1
            sc += hit
            distintos += bool(hit)
        puntos.append((sc, distintos, o["id"]))
    puntos.sort(key=lambda x: (-x[0], -x[1]))
    mejor = puntos[0]
    segundo = puntos[1][0] if len(puntos) > 1 else -1
    return mejor[2] if mejor[0] >= 3 and mejor[1] >= 2 and mejor[0] > segundo else ""


def sugerir_temas(proyecto, ctx: dict, maximo: int = 2) -> list[str]:
    """Temas del banco de hashtags que encajan con el clip (categoría y lo que se dice)."""
    if not ctx:
        return []
    cat, cab, cuerpo, t_cab, t_cuerpo = _textos(ctx)
    puntos = []
    for i, tema in enumerate(proyecto.banco_por_tamano()):
        partes = [normalizar(x) for x in tema.split("_") if x]
        nombre = " ".join(partes)
        sc = 2 if nombre == cat or (partes and partes[0] == cat) else 0
        if any(_aparece(x, cab, t_cab) for x in partes):
            sc += 2
        elif any(_aparece(x, cuerpo, t_cuerpo) for x in partes):
            sc += 1
        if sc >= 2:
            puntos.append((-sc, i, tema))
    return [t for _, _, t in sorted(puntos)[:maximo]]


_VACIAS = {"para", "porque", "como", "cuando", "donde", "pero", "esto", "esta", "este", "estos", "estas",
           "tiene", "tienes", "hace", "hacer", "sobre", "entre", "desde", "hasta", "todo", "toda", "todos",
           "nada", "algo", "solo", "cada", "mucho", "menos", "eres"}


def repite_gancho(copy: str, gancho: str, n: int = 125) -> bool:
    """True si los primeros `n` caracteres del caption recogen el gancho de la slide 1.

    Se comparan las palabras con contenido (≥ 4 letras) del gancho: tiene que salir al
    menos la mitad (vale la misma raíz: «objeción»/«objeciones»).
    """
    clave = [w for w in normalizar(gancho).split() if len(w) >= 4 and w not in _VACIAS]
    if not clave:
        return True
    inicio = normalizar((copy or "")[:n]).split()

    def sale(w: str) -> bool:
        raiz = w[:5] if len(w) >= 6 else w
        return any(x == w or (len(x) >= 4 and x.startswith(raiz)) for x in inicio)
    return sum(sale(w) for w in clave) * 2 >= len(clave)


def hashtags_finales(proyecto, pid: str, tematicos: list[str]) -> list[str]:
    """Fijos de la plataforma + temáticos, sin duplicados y en ese orden."""
    out = []
    for t in proyecto.fijos(pid) + [normalizar_hashtag(t) for t in tematicos]:
        if t and t not in out:
            out.append(t)
    return out


def elegir_hashtags(proyecto, pid: str, temas: list[str], forzados: list[str],
                    evitar: list[frozenset[str]], historial: list[frozenset[str]]) -> tuple[list[str] | None, str]:
    """Conjunto de temáticos VÁLIDO y ROTADO del banco, de los `temas` dados (más los `forzados`).

    Cumple las cuotas de plataformas.<p>.hashtags (temáticos, total con los fijos, amplios_max y,
    si se puede, nicho_min), no repite ningún conjunto de `evitar` (los últimos registrados y los
    de la misma tanda) si hay alternativa y, a igualdad, usa lo que menos ha salido en `historial`
    (lo más reciente al final), cubre todos los temas y mezcla tamaños. Determinista.
    Devuelve (temáticos, "") o (None, motivo).
    """
    banco = proyecto.banco_por_tamano()
    temas = [temas] if isinstance(temas, str) else [str(t) for t in temas or [] if str(t).strip()]
    raros = [t for t in temas if t not in banco]
    if raros:
        return None, f"hashtags_temas desconocidos: {', '.join(raros)} (temas del banco: {', '.join(banco)})"
    if not temas:
        return None, "hashtags_temas vacío"
    reglas = proyecto.reglas_hashtags(pid)
    fijos = proyecto.fijos(pid)
    forz = list(dict.fromkeys(t for t in (normalizar_hashtag(x) for x in forzados or []) if t and t not in fijos))
    tam = proyecto.tamano_hashtag
    # candidatos: por tamaño y alternando entre los temas pedidos (orden estable = el del banco)
    cands, de_tema = [], {}
    for t_tam in ("nicho", "medio", "amplio", "sin_tamano"):
        listas = [banco[t][t_tam] for t in temas]
        for i in range(max((len(l) for l in listas), default=0)):
            for t, l in zip(temas, listas):
                if i < len(l):
                    de_tema.setdefault(l[i], set()).add(t)
                    if l[i] not in cands and l[i] not in fijos and l[i] not in forz:
                        cands.append(l[i])
    for t in temas:  # una etiqueta que sale en varios temas los cubre todos
        for g in banco[t].values():
            for x in g:
                de_tema.setdefault(x, set()).add(t)
    tmin = int(reglas.get("tematicos_min", 1) or 0)
    tmax = int(reglas.get("tematicos_max", max(tmin, 3)))
    nf = len(fijos)
    tot_min, tot_max = reglas.get("total_min"), reglas.get("total_max") or reglas.get("max_total")
    lo = max(tmin, (tot_min - nf) if tot_min else 0, len(forz), 1)
    hi = min(tmax, (tot_max - nf) if tot_max else tmax)
    if lo > hi:
        return None, f"las cuotas de {pid} no se pueden cumplir con {len(forz)} forzado(s)"
    ideal = min(hi, max(lo, (tmin + tmax + 1) // 2))
    tamanos = sorted(range(lo, hi + 1), key=lambda n: (abs(n - ideal), n))
    amax, nmin = reglas.get("amplios_max"), int(reglas.get("nicho_min") or 0)
    hay_medio = any(tam(x) == "medio" for x in cands)
    ventana = max(2 * int(reglas.get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0), 6)
    peso: dict[str, int] = {}
    for k, conj in enumerate(reversed(historial or []), start=1):
        for x in conj:
            peso[x] = peso.get(x, 0) + max(0, ventana - k + 1)
    evitar = set(evitar or [])
    idx = {x: i for i, x in enumerate(cands)}
    mejor = None
    for n in tamanos:
        k = n - len(forz)
        if k < 0 or k > len(cands):
            continue
        for combo in itertools.combinations(cands, k):
            conj = forz + list(combo)
            finales = fijos + conj
            amplios = sum(tam(x) == "amplio" for x in finales)
            if amax is not None and amplios > amax:
                continue
            nichos = sum(tam(x) == "nicho" for x in finales)
            cubiertos = set().union(*(de_tema.get(x, set()) for x in conj)) if conj else set()
            clave = (max(0, nmin - nichos), frozenset(conj) in evitar, sum(peso.get(x, 0) for x in conj),
                     -len(cubiertos & set(temas)), int(hay_medio and not any(tam(x) == "medio" for x in conj)),
                     abs(n - ideal), sum(idx.get(x, 0) for x in combo))
            if mejor is None or clave < mejor[0]:
                mejor = (clave, conj)
        if mejor is not None and mejor[0][:2] == (0, False):
            break  # el tamaño ideal ya da un conjunto que cumple todo
    if mejor is None:
        return None, (f"no hay un conjunto válido con los temas {', '.join(temas)} "
                      f"({proyecto.texto_reglas_hashtags(pid)}): añade temas o escribe los hashtags")
    orden = {"nicho": 0, "medio": 1, "amplio": 2}
    conj = forz + sorted(mejor[1][len(forz):], key=lambda x: (orden.get(tam(x) or "", 3), idx.get(x, 0)))
    return conj, ""


def tematicos_de(proyecto, pid: str, hashtags) -> frozenset[str]:
    """Conjunto de temáticos (sin los fijos actuales de la plataforma) de una lista o texto de hashtags."""
    if isinstance(hashtags, str):
        hashtags = RE_HASHTAG.findall(hashtags)
    fijos = set(proyecto.fijos(pid))
    return frozenset(t for t in (normalizar_hashtag(str(x)) for x in hashtags or []) if t and t not in fijos)


def texto_para_pegar(proyecto, pid: str, bloque: dict, formato: str = "reel") -> str:
    conf = proyecto.conf_formato(pid, formato) if proyecto.admite(pid, formato) else proyecto.plataforma(pid)
    tags = " ".join(hashtags_finales(proyecto, pid, bloque.get("hashtags") or []))
    plantilla = conf.get("formato_texto") or "{copy}\n\n{hashtags}"
    return plantilla.format(copy=(bloque.get("copy") or "").strip(), hashtags=tags,
                            titulo=(bloque.get("titulo") or "").strip()).strip()


def validar(proyecto, tanda: dict, copys_existentes: dict[str, dict[str, str]],
            recientes: dict[str, list[tuple[str, frozenset[str]]]] | None = None
            ) -> tuple[list[str], list[str], list[str]]:
    """Devuelve (errores, avisos, avisos_de_estilo). Con errores no se registra nada.

    avisos_de_estilo ⊂ avisos: los de la auditoría que no son literales del clip
    (`registrar --estricto` no escribe si queda alguno).
    copys_existentes: {plataforma: {copy normalizado: clip}} ya registrados, para no repetir.
    recientes: {plataforma: [(clip, temáticos), ...]} registrados, en orden de alta, para la
               rotación de hashtags (se miran los últimos `rotacion_ultimos`).
    Con `hashtags_temas` (en la pieza o en el bloque de la plataforma) y `hashtags` vacío (o con
    menos de los mínimos), elige los temáticos (elegir_hashtags) y los deja en el bloque.
    """
    errores, avisos, estilo = [], [], []
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
        formato = c.get("formato") or "reel"
        if formato not in config.FORMATOS:
            errores.append(f"[{et}] formato '{formato}' desconocido (usa {', '.join(config.FORMATOS)}).")
            continue
        if not (c.get("tema") or "").strip():
            errores.append(f"[{et}] falta 'tema'.")
        ruta = c.get("ruta")
        if not ruta or not Path(ruta).exists():
            que = "la carpeta del carrusel" if formato == "carrusel" else "el MP4"
            avisos.append(f"[{et}] {que} no está en '{ruta}': se registra igual pero sin .txt ni enlace.")

        for campo in proyecto.campos_extra():
            extra = c.setdefault("extra", {})
            val = str(extra.get(campo["id"]) or "").strip()
            permitidos = proyecto.valores_campo(campo)
            if campo.get("obligatorio") and not val:
                errores.append(f"[{et}] falta '{campo['id']}'"
                               + (f" (valores: {', '.join(permitidos)})" if permitidos else "") + ".")
            elif val and permitidos and val not in permitidos:
                canon = proyecto.canon_valor(campo, val) if isinstance(campo.get("valores"), list) else None
                if canon:
                    extra[campo["id"]] = canon  # 'Interacción' → 'interaccion'
                else:
                    errores.append(f"[{et}] '{campo['id']}' = '{val}' no es válido. Usa: {', '.join(permitidos)}.")

        plats = c.get("plataformas") or {}
        if not plats:
            errores.append(f"[{et}] no tiene ninguna plataforma.")
        for pid, b in plats.items():
            ep = f"[{et} · {pid}]"
            if pid not in (proyecto.conf.get("plataformas") or {}):
                errores.append(f"{ep} plataforma no definida en el proyecto.")
                continue
            if not proyecto.admite(pid, formato):
                errores.append(f"{ep} {proyecto.nombre_plataforma(pid)} no admite {config.FORMATOS[formato].lower()} "
                               f"(proyecto.json → plataformas.{pid}.formatos).")
                continue
            if not proyecto.plataforma(pid).get("activa"):
                avisos.append(f"{ep} la plataforma no está activa en el proyecto (se registra igual).")
            conf = proyecto.conf_formato(pid, formato)
            copy = (b.get("copy") or "").strip()

            # --- título (YouTube) ---
            if conf.get("requiere_titulo"):
                tit = (b.get("titulo") or "").strip()
                if not tit:
                    errores.append(f"{ep} falta 'titulo'.")
                elif conf.get("titulo_max") and len(tit) > conf["titulo_max"]:
                    errores.append(f"{ep} título de {len(tit)} caracteres (máx. {conf['titulo_max']}).")
                for frag in auditoria.palabras_prohibidas(tit, proyecto.palabras_prohibidas):
                    errores.append(f"{ep} el título lleva la palabra prohibida «{frag}» (identidad del proyecto).")

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
                avisos.append(f"{ep} copy de {len(copy)} caracteres (recomendado {rec[0]}–{rec[1]}"
                              + (" en un carrusel" if formato == "carrusel" else "") + ").")
            if formato == "carrusel":
                g1 = (c.get("contexto") or {}).get("gancho_slide1") or ""
                n125 = int(conf.get("gancho_max") or 125)
                if g1 and not repite_gancho(copy, g1, n125):
                    avisos.append(f"{ep} el caption no repite el gancho de la slide 1 («{g1[:80]}») "
                                  f"en sus primeros {n125} caracteres.")

            # --- auditoría (lib/auditoria.py · referencias/auditoria_copy.md) ---
            for h in auditoria.auditar(copy, conf, c.get("contexto"), proyecto.nombre_plataforma(pid),
                                       identidad=proyecto.identidad):
                if h.nivel == "error":
                    errores.append(f"{ep} {h.mensaje}")
                elif h.nivel == "aviso":
                    avisos.append(f"{ep} estilo: {h.mensaje}")
                    estilo.append(avisos[-1])
                # "literal": frase literal del clip → se permite, no se avisa

            # --- hashtags (automáticos si vienen hashtags_temas y faltan) ---
            temas = b.get("hashtags_temas") or c.get("hashtags_temas")
            if temas:
                actuales = b.get("hashtags") or []
                if isinstance(actuales, str):
                    actuales = actuales.split()
                reglas = proyecto.reglas_hashtags(pid)
                nf = len(proyecto.fijos(pid))
                minimo = max(int(reglas.get("tematicos_min", 1) or 0),
                             (reglas["total_min"] - nf) if reglas.get("total_min") else 0, 1)
                forz = [t for t in actuales if normalizar_hashtag(str(t)) not in proyecto.fijos(pid)]
                if len(forz) < minimo:
                    n = int(reglas.get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0)
                    previos = [st for cl, st in recientes.get(pid, []) if cl.lower() != et.lower()]
                    en_tanda = list(sets_tanda.get(pid, {}))
                    elegidos, motivo = elegir_hashtags(proyecto, pid, temas, forz,
                                                       (previos[-n:] if n else []) + en_tanda, previos + en_tanda)
                    if elegidos is None:
                        errores.append(f"{ep} hashtags automáticos: {motivo}.")
                    else:
                        b["hashtags"] = elegidos
            errores_h, avisos_h, tem = _validar_hashtags(proyecto, pid, b, pool, et, recientes, sets_tanda)
            errores += [f"{ep} {e}" for e in errores_h]
            avisos += [f"{ep} {a}" for a in avisos_h]
            b["hashtags"] = tem  # normalizados

            # --- longitud total ---
            texto = texto_para_pegar(proyecto, pid, b, formato)
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

    return errores, avisos, estilo


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

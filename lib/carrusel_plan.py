"""
CARRUSELES · plan.json: carga, normalización y validación.

El plan lo escribe el subagente (LLM) a partir de una fuente (clip/vídeo,
artículo de TheTextos o tema de Sergio). Aquí se comprueba la ESTRUCTURA y el
ESTILO del texto antes de renderizar. El ajuste del texto al lienzo (si cabe o
no) lo comprueba `lib/carrusel_render.py`.

Niveles:
  ERROR  bloquea el render (nº de slides fuera de 2-10, primera ≠ gancho o
         última ≠ cierre, campos obligatorios vacíos, valores fuera de su lista,
         marcado `**` sin cerrar, emojis por encima de `emojis_max`).
  AVISO  no bloquea (menos de 4 slides, textos por encima de las longitudes
         orientativas, más de una palabra destacada, mayúsculas, primera
         persona, fórmula poco afín al objetivo...).

Esquema (resumen; detalle en README.md):
  tipo, proyecto, slug, tema, formula, objetivo, pilar,
  fuente {tipo, ruta, credito}, slides [{n, rol, titulo, texto, ...}],
  portada_fondo y portada_texto ("abajo" | "centro") (opcionales)
Extras opcionales por slide: `numero` (valor: número a mostrar o false),
`puntos` (cierre: lista-resumen) y `peticion` (cierre: la única petición).

Rutas relativas (`fuente.ruta`, `portada_fondo.ruta`): se buscan junto al plan,
en TheHistoria y en PruebasIA (p. ej. `_Historico/<id>/<video>/...`).
`validar_material` comprueba que la portada sea material DEL PROYECTO (nada del
banco común salvo política `banco_comun`, nada de internet ni de otro proyecto).
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path

import config

FORMULAS = ("IG5_lista", "IG6_antes_despues", "IG7_mitos", "IG8_metodo")
OBJETIVOS = ("guardados", "compartidos", "comentarios", "seguidores")
PILARES = ("educativo", "historia", "interaccion", "promocion")
FUENTE_TIPOS = ("clip", "video", "articulo", "tema")
ROLES = ("gancho", "valor", "cierre")
PORTADA_TEXTO = ("abajo", "centro")       # dónde va el texto del gancho con foto

# Objetivo(s) para los que rinde cada fórmula (si no casa, AVISO).
OBJETIVOS_POR_FORMULA = {
    "IG5_lista": ("guardados",),
    "IG6_antes_despues": ("guardados", "seguidores"),
    "IG7_mitos": ("compartidos",),
    "IG8_metodo": ("guardados",),
}

IMAGEN_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Orden de claves del carrusel.json (contrato con TheCopy).
ORDEN_CLAVES = ("tipo", "proyecto", "slug", "tema", "formula", "objetivo", "pilar",
                "fuente", "slides")
ORDEN_SLIDE = ("n", "rol", "titulo", "texto")


@dataclass
class Hallazgo:
    nivel: str             # "ERROR" | "AVISO"
    mensaje: str
    slide: int | None = None

    def __str__(self) -> str:
        donde = f"slide {self.slide}: " if self.slide else ""
        return f"{self.nivel} · {donde}{self.mensaje}"


# ------------------------------------------------------------------ texto
MARCA = "**"

# Pictogramas emoji (rangos propios): símbolos y pictogramas del plano 1,
# símbolos varios y dingbats, flechas/figuras del bloque 2B00, relojes,
# selector de variación emoji y tecla. Las flechas tipográficas (→) no cuentan.
_EMOJI_BASE = (
    "\U0001F000-\U0001FAFF"
    "☀-➿"
    "⬀-⯿"
    "⌚⌛⌨⏏⏩-⏳⏸-⏺"
    "〰〽㊗㊙"
)
_RE_EMOJI = re.compile(
    rf"[{_EMOJI_BASE}]️?(?:‍[{_EMOJI_BASE}]️?)*|[0-9#*]?️?⃣|️")

_RE_MINUSCULA_TRAS_PUNTO = re.compile(
    r"[.!?…][»\"'’”)\]]*\s+[¿¡«\"'“(\[]*([a-záéíóúüñ])")
_RE_MAYUSCULAS = re.compile(r"\b[A-ZÁÉÍÓÚÜÑ]{4,}\b")
_RE_PRIMERA_PERSONA = re.compile(r"(?i)\b(yo|mi|mis|mí|me|conmigo)\b")
_RE_CITAS = re.compile(r"«[^»]*»|\"[^\"]*\"|“[^”]*”")


def quitar_marcas(s: str) -> str:
    return (s or "").replace(MARCA, "")


def contar_destacados(s: str) -> int:
    return (s or "").count(MARCA) // 2


def contar_palabras(s: str) -> int:
    """Palabras «de verdad» (con alguna letra o cifra), sin el marcado."""
    return sum(1 for t in quitar_marcas(s).split() if re.search(r"[^\W_]", t))


def contar_emojis(s: str) -> int:
    return len(_RE_EMOJI.findall(s or ""))


def slugify(s: str, maxlen: int = 48) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "carrusel"


def textos_de_slide(slide: dict) -> list[tuple[str, str]]:
    """(campo, texto) de todo lo que se pinta en la slide (con marcado)."""
    out = []
    for campo in ("titulo", "texto", "peticion"):
        v = slide.get(campo)
        if isinstance(v, str) and v.strip():
            out.append((campo, v))
    for i, p in enumerate(slide.get("puntos") or [], 1):
        if isinstance(p, str) and p.strip():
            out.append((f"puntos[{i}]", p))
    return out


def _avisos_de_escritura(campo: str, texto: str) -> list[str]:
    """Sentence case, signos de apertura, mayúsculas sostenidas, 1.ª persona."""
    t = quitar_marcas(texto).strip()
    out = []
    primero = re.search(r"[^\W_]", t)
    if primero and primero.group().isalpha() and primero.group().islower():
        out.append(f"`{campo}` empieza en minúscula («{t[:30]}»).")
    for m in _RE_MINUSCULA_TRAS_PUNTO.finditer(t):
        out.append(f"`{campo}`: minúscula tras punto («…{t[max(0, m.start()):m.end() + 12]}»).")
        break
    for m in _RE_MAYUSCULAS.finditer(t):
        out.append(f"`{campo}`: «{m.group()}» en mayúsculas sostenidas (usa sentence case).")
        break
    if t.count("?") > t.count("¿"):
        out.append(f"`{campo}`: falta el signo de apertura «¿».")
    if t.count("!") > t.count("¡"):
        out.append(f"`{campo}`: falta el signo de apertura «¡».")
    sin_citas = _RE_CITAS.sub(" ", t)
    m = _RE_PRIMERA_PERSONA.search(sin_citas)
    if m:
        out.append(f"`{campo}`: primera persona («{m.group()}»). El perfil habla de tú, "
                   f"no como si fuera el autor de la fuente.")
    return out


# ------------------------------------------------------------------ plan
def _vacio(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def resolver_ruta(ruta: str, plan_dir: Path | None) -> Path:
    p = Path(ruta)
    if p.is_absolute():
        return p
    for base in (plan_dir, config.PROJECT_ROOT, config.PRUEBAS_IA):
        if base is not None and (base / p).exists():
            return base / p
    return (plan_dir or config.PROJECT_ROOT) / p


def normalizar_portada(valor, plan_dir: Path | None) -> dict | None:
    """`portada_fondo` admite "ruta" o {"ruta", "segundo", "foco_y"}."""
    if _vacio(valor):
        return None
    if isinstance(valor, str):
        valor = {"ruta": valor}
    if not isinstance(valor, dict):
        return {"_error": "debe ser una ruta o un objeto {ruta, segundo, foco_y}"}
    out = dict(valor)
    if _vacio(out.get("ruta")):
        return {"_error": "falta `ruta`"}
    out["_path"] = resolver_ruta(str(out["ruta"]), plan_dir)
    return out


def validar_plan(plan, estilo: dict, plan_dir: Path | None = None
                 ) -> tuple[dict, list[Hallazgo]]:
    """Devuelve (plan normalizado, hallazgos). No pinta nada ni toca disco."""
    H: list[Hallazgo] = []

    def err(msg, slide=None):
        H.append(Hallazgo("ERROR", msg, slide))

    def aviso(msg, slide=None):
        H.append(Hallazgo("AVISO", msg, slide))

    if not isinstance(plan, dict):
        err("el plan debe ser un objeto JSON.")
        return {}, H
    p = copy.deepcopy(plan)
    p.pop("creado", None)
    lon = estilo.get("longitudes") or {}

    # --- cabecera
    if not _vacio(p.get("tipo")) and p["tipo"] != "carrusel":
        err(f"`tipo` = «{p['tipo']}»; aquí solo vale «carrusel».")
    p["tipo"] = "carrusel"
    if _vacio(p.get("proyecto")):
        p["proyecto"] = estilo.get("proyecto") or ""
        if p["proyecto"]:
            aviso(f"sin `proyecto`: uso «{p['proyecto']}» (el de estilo.json).")
        else:
            err("falta `proyecto`.")
    if _vacio(p.get("tema")):
        err("falta `tema`.")
    slug_ok = slugify(p.get("slug") or p.get("tema") or "")
    if not _vacio(p.get("slug")) and slug_ok != p["slug"]:
        aviso(f"`slug` normalizado a «{slug_ok}» (solo a-z, 0-9 y guiones).")
    p["slug"] = slug_ok

    for campo, validos in (("formula", FORMULAS), ("objetivo", OBJETIVOS), ("pilar", PILARES)):
        v = p.get(campo)
        if _vacio(v):
            err(f"falta `{campo}` ({' | '.join(validos)}).")
        elif v not in validos:
            err(f"`{campo}` = «{v}» no vale. Opciones: {' | '.join(validos)}.")
    f, o = p.get("formula"), p.get("objetivo")
    if f in OBJETIVOS_POR_FORMULA and o in OBJETIVOS and o not in OBJETIVOS_POR_FORMULA[f]:
        aviso(f"{f} rinde para {' / '.join(OBJETIVOS_POR_FORMULA[f])}, no para «{o}». "
              f"Revisa la fórmula o el objetivo.")

    # --- fuente
    fuente = p.get("fuente")
    if not isinstance(fuente, dict):
        err("falta `fuente` {tipo, ruta, credito}.")
        p["fuente"] = fuente = {}
    ft = fuente.get("tipo")
    if _vacio(ft):
        err(f"falta `fuente.tipo` ({' | '.join(FUENTE_TIPOS)}).")
    elif ft not in FUENTE_TIPOS:
        err(f"`fuente.tipo` = «{ft}» no vale. Opciones: {' | '.join(FUENTE_TIPOS)}.")
    fuente.setdefault("ruta", "")
    fuente.setdefault("credito", "")
    if ft in ("clip", "video", "articulo"):
        if _vacio(fuente.get("ruta")):
            err("falta `fuente.ruta` (de dónde sale el contenido).")
        elif not resolver_ruta(fuente["ruta"], plan_dir).exists():
            aviso(f"`fuente.ruta` no existe en disco: {fuente['ruta']}")
    if ft in ("clip", "video") and _vacio(fuente.get("credito")):
        aviso("fuente de vídeo sin `fuente.credito` (p. ej. «Ideas de <autor>»; ver reglas.md del proyecto).")

    # --- portada opcional
    pt = p.get("portada_texto")
    if not _vacio(pt) and pt not in PORTADA_TEXTO:
        err(f"`portada_texto` = «{pt}» no vale ({' | '.join(PORTADA_TEXTO)}).", 1)
    if "portada_fondo" in p:
        port = normalizar_portada(p.get("portada_fondo"), plan_dir)
        if port and "_error" in port:
            err(f"`portada_fondo`: {port['_error']}.", 1)
        elif port:
            path: Path = port["_path"]
            ext = path.suffix.lower()
            if not path.exists():
                err(f"`portada_fondo` no existe: {port['ruta']}", 1)
            elif ext not in IMAGEN_EXTS and ext not in config.VIDEO_EXTS:
                err(f"`portada_fondo` debe ser imagen o vídeo (extensión «{ext}»).", 1)
            seg = port.get("segundo", 0)
            if not isinstance(seg, (int, float)) or seg < 0:
                err("`portada_fondo.segundo` debe ser un número ≥ 0.", 1)
            fy = port.get("foco_y", estilo.get("portada_foco_y", 0.5))
            if not isinstance(fy, (int, float)) or not 0 <= fy <= 1:
                err("`portada_fondo.foco_y` debe estar entre 0 y 1.", 1)

    # --- slides
    slides = p.get("slides")
    if not isinstance(slides, list) or not slides:
        err("faltan las `slides`.")
        p["slides"] = []
        return p, H
    total = len(slides)
    if total < config.CARRUSEL_MIN_SLIDES or total > config.CARRUSEL_MAX_SLIDES:
        err(f"{total} slides: un carrusel lleva entre {config.CARRUSEL_MIN_SLIDES} y "
            f"{config.CARRUSEL_MAX_SLIDES}.")
    elif total < 4:
        aviso(f"solo {total} slides: con menos de 4 suele funcionar mejor una imagen suelta.")

    emojis_max = int(estilo.get("emojis_max", 0))
    emojis_total = 0
    for i, s in enumerate(slides, 1):
        if not isinstance(s, dict):
            err("la slide debe ser un objeto JSON.", i)
            continue
        if "n" in s and s["n"] != i:
            err(f"`n` = {s['n']}, pero ocupa la posición {i} (las slides van en orden).", i)
        s["n"] = i
        rol = s.get("rol")
        if rol not in ROLES:
            err(f"`rol` = «{rol}» no vale ({' | '.join(ROLES)}).", i)
        esperado = "gancho" if i == 1 else "cierre" if i == total else "valor"
        if rol in ROLES and rol != esperado:
            err(f"la slide {i} debe ser «{esperado}» (es «{rol}"
                f"»): la 1.ª es el gancho, la última el cierre y el resto, valor.", i)
        s.setdefault("texto", "")

        if _vacio(s.get("titulo")):
            err("falta `titulo`.", i)
        if rol == "valor" and _vacio(s.get("texto")):
            err("falta `texto` (una idea con su explicación).", i)
        puntos = s.get("puntos")
        if puntos is not None:
            if rol != "cierre":
                aviso("`puntos` solo se pinta en la slide de cierre; aquí se ignora.", i)
            elif not isinstance(puntos, list) or any(_vacio(x) or not isinstance(x, str)
                                                    for x in puntos):
                err("`puntos` debe ser una lista de textos no vacíos.", i)
        if rol == "cierre":
            if _vacio(s.get("texto")) and not puntos:
                err("el cierre necesita `texto` o `puntos` (el resumen que merece guardarse).", i)
            if _vacio(s.get("peticion")):
                aviso("cierre sin `peticion`: asegúrate de que lleva UNA sola petición "
                      "(guárdalo / sígueme / link en la bio).", i)
        elif not _vacio(s.get("peticion")):
            aviso("`peticion` solo se pinta en la slide de cierre; aquí se ignora.", i)
        if "numero" in s and rol != "valor":
            aviso("`numero` solo se usa en las slides de valor.", i)

        # Texto: marcado, emojis, longitudes y escritura.
        textos = textos_de_slide(s)
        destacados = 0
        for campo, t in textos:
            if t.count(MARCA) % 2:
                err(f"`{campo}`: marcado `**` sin cerrar.", i)
            destacados += contar_destacados(t)
            emojis_total += (ne := contar_emojis(t))
            if ne and emojis_max == 0:
                err(f"`{campo}` lleva {ne} emoji(s): este proyecto va sin emojis.", i)
            for a in _avisos_de_escritura(campo, t):
                aviso(a, i)
        if destacados > 1:
            aviso(f"{destacados} palabras destacadas; como mucho una por slide.", i)

        np_tit = contar_palabras(s.get("titulo") or "")
        np_txt = contar_palabras(s.get("texto") or "")
        if rol == "gancho":
            lim = lon.get("gancho_palabras", 12)
            if np_tit + np_txt > lim:
                aviso(f"el gancho suma {np_tit + np_txt} palabras (orientativo: ≤ {lim}).", i)
        else:
            lim_t, lim_x = lon.get("titulo_palabras", 8), lon.get("texto_palabras", 25)
            if np_tit > lim_t:
                aviso(f"título de {np_tit} palabras (orientativo: ≤ {lim_t}).", i)
            if np_txt > lim_x:
                aviso(f"texto de {np_txt} palabras (orientativo: ≤ {lim_x}).", i)
            if rol == "cierre":
                lim_p = lon.get("punto_palabras", 7)
                for k, x in enumerate(puntos or [], 1):
                    if isinstance(x, str) and contar_palabras(x) > lim_p:
                        aviso(f"punto {k} de {contar_palabras(x)} palabras "
                              f"(orientativo: ≤ {lim_p}).", i)
                lim_q = lon.get("peticion_palabras", 12)
                if contar_palabras(s.get("peticion") or "") > lim_q:
                    aviso(f"petición de más de {lim_q} palabras.", i)

    if emojis_max > 0 and emojis_total > emojis_max:
        err(f"{emojis_total} emojis en el carrusel (máximo {emojis_max}).")
    return p, H


def _bajo(path: Path, raiz: Path) -> bool:
    try:
        path.resolve().relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


def _es_url(ruta) -> bool:
    return isinstance(ruta, str) and ruta.strip().lower().startswith(("http://", "https://", "www."))


def validar_material(plan: dict, proyecto, plan_dir: Path | None) -> list[Hallazgo]:
    """La portada solo puede ser material DEL PROYECTO y la fuente no puede ser
    de otro proyecto (nunca se mezclan). Devuelve ERRORES."""
    from lib.proyectos import es_ajeno, es_propio
    H: list[Hallazgo] = []
    port = plan.get("portada_fondo")
    ruta = port.get("ruta") if isinstance(port, dict) else port
    if _es_url(ruta):
        H.append(Hallazgo("ERROR", "`portada_fondo` es una URL: la portada sale del material "
                                   "del proyecto, nunca de internet.", 1))
    elif not _vacio(ruta) and isinstance(ruta, str):
        path = resolver_ruta(ruta, plan_dir)
        if es_ajeno(path, proyecto) and not es_propio(path, proyecto):
            H.append(Hallazgo("ERROR", f"`portada_fondo` es material de OTRO proyecto: {ruta}", 1))
        elif _bajo(path, config.FONDOS_DIR) and not es_propio(path, proyecto):
            H.append(Hallazgo("ERROR", f"`portada_fondo` es del banco común de TheEditor y el "
                                       f"proyecto «{proyecto.id}» no lo admite (b-roll "
                                       f"«{proyecto.broll}»): {ruta}", 1))
        elif not es_propio(path, proyecto):
            H.append(Hallazgo("ERROR", f"`portada_fondo` no es material del proyecto "
                                       f"«{proyecto.id}» ({ruta}). Vale lo que esté en "
                                       f"_Historico/{proyecto.id}/, proyectos/{proyecto.id}/, "
                                       f"TheEditor/proyectos/{proyecto.id}/, "
                                       f"TheDescarga/descargas/{proyecto.id}/ o sus carpetas "
                                       f"de publicación"
                                       + (" (o el banco común, por su política)"
                                          if proyecto.broll == "banco_comun" else "") + ".", 1))
        elif not proyecto.internet and path.name.lower().startswith(config.PREFIJOS_INTERNET):
            H.append(Hallazgo("ERROR", f"`portada_fondo` es un clip de internet ({path.name}) y "
                                       f"el proyecto no admite recursos de internet.", 1))
    fuente = plan.get("fuente") if isinstance(plan.get("fuente"), dict) else {}
    fr = fuente.get("ruta")
    if isinstance(fr, str) and fr.strip() and not _es_url(fr):
        path = resolver_ruta(fr, plan_dir)
        if es_ajeno(path, proyecto) and not es_propio(path, proyecto):
            H.append(Hallazgo("ERROR", f"`fuente.ruta` es de OTRO proyecto: {fr} "
                                       f"(no se mezclan proyectos)."))
    return H


def plan_para_json(p: dict) -> dict:
    """Plan normalizado con las claves del contrato en orden (sin internos `_`)."""
    out = {k: p[k] for k in ORDEN_CLAVES if k in p}
    slides = []
    for s in p.get("slides") or []:
        if not isinstance(s, dict):
            continue
        d = {k: s.get(k, "") for k in ORDEN_SLIDE}
        d.update({k: v for k, v in s.items() if k not in d and not k.startswith("_")})
        slides.append(d)
    out["slides"] = slides
    for k, v in p.items():
        if k not in out and not k.startswith("_"):
            out[k] = v
    return out

"""
AUDITORÍA del copy antes de registrar.

Adaptado de sergebulaev/instagram-skills (MIT): ig-humanizer V3 (scrub-rules,
audit-checklist, post-audit), llevado al español de España y a captions cortos.
Checklist para personas: `referencias/auditoria_copy.md`.

Niveles de cada hallazgo:
  error    → BLOQUEA el registro: gancho demasiado largo, cebo de interacción,
             cierre vacío, palabra prohibida de la identidad.
  aviso    → estilo: paralelismo negativo, revelación, anuncio de sinceridad,
             vocabulario de IA por densidad, emojis de más, primera persona del
             singular. Se corrige REESCRIBIENDO antes de registrar (no bloquea,
             salvo con `registrar --estricto`).
  literal  → un aviso de estilo cuyo fragmento es literal de lo que se dice en
             el clip (contexto.frase_viral / contexto.transcripcion) o en las
             slides del carrusel. Se permite: no cuenta como aviso.

Configuración (conf efectiva = identidad < plataforma < formato, ver Proyecto.conf_formato):
  gancho_max   máx. de caracteres de la primera frase/línea.
  emojis_max   máx. de emojis en el copy (identidad.voz.emojis_max salvo que la plataforma
               lo sobrescriba; sin valor = no se comprueba).
Identidad (CEO_Sergete/proyectos.json → identidad), si se pasa:
  voz.persona          activa el aviso de primera persona del singular (fuera de comillas
                       y salvo frase literal del clip).
  palabras_prohibidas  error si aparece alguna (sin distinguir tildes ni mayúsculas).

Modo `solo_estilo` (lo usa TheHistoria para el texto de las slides de los
carruseles: `copys.py auditar --solo-estilo --json --texto "..."`): solo estilo y
emojis, más los cebos de interacción y los cierres vacíos (errores). Nada de
gancho de 125 (ni CTA, hashtags o longitud, que se miran en lib/tanda.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from lib.carrusel import texto_slides
from lib.util import normalizar

I = re.IGNORECASE


@dataclass
class Hallazgo:
    nivel: str        # "error" | "aviso" | "literal"
    regla: str        # gancho | cebo | cierre_vacio | palabra_prohibida | paralelismo | revelacion | sinceridad
    #                   | vocabulario | emojis | primera_persona
    mensaje: str
    fragmento: str = ""


# ------------------------------------------------------------------ patrones
# Inicio de frase: principio de línea o tras . ! ? … (lookbehind de ancho fijo).
_INICIO = r"(?:^|(?<=[.!?…]\s)|(?<=[.!?…]\s\s))[\s¡¿\"«“]*"

# ERROR · cebo de interacción (Instagram lo penaliza).
CEBOS = [
    # comenta SÍ / YO / "QUIERO" / PALABRA en mayúsculas / comenta si... / comenta abajo
    r"(?i:\bcomenta(?:me|lo|nos)?)\s+(?:(?i:con\s+)?(?i:la\s+palabra\s+))?"
    r"(?:[\"«“'][^\"»”'\n]{1,30}[\"»”']|(?i:s[ií]|yo|aqu[ií]|abajo|un\s+emoji)\b|[A-ZÁÉÍÓÚÑ]{2,}\b)",
    # escribe X en los comentarios · déjalo / dime / te leo en comentarios
    r"(?i)\b(?:escribe|escr[ií]beme|pon|ponme|deja|d[eé]jame|d[eé]jalo|d[eé]janos|dime|cu[eé]ntame|te\s+leo|os\s+leo|nos\s+leemos)\b"
    r"[^.!?\n]{0,40}?\ben\s+(?:los\s+)?comentarios\b",
    # etiqueta / menciona a...
    r"(?i)\b(?:etiqueta|menciona)(?:lo|la|le)?\s+(?:a\s+)?(?:alguien|un[ao]?|tus?|ese|esa|esos|esas|dos|tres|\d+|quien|qui[eé]n)\b",
    # dale like / me gusta / corazón · deja tu like
    r"(?i)\b(?:dale|d[eé]jame|deja)\s+(?:un\s+|tu\s+)?(?:like|me\s+gusta|al\s+coraz[oó]n|coraz[oó]n|corazoncito)\b",
    # doble tap
    r"(?i)\bdoble\s+(?:tap|toque|clic|click)\b",
    # comparte si... / si (te ha gustado...), comparte
    r"(?i)\bcomp[aá]rte(?:lo|la|los|las|nos)?\s+si\b",
    r"(?i)\bsi\s+[^.!?\n,]{1,50},\s*comp[aá]rte(?:lo|la|los|las)?\b",
]

# ERROR · cierres vacíos: preguntas genéricas que no aportan.
CIERRES_VACIOS = [
    r"(?i)¿\s*(?:y\s+)?(?:t[uú]\s+)?qu[eé]\s+(?:opinas|piensas|te\s+parece|dices|opin[aá]is|pens[aá]is|os\s+parece)\s*\?",
    r"(?i)¿\s*(?:est[aá]s|est[aá]is)\s+de\s+acuerdo\s*\?",
    r"(?i)¿\s*(?:alguna\s+)?opini[oó]n(?:es)?\s*\?",
    r"(?i)¿\s*y\s+t[uú]\s*\?",
    r"(?i)¿\s*lo\s+sab[ií]as\s*\?",
]

# AVISO · paralelismo negativo.
_CLITICOS = r"(?:me|te|se|lo|la|le|nos|os|los|las|les)"
_CLITICO = r"(?:" + _CLITICOS + r"\s+)?(?!" + _CLITICOS + r"\b)"  # el verbo nunca es solo el clítico
PARALELISMOS = [
    # No necesitas X. Necesitas Y. · no es X, es Y · no va de X, va de Y · El problema no es X, es Y
    # No se trata de X. Se trata de Y. · no te vendo X, te vendo Y   (mismo verbo repetido)
    r"(?i)\bno\s+(" + _CLITICO + r"[a-záéíóúüñ]+)\b[^.!?\n]{1,80}?[,;:.]\s+(?:sino\s+(?:que\s+)?)?\1\b",
    # no es X sino Y · no solo X, sino (también) Y
    r"(?i)\bno\s+[^.!?\n]{1,60}?\bsino\b",
    # Sin X. Sin Y. Solo Z. · Ni X. Ni Y. Solo Z. · No X. No Y. Solo Z.
    r"(?i)\b(sin|ni|no)\s+[^.,;:!?\n]{1,40}[.,;]\s+\1\s+[^.,;:!?\n]{1,40}[.,;:]\s+(?:y\s+)?"
    r"(?:solo|s[oó]lo|solamente|[uú]nicamente|nada\s+m[aá]s\s+que)\b",
    # Deja de X. Empieza a Y.
    r"(?i)\bdeja\s+de\s+[^.!?\n]{1,60}?[.,;:]\s+(?:y\s+)?(?:empieza|ponte|aprende)\s+a\b",
]

# AVISO · revelaciones (el puente que anuncia lo que viene).
REVELACIONES = [
    r"(?i)¿\s*(?:y\s+)?(?:el|la|lo|los|las)\s+(?:resultados?|clave|secreto|problema|diferencia|verdad|respuesta|truco|"
    r"motivo|raz[oó]n|mejor|peor|curioso|gracioso|l[oó]gico|lecci[oó]n|trampa|consecuencia|soluci[oó]n|giro)\s*\?",
    r"(?i)¿\s*(?:y\s+)?(?:por\s*qu[eé]|c[oó]mo|qu[eé]\s+pas[oó]|qu[eé]\s+hice)\s*\?\s*"
    r"(?:porque|pues|muy\s+f[aá]cil|f[aá]cil|sencillo|simple)\b",
    r"(?i)¿\s*(?:y\s+)?sabes\s+qu[eé]\s*\?",
    r"(?i)\b(?:spoiler|plot\s+twist|giro\s+de\s+guion)\s*:",
    r"(?im)" + _INICIO + r"(?:aqu[ií]\s+(?:va|van|tienes|te\s+dejo|est[aá])|esto\s+es\s+lo\s+que|te\s+cuento|te\s+explico|"
    r"hablemos\s+de|vamos\s+a\s+hablar\s+de|lo\s+que\s+nadie\s+te\s+cuenta)\b[^.!?\n]{0,60}:",
    r"(?i)\baqu[ií]\s+tienes\s+(?:c[oó]mo|el\s+c[oó]mo|por\s+qu[eé])\s*[.:!]",
]

# AVISO · anuncios de sinceridad como apertura (de la frase o del copy).
SINCERIDAD = [
    r"(?im)" + _INICIO + r"(?:te\s+voy\s+a\s+ser\s+|voy\s+a\s+ser\s+|siendo\s+|para\s+ser\s+)"
    r"(?:sincer[oa]|honest[oa]|clar[oa]|direct[oa])\b",
    r"(?im)" + _INICIO + r"(?:seamos\s+(?:sinceros|honestos|claros|realistas)|sinceramente|honestamente|"
    r"no\s+te\s+voy\s+a\s+mentir|no\s+voy\s+a\s+mentir(?:te)?|hablemos\s+claro|te\s+lo\s+(?:voy\s+a\s+decir|digo)\s+claro|"
    r"lo\s+dir[eé]\s+claro|la\s+verdad\s+es\s+que|la\s+cruda\s+(?:verdad|realidad)|(?:la\s+)?verdad\s+inc[oó]moda|"
    r"opini[oó]n\s+impopular|sin\s+rodeos\s*:|sin\s+filtros\s*:|te\s+cuento\s+un\s+secreto)",
]

# AVISO por densidad · vocabulario de IA en español (≥ VOCAB_UMBRAL en un mismo párrafo).
VOCAB_IA = [
    r"\bfundamental(?:es|mente)?\b", r"\bcrucial(?:es)?\b", r"\besencial(?:es|mente)?\b",
    r"\bpotenci(?:a|ar|ará|arás|e|es|ando|ado|ada)\b", r"\bimpuls(?:a|ar|ará|arás|e|es|ando|ado|ada)\b",
    r"\btransform(?:a|ar|ará|arás|e|es|ando|ado|ada|ación|ador|adora)\b",
    r"\bdesbloque(?:a|ar|ará|arás|e|es|ando|ado|ada)\b", r"\bsin\s+(?:lugar\s+a\s+)?duda\b",
    r"\ben\s+definitiva\b", r"\ben\s+el\s+mundo\s+(?:actual|de\s+hoy)\b", r"\ben\s+la\s+era\s+(?:digital|de\s+la\s+ia)\b",
    r"\bhoy\s+en\s+d[ií]a\b", r"\b(?:siguiente|pr[oó]ximo)\s+nivel\b", r"\bsum[eé]rge(?:te|rte)\b|\bsumergirte\b",
    r"\bdescubre\b", r"\brevolucion(?:a|ar|ario|aria)\b", r"\boptimiz(?:a|ar|ación)\b", r"\bmaximiz(?:a|ar|ará)\b",
    r"\bexponencial(?:es|mente)?\b", r"\bla\s+clave\s+del\s+[ée]xito\b", r"\breglas\s+del\s+juego\b",
    r"\bun\s+antes\s+y\s+un\s+despu[eé]s\b", r"\bcabe\s+destacar\b", r"\bes\s+importante\s+(?:destacar|se[ñn]alar)\b",
    r"\bjuega\s+un\s+papel\b", r"\bpanorama\b", r"\becosistema\b", r"\bsinergias?\b", r"\bhol[ií]stic[oa]\b",
    r"\bempoder(?:a|ar|ado|ada|amiento)\b", r"\bfoment(?:a|ar)\b", r"\ben\s+resumen\b", r"\ben\s+conclusi[oó]n\b",
    r"\bal\s+final\s+del\s+d[ií]a\b", r"\bverdaderamente\b", r"\bsin\s+precedentes\b", r"\btu\s+viaje\b",
]
VOCAB_UMBRAL = 2

# Emojis: pictogramas, banderas y teclas (las flechas → y símbolos © ™ no cuentan).
_EMO = "\U0001F000-\U0001FAFF\u2600-\u27BF\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55\u231A\u231B\u23E9-\u23F3\u23F8-\u23FA"
RE_EMOJI = re.compile(
    r"[\U0001F1E6-\U0001F1FF]{2}"                                   # banderas
    r"|[0-9#*]\uFE0F?\u20E3"                                        # teclas 1️⃣
    rf"|[{_EMO}][\U0001F3FB-\U0001F3FF]?\uFE0F?(?:\u200D[{_EMO}][\U0001F3FB-\U0001F3FF]?\uFE0F?)*")

# AVISO · primera persona del singular (si la identidad define voz.persona). Solo formas
# inequívocas: pronombres, una lista de verbos frecuentes y los pretéritos/futuros en -é/-í.
_P1_PRONOMBRES = r"yo|me|m[ií]|mis|conmigo|m[ií]os?|m[ií]as?"
_P1_VERBOS = (r"soy|estoy|voy|doy|tengo|hago|digo|pongo|salgo|vengo|traigo|puedo|quiero|creo|pienso|necesito|"
              r"vendo|ense[ñn]o|recomiendo|explico|prometo|aseguro|garantizo|conozco|opino|siento|veo|hablo|"
              r"escribo|aprendo|comparto|cobro|gano|llevo|considero|he|fui|hice|dije|tuve|estuve|pude|quise|"
              r"puse|vine|supe|vi")
RE_P1 = re.compile(rf"\b(?:{_P1_PRONOMBRES}|{_P1_VERBOS}|[a-záéíóúüñ]{{2,}}[éí])\b", re.IGNORECASE)
# Palabras en -é/-í que no son verbos en 1.ª persona.
_NO_P1 = {"qué", "porqué", "café", "bebé", "olé", "josé", "cliché", "puré", "comité", "consomé", "canapé",
          "chalé", "bidé", "aquí", "allí", "ahí", "así", "jabalí", "maniquí", "esquí", "rubí", "colibrí",
          "frenesí", "marroquí", "iraní", "israelí", "baladí", "alhelí", "ají", "bisturí", "pakistaní", "paquistaní"}
# Lo que va entre comillas (una objeción del cliente, una cita) no cuenta como primera persona.
RE_COMILLAS = re.compile(r"\"[^\"\n]*\"|«[^»\n]*»|“[^”\n]*”|‘[^’\n]*’")

_C = {k: [re.compile(p) for p in v] for k, v in {
    "cebo": CEBOS, "cierre_vacio": CIERRES_VACIOS, "paralelismo": PARALELISMOS,
    "revelacion": REVELACIONES, "sinceridad": SINCERIDAD}.items()}
_VOCAB = [re.compile(p, I) for p in VOCAB_IA]

MENSAJES = {
    "cebo": "cebo de interacción «{f}»: Instagram lo penaliza. Cierra con el CTA del proyecto.",
    "cierre_vacio": "cierre vacío «{f}»: pregunta genérica que no aporta. Cierra con el CTA.",
    "paralelismo": "paralelismo negativo «{f}»: dilo en positivo y directo, sin contraponer «no X / sí Y».",
    "revelacion": "revelación «{f}»: quita el puente y deja que la frase siguiente hable sola.",
    "sinceridad": "anuncio de sinceridad «{f}»: bórralo y empieza por el hecho.",
    "palabra_prohibida": "palabra prohibida «{f}» (identidad del proyecto): quítala o reformula sin ella.",
    "primera_persona": "primera persona del singular ({f}): la voz del proyecto (identidad.voz.persona) es de tú "
                       "al lector, con quien sale en el clip en tercera persona. Reescríbelo.",
}


# ------------------------------------------------------------------ utilidades
def gancho(texto: str) -> str:
    """Primera frase o primera línea (lo que acabe antes): lo que se lee antes del «más»."""
    linea = (texto or "").strip().split("\n", 1)[0].strip()
    m = re.search(r"[.!?…]+[\"»”')]*(?=\s+[¿¡\"«“(]?[A-ZÁÉÍÓÚÑ0-9]|\s*$)", linea)
    return linea[:m.end()].strip() if m else linea


def contar_emojis(texto: str) -> int:
    return len(RE_EMOJI.findall(texto or ""))


def _fuente_literal(contexto: dict | None) -> str:
    if not contexto:
        return ""
    # Reel: lo que se dice en el clip. Carrusel: el texto de sus slides (el caption repite el gancho);
    # se calcula aquí desde contexto.slides (las tandas antiguas traían texto_slides ya hecho).
    partes = [str(contexto.get(k) or "") for k in ("frase_viral", "transcripcion", "texto_slides")]
    partes.append(texto_slides(contexto))
    return normalizar(" ".join(partes))


_VOCALES = {"a": "[aáàä]", "e": "[eéèë]", "i": "[iíìï]", "o": "[oóòö]", "u": "[uúùü]", "n": "[nñ]"}


def _rx_prohibida(palabra: str) -> re.Pattern | None:
    """Regex que encuentra `palabra` en el texto original sin distinguir tildes ni mayúsculas."""
    n = normalizar(palabra)
    if not n:
        return None
    cuerpo = r"\s+".join("".join(_VOCALES.get(ch, re.escape(ch)) for ch in w) for w in n.split())
    return re.compile(rf"(?<!\w){cuerpo}(?!\w)", re.IGNORECASE)


def palabras_prohibidas(texto: str, prohibidas: list[str]) -> list[str]:
    """Fragmentos del texto que son palabras prohibidas (tal y como aparecen)."""
    out = []
    for w in prohibidas or []:
        rx = _rx_prohibida(w)
        if rx:
            out += [m.group(0) for m in rx.finditer(texto or "")]
    return out


def primera_persona(texto: str, fuente_norm: str = "") -> tuple[list[str], list[str]]:
    """(formas en 1.ª persona del singular, las que están en frases literales del clip).

    No cuenta lo que va entre comillas (objeciones de clientes, citas).
    """
    limpio = RE_COMILLAS.sub(" ", texto or "")
    propias, literales = [], []
    for frase in re.split(r"(?<=[.!?…])\s+|\n+", limpio):
        hits = [m.group(0) for m in RE_P1.finditer(frase) if m.group(0).lower() not in _NO_P1]
        if hits:
            (literales if es_literal(frase.strip(), fuente_norm) else propias).extend(hits)
    return propias, literales


def es_literal(fragmento: str, fuente_norm: str) -> bool:
    """True si el fragmento sale tal cual (o casi) en lo que se dice en el clip."""
    frag = normalizar(fragmento)
    if not frag or not fuente_norm:
        return False
    if frag in fuente_norm:
        return True
    ft, tt = frag.split(), fuente_norm.split()
    if len(ft) < 3:
        return False
    for ancho in {len(ft) - 1, len(ft), len(ft) + 1, len(ft) + 2}:
        for i in range(0, max(1, len(tt) - ancho + 1)):
            if SequenceMatcher(None, ft, tt[i:i + ancho]).ratio() >= 0.85:
                return True
    return False


def _hasta_fin_de_frase(texto: str, fin: int, maximo: int = 50) -> str:
    """Lo que queda de la frase tras `fin` (para enseñar el fragmento entero)."""
    m = re.search(r"[.!?\n]", texto[fin:fin + maximo])
    return texto[fin:fin + (m.end() if m else 0)]


def _corto(t: str, n: int = 70) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


# ------------------------------------------------------------------ auditoría
def auditar(texto: str, conf_plat: dict | None = None, contexto: dict | None = None,
            plataforma: str = "", solo_estilo: bool = False, identidad: dict | None = None) -> list[Hallazgo]:
    """Audita un copy (sin hashtags). Devuelve los hallazgos (error / aviso / literal).

    solo_estilo: sin la comprobación del gancho (para textos que no son un caption,
    como las slides de un carrusel). Cebos, cierres vacíos, estilo y emojis, sí.
    identidad: la del proyecto (palabras prohibidas y, si hay voz.persona, primera persona).
    """
    conf = conf_plat or {}
    texto = (texto or "").strip()
    out: list[Hallazgo] = []
    if not texto:
        return out
    fuente = _fuente_literal(contexto)

    # ERROR · gancho
    mx = None if solo_estilo else conf.get("gancho_max")
    if mx:
        g = gancho(texto)
        if len(g) > mx:
            out.append(Hallazgo("error", "gancho",
                                f"gancho de {len(g)} caracteres (máx. {mx}): «{_corto(g, 60)}». "
                                "Acórtalo para que se entienda antes del «más».", g))

    # ERROR · cebos y cierres vacíos (no tienen excepción de literal)
    for regla in ("cebo", "cierre_vacio"):
        for rx in _C[regla]:
            for m in rx.finditer(texto):
                out.append(Hallazgo("error", regla, MENSAJES[regla].format(f=_corto(m.group(0))), m.group(0)))

    # ERROR · palabras prohibidas de la identidad (sin excepciones)
    ident = identidad or {}
    for frag in palabras_prohibidas(texto, ident.get("palabras_prohibidas") or []):
        out.append(Hallazgo("error", "palabra_prohibida", MENSAJES["palabra_prohibida"].format(f=frag), frag))

    # AVISO · estilo (salvo que sea literal del clip)
    vistos: set[tuple[int, int]] = set()
    for regla in ("paralelismo", "revelacion", "sinceridad"):
        for rx in _C[regla]:
            for m in rx.finditer(texto):
                frag = m.group(0).strip()
                tramo = (m.start(), m.end())
                if any(a <= tramo[0] < b or tramo[0] <= a < tramo[1] for a, b in vistos):
                    continue  # el mismo trozo ya lo marcó otra regla
                vistos.add(tramo)
                visible = frag + (_hasta_fin_de_frase(texto, m.end()) if regla == "paralelismo" else "")
                msg = MENSAJES[regla].format(f=_corto(visible, 90))
                if es_literal(frag.strip("¡¿\"«“"), fuente):
                    out.append(Hallazgo("literal", regla, f"(literal del clip, se permite) {msg}", frag))
                else:
                    out.append(Hallazgo("aviso", regla, msg, frag))

    # AVISO · vocabulario de IA por densidad (por párrafo)
    for parrafo in re.split(r"\n\s*\n", texto):
        hits = [m.group(0) for rx in _VOCAB for m in rx.finditer(parrafo)]
        propios = [h for h in hits if not (fuente and f" {normalizar(h)} " in f" {fuente} ")]
        if len(propios) >= VOCAB_UMBRAL:
            out.append(Hallazgo("aviso", "vocabulario",
                                f"{len(propios)} expresiones de IA en el mismo párrafo ({', '.join(propios)}): "
                                "cámbialas por algo concreto o quítalas.", ", ".join(propios)))

    # AVISO · primera persona del singular (si la identidad define la persona de la voz)
    persona = str((ident.get("voz") or {}).get("persona") or "").strip()
    if persona:
        propias, literales = primera_persona(texto, fuente)
        for nivel, hits in (("aviso", propias), ("literal", literales)):
            if hits:
                formas = ", ".join(f"«{h}»" for h in dict.fromkeys(hits))
                msg = MENSAJES["primera_persona"].format(f=formas)
                if nivel == "literal":
                    msg = f"(literal del clip, se permite) {msg}"
                out.append(Hallazgo(nivel, "primera_persona", msg, ", ".join(dict.fromkeys(hits))))

    # AVISO · emojis
    emax = conf.get("emojis_max")
    if emax is not None:
        emos = RE_EMOJI.findall(texto)
        if len(emos) > emax:
            donde = f" en {plataforma}" if plataforma else ""
            out.append(Hallazgo("aviso", "emojis", f"{len(emos)} emoji(s){donde} (máx. {emax}).", " ".join(emos)))
    return out

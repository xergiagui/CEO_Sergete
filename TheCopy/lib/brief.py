"""
BRIEF del proyecto (`copys.py brief --proyecto <id>`): lo ÚNICO que el subagente `copy`
necesita leer, junto con la tanda, para escribir los copys. Se compone en el momento desde
las fuentes únicas, sin copiar nada:

  identidad     CEO_Sergete/proyectos.json → identidad (voz, tono, persona, landing…)
  reglas        proyectos/<id>/proyecto.json → reglas_copy
  campos        proyecto.json → campos_extra (ayuda) + ofertas.json (cuando_usarla, CTA genérico)
  plataformas   proyecto.json → plataformas activas y sus formatos (guía y límites)
  hashtags      proyecto.json → plataformas.<p>.hashtags (cifras) + hashtags.json (banco por
                tamaño) + los últimos conjuntos registrados (para rotar)

Objetivo: ≤ ~1,5k tokens. `banco_copys.json` solo hace falta si un clip trae `aviso`, y
`referencias/` solo si un aviso no se entiende.
"""
from __future__ import annotations

import config


def _limites(conf: dict) -> list[str]:
    out = []
    if conf.get("requiere_titulo"):
        out.append(f"título obligatorio ≤ {conf.get('titulo_max', '…')} car.")
    if conf.get("gancho_max"):
        out.append(f"gancho (1.ª frase) ≤ {conf['gancho_max']} car.")
    rec = conf.get("copy_recomendado")
    if rec:
        out.append(f"copy {rec[0]}–{rec[1]} car.")
    if conf.get("max_caracteres"):
        out.append(f"máx. {conf['max_caracteres']} con hashtags")
    if conf.get("cta_obligatorio"):
        out.append("CTA obligatorio" + (f" (p. ej. «{conf['cta_ejemplo']}»)" if conf.get("cta_ejemplo") else ""))
    if conf.get("emojis_max") is not None:
        out.append(f"emojis ≤ {conf['emojis_max']}")
    return out


def brief(p, recientes: dict[str, list[tuple[str, frozenset[str]]]] | None = None) -> str:
    ident, voz = p.identidad, p.voz
    L = [f"BRIEF {p.nombre} ({p.id}). Lee solo esto y la tanda (banco_copys.json, solo si un clip trae `aviso`; "
         "referencias/, solo si un aviso no se entiende).", ""]

    # ---- identidad (CEO_Sergete/proyectos.json → identidad)
    L.append("IDENTIDAD")
    cuenta = [x for x in (ident.get("cuenta_ig"), p.landing and f"landing {p.landing}{p.afiliado}") if x]
    if cuenta:
        L.append("- " + " · ".join(cuenta))
    if voz.get("persona"):
        L.append(f"- Persona: {voz['persona']}")
    L.append("- " + " · ".join([f"Tono: {p.tono}"] + ([p.idioma] if p.idioma else [])
                               + ([f"emojis ≤ {voz['emojis_max']}"] if voz.get("emojis_max") is not None else [])))
    if ident.get("no_suplantar"):
        L.append(f"- No suplantar: {ident['no_suplantar']}")
    if p.palabras_prohibidas:
        L.append(f"- Prohibidas (error): {', '.join(p.palabras_prohibidas)}")

    # ---- reglas del copy (proyecto.json)
    L += ["", "REGLAS"] + [f"- {r}" for r in p.conf.get("reglas_copy") or []]

    # ---- campos propios (campos_extra + ofertas.json)
    L += ["", "CAMPOS (extra.*)"]
    for campo in p.campos_extra():
        cid = campo["id"]
        ob = "" if campo.get("obligatorio") else " (opcional)"
        if campo.get("valores") == "ofertas":
            L.append(f"- {cid}{ob}, viene sugerida; revísala (id (nombre): cuándo):")
            for o in p.ofertas.get("ofertas") or []:
                L.append(f"  {o['id']} ({o.get('nombre', o['id'])}): {o.get('cuando_usarla', '')}")
            gen = p.ofertas.get("generico") or {}
            if gen:
                L.append(f"  {gen.get('id', 'generico')}: {gen.get('cuando_usarla', '')}"
                         + (f" CTA: «{gen['cta']}»" if gen.get("cta") else ""))
        else:
            vals = p.valores_campo(campo)
            linea = f"- {cid}{ob}" + (f" ({' | '.join(vals)})" if vals else " (texto libre)")
            L.append(linea + (f": {campo['ayuda']}" if campo.get("ayuda") else ""))

    # ---- tipos de clip (proyecto.json → tipos_clip): caption y hashtags fijos por tipo
    tc = p.tipos_clip
    if tc:
        L += ["", f"TIPOS DE CLIP (el tipo = primera letra del nombre del clip, patrón {tc.get('patron')})"]
        if tc.get("nota"):
            L.append(f"- {tc['nota']}")
        for t, d in tc["tipos"].items():
            L.append(f"- {t}: «{d['caption']}» · {' '.join(p.hashtags_de_tipo(t))}")

    # ---- plataformas activas, por formato
    L += ["", "PLATAFORMAS ACTIVAS"]
    for pid in p.plataformas_activas():
        nombre = p.nombre_plataforma(pid)
        base = None
        for fmt in p.formatos(pid):
            conf = p.conf_formato(pid, fmt)
            lim = _limites(conf)
            if base is not None:
                lim = [x for x in lim if x not in base] or ["mismos límites"]
            else:
                base = lim
            guia = f" {conf['guia']}" if conf.get("guia") else ""
            lim_txt = " · ".join(lim)
            L.append(f"- {nombre} · {config.FORMATOS.get(fmt, fmt)}: {lim_txt}{'' if lim_txt.endswith('.') else '.'}{guia}")

    # ---- hashtags (cifras: plataformas.<p>.hashtags · banco: hashtags.json)
    L += ["", "HASHTAGS"]
    if tc:
        L.append("- Fijos por tipo (tabla de arriba): los pone el script, literales y en ese orden; deja "
                 "\"hashtags\": []. No hay banco temático ni rotación.")
    for pid in [] if tc else p.plataformas_activas():
        fijos = " ".join(f"{t} ({p.tamano_hashtag(t) or '?'})" for t in p.fijos(pid)) or "ninguno"
        L.append(f"- {p.nombre_plataforma(pid)}: fijos {fijos}, los pone el script · {p.texto_reglas_hashtags(pid)}.")
    if not tc:
        L.append("- Automáticos: \"hashtags\": [] + \"hashtags_temas\" en la pieza (viene sugerido) → registrar elige "
                 "un conjunto válido y rotado. Escribe hashtags solo para forzar alguno (completa el resto).")
        L.append("- Banco, tema: nicho | medio | amplio")
        for tema, g in p.banco_por_tamano().items():
            partes = [" ".join(g[t]) or "—" for t in ("nicho", "medio", "amplio")]
            if g["sin_tamano"]:
                partes.append("sin tamaño: " + " ".join(g["sin_tamano"]))
            L.append(f"  {tema}: {' | '.join(partes)}")
    for pid in [] if tc else p.plataformas_activas():
        n = int(p.reglas_hashtags(pid).get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0)
        ult = (recientes or {}).get(pid, [])[-n:] if n else []
        txt = "; ".join(f"{c}: {' '.join(sorted(s)) or '—'}" for c, s in ult) if ult else "ninguno aún"
        L.append(f"- Últimos en {p.nombre_plataforma(pid)}: {txt}")

    # ---- tanda y registro
    L += ["", "TANDA",
          "- Por pieza: completa extra y el copy de cada plataforma (+ titulo si aparece); revisa lo sugerido "
          + ("(tema, tipo_clip: trae el caption_literal y si es la primera vez del tipo). Copys distintos, sin hashtags dentro."
             if tc else "(tema, oferta, hashtags_temas). Copys distintos, sin hashtags dentro."),
          ("- Un clip con `aviso` (sin contexto) no bloquea: el caption sale del tipo (tabla de arriba); para el `tema`, "
           "pide una línea al CEO." if tc else
           f"- Solo `aviso` (sin contexto): copys.py banco --proyecto {p.id} y adapta uno (libre), o pide una línea al CEO."),
          "- registrar --entrada <tanda> --simular → corrige → registrar --entrada <tanda> --planificar. Al CEO: ID, "
          + ("texto final, fecha y hora, y la línea FALTAN." if tc else "oferta, texto final y la línea FALTAN.")
          + " Excel abierto: avisa, no reintentes.",
          "- Cambiar un copy: pendientes --clip <pieza> --incluir-registrados → registrar --reemplazar (solo esa)."]
    return "\n".join(L)

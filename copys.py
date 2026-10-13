"""
TheCopy — copys y hashtags de las piezas (Reels y carruseles), relacionados en un
registro, y calendario de publicación.

Flujo normal (lo lleva el subagente `copy` de CEO_Sergete):
  1. copys.py pendientes            → tanda JSON con las piezas sin copy + su contexto
                                      (Reels = MP4; carruseles = carpetas con carrusel.json)
  2. (el subagente rellena la tanda: tema, oferta, objetivo, pilar, copy y hashtags
      temáticos; `copys.py hashtags` enseña el banco por tamaño y los últimos conjuntos usados)
  3. copys.py auditar --entrada <tanda>     → informe de estilo (se corrige reescribiendo)
  4. copys.py registrar --entrada <tanda>   → valida + audita → Excel + .txt
  5. copys.py calendario planificar → fecha y hora a lo registrado (+ historias del día)
  6. copys.py calendario hoy        → qué se publica hoy, con el texto listo para pegar
  7. copys.py sincronizar           → Estado/ruta según la carpeta donde esté cada pieza

Proyectos: cada orden trabaja con UN proyecto (`--proyecto <id>`; sin él, el único que
haya; con varios, error con la lista). Registro, tandas (tandas/<id>/), calendario y .txt
son siempre los de ese proyecto, y nunca se lee ni escribe en carpetas de otro.

Ejecuta con el entorno propio:  .venv\\Scripts\\python.exe copys.py <orden> ...
(El script NO se llama copy.py: chocaría con el módulo `copy` de Python.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import config
from lib import auditoria as audit
from lib import calendario as cal
from lib import carrusel as car
from lib import proyecto as proy
from lib import tanda as tnd
from lib import txt
from lib.metadatos import BuscadorMetadatos
from lib.registro import Registro, RegistroBloqueado, esta_bloqueado, formato_de_fila
from lib.util import escribir_json, forzar_utf8, leer_json, normalizar


# ---------------------------------------------------------------- helpers
def _proyecto(pid: str | None) -> proy.Proyecto:
    """--proyecto <id>; sin él, el único proyecto que haya (sin contar _plantilla); con varios, error."""
    return proy.elegir(pid)


def _proyecto_de_tanda(tanda: dict, pid_arg: str | None) -> proy.Proyecto:
    """El proyecto de una tanda es el suyo (campo `proyecto`); --proyecto, si se da, tiene que coincidir."""
    pid_tanda = tanda.get("proyecto")
    if pid_arg and pid_tanda and pid_arg != pid_tanda:
        raise proy.ErrorProyecto(f"La tanda es del proyecto '{pid_tanda}' y has pedido --proyecto {pid_arg}: "
                                 "no se mezclan proyectos.")
    return _proyecto(pid_tanda or pid_arg)


def _ajena(p: proy.Proyecto, ruta: Path | str | None, que: str) -> None:
    """Error si `ruta` es de OTRO proyecto (sus carpetas de piezas, su registro o sus tandas)."""
    otro = proy.de_otro_proyecto(p.id, ruta)
    if otro:
        raise proy.ErrorProyecto(f"{que} {ruta} es del proyecto '{otro}', no de '{p.id}': no se mezclan proyectos.")


def _excel(args, p: proy.Proyecto) -> Path:
    """Registro del proyecto o el de --excel (pruebas), que no puede ser el de otro proyecto."""
    if getattr(args, "excel", None):
        excel = Path(args.excel)
        _ajena(p, excel, "--excel")
        return excel
    return p.registro_path


def _carpeta(p: proy.Proyecto, alternativa: str | None, propia: Path | None, que: str) -> Path | None:
    """Carpeta alternativa (pruebas) o la del proyecto; nunca la de otro proyecto."""
    if alternativa:
        _ajena(p, alternativa, que)
        return Path(alternativa)
    return propia


def _pid_de_nombre(p: proy.Proyecto, nombre: str | None) -> str | None:
    for pid in p.conf.get("plataformas") or {}:
        if p.nombre_plataforma(pid).lower() == str(nombre or "").lower():
            return pid
    return None


def _filas_de_clip(reg: Registro, clip: str) -> list[dict]:
    return [d for _, d in reg.filas() if str(d.get("Clip") or "").lower() == clip.lower()]


def _hashtags_recientes(p: proy.Proyecto, reg: Registro | None) -> dict[str, list[tuple[str, frozenset[str]]]]:
    """{plataforma: [(clip, temáticos), ...]} en el orden del registro (para la rotación)."""
    out: dict[str, list[tuple[str, frozenset[str]]]] = {}
    for _, d in (reg.filas() if reg else []):
        pid = _pid_de_nombre(p, d.get("Plataforma"))
        if pid and d.get("Hashtags"):
            out.setdefault(pid, []).append((str(d.get("Clip") or ""), tnd.tematicos_de(p, pid, str(d["Hashtags"]))))
    return out


def _clips_en(carpeta: Path, recursivo: bool = False) -> list[Path]:
    if not carpeta or not carpeta.exists():
        return []
    it = carpeta.rglob("*") if recursivo else carpeta.iterdir()
    return sorted(f for f in it if f.is_file() and f.suffix.lower() in config.EXT_VIDEO)


def _fecha_arg(txt_fecha: str | None, nombre: str) -> dt.date | None:
    if not txt_fecha:
        return None
    f = cal.a_fecha(txt_fecha)
    if not f:
        raise proy.ErrorProyecto(f"{nombre} '{txt_fecha}' no es una fecha (usa AAAA-MM-DD).")
    return f


# ---------------------------------------------------------------- órdenes
def cmd_proyectos(args) -> int:
    ids = proy.listar()
    if not ids:
        print("No hay proyectos. Crea uno con: copys.py nuevo-proyecto <id> --nombre \"...\"")
        return 0
    for pid in ids:
        try:
            p = proy.Proyecto(pid)
            plats = ", ".join(p.nombre_plataforma(x) for x in p.plataformas_activas())
            calend = "calendario activo" if p.calendario_activo else "sin calendario"
            print(f"- {pid:<16} {p.nombre}  ·  {p.tipo or 'tipo ?'}  ·  IDs {p.prefijo_id}-  ·  plataformas activas: "
                  f"{plats}  ·  {calend}  ·  registro: {p.registro_path.name}")
            faltan = [f"{que} ({c})" for que, c in (("pendiente", p.carpeta_pendiente), ("publicado", p.carpeta_publicado))
                      if c and not c.exists()]
            if p.calendario_activo and p.carpeta_historias and not p.carpeta_historias.exists():
                faltan.append(f"historias ({p.carpeta_historias})")
            if faltan:
                print(f"    [!] no existen (las crea el CEO): {'; '.join(faltan)}")
            sin = p.sin_rellenar()
            if sin:
                print(f"    por rellenar: {'; '.join(sin)}")
        except proy.ErrorProyecto as e:
            print(f"- {pid:<16} [config incorrecta] {e}")
    return 0


def cmd_pendientes(args) -> int:
    p = _proyecto(args.proyecto)
    carpeta = _carpeta(p, args.carpeta, p.carpeta_pendiente, "--carpeta")
    if not carpeta:
        print(f"[!] {p.id}/proyecto.json no define carpetas.pendiente.")
        return 1
    if not carpeta.exists():
        print(f"[!] No existe la carpeta pendiente de {p.nombre}: {carpeta}\n"
              f"    La crea el CEO (CEO_Sergete/REVISADOS/{p.id}/…); hasta entonces no hay piezas que buscar.")
        return 1
    plataformas = args.plataformas.split(",") if args.plataformas else p.plataformas_activas()
    for pid in plataformas:
        p.plataforma(pid)  # valida que exista

    clips = _clips_en(carpeta)
    carrs = car.carruseles_en(carpeta)
    if args.clip:
        quiero = {c.lower() for c in args.clip} | {Path(c).stem.lower() for c in args.clip}
        clips = [c for c in clips if c.name.lower() in quiero or c.stem.lower() in quiero]
        carrs = [d for d in carrs if d.name.lower() in quiero]

    excel = _excel(args, p)
    salida = Path(args.salida) if args.salida else (
        config.TANDAS_DIR / p.id / f"{p.id}_{dt.datetime.now():%Y%m%d_%H%M%S}.json")
    _ajena(p, salida, "--salida")
    reg = Registro(excel, p) if excel.exists() else None
    meta = BuscadorMetadatos(p)

    def faltan_en(nombre: str, plats: list[str]) -> list[str]:
        return [pid for pid in plats
                if args.incluir_registrados or not (reg and reg.buscar(nombre, p.nombre_plataforma(pid)))]

    piezas, ya, sin_plataforma = [], [], []
    for c in clips:
        faltan = faltan_en(c.name, plataformas)
        if not faltan:
            ya.append(c.name)
            continue
        piezas.append({"ruta": c, "contexto": meta.contexto(c), "plataformas": faltan, "formato": "reel"})
    for d in carrs:
        admiten = [pid for pid in plataformas if p.admite(pid, "carrusel")]
        if not admiten:
            sin_plataforma.append(d.name)
            continue
        faltan = faltan_en(d.name, admiten)
        if not faltan:
            ya.append(d.name)
            continue
        ctx = car.contexto(d, p)
        extra = {}
        for cid in ("objetivo", "pilar"):
            campo = p.campo(cid)
            if campo and ctx.get(cid):
                extra[cid] = p.canon_valor(campo, ctx[cid]) or ""
        piezas.append({"ruta": d, "contexto": ctx, "plataformas": faltan, "formato": "carrusel",
                       "tema": ctx.get("tema") or "", "extra": extra})

    tanda = tnd.esqueleto(p, piezas)
    # Pieza ya registrada en otra plataforma → mismo tema y campos propios (lo del Excel manda).
    for bloque in tanda["clips"]:
        previas = _filas_de_clip(reg, bloque["clip"]) if reg else []
        if previas:
            bloque["tema"] = previas[0].get("Tema") or bloque["tema"]
            for campo in p.campos_extra():
                visible = previas[0].get(campo["columna"])
                if visible in (None, ""):
                    continue
                ids = {v: k for k, v in (p.valores_campo(campo) or {}).items()}
                bloque["extra"][campo["id"]] = ids.get(visible, visible) or ""

    n_r = len(clips)
    n_c = len(carrs)
    print(f"Proyecto {p.nombre} · carpeta: {carpeta}")
    print(f"{n_r} Reel(s) y {n_c} carrusel(es) en la carpeta · {len(ya)} ya tienen copy · {len(piezas)} pendiente(s)")
    if sin_plataforma:
        print(f"  aviso: ninguna de las plataformas pedidas admite carrusel: {', '.join(sin_plataforma)}")
    if not piezas:
        return 0

    escribir_json(salida, tanda)
    for pz in piezas:
        ctx = pz["contexto"]
        if pz["formato"] == "carrusel":
            info = f"carrusel · {ctx.get('formula') or '¿fórmula?'} · {ctx.get('n_imagenes')} slides · «{ctx.get('gancho_slide1', '')}»"
        else:
            info = ctx.get("frase_viral") or ctx.get("titulo") or ctx.get("gancho_texto") or ""
        aviso = f"  [aviso: {ctx['aviso']}]" if ctx.get("aviso") else ""
        print(f"  - {Path(pz['ruta']).name}  [{', '.join(pz['plataformas'])}]  {info}{aviso}")
    print(f"\nTANDA: {salida}")
    return 0


def cmd_registrar(args) -> int:
    entrada = Path(args.entrada)
    tanda = leer_json(entrada)
    p = _proyecto_de_tanda(tanda, args.proyecto)
    _ajena(p, entrada, "La tanda")
    excel = _excel(args, p)
    reg = Registro(excel, p)

    existentes: dict[str, dict[str, str]] = {}
    for _, d in reg.filas():
        pid = _pid_de_nombre(p, d.get("Plataforma"))
        if pid and d.get("Copy"):
            existentes.setdefault(pid, {})[normalizar(str(d["Copy"]))] = str(d.get("Clip"))

    errores, avisos = tnd.validar(p, tanda, existentes, _hashtags_recientes(p, reg))
    # Nunca se escribe un .txt en las carpetas de otro proyecto.
    propias = p.carpetas_propias()
    for c in tanda.get("clips") or []:
        ruta = c.get("ruta")
        if not ruta:
            continue
        otro = proy.de_otro_proyecto(p.id, ruta)
        if otro:
            errores.append(f"[{c.get('clip')}] está en una carpeta del proyecto '{otro}' ({ruta}): "
                           f"esta tanda es de '{p.id}' y no se mezclan proyectos.")
        elif not any(proy.dentro_de(ruta, x) for x in propias):
            avisos.append(f"[{c.get('clip')}] no está en las carpetas de {p.nombre} ({ruta}).")
    if not args.reemplazar:
        for c in tanda.get("clips") or []:
            for pid in c.get("plataformas") or {}:
                if pid in (p.conf.get("plataformas") or {}) and reg.buscar(c.get("clip", ""), p.nombre_plataforma(pid)):
                    errores.append(f"[{c.get('clip')} · {pid}] ya está registrado (usa --reemplazar para cambiarlo).")

    for a in avisos:
        print(f"  aviso: {a}")
    if errores:
        print(f"\n[X] {len(errores)} error(es); no se ha registrado nada:")
        for e in errores:
            print(f"  - {e}")
        return 1

    if args.simular:
        print(f"\n[simulación] Todo válido. Esto se registraría en {excel}:\n")
        for c in tanda["clips"]:
            fmt = c.get("formato") or "reel"
            for pid, b in c["plataformas"].items():
                print(f"── {c['clip']} · {config.FORMATOS[fmt]} · {p.nombre_plataforma(pid)}")
                if b.get("titulo"):
                    print(f"Título: {b['titulo']}")
                print(tnd.texto_para_pegar(p, pid, b, fmt) + "\n")
        return 0

    if esta_bloqueado(excel):
        print(f"[!] El Excel está abierto: {excel}\n    Ciérralo y repite la orden (no se ha escrito nada).")
        return 2

    hoy = dt.date.today()
    resumen = []
    for c in tanda["clips"]:
        fmt = c.get("formato") or "reel"
        ruta = Path(c["ruta"]) if c.get("ruta") else None
        id_clip = reg.id_de_clip(c["clip"]) or reg.siguiente_id()
        extras = {}
        for campo in p.campos_extra():
            val = (c.get("extra") or {}).get(campo["id"]) or ""
            extras[campo["columna"]] = (p.valores_campo(campo) or {}).get(val, val)
        for pid, b in c["plataformas"].items():
            nombre_plat = p.nombre_plataforma(pid)
            fila = reg.buscar(c["clip"], nombre_plat)
            texto = tnd.texto_para_pegar(p, pid, b, fmt)
            datos = {
                "ID": id_clip, "Clip": c["clip"], "Plataforma": nombre_plat,
                "Tema": c["tema"].strip(), **extras,
                "Título": (b.get("titulo") or "").strip() or None,
                "Copy": b["copy"].strip(),
                "Hashtags": " ".join(tnd.hashtags_finales(p, pid, b.get("hashtags") or [])),
                "Texto para pegar": texto, "Nº caracteres": len(texto),
            }
            if fila is None:
                datos.update({"Estado": "Pendiente", "Fecha alta": hoy, "Formato": config.FORMATOS[fmt]})
            elif not reg.ws.cell(row=fila, column=reg.col["Formato"]).value:
                datos["Formato"] = config.FORMATOS[fmt]  # lo que haya a mano, se respeta
            fila = reg.escribir(fila, datos)
            reg.enlazar(fila, ruta)
        resumen.append((id_clip, c, ruta, fmt))

    try:
        reg.guardar()
    except RegistroBloqueado as e:
        print(f"[!] {e}")
        return 2

    print(f"[OK] Registrado en {excel}")
    for id_clip, c, ruta, fmt in resumen:
        destino = None
        if not args.sin_txt and ruta:
            destino = txt.escribir(p, ruta, _filas_de_clip(reg, c["clip"]))
        donde = (f"{destino.parent.name}\\{destino.name}" if fmt == "carrusel" else destino.name) if destino else ""
        print(f"  {id_clip}  {config.FORMATOS[fmt]:<9} {c['clip']}  [{', '.join(c['plataformas'])}]"
              + (f"  → {donde}" if destino else "  (sin .txt)"))

    tanda["registrada"] = dt.datetime.now().isoformat(timespec="seconds")
    tanda["registro"] = str(excel)
    escribir_json(entrada, tanda)
    if p.calendario_activo:
        print(f"\nSiguiente: copys.py calendario planificar --proyecto {p.id}  (fecha y hora de publicación para lo registrado)")
    return 0


def cmd_sincronizar(args) -> int:
    p = _proyecto(args.proyecto)
    excel = _excel(args, p)
    pend = _carpeta(p, args.pendiente, p.carpeta_pendiente, "--pendiente")
    publ = _carpeta(p, args.publicado, p.carpeta_publicado, "--publicado")
    if not excel.exists():
        print(f"Aún no hay registro para {p.nombre} ({excel}).")
        return 0
    faltan = [str(c) for c in (pend, publ) if c and not c.exists()]
    if faltan:
        print(f"  aviso: no existe {' ni '.join(faltan)} (la crea el CEO): lo que estuviera ahí saldrá como No encontrado.")

    # Reels (MP4) y carruseles (carpetas con carrusel.json), por nombre; si está en las dos, manda Publicados.
    donde: dict[str, tuple[Path, str]] = {}
    for base, sitio in ((pend, "pendiente"), (publ, "publicado")):
        for f in _clips_en(base, recursivo=True):
            donde[f.name.lower()] = (f, sitio)
        for d in car.carruseles_en(base, recursivo=True):
            donde[d.name.lower()] = (d, sitio)

    reg = Registro(excel, p)
    hoy = dt.date.today()
    cambios, txt_rehechos, formato_puesto = [], set(), 0
    for fila, d in reg.filas():
        clip = str(d.get("Clip") or "")
        estado = d.get("Estado") or "Pendiente"
        fmt = formato_de_fila(d)
        if not d.get("Formato"):
            reg.escribir(fila, {"Formato": config.FORMATOS[fmt]})  # Excel antiguo: se rellena el hueco
            formato_puesto += 1
        hallado = donde.get(clip.lower())
        if not hallado:
            if estado == "Pendiente":
                reg.escribir(fila, {"Estado": "No encontrado"})
                cambios.append(f"{d.get('ID')} {clip} [{d.get('Plataforma')}]: Pendiente → No encontrado")
            continue
        ruta, sitio = hallado
        if str(d.get("Ruta") or "") != str(ruta.resolve()):
            antigua = Path(str(d.get("Ruta") or ""))
            reg.enlazar(fila, ruta)
            cambios.append(f"{d.get('ID')} {clip} [{d.get('Plataforma')}]: ruta → {ruta.parent.name}")
            txt_viejo = txt.ruta_txt(antigua, fmt) if d.get("Ruta") else None
            if txt_viejo and txt_viejo.exists() and not antigua.exists():
                txt_viejo.unlink()  # el .txt se quedó atrás al mover el MP4; se rehace junto al MP4
        nuevo = None
        if sitio == "publicado" and estado in ("Pendiente", "No encontrado"):
            nuevo = "Publicado"
            if not d.get("Fecha publicación"):
                reg.escribir(fila, {"Fecha publicación": hoy})
        elif sitio == "pendiente" and estado == "No encontrado":
            nuevo = "Pendiente"
        if nuevo:
            reg.escribir(fila, {"Estado": nuevo})
            cambios.append(f"{d.get('ID')} {clip} [{d.get('Plataforma')}]: {estado} → {nuevo}")
        if not txt.ruta_txt(ruta, fmt).exists():
            txt_rehechos.add((clip, ruta))

    if cambios or formato_puesto or reg.columnas_nuevas:
        try:
            reg.guardar()
        except RegistroBloqueado as e:
            print(f"[!] {e}")
            return 2
    for clip, ruta in sorted(txt_rehechos):
        txt.escribir(p, ruta, _filas_de_clip(reg, clip))

    print(f"Sincronizado {p.nombre}: {len(cambios)} cambio(s), {len(txt_rehechos)} .txt regenerado(s).")
    if reg.columnas_nuevas:
        print(f"  columnas añadidas al Excel: {', '.join(reg.columnas_nuevas)}")
    if formato_puesto:
        print(f"  Formato rellenado en {formato_puesto} fila(s) que lo tenían vacío.")
    for c in cambios:
        print(f"  - {c}")
    return 0


def cmd_ver(args) -> int:
    p = _proyecto(args.proyecto)
    excel = _excel(args, p)
    if not excel.exists():
        print(f"Aún no hay registro para {p.nombre} ({excel}).")
        return 0
    reg = Registro(excel, p)
    filas = [d for _, d in reg.filas()]
    if args.clip:
        q = args.clip.lower()
        filas = [d for d in filas if q in str(d.get("Clip") or "").lower() or q == str(d.get("ID") or "").lower()]
        for d in filas:
            fmt = config.FORMATOS[formato_de_fila(d)]
            prevista = cal.a_fecha(d.get("Fecha prevista"))
            plan = f" · previsto {prevista:%d/%m/%Y} {cal.hhmm(cal.a_hora(d.get('Hora prevista')))}" if prevista else ""
            print(f"── {d.get('ID')} · {d.get('Clip')} · {fmt} · {d.get('Plataforma')} · {d.get('Estado')}{plan}")
            if d.get("Título"):
                print(f"Título: {d['Título']}")
            print(f"{d.get('Texto para pegar')}\n")
        if not filas:
            print("Sin coincidencias.")
        return 0
    por_estado: dict[str, int] = {}
    for d in filas:
        k = f"{d.get('Plataforma')} · {config.FORMATOS[formato_de_fila(d)]} · {d.get('Estado')}"
        por_estado[k] = por_estado.get(k, 0) + 1
    print(f"{p.nombre}: {len({d.get('ID') for d in filas})} pieza(s), {len(filas)} fila(s) · {excel}")
    for k, n in sorted(por_estado.items()):
        print(f"  {k}: {n}")
    return 0


def cmd_banco(args) -> int:
    p = _proyecto(args.proyecto)
    excel = _excel(args, p)
    usados: list[str] = []
    if excel.exists():
        usados = [normalizar(str(d.get("Copy") or "")) for _, d in Registro(excel, p).filas()]
    print(f"Banco de copys de {p.nombre} (proyectos/{p.id}/banco_copys.json)")

    def veces(copy: str) -> int:
        n = normalizar(copy)
        return sum(1 for u in usados if n and n in u)

    grupos = {"genericos": p.banco.get("genericos") or []}
    grupos.update(p.banco.get("por_oferta") or {})
    if args.oferta:
        grupos = {k: v for k, v in grupos.items() if k == args.oferta}
    for grupo, copys in grupos.items():
        print(f"\n[{grupo}]")
        for i, c in enumerate(copys, 1):
            v = veces(c)
            print(f"  {i:>2}. {'(usado ' + str(v) + ')' if v else '(libre)':<10} {c}")
    return 0


def cmd_auditar(args) -> int:
    """Solo informe: no reescribe nada. Checklist en referencias/auditoria_copy.md.

    --solo-estilo: solo estilo y emojis (+ cebos y cierres vacíos): sin gancho, CTA, hashtags ni
    longitud. Lo usa TheHistoria para el texto de las slides. --json: lista JSON por stdout.
    """
    def fallo(msg: str) -> int:
        print(msg, file=sys.stderr if args.json else sys.stdout)
        return 2

    if sum(bool(x) for x in (args.entrada, args.texto, args.banco)) != 1:
        return fallo("[!] Usa una (y solo una) de: --entrada <tanda>, --texto \"...\" o --banco.")
    items = []  # (etiqueta, copy, conf_plataforma, nombre_plataforma, contexto)
    p = None
    if args.entrada:
        tanda = leer_json(Path(args.entrada))
        p = _proyecto_de_tanda(tanda, args.proyecto)
        for c in tanda.get("clips") or []:
            fmt = c.get("formato") or "reel"
            for pid, b in (c.get("plataformas") or {}).items():
                if pid in (p.conf.get("plataformas") or {}):
                    nombre = p.nombre_plataforma(pid)
                    conf = p.conf_formato(pid, fmt) if p.admite(pid, fmt) else p.plataforma(pid)
                    items.append((f"{c.get('clip')} · {nombre}", b.get("copy") or "", conf, nombre, c.get("contexto")))
    else:
        try:
            p = _proyecto(args.proyecto)
            pid = args.plataforma or p.plataformas_activas()[0]
            conf, nombre = p.plataforma(pid), p.nombre_plataforma(pid)
        except proy.ErrorProyecto:
            if not (args.solo_estilo and args.texto):
                raise
            conf, nombre = {"emojis_max": 0}, ""  # sin proyecto claro: estilo con 0 emojis
        if args.texto:
            items.append(("texto", args.texto, conf, nombre, None))
        else:
            grupos = {"genericos": p.banco.get("genericos") or []}
            grupos.update(p.banco.get("por_oferta") or {})
            for grupo, copys in grupos.items():
                for i, copy in enumerate(copys, 1):
                    items.append((f"{grupo} {i}", copy, conf, nombre, None))

    resultados = [(et, copy, audit.auditar(copy, conf, ctx, nombre, solo_estilo=args.solo_estilo))
                  for et, copy, conf, nombre, ctx in items]
    hay_error = any(h.nivel == "error" for _, _, hs in resultados for h in hs)

    if args.json:
        lista = []
        for et, _, hs in resultados:
            for h in hs:
                d = {"nivel": h.nivel, "regla": h.regla, "fragmento": h.fragmento, "mensaje": h.mensaje}
                if not args.texto:
                    d["pieza"] = et
                lista.append(d)
        # ASCII puro: se lee bien desde cualquier consola o subprocess de Windows
        print(json.dumps(lista, ensure_ascii=True))
        return 1 if hay_error else 0

    modo = " · solo estilo" if args.solo_estilo else ""
    print(f"Auditoría{' · ' + p.nombre if p else ''}{modo} · checklist: referencias/auditoria_copy.md")
    n_err = n_av = n_ok = 0
    for etiqueta, copy, hs in resultados:
        errores = [h for h in hs if h.nivel == "error"]
        avisos = [h for h in hs if h.nivel == "aviso"]
        n_err += bool(errores)
        n_av += bool(avisos) and not errores
        n_ok += not errores and not avisos
        if args.banco and not hs:
            continue  # en el banco solo se enseña lo marcado
        estado = "ERROR" if errores else ("AVISO" if avisos else "OK")
        print(f"\n[{estado}] {etiqueta}\n  {copy}")
        for h in hs:
            print(f"    {h.nivel.upper():<8}{h.mensaje}")
    print(f"\n{len(items)} texto(s): {n_err} con error · {n_av} con avisos de estilo · {n_ok} limpios.")
    if n_err or n_av:
        print("Corrige reescribiendo: los errores bloquean el registro y los avisos de estilo se arreglan antes "
              "de registrar (solo se dejan si la frase es literal del clip).")
    return 1 if hay_error else 0


def cmd_hashtags(args) -> int:
    """Banco temático por tamaño, reglas de la plataforma y últimos conjuntos usados."""
    p = _proyecto(args.proyecto)
    pid = args.plataforma or p.plataformas_activas()[0]
    nombre, reglas = p.nombre_plataforma(pid), (p.plataforma(pid).get("hashtags") or {})
    fijos = p.fijos(pid)
    fijos_txt = " ".join(f"{t} ({p.tamano_hashtag(t) or '?'})" for t in fijos) or "(ninguno)"
    partes = [f"fijos: {fijos_txt}",
              f"temáticos {reglas.get('tematicos_min', 0)}–{reglas.get('tematicos_max', '…')}"]
    tmax = reglas.get("total_max") or reglas.get("max_total")
    if reglas.get("total_min") or tmax:
        partes.append(f"total {reglas.get('total_min', 0)}–{tmax or '…'} con los fijos")
    if "nicho_min" in reglas:
        partes.append(f"mín. {reglas['nicho_min']} de nicho")
    if "amplios_max" in reglas:
        partes.append(f"máx. {reglas['amplios_max']} amplio(s)")
    print(f"{p.nombre} · {nombre}: " + " · ".join(partes))
    if p.hashtags.get("_tamanos"):
        print(f"Tamaños: {p.hashtags['_tamanos']}")
    for tema, g in p.banco_por_tamano().items():
        if args.tema and tema != args.tema:
            continue
        print(f"\n[{tema}]")
        for tam in ("nicho", "medio", "amplio", "sin_tamano"):
            if g[tam]:
                print(f"  {tam:<10} {' '.join(g[tam])}")
    excel = _excel(args, p)
    if excel.exists():
        n = int(reglas.get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0)
        ult = _hashtags_recientes(p, Registro(excel, p)).get(pid, [])[-n:] if n else []
        if ult:
            print(f"\nÚltimos {len(ult)} conjuntos de temáticos en {nombre} (no repetirlos):")
            for clip, s in ult:
                print(f"  {clip}: {' '.join(sorted(s)) or '(sin temáticos)'}")
    return 0


# ---------------------------------------------------------------- calendario
def cmd_calendario(args) -> int:
    p = _proyecto(args.proyecto)
    cfg = cal.Conf(p)
    if not cfg.activo:
        print(f"[!] El calendario de {p.nombre} está desactivado (proyecto.json → calendario.activo).")
        return 1
    excel = _excel(args, p)
    carpeta_hist = _carpeta(p, args.carpeta_historias, p.carpeta_historias, "--carpeta-historias")
    hoy = cal.hoy_en(cfg.zona)
    if not excel.exists():
        msg = f"Aún no hay registro para {p.nombre} ({excel}): no hay piezas en el calendario."
        if carpeta_hist and not carpeta_hist.exists():
            msg += f" Tampoco existe la carpeta de historias {carpeta_hist} (la crea el CEO)."
        print(json.dumps({"aviso": msg}, ensure_ascii=True) if getattr(args, "json", False) else msg)
        return 0
    acciones = {"planificar": _cal_planificar, "hoy": _cal_hoy, "ver": _cal_ver}
    return acciones[args.accion](args, p, cfg, excel, carpeta_hist, hoy)


def _cal_planificar(args, p, cfg, excel: Path, carpeta_hist: Path | None, hoy: dt.date) -> int:
    inicio = _fecha_arg(args.desde, "--desde") or hoy + dt.timedelta(days=1)
    semanas = args.semanas or cfg.semanas
    reg = Registro(excel, p)
    piezas = cal.piezas_de_registro(p, reg, BuscadorMetadatos(p))
    ilegibles = [pz for pz in piezas if pz.fecha is None and _celda_llena(reg, pz, "Fecha prevista")]
    for pz in ilegibles:
        pz.estado = "Descartado"  # no se planifica (ni se pisa lo escrito) hasta que se corrija
    res = cal.planificar(p, piezas, inicio, semanas, hoy, args.replanificar_atrasados)
    fin = res["fin"]

    hist = None
    if carpeta_hist:
        hist = cal.asignar_historias(reg.historias(), cal.archivos_historias(carpeta_hist), inicio, fin, hoy, cfg,
                                     args.replanificar_atrasados)
        hist_por_dia = hist["por_dia"]
    else:
        hist_por_dia = cal.historias_por_dia(reg.historias())
    vivas = [pz for pz in piezas if pz not in ilegibles]
    semanas_l = [cal.lunes(inicio) + k * cal.UNA_SEMANA for k in range(max(1, semanas))]
    balances = [cal.balance(w, vivas, cfg, inicio, fin, hist_por_dia, inicio) for w in semanas_l]
    dir_cal = excel.parent / "calendario"
    mds = {b["semana"]: dir_cal / f"{b['semana']}.md" for b in balances}

    if not args.simular:
        if esta_bloqueado(excel):
            msg = f"El Excel está abierto: {excel}. Ciérralo y repite la orden (no se ha escrito nada)."
            print(json.dumps({"error": msg}, ensure_ascii=True) if args.json else f"[!] {msg}")
            return 2
        plan = reg.plan_auto()
        for pz in vivas:
            if pz.estado == "Descartado":
                continue
            for fila in pz.filas:
                celda = lambda col: reg.ws.cell(row=fila, column=reg.col[col]).value
                datos = {}
                if pz.nueva:
                    datos = {"Fecha prevista": pz.fecha, "Hora prevista": pz.hora}
                else:  # solo se rellena lo vacío: lo escrito a mano se respeta
                    if pz.fecha and celda("Fecha prevista") in (None, ""):
                        datos["Fecha prevista"] = pz.fecha
                    if pz.hora and celda("Hora prevista") in (None, ""):
                        datos["Hora prevista"] = pz.hora
                if celda("Formato") in (None, ""):
                    datos["Formato"] = config.FORMATOS[pz.formato]
                if datos:
                    reg.escribir(fila, datos)
            if pz.nueva:
                plan[pz.id] = (pz.fecha.isoformat(), cal.hhmm(pz.hora))
        ids = {pz.id for pz in piezas}
        reg.escribir_plan_auto({k: v for k, v in plan.items() if k in ids})
        if hist is not None:
            reg.escribir_historias([(f, a, str(carpeta_hist)) for a, f in hist["asignacion"].items()])
        try:
            reg.guardar()
        except RegistroBloqueado as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=True) if args.json else f"[!] {e}")
            return 2
        dir_cal.mkdir(parents=True, exist_ok=True)
        for b in balances:
            mds[b["semana"]].write_text(cal.md_semana(p, cfg, b, vivas, hist_por_dia, carpeta_hist, hoy, inicio),
                                        encoding="utf-8")

    if args.json:
        out = {
            "proyecto": p.id, "simulacion": bool(args.simular), "hoy": hoy.isoformat(),
            "desde": inicio.isoformat(), "hasta": fin.isoformat(), "excel": str(excel),
            "asignadas": [pz.resumen() for pz in res["asignadas"]],
            "replanificadas": [{**pz.resumen(), "fecha_antes": pz.fecha_antes.isoformat()} for pz in res["movidas"]],
            "horas_puestas": [pz.resumen() for pz in res["horas"]],
            "atrasadas": [pz.resumen() for pz in res["atrasadas"] + res["atrasadas_manuales"]],
            "sin_hueco": [pz.resumen() for pz in res["sin_hueco"]],
            "fecha_ilegible": [{"id": pz.id, "pieza": pz.clip} for pz in ilegibles],
            "historias": None if hist is None else {
                "carpeta": str(carpeta_hist), "nuevas": hist["nuevas"], "sin_dia": hist["sin_dia"],
                "atrasadas": hist["atrasadas"], "replanificadas": hist["movidas"]},
            "semanas": [cal.balance_json(b, None if args.simular else mds[b["semana"]]) for b in balances],
            "faltan": {b["semana"]: {"reels": b["faltan"]["reel"], "carruseles": b["faltan"]["carrusel"],
                                     "cualquiera": b["faltan"]["cualquiera"], "huecos": len(b["huecos"]),
                                     "historias": b["historias_faltan"]} for b in balances},
        }
        print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
        return 0

    print(f"Calendario {p.nombre} · desde {cal.dia_corto(inicio)}/{inicio:%Y} · {len(balances)} semana(s): "
          f"{balances[0]['semana']} a {balances[-1]['semana']}" + ("  [simulación: no se escribe nada]" if args.simular else ""))
    if res["asignadas"]:
        print(f"\nAsignadas {len(res['asignadas'])} pieza(s):")
        for pz in sorted(res["asignadas"], key=lambda x: x.momento):
            antes = f"  (antes {pz.fecha_antes:%d/%m}, atrasada)" if pz.fecha_antes else ""
            print(f"  {cal.dia_corto(pz.fecha)} {cal.hhmm(pz.hora)}  {pz.fmt:<9} {pz.id}  {pz.clip:<34} "
                  f"{pz.objetivo or '—'} · {pz.pilar or '—'}{antes}")
    else:
        print("\nNada nuevo que colocar (todo lo pendiente ya tiene fecha).")
    if res["horas"]:
        print("Hora puesta a piezas con fecha manual sin hora: "
              + ", ".join(f"{pz.id} {cal.hhmm(pz.hora)}" for pz in res["horas"]))
    atras = res["atrasadas"] + res["atrasadas_manuales"]
    if atras:
        extra = ("fecha puesta a mano: no se mueven" if args.replanificar_atrasados
                 else "no se mueven; --replanificar-atrasados mueve las que puso el planificador")
        print(f"ATRASADAS sin publicar ({extra}): "
              + ", ".join(f"{pz.id} ({pz.fecha:%d/%m})" for pz in atras))
    if res["sin_hueco"]:
        print(f"Sin hueco en estas semanas (amplía --semanas): {', '.join(pz.id for pz in res['sin_hueco'])}")
    if ilegibles:
        print("Fecha prevista que no se entiende (usa dd/mm/aaaa; no se toca): "
              + ", ".join(f"{pz.id}" for pz in ilegibles))
    if hist is not None and not carpeta_hist.exists():
        print(f"Historias: [!] no existe la carpeta {carpeta_hist}")
    elif hist is not None:
        print(f"Historias: {hist['nuevas']} asignada(s) nuevas · {len(hist['sin_dia'])} sin día"
              + (f" · {len(hist['atrasadas'])} atrasada(s)" if hist["atrasadas"] else "")
              + f" · carpeta: {carpeta_hist}")
    else:
        print("Historias: sin carpeta configurada (calendario.historias.carpeta).")
    print()
    for b in balances:
        print(cal.linea_semana(b))
        if b["avisos"]:
            print("  avisos: " + "; ".join(b["avisos"]))
        if not args.simular:
            print(f"  → {mds[b['semana']]}")
    print(cal.linea_faltan(balances))
    return 0


def _celda_llena(reg: Registro, pz, col: str) -> bool:
    return any(reg.ws.cell(row=f, column=reg.col[col]).value not in (None, "") for f in pz.filas)


def _cal_hoy(args, p, cfg, excel: Path, carpeta_hist: Path | None, hoy: dt.date) -> int:
    fecha = _fecha_arg(args.fecha, "--fecha") or hoy
    reg = Registro(excel, p)
    piezas = cal.piezas_de_registro(p, reg)
    print(cal.texto_hoy(p, cfg, piezas, fecha, hoy, cal.historias_por_dia(reg.historias()), carpeta_hist))
    return 0


def _cal_ver(args, p, cfg, excel: Path, carpeta_hist: Path | None, hoy: dt.date) -> int:
    reg = Registro(excel, p)
    piezas = cal.piezas_de_registro(p, reg)
    hist_por_dia = cal.historias_por_dia(reg.historias())
    manana = hoy + dt.timedelta(days=1)
    if args.semana:
        try:
            semanas = [cal.lunes_de_semana(args.semana)]
        except ValueError as e:
            print(f"[!] {e}")
            return 1
    else:
        w0 = cal.lunes(hoy)
        futuras = [cal.lunes(pz.cuando) for pz in piezas
                   if pz.estado != "Descartado" and pz.cuando and pz.cuando >= hoy]
        n = min(((max(futuras, default=w0) - w0).days // 7) + 1, 8)
        semanas = [w0 + k * cal.UNA_SEMANA for k in range(n)]
    print(f"Calendario {p.nombre} · hoy {cal.dia_corto(hoy)}/{hoy:%Y}")
    for w in semanas:
        b = cal.balance(w, piezas, cfg, manana, dt.date.max, hist_por_dia, hoy)
        print("\n" + cal.linea_semana(b))
        lineas = [(pz.momento, f"  {cal.dia_corto(pz.cuando)} {cal.hhmm(pz.hora) or '--:--'}  {pz.fmt:<9} {pz.id}  "
                               f"{pz.clip:<34} {pz.objetivo or '—'} · {pz.pilar or '—'}{cal._marca(pz, hoy)}")
                  for pz in b["piezas"]]
        lineas += [(dt.datetime.combine(d, h), f"  {cal.dia_corto(d)} {cal.hhmm(h)}  (hueco libre)") for d, h in b["huecos"]]
        for _, linea in sorted(lineas, key=lambda x: x[0]):
            print(linea)
        dias_h = [f"{config.DIAS[i]} {n}" for i, n in enumerate(b["historias_por_dia"].values())]
        print(f"  historias: {b['historias']} ({', '.join(dias_h)})")
        if b["avisos"]:
            print("  avisos: " + "; ".join(b["avisos"]))
    atras = sorted((pz for pz in piezas if pz.atrasada(hoy)), key=lambda x: x.momento)
    if atras:
        print(f"\nATRASADO ({len(atras)}): previsto antes de hoy y sin publicar")
        for pz in atras:
            print(f"  {cal.dia_corto(pz.fecha)} {cal.hhmm(pz.hora)}  {pz.fmt:<9} {pz.id}  {pz.clip}"
                  + ("  (fecha manual)" if pz.manual else ""))
    sin = [pz for pz in piezas if pz.estado == "Pendiente" and not pz.fecha]
    ilegibles = [pz for pz in sin if _celda_llena(reg, pz, "Fecha prevista")]
    sin = [pz for pz in sin if pz not in ilegibles]
    if ilegibles:
        print("\nFecha prevista que no se entiende (usa dd/mm/aaaa): " + ", ".join(pz.id for pz in ilegibles))
    if sin:
        print(f"\nSin fecha: {len(sin)} pieza(s) ({', '.join(pz.id for pz in sin)}) → copys.py calendario planificar")
    return 0


def cmd_nuevo_proyecto(args) -> int:
    """Crea proyectos/<id>/ desde la plantilla (solo en TheCopy) y dice qué falta rellenar.

    Las carpetas del CEO (REVISADOS/<id>, HISTORIAS/<id>) NO se crean aquí: si faltan, se avisa.
    """
    proy.valida_id(args.id)
    if args.prefijo and args.prefijo.upper() in proy.prefijos_usados():
        raise proy.ErrorProyecto(f"El prefijo {args.prefijo.upper()} ya lo usa el proyecto "
                                 f"'{proy.prefijos_usados()[args.prefijo.upper()]}': elige otro con --prefijo.")
    destino, ceo = proy.crear(args.id, args.nombre, args.prefijo, args.tipo)
    p = proy.Proyecto(args.id)
    print(f"[OK] Proyecto '{p.id}' creado en {destino}")
    print(f"  nombre: {p.nombre} · tipo: {p.tipo or '(sin tipo)'} · IDs: {p.prefijo_id}-0001… · "
          f"registro: {p.registro_path.name}")
    if ceo:
        print(f"  (nombre/tipo/prefijo/descripción tomados del índice del CEO: {config.INDICE_PROYECTOS.name})")
        plats_ceo = [x for x in (ceo.get("plataformas") or []) if x not in p.plataformas_activas()]
        if plats_ceo:
            print(f"  aviso: el índice del CEO dice plataformas {', '.join(ceo['plataformas'])}; aquí solo están "
                  f"activas {', '.join(p.plataformas_activas())}. Actívalas cuando Sergio confirme fijos y CTA.")
    else:
        print(f"  aviso: '{p.id}' no está en el índice del CEO ({config.INDICE_PROYECTOS}); lo da de alta el CEO.")
    otro = proy.prefijos_usados(excepto=p.id).get(p.prefijo_id)
    if otro:
        print(f"  aviso: el prefijo {p.prefijo_id} ya lo usa '{otro}': cámbialo en proyecto.json → prefijo_id.")

    print("\nCarpetas (las del CEO las crea el CEO):")
    for que, c in (("pendiente", p.carpeta_pendiente), ("publicado", p.carpeta_publicado),
                   ("historias", p.carpeta_historias)):
        print(f"  {que:<10} {c}  " + ("[ok]" if c and c.exists() else "[NO EXISTE: avisa al CEO]"))
    for c, transicion in p.carpetas_contexto():
        if not transicion:
            print(f"  {'contexto':<10} {c}  " + ("[ok]" if c.exists() else "[aún no existe: la crean TheEditor/el CEO]"))

    print("\nFalta rellenar (pregunta a Sergio lo que no sepas; no lo inventes):")
    for x in p.sin_rellenar():
        print(f"  - {x}")
    print(f"\nArchivos: {destino}\\proyecto.json · ofertas.json · hashtags.json · banco_copys.json")
    return 0


# ---------------------------------------------------------------- CLI
def main() -> int:
    forzar_utf8()
    ap = argparse.ArgumentParser(description="TheCopy: copys + hashtags de Reels y carruseles, con registro y calendario.")
    sub = ap.add_subparsers(dest="orden", required=True)

    sub.add_parser("proyectos", help="Lista los proyectos y sus plataformas activas.")

    s = sub.add_parser("pendientes", help="Crea una tanda con las piezas (Reels y carruseles) que aún no tienen copy.")
    s.add_argument("--proyecto")
    s.add_argument("--carpeta", help="Carpeta de piezas (def. la 'pendiente' del proyecto).")
    s.add_argument("--clip", action="append", help="Solo esta pieza: MP4 o carpeta de carrusel (repetible).")
    s.add_argument("--plataformas", help="Lista separada por comas (def. las activas).")
    s.add_argument("--incluir-registrados", action="store_true", help="Incluye piezas que ya tienen copy.")
    s.add_argument("--excel", help="Registro alternativo (pruebas).")
    s.add_argument("--salida", help="Ruta del JSON de la tanda.")

    s = sub.add_parser("registrar", help="Valida una tanda rellena y la registra (Excel + .txt).")
    s.add_argument("--entrada", required=True)
    s.add_argument("--proyecto", help="Opcional: si se da, tiene que ser el de la tanda.")
    s.add_argument("--excel", help="Registro alternativo (pruebas).")
    s.add_argument("--simular", action="store_true", help="Solo valida y muestra; no escribe nada.")
    s.add_argument("--reemplazar", action="store_true", help="Sobrescribe el copy de piezas ya registradas.")
    s.add_argument("--sin-txt", action="store_true", help="No escribe el .txt.")

    s = sub.add_parser("sincronizar", help="Actualiza Estado/ruta según dónde esté cada MP4 o carpeta de carrusel.")
    s.add_argument("--proyecto")
    s.add_argument("--excel")
    s.add_argument("--pendiente", help="Carpeta pendiente alternativa.")
    s.add_argument("--publicado", help="Carpeta publicados alternativa.")

    s = sub.add_parser("ver", help="Resumen del registro o el copy de una pieza/ID.")
    s.add_argument("clip", nargs="?")
    s.add_argument("--proyecto")
    s.add_argument("--excel")

    s = sub.add_parser("banco", help="Copys del banco del proyecto y cuántas veces se han usado.")
    s.add_argument("--proyecto")
    s.add_argument("--oferta")
    s.add_argument("--excel", help="Registro alternativo (pruebas).")

    s = sub.add_parser("auditar", help="Audita copys (gancho, cebos, estilo). Solo informe, no reescribe.")
    s.add_argument("--entrada", help="Tanda JSON (usa el contexto de la pieza para las frases literales).")
    s.add_argument("--texto", help="Un texto suelto.")
    s.add_argument("--banco", action="store_true", help="Audita banco_copys.json del proyecto.")
    s.add_argument("--proyecto", help="Para --texto/--banco; con --entrada, si se da, tiene que ser el de la tanda.")
    s.add_argument("--plataforma", help="Reglas de esta plataforma para --texto/--banco (def. la 1.ª activa).")
    s.add_argument("--solo-estilo", action="store_true",
                   help="Solo estilo y emojis (+ cebos y cierres vacíos): sin gancho, CTA, hashtags ni longitud.")
    s.add_argument("--json", action="store_true",
                   help="Lista JSON de {nivel, regla, fragmento, mensaje} por stdout. Sale con 1 si hay errores.")

    s = sub.add_parser("hashtags", help="Banco de hashtags por tamaño, reglas y últimos conjuntos usados.")
    s.add_argument("--proyecto")
    s.add_argument("--plataforma", help="Def. la 1.ª activa.")
    s.add_argument("--tema", help="Solo este tema del banco.")
    s.add_argument("--excel", help="Registro alternativo (pruebas).")

    s = sub.add_parser("calendario", help="Calendario de publicación: planificar, hoy, ver.")
    cs = s.add_subparsers(dest="accion", required=True)

    def comunes(x):
        x.add_argument("--proyecto")
        x.add_argument("--excel", help="Registro alternativo (pruebas). Los .md van a <carpeta del Excel>/calendario/.")
        x.add_argument("--carpeta-historias", help="Carpeta de historias alternativa (def. calendario.historias.carpeta).")

    c = cs.add_parser("planificar", help="Pone fecha y hora a lo registrado y pendiente sin fecha; reparte historias.")
    comunes(c)
    c.add_argument("--semanas", type=int, help="Semanas a planificar (def. calendario.semanas_por_defecto).")
    c.add_argument("--desde", help="Primer día con huecos (AAAA-MM-DD; def. mañana).")
    c.add_argument("--simular", action="store_true", help="Enseña el plan sin escribir nada.")
    c.add_argument("--replanificar-atrasados", action="store_true",
                   help="Mueve las atrasadas que puso el planificador (las manuales, nunca).")
    c.add_argument("--json", action="store_true", help="Salida JSON (balance y huecos por semana).")
    c = cs.add_parser("hoy", help="Qué toca publicar ese día: pieza, hora, ruta, texto para pegar e historias.")
    comunes(c)
    c.add_argument("--fecha", help="AAAA-MM-DD (def. hoy).")
    c = cs.add_parser("ver", help="Resumen del plan por semanas; marca lo ATRASADO.")
    comunes(c)
    c.add_argument("--semana", help="Solo esta semana (AAAA-Www, p. ej. 2026-W42).")

    s = sub.add_parser("nuevo-proyecto", help="Da de alta un proyecto desde la plantilla y dice qué falta rellenar.")
    s.add_argument("id", help="Minúsculas y sin espacios (el mismo id que en CEO_Sergete/proyectos.json).")
    s.add_argument("--nombre", help="Nombre visible (def. el del índice del CEO).")
    s.add_argument("--prefijo", help="Prefijo de los IDs, p. ej. MM (def. el del índice del CEO o 3 letras del nombre).")
    s.add_argument("--tipo", choices=list(config.TIPOS), help="largos | clipping (def. el del índice del CEO).")

    args = ap.parse_args()
    ordenes = {"proyectos": cmd_proyectos, "pendientes": cmd_pendientes, "registrar": cmd_registrar,
               "sincronizar": cmd_sincronizar, "ver": cmd_ver, "banco": cmd_banco,
               "auditar": cmd_auditar, "hashtags": cmd_hashtags, "calendario": cmd_calendario,
               "nuevo-proyecto": cmd_nuevo_proyecto}
    try:
        return ordenes[args.orden](args)
    except proy.ErrorProyecto as e:
        print(f"[!] {e}", file=sys.stderr if getattr(args, "json", False) else sys.stdout)
        return 1
    except RegistroBloqueado as e:
        print(f"[!] {e}", file=sys.stderr if getattr(args, "json", False) else sys.stdout)
        return 2


if __name__ == "__main__":
    sys.exit(main())

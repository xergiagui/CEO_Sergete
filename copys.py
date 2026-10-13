"""
TheCopy — copys y hashtags de los clips, relacionados en un registro.

Flujo normal (lo lleva el subagente `copy` de CEO_Sergete):
  1. copys.py pendientes            → tanda JSON con los clips sin copy + su contexto
  2. (el subagente rellena la tanda: tema, oferta, copy y hashtags temáticos)
  3. copys.py registrar --entrada <tanda>   → valida → Excel + <clip>.txt junto al MP4
  4. copys.py sincronizar           → Estado/ruta según la carpeta donde esté cada MP4

Ejecuta con el entorno propio:  .venv\\Scripts\\python.exe copys.py <orden> ...
(El script NO se llama copy.py: chocaría con el módulo `copy` de Python.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import config
from lib import proyecto as proy
from lib import tanda as tnd
from lib import txt
from lib.metadatos import BuscadorMetadatos
from lib.registro import Registro, RegistroBloqueado, esta_bloqueado
from lib.util import escribir_json, forzar_utf8, leer_json, normalizar


# ---------------------------------------------------------------- helpers
def _proyecto(pid: str | None) -> proy.Proyecto:
    if not pid:
        disponibles = proy.listar()
        if len(disponibles) != 1:
            raise proy.ErrorProyecto(
                f"Indica --proyecto ({', '.join(disponibles) or 'no hay ninguno'}).")
        pid = disponibles[0]
    return proy.Proyecto(pid)


def _pid_de_nombre(p: proy.Proyecto, nombre: str | None) -> str | None:
    for pid in p.conf.get("plataformas") or {}:
        if p.nombre_plataforma(pid).lower() == str(nombre or "").lower():
            return pid
    return None


def _filas_de_clip(reg: Registro, clip: str) -> list[dict]:
    return [d for _, d in reg.filas() if str(d.get("Clip") or "").lower() == clip.lower()]


def _clips_en(carpeta: Path, recursivo: bool = False) -> list[Path]:
    if not carpeta or not carpeta.exists():
        return []
    it = carpeta.rglob("*") if recursivo else carpeta.iterdir()
    return sorted(f for f in it if f.is_file() and f.suffix.lower() in config.EXT_VIDEO)


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
            print(f"- {pid:<16} {p.nombre}  ·  plataformas activas: {plats}  ·  registro: {p.registro_path.name}")
        except proy.ErrorProyecto as e:
            print(f"- {pid:<16} [config incorrecta] {e}")
    return 0


def cmd_pendientes(args) -> int:
    p = _proyecto(args.proyecto)
    carpeta = Path(args.carpeta) if args.carpeta else p.carpeta_pendiente
    if not carpeta or not carpeta.exists():
        print(f"[!] No existe la carpeta de pendientes: {carpeta}")
        return 1
    plataformas = args.plataformas.split(",") if args.plataformas else p.plataformas_activas()
    for pid in plataformas:
        p.plataforma(pid)  # valida que exista

    clips = _clips_en(carpeta)
    if args.clip:
        quiero = {c.lower() for c in args.clip} | {Path(c).stem.lower() for c in args.clip}
        clips = [c for c in clips if c.name.lower() in quiero or c.stem.lower() in quiero]

    excel = Path(args.excel) if args.excel else p.registro_path
    reg = Registro(excel, p) if excel.exists() else None
    meta = BuscadorMetadatos()
    lote, ya = [], []
    for c in clips:
        faltan = [pid for pid in plataformas
                  if args.incluir_registrados or not (reg and reg.buscar(c.name, p.nombre_plataforma(pid)))]
        if not faltan:
            ya.append(c.name)
            continue
        lote.append((c, meta.contexto(c), faltan))

    salida = Path(args.salida) if args.salida else (
        config.TANDAS_DIR / f"{p.id}_{dt.datetime.now():%Y%m%d_%H%M%S}.json")
    tanda = tnd.esqueleto(p, lote)
    # Clip ya registrado en otra plataforma → mismo tema y campos propios.
    for bloque in tanda["clips"]:
        previas = _filas_de_clip(reg, bloque["clip"]) if reg else []
        if previas:
            bloque["tema"] = previas[0].get("Tema") or ""
            for campo in p.campos_extra():
                visible = previas[0].get(campo["columna"])
                ids = {v: k for k, v in (p.valores_campo(campo) or {}).items()}
                bloque["extra"][campo["id"]] = ids.get(visible, visible) or ""

    print(f"Proyecto {p.nombre} · carpeta: {carpeta}")
    print(f"{len(clips)} clip(s) en la carpeta · {len(ya)} ya tienen copy · {len(lote)} pendiente(s)")
    if not lote:
        return 0

    escribir_json(salida, tanda)
    for c, ctx, faltan in lote:
        info = ctx.get("frase_viral") or ctx.get("titulo") or ctx.get("aviso", "")
        print(f"  - {c.name}  [{', '.join(faltan)}]  {info}")
    print(f"\nTANDA: {salida}")
    return 0


def cmd_registrar(args) -> int:
    entrada = Path(args.entrada)
    tanda = leer_json(entrada)
    p = _proyecto(tanda.get("proyecto"))
    excel = Path(args.excel) if args.excel else p.registro_path
    reg = Registro(excel, p)

    existentes: dict[str, dict[str, str]] = {}
    for _, d in reg.filas():
        pid = _pid_de_nombre(p, d.get("Plataforma"))
        if pid and d.get("Copy"):
            existentes.setdefault(pid, {})[normalizar(str(d["Copy"]))] = str(d.get("Clip"))

    errores, avisos = tnd.validar(p, tanda, existentes)
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
            for pid, b in c["plataformas"].items():
                print(f"── {c['clip']} · {p.nombre_plataforma(pid)}")
                if b.get("titulo"):
                    print(f"Título: {b['titulo']}")
                print(tnd.texto_para_pegar(p, pid, b) + "\n")
        return 0

    if esta_bloqueado(excel):
        print(f"[!] El Excel está abierto: {excel}\n    Ciérralo y repite la orden (no se ha escrito nada).")
        return 2

    hoy = dt.date.today()
    resumen = []
    for c in tanda["clips"]:
        ruta = Path(c["ruta"]) if c.get("ruta") else None
        id_clip = reg.id_de_clip(c["clip"]) or reg.siguiente_id()
        extras = {}
        for campo in p.campos_extra():
            val = (c.get("extra") or {}).get(campo["id"]) or ""
            extras[campo["columna"]] = (p.valores_campo(campo) or {}).get(val, val)
        for pid, b in c["plataformas"].items():
            nombre_plat = p.nombre_plataforma(pid)
            fila = reg.buscar(c["clip"], nombre_plat)
            texto = tnd.texto_para_pegar(p, pid, b)
            datos = {
                "ID": id_clip, "Clip": c["clip"], "Plataforma": nombre_plat,
                "Tema": c["tema"].strip(), **extras,
                "Título": (b.get("titulo") or "").strip() or None,
                "Copy": b["copy"].strip(),
                "Hashtags": " ".join(tnd.hashtags_finales(p, pid, b.get("hashtags") or [])),
                "Texto para pegar": texto, "Nº caracteres": len(texto),
            }
            if fila is None:
                datos.update({"Estado": "Pendiente", "Fecha alta": hoy})
            fila = reg.escribir(fila, datos)
            reg.enlazar(fila, ruta)
        resumen.append((id_clip, c, ruta))

    try:
        reg.guardar()
    except RegistroBloqueado as e:
        print(f"[!] {e}")
        return 2

    print(f"[OK] Registrado en {excel}")
    for id_clip, c, ruta in resumen:
        destino = None
        if not args.sin_txt and ruta:
            destino = txt.escribir(p, ruta, _filas_de_clip(reg, c["clip"]))
        print(f"  {id_clip}  {c['clip']}  [{', '.join(c['plataformas'])}]"
              + (f"  → {destino.name}" if destino else "  (sin .txt)"))

    tanda["registrada"] = dt.datetime.now().isoformat(timespec="seconds")
    tanda["registro"] = str(excel)
    escribir_json(entrada, tanda)
    return 0


def cmd_sincronizar(args) -> int:
    p = _proyecto(args.proyecto)
    excel = Path(args.excel) if args.excel else p.registro_path
    if not excel.exists():
        print(f"Aún no hay registro para {p.nombre} ({excel}).")
        return 0
    pend = Path(args.pendiente) if args.pendiente else p.carpeta_pendiente
    publ = Path(args.publicado) if args.publicado else p.carpeta_publicado

    donde: dict[str, tuple[Path, str]] = {}
    for f in _clips_en(pend, recursivo=True):
        donde[f.name.lower()] = (f, "pendiente")
    for f in _clips_en(publ, recursivo=True):
        donde[f.name.lower()] = (f, "publicado")  # si está en las dos, manda Publicados

    reg = Registro(excel, p)
    hoy = dt.date.today()
    cambios, txt_rehechos = [], set()
    for fila, d in reg.filas():
        clip = str(d.get("Clip") or "")
        estado = d.get("Estado") or "Pendiente"
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
            txt_viejo = antigua.with_suffix(".txt") if d.get("Ruta") else None
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
        if not ruta.with_suffix(".txt").exists():
            txt_rehechos.add((clip, ruta))

    if cambios:
        try:
            reg.guardar()
        except RegistroBloqueado as e:
            print(f"[!] {e}")
            return 2
    for clip, ruta in sorted(txt_rehechos):
        txt.escribir(p, ruta, _filas_de_clip(reg, clip))

    print(f"Sincronizado {p.nombre}: {len(cambios)} cambio(s), {len(txt_rehechos)} .txt regenerado(s).")
    for c in cambios:
        print(f"  - {c}")
    return 0


def cmd_ver(args) -> int:
    p = _proyecto(args.proyecto)
    excel = Path(args.excel) if args.excel else p.registro_path
    if not excel.exists():
        print(f"Aún no hay registro para {p.nombre}.")
        return 0
    reg = Registro(excel, p)
    filas = [d for _, d in reg.filas()]
    if args.clip:
        q = args.clip.lower()
        filas = [d for d in filas if q in str(d.get("Clip") or "").lower() or q == str(d.get("ID") or "").lower()]
        for d in filas:
            print(f"── {d.get('ID')} · {d.get('Clip')} · {d.get('Plataforma')} · {d.get('Estado')}")
            if d.get("Título"):
                print(f"Título: {d['Título']}")
            print(f"{d.get('Texto para pegar')}\n")
        if not filas:
            print("Sin coincidencias.")
        return 0
    por_estado: dict[str, int] = {}
    for d in filas:
        k = f"{d.get('Plataforma')} · {d.get('Estado')}"
        por_estado[k] = por_estado.get(k, 0) + 1
    print(f"{p.nombre}: {len({d.get('ID') for d in filas})} clip(s), {len(filas)} fila(s) · {excel}")
    for k, n in sorted(por_estado.items()):
        print(f"  {k}: {n}")
    return 0


def cmd_banco(args) -> int:
    p = _proyecto(args.proyecto)
    usados: list[str] = []
    if p.registro_path.exists():
        usados = [normalizar(str(d.get("Copy") or "")) for _, d in Registro(p.registro_path, p).filas()]

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


def cmd_nuevo_proyecto(args) -> int:
    destino = proy.crear(args.id, args.nombre, args.prefijo)
    print(f"[OK] Proyecto creado en {destino}")
    print("Rellena: proyecto.json (tono, carpetas, plataformas), ofertas.json, hashtags.json, banco_copys.json.")
    return 0


# ---------------------------------------------------------------- CLI
def main() -> int:
    forzar_utf8()
    ap = argparse.ArgumentParser(description="TheCopy: copys + hashtags de los clips, con registro.")
    sub = ap.add_subparsers(dest="orden", required=True)

    sub.add_parser("proyectos", help="Lista los proyectos y sus plataformas activas.")

    s = sub.add_parser("pendientes", help="Crea una tanda con los clips que aún no tienen copy.")
    s.add_argument("--proyecto")
    s.add_argument("--carpeta", help="Carpeta de clips (def. la 'pendiente' del proyecto).")
    s.add_argument("--clip", action="append", help="Solo este clip (repetible).")
    s.add_argument("--plataformas", help="Lista separada por comas (def. las activas).")
    s.add_argument("--incluir-registrados", action="store_true", help="Incluye clips que ya tienen copy.")
    s.add_argument("--excel", help="Registro alternativo (pruebas).")
    s.add_argument("--salida", help="Ruta del JSON de la tanda.")

    s = sub.add_parser("registrar", help="Valida una tanda rellena y la registra (Excel + .txt).")
    s.add_argument("--entrada", required=True)
    s.add_argument("--excel", help="Registro alternativo (pruebas).")
    s.add_argument("--simular", action="store_true", help="Solo valida y muestra; no escribe nada.")
    s.add_argument("--reemplazar", action="store_true", help="Sobrescribe el copy de clips ya registrados.")
    s.add_argument("--sin-txt", action="store_true", help="No escribe el .txt junto al MP4.")

    s = sub.add_parser("sincronizar", help="Actualiza Estado/ruta según dónde esté cada MP4.")
    s.add_argument("--proyecto")
    s.add_argument("--excel")
    s.add_argument("--pendiente", help="Carpeta pendiente alternativa.")
    s.add_argument("--publicado", help="Carpeta publicados alternativa.")

    s = sub.add_parser("ver", help="Resumen del registro o el copy de un clip/ID.")
    s.add_argument("clip", nargs="?")
    s.add_argument("--proyecto")
    s.add_argument("--excel")

    s = sub.add_parser("banco", help="Copys del banco del proyecto y cuántas veces se han usado.")
    s.add_argument("--proyecto")
    s.add_argument("--oferta")

    s = sub.add_parser("nuevo-proyecto", help="Da de alta un proyecto desde la plantilla.")
    s.add_argument("id")
    s.add_argument("--nombre", required=True)
    s.add_argument("--prefijo", help="Prefijo de los IDs (ej. MM).")

    args = ap.parse_args()
    ordenes = {"proyectos": cmd_proyectos, "pendientes": cmd_pendientes, "registrar": cmd_registrar,
               "sincronizar": cmd_sincronizar, "ver": cmd_ver, "banco": cmd_banco,
               "nuevo-proyecto": cmd_nuevo_proyecto}
    try:
        return ordenes[args.orden](args)
    except proy.ErrorProyecto as e:
        print(f"[!] {e}")
        return 1
    except RegistroBloqueado as e:
        print(f"[!] {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

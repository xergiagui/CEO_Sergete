"""
TheHistoria — CARRUSELES de Instagram (tercera vía).

Valida un plan.json (lo escribe el subagente a partir de un clip/vídeo, un
artículo de TheTextos o un tema), audita el estilo con TheCopy (una sola
llamada), renderiza las slides 1080x1350 y deja la carpeta de salida que lee
TheCopy:

  salidas/<id>/carrusel_<AAAAMMDD-HHMM>_<slug>/
    01.jpg … NN.jpg   1080x1350, JPEG ~92, sRGB, < 8 MB, en orden
    carrusel.json     plan + metadatos (`creado`)
    _vista.jpg        hoja de contacto (solo para revisar)

Re-render del mismo slug: sustituye la salida no aprobada anterior (no se
acumulan carpetas). PROYECTO: manda el `proyecto` del plan; `--proyecto` es
opcional y, si se da, debe coincidir. Maquetación: proyectos/<id>/estilo.json;
colores, handle y emojis: identidad del proyecto (CEO_Sergete/proyectos.json).

Uso:
  python carruseles.py --fuente <video|ruta> [--proyecto ID]    material para el plan
  python carruseles.py --listar [--proyecto ID]                 qué hay hecho y de dónde
  python carruseles.py --plan proyectos/<id>/planes/<slug>.json [--solo-validar]
  python carruseles.py --aprobar <carpeta> [--proyecto ID]      → REVISADOS/<id>/1. pte Publicar
  python carruseles.py --candidatos-portada <video.mp4> [--n 8] [--hoja ruta.jpg]
  (`--destino DIR` en --plan/--aprobar: otra carpeta base, para pruebas)

Ejecuta con el .venv de TheEditor (Pillow + imageio-ffmpeg). No instala nada.
Códigos de salida: 0 OK · 1 errores de validación/QC · 2 uso o fichero ilegible.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

import config
from lib import thecopy
from lib.aprobar import nombre_unico
from lib.carrusel_fuente import fuente_compacta, listado, resolver_fuente
from lib.carrusel_plan import Hallazgo, plan_para_json, validar_material, validar_plan
from lib.proyectos import Proyecto, ProyectoError, proyecto_de_ruta, resolver
from lib.carrusel_render import (Maquetador, NoCabe, candidatos_portada, guardar_jpg,
                                 hoja_contacto, perfil_srgb, preparar_portada)



def _args(argv=None):
    p = argparse.ArgumentParser(description="Genera un CARRUSEL de Instagram (4:5) desde un plan.json.")
    p.add_argument("--plan", help="ruta del plan.json")
    p.add_argument("--fuente", metavar="VIDEO|RUTA",
                   help="imprime el material para escribir el plan (transcripción sin tiempos, "
                        "cortes, clips y campos válidos)")
    p.add_argument("--listar", action="store_true",
                   help="carruseles del proyecto con su estado y vídeos de _Historico")
    p.add_argument("--aprobar", metavar="CARPETA",
                   help="mueve la carpeta del carrusel a REVISADOS/<id>/1. pte Publicar/")
    p.add_argument("--proyecto", default=None,
                   help="id del proyecto (con --plan, opcional: manda el del plan y debe coincidir)")
    p.add_argument("--destino", default=None,
                   help="PRUEBAS: carpeta base alternativa de la salida (--plan) o del "
                        "destino (--aprobar)")
    p.add_argument("--estilo", default=None,
                   help="estilo.json (def. proyectos/<id>/estilo.json)")
    p.add_argument("--auditar", action=argparse.BooleanOptionalAction, default=None,
                   help="auditar el estilo con TheCopy (def.: sí, si TheCopy está)")
    p.add_argument("--solo-validar", action="store_true",
                   help="valida, comprueba que el texto cabe y audita; no escribe nada")
    p.add_argument("--candidatos-portada", metavar="VIDEO",
                   help="lista los fotogramas más nítidos (cara en la mitad superior) "
                        "para elegir `portada_fondo.segundo`; no necesita plan")
    p.add_argument("--n", type=int, default=8, help="nº de candidatos (def. 8)")
    p.add_argument("--hoja", help="dónde guardar la hoja de candidatos (def. carpeta temporal)")
    a = p.parse_args(argv)
    modos = [m for m in ("plan", "fuente", "listar", "aprobar", "candidatos_portada")
             if getattr(a, m)]
    if len(modos) != 1:
        p.error("usa una (y solo una) de: --plan, --fuente, --listar, --aprobar o "
                "--candidatos-portada")
    return a


def _fuente(args) -> int:
    try:
        proyecto = resolver(args.proyecto)
        ruta = resolver_fuente(args.fuente, proyecto)
    except ProyectoError as e:
        print(f"[!] {e}")
        return 2
    texto, tipo, rel = fuente_compacta(ruta, proyecto)
    fuente = {"tipo": tipo, "ruta": rel}
    print(f"# Fuente · proyecto «{proyecto.id}»\n"
          f"\"fuente\": {json.dumps(fuente, ensure_ascii=False)}"
          + (f"   (credito por defecto: «{proyecto.credito_defecto}»)"
             if tipo == "video" and proyecto.credito_defecto else "") + "\n")
    print(texto)
    campos, origen = thecopy.campos(proyecto.id)
    print(f"\n## Campos del plan (de {origen})\n{thecopy.resumen_campos(campos)}")
    return 0


def _listar(args) -> int:
    try:
        proyecto = resolver(args.proyecto)
    except ProyectoError as e:
        print(f"[!] {e}")
        return 2
    print(listado(proyecto))
    return 0


def _aprobar(args) -> int:
    """Mueve la carpeta del carrusel a REVISADOS/<id>/1. pte Publicar/ (nombre único)."""
    arg = Path(args.aprobar)
    carpeta = None
    for cand in ([arg] if arg.is_absolute() else [Path.cwd() / arg, config.PROJECT_ROOT / arg]):
        if (cand / "carrusel.json").exists():
            carpeta = cand.resolve()
            break
    try:
        if carpeta is None:
            proyecto = resolver(args.proyecto)
            cand = proyecto.salidas_dir / arg.name
            if not (cand / "carrusel.json").exists():
                print(f"[!] No encuentro el carrusel «{args.aprobar}» (ni como ruta ni en "
                      f"salidas/{proyecto.id}/).")
                return 2
            carpeta = cand.resolve()
        datos = json.loads((carpeta / "carrusel.json").read_text(encoding="utf-8"))
        pid_json = str(datos.get("proyecto") or "").strip()
        try:
            rel = carpeta.relative_to(config.OUT_DIR.resolve())
            pid_ruta = rel.parts[0] if len(rel.parts) > 1 else ""
        except ValueError:
            pid_ruta = ""
        pids = {x for x in (pid_json, pid_ruta, (args.proyecto or "").strip()) if x}
        if len(pids) > 1:
            print(f"[!] El carrusel no casa con el proyecto (carrusel.json: «{pid_json or '-'}», "
                  f"carpeta: «{pid_ruta or '-'}», --proyecto: «{args.proyecto or '-'}»): "
                  f"no se mezclan proyectos.")
            return 2
        proyecto = resolver(pids.pop() if pids else None)
    except ProyectoError as e:
        print(f"[!] {e}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[!] carrusel.json ilegible ({e.msg}).")
        return 2
    fallos = _qc(carpeta, len(datos.get("slides") or []))
    if fallos:
        print("[X] La carpeta no pasa el QC; no se mueve:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    base = Path(args.destino).resolve() if args.destino else proyecto.revisados_pte
    base.mkdir(parents=True, exist_ok=True)
    destino = nombre_unico(base, carpeta.name)
    shutil.move(str(carpeta), str(destino))
    print(f"[OK] Carrusel aprobado: {destino}")
    extra = f' --carpeta "{base}"' if args.destino else ""
    print("Siguiente (TheCopy, copy + hashtags):\n"
          f"  ..\\TheCopy\\.venv\\Scripts\\python.exe ..\\TheCopy\\copys.py pendientes "
          f"--proyecto {proyecto.id} --clip \"{destino.name}\"{extra}")
    return 0


def _candidatos(args) -> int:
    import tempfile
    from PIL import ImageDraw
    video = Path(args.candidatos_portada)
    if not video.exists():
        print(f"[!] No existe el vídeo: {video}")
        return 2
    cands = candidatos_portada(video, n=max(1, args.n))
    if not cands:
        print("[!] No se pudo leer ningún fotograma.")
        return 2
    print(f"[i] {video.name}: {len(cands)} fotogramas más nítidos (varianza del laplaciano "
          f"en la zona de la cara):")
    for seg, nit, _ in cands:
        print(f"    segundo {seg:>6.1f} · nitidez {nit:7.1f}")
    miniaturas = []
    for seg, nit, im in cands:
        th = im.resize((270, round(270 * im.height / im.width)))
        ImageDraw.Draw(th).text((8, 8), f"s={seg:g}  n={nit:.0f}", fill=(255, 210, 0))
        miniaturas.append(th)
    hoja = Image.new("RGB", (len(miniaturas) * 280, max(m.height for m in miniaturas) + 10),
                     (20, 20, 20))
    for i, m in enumerate(miniaturas):
        hoja.paste(m, (5 + i * 280, 5))
    destino = Path(args.hoja) if args.hoja else \
        Path(tempfile.gettempdir()) / f"candidatos_{video.stem}.jpg"
    hoja.save(destino, "JPEG", quality=85)
    print(f"[i] Hoja: {destino}")
    print("    Elige el de gesto natural y ponlo en `portada_fondo.segundo` "
          "(ajusta `foco_y` para dejar la cara en la mitad superior).")
    return 0


def _imprimir(hallazgos: list[Hallazgo]):
    for nivel in ("ERROR", "AVISO"):
        hs = [h for h in hallazgos if h.nivel == nivel]
        if hs:
            print(f"\n{nivel}ES ({len(hs)}):" if nivel == "ERROR" else f"\nAVISOS ({len(hs)}):")
            for h in hs:
                donde = f"slide {h.slide}: " if h.slide else ""
                print(f"  - {donde}{h.mensaje}")


def _comprobar_ajuste(plan: dict, maq: Maquetador) -> list[Hallazgo]:
    out, idx_valor = [], 0
    for s in plan.get("slides") or []:
        if not isinstance(s, dict) or s.get("rol") not in ("gancho", "valor", "cierre") \
                or not (s.get("titulo") or "").strip():
            continue
        if s["rol"] == "valor":
            idx_valor += 1
            if not (s.get("texto") or "").strip():
                continue
        try:
            _, _, t, _ = maq.maquetar(s, idx_valor if s["rol"] == "valor" else None)
            if t <= 0.0:
                out.append(Hallazgo("AVISO", "el texto solo cabe al tamaño mínimo; "
                                             "conviene acortarlo.", s["n"]))
        except NoCabe as e:
            out.append(Hallazgo("ERROR", f"el texto no cabe: {e}.", s["n"]))
    return out


def _auditar(plan: dict, activar: bool | None) -> tuple[str, int, int]:
    """Una sola llamada a TheCopy para todas las slides (con --proyecto).
    Devuelve (estado, nº errores, nº avisos)."""
    if activar is False:
        print("\nAuditoría de estilo (TheCopy): desactivada (--no-auditar).")
        return "desactivada", 0, 0
    ok, motivo, res, aviso = thecopy.auditar_slides(plan.get("slides") or [], plan.get("proyecto"))
    if aviso:
        print(f"\n[!] Auditoría: {aviso}.")
    if not ok:
        print(f"\n[!] Auditoría de estilo (TheCopy) NO disponible: {motivo}. "
              f"Sigo sin auditar.")
        return "no disponible", 0, 0
    n_err = n_av = 0
    lineas = []
    for n in sorted(res):
        for h in res[n]:
            nivel = str(h.get("nivel", "aviso")).lower()
            if nivel == "literal":
                continue
            n_err += nivel == "error"
            n_av += nivel != "error"
            frag = h.get("fragmento") or ""
            frag = f" «{frag}»" if frag else ""
            lineas.append(f"  - slide {n} · {nivel} · {h.get('regla', '?')}{frag}: "
                          f"{h.get('mensaje', '')}")
    if lineas:
        print(f"\nAuditoría de estilo (TheCopy): {n_err} error(es), {n_av} aviso(s) "
              f"(no bloquea; reescribe y vuelve a lanzar):")
        print("\n".join(lineas))
    else:
        print("\nAuditoría de estilo (TheCopy): sin hallazgos.")
    return "ok", n_err, n_av


def _proyecto_del_plan(plan_raw, pid_arg: str | None, plan_path: Path) -> Proyecto:
    """El `proyecto` del plan manda; `--proyecto` (si se da) debe coincidir."""
    pid_plan = ""
    if isinstance(plan_raw, dict) and isinstance(plan_raw.get("proyecto"), str):
        pid_plan = plan_raw["proyecto"].strip()
    pid_arg = (pid_arg or "").strip()
    if pid_plan and pid_arg and pid_plan != pid_arg:
        raise ProyectoError(f"el plan es del proyecto «{pid_plan}» y has pedido --proyecto "
                            f"{pid_arg}: no se mezclan proyectos.")
    proyecto = resolver(pid_plan or pid_arg or None)
    carpeta = proyecto_de_ruta(plan_path)
    if carpeta and carpeta != proyecto.id:
        raise ProyectoError(f"el plan está en proyectos/{carpeta}/ pero es del proyecto "
                            f"«{proyecto.id}»: no se mezclan proyectos.")
    if isinstance(plan_raw, dict) and not pid_plan:
        plan_raw["proyecto"] = proyecto.id
    return proyecto


def _carpeta_salida(base: Path, slug: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M")
    d = base / f"carrusel_{ts}_{slug}"
    if d.exists():                       # re-render en el mismo minuto: se rehace
        for f in list(d.glob("[0-9][0-9].jpg")) + [d / "_vista.jpg", d / "carrusel.json"]:
            if f.exists():
                f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _salidas_previas(base: Path, slug: str, nueva: Path) -> list[Path]:
    """Salidas NO aprobadas del mismo slug en `base` (las aprobadas ya no están
    aquí: viven en REVISADOS). Se sustituyen tras un render correcto."""
    patron = re.compile(r"^carrusel_\d{8}-\d{4}_" + re.escape(slug) + r"$")
    if not base.is_dir():
        return []
    return [d for d in base.iterdir()
            if d.is_dir() and patron.match(d.name) and d.resolve() != nueva.resolve()]


def _qc(carpeta: Path, n: int) -> list[str]:
    fallos = []
    esperados = [f"{i:02d}.jpg" for i in range(1, n + 1)]
    presentes = sorted(p.name for p in carpeta.glob("[0-9][0-9].jpg"))
    if presentes != esperados:
        fallos.append(f"imágenes {presentes} ≠ esperadas {esperados}")
    for nombre in esperados:
        p = carpeta / nombre
        if not p.exists():
            continue
        with Image.open(p) as im:
            if im.size != (config.CARRUSEL_W, config.CARRUSEL_H):
                fallos.append(f"{nombre}: {im.size[0]}x{im.size[1]} (debe ser "
                              f"{config.CARRUSEL_W}x{config.CARRUSEL_H})")
            if im.format != "JPEG" or im.mode != "RGB":
                fallos.append(f"{nombre}: {im.format}/{im.mode} (debe ser JPEG RGB)")
        if p.stat().st_size >= config.CARRUSEL_MAX_BYTES:
            fallos.append(f"{nombre}: {p.stat().st_size / 1e6:.1f} MB (límite 8 MB)")
    for extra in ("carrusel.json", "_vista.jpg"):
        if not (carpeta / extra).exists():
            fallos.append(f"falta {extra}")
    return fallos


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = _args(argv)
    if args.candidatos_portada:
        return _candidatos(args)
    if args.fuente:
        return _fuente(args)
    if args.listar:
        return _listar(args)
    if args.aprobar:
        return _aprobar(args)

    plan_path = Path(args.plan).resolve()
    try:
        plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        proyecto = _proyecto_del_plan(plan_raw, args.proyecto, plan_path)
        estilo_path = Path(args.estilo) if args.estilo else proyecto.estilo_path
        estilo = proyecto.estilo(estilo_path)      # maquetación + identidad
    except ProyectoError as e:
        print(f"[!] {e}")
        return 2
    except FileNotFoundError as e:
        print(f"[!] No encuentro el fichero: {e.filename}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[!] JSON ilegible ({e.msg}, línea {e.lineno}): revisa el plan o el estilo.")
        return 2
    if estilo.get("proyecto") and estilo["proyecto"] != proyecto.id:
        print(f"[!] {estilo_path.name} es del proyecto «{estilo['proyecto']}», no de "
              f"«{proyecto.id}»: no se mezclan proyectos.")
        return 2
    if estilo.get("_rellenar"):
        print(f"[!] {estilo_path} sigue siendo la plantilla (`_rellenar: true`): ajusta la "
              f"maquetación del proyecto y quita `_rellenar` antes de hacer carruseles.")
        return 2
    if proyecto.seccion("carruseles").get("activos") is False:
        print(f"[!] El proyecto «{proyecto.id}» no tiene los carruseles activos "
              f"(proyectos/{proyecto.id}/proyecto.json → carruseles.activos).")
        return 2
    print(f"[i] {proyecto.resumen()}")
    for a in proyecto.avisos():
        print(f"[aviso] {a}")
    campos, origen_campos = thecopy.campos(proyecto.id)
    if origen_campos != "TheCopy":
        print(f"[aviso] Campos del plan: {origen_campos}.")

    if int(estilo.get("margen_lateral", 0)) < max(100, int(estilo.get("recorte_perfil", 45))):
        print("[!] estilo.json: `margen_lateral` debe ser ≥ 100 px (la cuadrícula del perfil "
              "recorta ~45 px por lado).")
        return 2

    if isinstance(plan_raw, dict) and not str(plan_raw.get("slug") or "").strip() \
            and proyecto_de_ruta(plan_path):
        plan_raw["slug"] = plan_path.stem          # planes/<slug>.json
    plan, hallazgos = validar_plan(plan_raw, estilo, plan_path.parent, campos,
                                   proyecto.credito_defecto)
    hallazgos += validar_material(plan, proyecto, plan_path.parent)
    maq = Maquetador(estilo)
    # Con foto, el texto del gancho va abajo (def.) o en el centro; sin foto, centro.
    maq.configurar_portada(bool(plan.get("portada_fondo")),
                           plan.get("portada_texto") or estilo.get("portada_texto"))
    hallazgos += _comprobar_ajuste(plan, maq)
    hallazgos.sort(key=lambda h: (h.slide or 0))
    n_slides = len(plan.get("slides") or [])
    print(f"[i] Plan: {plan_path.name} · {plan.get('formula')} · {plan.get('objetivo')} · "
          f"{n_slides} slides · slug «{plan.get('slug')}»")
    _imprimir(hallazgos)

    activar = args.auditar
    if activar is None:
        activar = thecopy.disponible()[0] or None
    estado_aud, aud_err, aud_av = _auditar(plan, activar)

    errores = [h for h in hallazgos if h.nivel == "ERROR"]
    if errores:
        print(f"\n[X] {len(errores)} error(es): no se renderiza. Corrige el plan y repite.")
        return 1
    if args.solo_validar:
        print("\n[OK] Plan válido (solo validación: no se ha escrito nada).")
        return 0

    # Render en memoria (si algo falla, no se deja una carpeta a medias).
    portada = None
    if plan.get("portada_fondo"):
        try:
            portada = preparar_portada(plan["portada_fondo"], plan_path.parent, estilo,
                                       modo=maq.modo_portada)
        except Exception as e:
            print(f"\n[X] Portada: {e}")
            return 1
    credito = ((plan.get("fuente") or {}).get("credito") or "").strip()
    ajustes = maq.ajustes(plan["slides"])       # valor: misma escala y misma caja
    imgs = []
    for s in plan["slides"]:
        t, y_top, idx_valor = ajustes[s["n"]]
        imgs.append(maq.render(s, s["n"], n_slides, idx_valor, credito=credito,
                               portada=portada, t_max=t, y_top=y_top))

    base = Path(args.destino).resolve() if args.destino else proyecto.salidas_dir
    carpeta = _carpeta_salida(base, plan["slug"])
    icc = perfil_srgb()
    calidad = int(estilo.get("jpeg_calidad", 92))
    pesos = [guardar_jpg(im, carpeta / f"{i:02d}.jpg", calidad, icc)
             for i, im in enumerate(imgs, 1)]
    datos = plan_para_json(plan)
    datos["creado"] = dt.datetime.now().isoformat(timespec="seconds")
    (carpeta / "carrusel.json").write_text(json.dumps(datos, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    hoja = hoja_contacto(imgs, fuente=maq.f.get("detalle", 24))
    hoja.save(carpeta / "_vista.jpg", "JPEG", quality=88)

    fallos = _qc(carpeta, n_slides)
    print(f"\n[i] Salida: {carpeta}")
    print(f"    {n_slides} slides · {min(pesos) / 1024:.0f}–{max(pesos) / 1024:.0f} KB por imagen · "
          f"vista: {carpeta / '_vista.jpg'}")
    aud = {"ok": f"{aud_err} error(es) y {aud_av} aviso(s) de estilo",
           "no disponible": "no disponible", "desactivada": "desactivada"}[estado_aud]
    print(f"    auditoría TheCopy: {aud} · avisos del plan: "
          f"{sum(h.nivel == 'AVISO' for h in hallazgos)}")
    if fallos:
        print("\n[X] QC de la salida con fallos:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    for previa in _salidas_previas(base, plan["slug"], carpeta):
        shutil.rmtree(previa)
        print(f"    sustituye a la salida anterior sin aprobar: {previa.name}")
    print(f"[OK] QC: {n_slides} JPG 1080x1350 en orden, < 8 MB, sRGB; carrusel.json y _vista.jpg.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

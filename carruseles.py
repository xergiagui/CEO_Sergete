"""
TheHistoria — CARRUSELES de Instagram (tercera vía).

Valida un plan.json (lo escribe el subagente a partir de un clip/vídeo, un
artículo de TheTextos o un tema), audita el estilo con TheCopy (opcional),
renderiza las slides 1080x1350 y deja la carpeta de salida que lee TheCopy:

  salidas/carrusel_<AAAAMMDD-HHMM>_<slug>/
    01.jpg … NN.jpg   1080x1350, JPEG ~92, sRGB, < 8 MB, en orden
    carrusel.json     plan + metadatos (`creado`)
    _vista.jpg        hoja de contacto (solo para revisar)

Uso:
  python carruseles.py --plan carruseles/planes/<slug>.json
  python carruseles.py --plan <plan.json> --solo-validar
  python carruseles.py --plan <plan.json> --no-auditar

Ejecuta con el .venv de TheEditor (Pillow + imageio-ffmpeg). No instala nada.
Códigos de salida: 0 OK · 1 errores de validación/QC · 2 uso o fichero ilegible.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image

import config
from lib import carrusel_auditoria as auditoria
from lib.carrusel_plan import Hallazgo, plan_para_json, validar_plan
from lib.carrusel_render import (Maquetador, NoCabe, cargar_estilo, guardar_jpg,
                                 hoja_contacto, perfil_srgb, preparar_portada)


def _args(argv=None):
    p = argparse.ArgumentParser(description="Genera un CARRUSEL de Instagram (4:5) desde un plan.json.")
    p.add_argument("--plan", required=True, help="ruta del plan.json")
    p.add_argument("--estilo", default=str(config.CARRUSEL_ESTILO),
                   help="estilo.json (def. carruseles/estilo.json)")
    p.add_argument("--auditar", action=argparse.BooleanOptionalAction, default=None,
                   help="auditar el estilo con TheCopy (def.: sí, si TheCopy está)")
    p.add_argument("--solo-validar", action="store_true",
                   help="valida, comprueba que el texto cabe y audita; no escribe nada")
    return p.parse_args(argv)


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
    """Imprime la auditoría por slide. Devuelve (estado, nº errores, nº avisos)."""
    if activar is False:
        print("\nAuditoría de estilo (TheCopy): desactivada (--no-auditar).")
        return "desactivada", 0, 0
    ok, motivo, res = auditoria.auditar_slides(plan.get("slides") or [], plan.get("proyecto"))
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


def _carpeta_salida(slug: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M")
    d = config.OUT_DIR / f"carrusel_{ts}_{slug}"
    if d.exists():                       # re-render en el mismo minuto: se rehace
        for f in list(d.glob("[0-9][0-9].jpg")) + [d / "_vista.jpg", d / "carrusel.json"]:
            if f.exists():
                f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    return d


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

    plan_path = Path(args.plan).resolve()
    try:
        plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        estilo = cargar_estilo(Path(args.estilo))
    except FileNotFoundError as e:
        print(f"[!] No encuentro el fichero: {e.filename}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[!] JSON ilegible ({e.msg}, línea {e.lineno}): revisa el plan o el estilo.")
        return 2

    if int(estilo.get("margen_lateral", 0)) < max(100, int(estilo.get("recorte_perfil", 45))):
        print("[!] estilo.json: `margen_lateral` debe ser ≥ 100 px (la cuadrícula del perfil "
              "recorta ~45 px por lado).")
        return 2

    plan, hallazgos = validar_plan(plan_raw, estilo, plan_path.parent)
    maq = Maquetador(estilo)
    hallazgos += _comprobar_ajuste(plan, maq)
    hallazgos.sort(key=lambda h: (h.slide or 0))
    n_slides = len(plan.get("slides") or [])
    print(f"[i] Plan: {plan_path.name} · {plan.get('formula')} · {plan.get('objetivo')} · "
          f"{n_slides} slides · slug «{plan.get('slug')}»")
    _imprimir(hallazgos)

    activar = args.auditar
    if activar is None:
        activar = auditoria.disponible()[0] or None
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
            portada = preparar_portada(plan["portada_fondo"], plan_path.parent, estilo)
        except Exception as e:
            print(f"\n[X] Portada: {e}")
            return 1
    credito = ((plan.get("fuente") or {}).get("credito") or "").strip()
    ajustes = maq.ajustes(plan["slides"])       # valor: misma escala y misma altura
    imgs = []
    for s in plan["slides"]:
        t, y_top, idx_valor = ajustes[s["n"]]
        imgs.append(maq.render(s, s["n"], n_slides, idx_valor, credito=credito,
                               portada=portada, t_max=t, y_top=y_top))

    carpeta = _carpeta_salida(plan["slug"])
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
    print(f"[OK] QC: {n_slides} JPG 1080x1350 en orden, < 8 MB, sRGB; carrusel.json y _vista.jpg.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

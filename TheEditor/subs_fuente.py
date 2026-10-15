#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subtítulos incrustados en la FUENTE (vía 1): los tapa antes del render.

Muchos vídeos de YouTube traen sus propios rótulos quemados (texto blanco sobre
caja oscura). Al recortar a 9:16 quedan cortados por los lados y asoman justo
debajo de NUESTROS subtítulos. Este paso, previo a la Fase C, los detecta en la
franja inferior del clip (`zona_y`) fotograma a fotograma y, SOLO mientras están
en pantalla, los tapa con un desenfoque fuerte de bordes suaves (o una banda
oscura) ajustado a la altura real de cada rótulo (con todas sus líneas, aunque
la primera quede por encima de `zona_y`). Va sobre el plano del
ponente: el gancho visual, el b-roll, el gancho de texto y nuestros subtítulos
se componen después, encima, así que nunca quedan tapados. Si el clip no trae
rótulos, no se toca (ni se recodifica).

Config por proyecto (`proyecto.json → subs_fuente`; sin la clave, no se hace nada):
    "subs_fuente": {"tapar": "desenfoque"}          # desenfoque | banda | no
  opcionales (px sobre 1080x1920):
    zona_y [1290, 1920]   franja donde se buscan (nuestros subtítulos acaban ~1280)
    margen_px 40          aire alrededor del texto (cubre la caja oscura)
    difuminado_px 24      borde suave del desenfoque
    sigma 70              fuerza del desenfoque
    banda_opacidad 0.85   opacidad de la banda negra (modo banda)
Desactivar en una ejecución: `editar_clips.py … --sin-tapar-subs`.

Uso suelto (prueba o diagnóstico; no toca nada si no se da --salida):
    python subs_fuente.py --proyecto mongemalo "<clip.mp4>"
    python subs_fuente.py --proyecto mongemalo "<clip.mp4>" --salida prueba.mp4
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import herramientas

MODOS = ("desenfoque", "banda", "no")
POR_DEFECTO = {
    "tapar": "no",
    "zona_y": [1290, 1920],
    "margen_px": 40,
    "difuminado_px": 24,
    "sigma": 70,
    "banda_opacidad": 0.85,
}
REF_H = 1920          # las cotas de la config van sobre un 1080x1920
FPS_ANALISIS = 30     # fotogramas analizados por segundo (t = i / 30)
# Detección (sobre la franja a media resolución, en gris):
_BLANCO, _OSCURO = 215, 110   # texto blanco · caja oscura
_BORDE_MIN = 12               # px blanco-junto-a-oscuro por fila para contar como texto
_OSCURO_MIN = 0.25            # fracción mínima de caja oscura en esa fila
_FILAS_MIN = 6                # filas de texto por fotograma (6 × 2 = 12 px reales)
_HUECO_MAX = 2                # fotogramas sin texto que no cortan un tramo
_UNIR_S = 0.25                # tramos separados menos que esto (y a la misma altura) se unen
_DUR_MIN = 3                  # tramos de menos fotogramas se descartan (ruido)
_HOLGURA_S = 0.07             # se tapa un poco antes y un poco después
# Fundidos de entrada/salida del rótulo (ya no es blanco puro, pero se ve): el
# tramo se alarga mientras en sus filas siga habiendo muchos bordes de contraste.
_FUNDIDO_DIF = 35             # salto de gris entre píxeles a 2 px que cuenta como borde
_FUNDIDO_MIN = 40             # bordes por fila (máximo de sus filas) para seguir tapando
_FUNDIDO_MAX_S = 0.8          # como mucho, esto antes y después
# Rótulos de VARIAS líneas: la caja detectada crece por las líneas contiguas del
# mismo rótulo (también por encima de `zona_y`, que solo sirve para encontrarlo).
_CRECER_ARRIBA = 300          # px (sobre 1920) que puede subir por encima de zona_y
_CRECER_HUECO = 140           # hueco máximo entre líneas del mismo rótulo (px sobre 1920)
_CRECER_MIN = 3               # mediana de px blanco-junto-a-oscuro por fila = línea de texto
_CRECER_FPS = 10              # fotogramas por segundo para el perfil del tramo


def config(cfg_proyecto: dict | None) -> dict | None:
    """Config normalizada de `proyecto.json → subs_fuente`, o None si no se tapa."""
    raw = (cfg_proyecto or {}).get("subs_fuente")
    if not raw:
        return None
    if raw is True:
        raw = {"tapar": "desenfoque"}
    elif isinstance(raw, str):
        raw = {"tapar": raw}
    if not isinstance(raw, dict):
        raise ValueError("proyecto.json → subs_fuente debe ser un objeto, p. ej. "
                         '{"tapar": "desenfoque"}.')
    c = dict(POR_DEFECTO)
    c.update({k: v for k, v in raw.items() if k in POR_DEFECTO})
    modo = str(c["tapar"]).strip().lower()
    if modo not in MODOS:
        raise ValueError(f"proyecto.json → subs_fuente.tapar «{c['tapar']}» no válido "
                         f"({' | '.join(MODOS)}).")
    if modo == "no":
        return None
    c["tapar"] = modo
    return c


def describir(c: dict | None) -> str:
    if not c:
        return "no"
    return f"{c['tapar']} (zona y {c['zona_y'][0]}-{c['zona_y'][1]}, solo mientras hay rótulo)"


def _par(n: float) -> int:
    n = int(round(n))
    return n - (n % 2)


def _filas_texto(f):
    """Filas (de la franja a media resolución) con rótulo blanco sobre caja oscura."""
    import numpy as np
    blanco = f > _BLANCO
    oscuro = f < _OSCURO
    cerca = oscuro.copy()
    for s in (1, 2):
        cerca[:, s:] |= oscuro[:, :-s]
        cerca[:, :-s] |= oscuro[:, s:]
    bordes = (blanco & cerca).sum(axis=1)
    frac_osc = oscuro.mean(axis=1)
    return np.where((bordes >= _BORDE_MIN) & (frac_osc >= _OSCURO_MIN))[0]


def _bordes_fila(f):
    """Bordes de contraste por fila (para seguir los fundidos del rótulo)."""
    import numpy as np
    g = np.abs(f[:, 2:].astype(np.int16) - f[:, :-2].astype(np.int16)) > _FUNDIDO_DIF
    return g.sum(axis=1).astype(np.int16)


def _crecer_vertical(video: Path, ff: str, unidos: list[dict], w: int, h: int,
                     k: float, z0: int, z1: int) -> None:
    """Amplía [ya, yb] de cada tramo por las líneas contiguas del mismo rótulo.

    Un rótulo de 2-3 líneas solo se detecta por la parte que cae en `zona_y`
    (o por las líneas con caja oscura): las demás asomaban encima o debajo del
    tapado. Por tramo, saca el perfil por filas (mediana, sobre sus fotogramas,
    de píxeles blancos junto a oscuros) en [z0 - _CRECER_ARRIBA, z1] y extiende la
    caja mientras haya filas de texto a menos de _CRECER_HUECO. Modifica `unidos`."""
    import numpy as np
    ze0 = _par(max(0, z0 - _CRECER_ARRIBA * k))
    aw, ah = _par(w / 2), _par((z1 - ze0) / 2)
    hueco = int(_CRECER_HUECO * k)
    for u in unidos:
        t0 = u["j0"] / FPS_ANALISIS
        dur = max((u["j1"] + 1) / FPS_ANALISIS - t0, 1.0 / FPS_ANALISIS)
        p = subprocess.run(
            [ff, "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(video),
             "-an", "-vf", f"crop={w}:{z1 - ze0}:0:{ze0},scale={aw}:{ah}:flags=area,"
             f"fps={_CRECER_FPS},format=gray", "-f", "rawvideo", "-"],
            capture_output=True)
        a = np.frombuffer(p.stdout, np.uint8)
        n = a.size // (aw * ah)
        if n == 0:
            continue
        perfiles = []
        for f in a[:n * aw * ah].reshape(n, ah, aw):
            blanco, oscuro = f > _BLANCO, f < _OSCURO
            cerca = oscuro.copy()
            for s in (1, 2):
                cerca[:, s:] |= oscuro[:, :-s]
                cerca[:, :-s] |= oscuro[:, s:]
            perfiles.append((blanco & cerca).sum(axis=1))
        texto = np.median(np.array(perfiles), axis=0) >= _CRECER_MIN

        def fila(y):  # px del vídeo -> fila del perfil
            return min(max((y - ze0) // 2, 0), ah - 1)

        for paso, borde in ((-1, "ya"), (1, "yb")):
            r, ultimo, sin_texto = fila(u[borde]), fila(u[borde]), 0
            while 0 <= r + paso < ah and sin_texto * 2 <= hueco:
                r += paso
                if texto[r]:
                    ultimo, sin_texto = r, 0
                else:
                    sin_texto += 1
            y = ze0 + 2 * ultimo + (2 if paso > 0 else 0)
            u[borde] = min(u[borde], y) if paso < 0 else max(u[borde], y)


def _misma_altura(ya: int, yb: int, t: dict, tol: int = 40) -> bool:
    """El rótulo [ya, yb] es el mismo (o casi) que el del tramo `t`."""
    return abs(ya - t["ya"]) <= tol and abs(yb - t["yb"]) <= tol


def detectar(video: Path, c: dict) -> list[dict]:
    """Tramos con rótulo de la fuente: [{t0, t1, y0, y1}] (s y px del vídeo).

    y0/y1 ya incluyen margen y borde suave, recortados al cuadro."""
    import numpy as np
    ff = herramientas.exigir_ffmpeg()
    w, h = herramientas.dimensiones(video)
    if not (w and h):
        raise RuntimeError(f"no puedo leer las dimensiones de {Path(video).name}")
    k = h / REF_H
    z0 = _par(max(0, min(h - 2, c["zona_y"][0] * k)))
    z1 = _par(max(z0 + 2, min(h, c["zona_y"][1] * k)))
    aw, ah = _par(w / 2), _par((z1 - z0) / 2)
    vf = (f"crop={w}:{z1 - z0}:0:{z0},scale={aw}:{ah}:flags=area,"
          f"fps={FPS_ANALISIS},format=gray")
    proc = subprocess.Popen([ff, "-v", "error", "-i", str(video), "-an", "-vf", vf,
                             "-f", "rawvideo", "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    tam = aw * ah
    marcas = []                       # (i, fila_min, fila_max) de los fotogramas con texto
    bordes = []                       # bordes por fila de cada fotograma (fundidos)
    i = 0
    try:
        while True:
            buf = proc.stdout.read(tam)
            if len(buf) < tam:
                break
            f = np.frombuffer(buf, np.uint8).reshape(ah, aw)
            filas = _filas_texto(f)
            if len(filas) >= _FILAS_MIN:
                marcas.append((i, int(filas.min()), int(filas.max())))
            bordes.append(_bordes_fila(f))
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()
    if i == 0:
        raise RuntimeError(f"ffmpeg no devolvió fotogramas de {Path(video).name}")

    # Fotogramas -> tramos (continuos y a la misma altura).
    tramos = []
    for (j, a, b) in marcas:
        ya, yb = z0 + 2 * a, z0 + 2 * b + 2
        t = tramos[-1] if tramos else None
        if (t and j - t["j1"] <= _HUECO_MAX + 1
                and _misma_altura(ya, yb, t)):
            t["j1"] = j
            t["ya"], t["yb"] = min(t["ya"], ya), max(t["yb"], yb)
        else:
            tramos.append({"j0": j, "j1": j, "ya": ya, "yb": yb})
    tramos = [t for t in tramos if t["j1"] - t["j0"] + 1 >= _DUR_MIN]
    # Fundidos: alarga cada tramo mientras sus filas sigan con mucho contraste.
    n_fund = int(_FUNDIDO_MAX_S * FPS_ANALISIS)

    def _sigue(j, t):
        a, b = (t["ya"] - z0) // 2, (t["yb"] - z0) // 2 + 1
        return 0 <= j < i and int(bordes[j][a:b].max(initial=0)) >= _FUNDIDO_MIN

    for t in tramos:
        for _ in range(n_fund):
            if not _sigue(t["j1"] + 1, t):
                break
            t["j1"] += 1
        for _ in range(n_fund):
            if not _sigue(t["j0"] - 1, t):
                break
            t["j0"] -= 1
    unidos = []
    for t in tramos:
        u = unidos[-1] if unidos else None
        if (u and (t["j0"] - u["j1"]) / FPS_ANALISIS <= _UNIR_S
                and _misma_altura(t["ya"], t["yb"], u)):
            u["j1"] = t["j1"]
            u["ya"], u["yb"] = min(u["ya"], t["ya"]), max(u["yb"], t["yb"])
        else:
            unidos.append(dict(t))
    try:
        _crecer_vertical(video, ff, unidos, w, h, k, z0, z1)
    except Exception as e:  # best-effort: sin crecer, la caja de siempre
        print(f"   [subs_fuente] no pude ampliar los rótulos de varias líneas ({e})")

    pad = int(c["margen_px"] * k) + (int(c["difuminado_px"] * k) if c["tapar"] == "desenfoque" else 0)
    out = []
    for t in unidos:
        y0 = _par(max(0, t["ya"] - pad))
        y1 = _par(min(h, t["yb"] + pad + 1))
        out.append({
            "t0": round(max(0.0, t["j0"] / FPS_ANALISIS - _HOLGURA_S), 3),
            "t1": round((t["j1"] + 1) / FPS_ANALISIS + _HOLGURA_S, 3),
            "y0": y0, "y1": y1,
        })
    return out


def _mascara(ancho: int, alto: int, borde: int) -> str:
    """Fuente de filtro: máscara gris opaca en el centro y degradada `borde` px
    arriba y abajo. Se calcula UNA vez (geq sobre un fotograma) y se repite con
    `loop`, así no cuesta nada por fotograma."""
    borde = max(1, min(borde, alto // 2))
    return (f"color=c=black:s={ancho}x{alto}:r={FPS_ANALISIS},format=gray,trim=end_frame=1,"
            f"geq=lum='255*min(1,min(Y+1,H-Y)/({borde}+1))',"
            f"loop=loop=-1:size=1,setpts=N/({FPS_ANALISIS}*TB)")


def tapar(entrada: Path, salida: Path, c: dict, tramos: list[dict] | None = None) -> list[dict]:
    """Escribe `salida` con los rótulos de la fuente tapados y devuelve los
    tramos. Sin tramos, no escribe nada (el llamador sigue con `entrada`).
    El audio se copia tal cual y la duración y los fotogramas no cambian."""
    if tramos is None:
        tramos = detectar(entrada, c)
    if not tramos:
        return []
    ff = herramientas.exigir_ffmpeg()
    w, h = herramientas.dimensiones(entrada)
    k = h / REF_H
    if c["tapar"] == "banda":
        op = max(0.0, min(1.0, float(c["banda_opacidad"])))
        cajas = ",".join(
            f"drawbox=x=0:y={t['y0']}:w=iw:h={t['y1'] - t['y0']}:color=black@{op:.2f}:t=fill:"
            f"enable='between(t,{t['t0']},{t['t1']})'" for t in tramos)
        filt = f"[0:v]{cajas}[v]"
    else:
        # Un solo desenfoque de la franja que cubre todos los tramos (con contexto
        # arriba y abajo para que la caja oscura se diluya), a 1/4 de resolución
        # (mismo aspecto, mucho más rápido); luego un recorte por tramo con su
        # máscara de bordes suaves, superpuesto solo mientras dura.
        ctx = int(100 * k)
        r0 = _par(max(0, min(t["y0"] for t in tramos) - ctx))
        r1 = _par(min(h, max(t["y1"] for t in tramos) + ctx))
        rh = r1 - r0
        sig = max(1.0, float(c["sigma"]) * k / 4)
        borde = max(1, int(c["difuminado_px"] * k))
        alturas = sorted({t["y1"] - t["y0"] for t in tramos})
        usos = {a: sum(1 for t in tramos if t["y1"] - t["y0"] == a) for a in alturas}
        cad = ["[0:v]split=2[base][src]",
               f"[src]crop={w}:{rh}:0:{r0},scale={_par(w / 4)}:{_par(rh / 4)}:flags=area,"
               f"gblur=sigma={sig:.2f}:steps=3,scale={w}:{rh}:flags=bicubic,"
               f"format=yuv420p,split={len(tramos)}" + "".join(f"[bl{i}]" for i in range(len(tramos)))]
        for a in alturas:
            cad.append(_mascara(w, a, borde) + f",split={usos[a]}"
                       + "".join(f"[m{a}_{u}]" for u in range(usos[a])))
        cont = {a: 0 for a in alturas}
        prev = "[base]"
        for i, t in enumerate(tramos):
            a = t["y1"] - t["y0"]
            m = f"[m{a}_{cont[a]}]"
            cont[a] += 1
            cad.append(f"[bl{i}]crop={w}:{a}:0:{t['y0'] - r0},format=yuva420p[c{i}]")
            cad.append(f"[c{i}]{m}alphamerge[a{i}]")
            sal = "[v]" if i == len(tramos) - 1 else f"[o{i}]"
            cad.append(f"{prev}[a{i}]overlay=x=0:y={t['y0']}:eof_action=pass:"
                       f"enable='between(t,{t['t0']},{t['t1']})'{sal}")
            prev = sal
        filt = ";".join(cad)
    herramientas.ejecutar([
        ff, "-y", "-i", str(entrada), "-filter_complex", filt,
        "-map", "[v]", "-map", "0:a?", "-fps_mode", "passthrough",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-t", f"{herramientas.duracion(entrada):.3f}",
        "-movflags", "+faststart", str(salida),
    ])
    return tramos


def resumen_tramos(tramos: list[dict]) -> str:
    if not tramos:
        return "sin rótulos de la fuente"
    seg = sum(t["t1"] - t["t0"] for t in tramos)
    return f"{len(tramos)} rótulo(s) de la fuente tapados ({seg:.0f} s)"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    import proyecto
    ap = argparse.ArgumentParser(description="Detecta (y tapa) los rótulos incrustados de la fuente en un clip 9:16.")
    ap.add_argument("clip", help="Clip 9:16 (p. ej. transcripciones/<v>/clips/<clip>.mp4).")
    proyecto.add_argumento(ap)
    ap.add_argument("--salida", help="Si se da, escribe aquí el clip tapado (prueba).")
    ap.add_argument("--modo", choices=MODOS[:2], help="Fuerza desenfoque o banda (solo esta prueba).")
    a = ap.parse_args()
    p = proyecto.resolver(a.proyecto)
    c = config(p.cfg)
    if a.modo:
        c = dict(c or POR_DEFECTO, tapar=a.modo)
    if not c:
        print(f"[subs_fuente] el proyecto {p.id} no tapa los rótulos de la fuente "
              f"(proyecto.json → subs_fuente); usa --modo para probar.")
        return 0
    tramos = detectar(Path(a.clip), c)
    for t in tramos:
        print(f"  {t['t0']:6.2f}-{t['t1']:6.2f} s · y {t['y0']}-{t['y1']}")
    if a.salida and tramos:
        tapar(Path(a.clip), Path(a.salida), c, tramos)
        print(f"OK -> {a.salida}")
    print(f"RESUMEN: {resumen_tramos(tramos)} · {describir(c)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

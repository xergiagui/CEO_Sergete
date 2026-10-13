"""
CARRUSELES · render de las slides (Pillow) → JPEG 1080x1350.

Cada slide se maqueta como una PILA VERTICAL de elementos (número, título,
barra de acento, texto, lista...). El ajuste automático prueba una escala `t`
de 1 (tamaños máximos) a 0 (mínimos): todos los textos encogen a la vez dentro
de su rango [max, min] de `estilo.json`. Si ni al mínimo cabe (en alto, o hay
una palabra más ancha que la columna), la slide lanza `NoCabe` → ERROR.

Roles:
  gancho  título grande centrado (+ línea del bucle abierto) y «desliza →»
          abajo a la derecha. Con foto (`portada_fondo`) y `portada_texto` =
          "abajo" (def.), el texto va en la mitad inferior (alineado abajo, por
          encima de «desliza») sobre un degradado oscuro que sube desde abajo,
          para que la cara se vea arriba; con
          "centro", texto en el centro óptico y oscurecido plano.
  valor   número grande en el color de acento, título, barra de acento y texto; contador
          «n/N» arriba a la derecha.
  cierre  título, lista-resumen opcional (`puntos`), texto, la petición en
          color de acento y el crédito de la fuente en pequeño.

Posición vertical: los bloques se centran en el CENTRO ÓPTICO (`centro_optico`,
~46 % de la altura). Las slides de valor comparten escala y caja: se centra la
caja de la más alta y el contenido de cada una va alineado arriba dentro de esa
caja, así el número grande queda a la misma altura en todas.

`**palabra**` pinta ese tramo en el color de acento. El estilo que llega aquí es
`Proyecto.estilo()`: maquetación de estilo.json + `colores`, `handle` y
`emojis_max` de la identidad del proyecto. El handle solo se pinta si existe.
"""
from __future__ import annotations

import io
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import config
from lib.carrusel_plan import IMAGEN_EXTS, MARCA, normalizar_portada

Run = tuple[str, bool]          # (texto, destacado)
Palabra = list[Run]
Linea = list[Palabra]


class NoCabe(Exception):
    """El texto de una slide no cabe ni con los tamaños mínimos."""


# ------------------------------------------------------------------ estilo
def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Fuentes:
    def __init__(self, estilo: dict):
        self.rutas = {rol: config.FONTS_DIR / nombre
                      for rol, nombre in (estilo.get("fuentes") or {}).items()}
        for rol, ruta in self.rutas.items():
            if not ruta.exists():
                raise FileNotFoundError(f"fuente «{rol}» no encontrada: {ruta}")
        self._cache: dict = {}

    def get(self, rol: str, size: int) -> ImageFont.FreeTypeFont:
        key = (rol, int(size))
        if key not in self._cache:
            self._cache[key] = ImageFont.truetype(str(self.rutas[rol]), int(size))
        return self._cache[key]


# ------------------------------------------------------------------ texto enriquecido
def parse_rico(s: str) -> list[list[Palabra]]:
    """Texto con `**destacado**` → párrafos (por \\n) → palabras → tramos."""
    parrafos: list[list[Palabra]] = [[]]
    palabra: Palabra = []
    buf, dest, i = "", False, 0

    def cerrar_tramo():
        nonlocal buf
        if buf:
            if palabra and palabra[-1][1] == dest:
                palabra[-1] = (palabra[-1][0] + buf, dest)
            else:
                palabra.append((buf, dest))
            buf = ""

    def cerrar_palabra():
        nonlocal palabra
        cerrar_tramo()
        if palabra:
            parrafos[-1].append(palabra)
            palabra = []

    while i < len(s):
        if s.startswith(MARCA, i):
            cerrar_tramo()
            dest = not dest
            i += len(MARCA)
            continue
        c = s[i]
        if c == "\n":
            cerrar_palabra()
            parrafos.append([])
        elif c.isspace():
            cerrar_palabra()
        else:
            buf += c
        i += 1
    cerrar_palabra()
    return parrafos


def _ancho(p: Palabra, font) -> float:
    return sum(font.getlength(t) for t, _ in p)


def _ancho_linea(linea: Linea, font) -> float:
    if not linea:
        return 0.0
    return sum(_ancho(p, font) for p in linea) + font.getlength(" ") * (len(linea) - 1)


def _voraz(parrafos, font, max_w: float) -> list[Linea] | None:
    esp = font.getlength(" ")
    out: list[Linea] = []
    for par in parrafos:
        cur: Linea = []
        cur_w = 0.0
        for p in par:
            w = _ancho(p, font)
            if w > max_w + 0.5:
                return None                      # palabra más ancha que la columna
            if cur and cur_w + esp + w > max_w:
                out.append(cur)
                cur, cur_w = [p], w
            else:
                cur_w = w if not cur else cur_w + esp + w
                cur.append(p)
        out.append(cur)
    return out


def envolver(parrafos, font, max_w: float, balancear: bool = False) -> list[Linea] | None:
    """Reparte en líneas. Con `balancear`, busca el ancho mínimo que mantiene el
    mismo nº de líneas (evita una palabra huérfana en la última línea)."""
    lineas = _voraz(parrafos, font, max_w)
    if lineas is None or not balancear or len(lineas) < 2:
        return lineas
    n, lo, hi, mejor = len(lineas), max_w * 0.45, max_w, lineas
    for _ in range(14):
        mid = (lo + hi) / 2
        cand = _voraz(parrafos, font, mid)
        if cand is not None and len(cand) == n:
            mejor, hi = cand, mid
        else:
            lo = mid
    return mejor


# ------------------------------------------------------------------ elementos
@dataclass
class _Pieza:
    """Elemento ya medido, listo para pintar en (x_col, y)."""
    alto: int
    pintar: callable


def _metricas(font) -> tuple[int, int]:
    cap = -font.getbbox("H", anchor="ls")[1]
    return cap, font.size


def _texto(draw_txt: str, font, max_w: float, color, acento, align: str,
           interlineado: float, balancear: bool) -> _Pieza | None:
    lineas = envolver(parse_rico(draw_txt), font, max_w, balancear)
    if lineas is None:
        return None
    cap, size = _metricas(font)
    lh = round(size * interlineado)
    alto = cap + (len(lineas) - 1) * lh + round(size * 0.14)
    esp = font.getlength(" ")

    def pintar(draw: ImageDraw.ImageDraw, x0: float, y: float, ancho_col: float):
        base = y + cap
        for linea in lineas:
            w = _ancho_linea(linea, font)
            x = x0 + (ancho_col - w) / 2 if align == "center" else x0
            for p in linea:
                for t, dest in p:
                    draw.text((x, base), t, font=font, fill=acento if dest else color,
                              anchor="ls")
                    x += font.getlength(t)
                x += esp
            base += lh

    return _Pieza(alto, pintar)


def _linea_simple(txt: str, font, color, align: str) -> _Pieza:
    """Una línea con alto de tinta ajustado (para el número grande)."""
    x0b, y0b, x1b, _ = font.getbbox(txt, anchor="ls")
    alto = -y0b

    def pintar(draw, x0, y, ancho_col):
        x = x0 + (ancho_col - (x1b - x0b)) / 2 - x0b if align == "center" else x0 - x0b
        draw.text((x, y + alto), txt, font=font, fill=color, anchor="ls")

    return _Pieza(alto, pintar)


def _barra(w: int, h: int, color, align: str) -> _Pieza:
    def pintar(draw, x0, y, ancho_col):
        x = x0 + (ancho_col - w) / 2 if align == "center" else x0
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)
    return _Pieza(h, pintar)


def _lista(puntos: list[str], f_num, f_txt, fmt: str, c_num, c_txt, acento,
           max_w: float, interlineado: float) -> _Pieza | None:
    col = f_num.getlength("00") + round(f_txt.size * 0.6)
    items = []
    for k, p in enumerate(puntos, 1):
        pieza = _texto(p, f_txt, max_w - col, c_txt, acento, "left", interlineado, False)
        if pieza is None:
            return None
        items.append((fmt.format(n=k), pieza))
    gap = round(f_txt.size * 0.55)
    alto = sum(p.alto for _, p in items) + gap * (len(items) - 1)
    cap_t, _ = _metricas(f_txt)

    def pintar(draw, x0, y, ancho_col):
        for num, pieza in items:
            draw.text((x0, y + cap_t), num, font=f_num, fill=c_num, anchor="ls")
            pieza.pintar(draw, x0 + col, y, ancho_col - col)
            y += pieza.alto + gap

    return _Pieza(alto, pintar)


# ------------------------------------------------------------------ maquetación
_PASOS = [round(1 - k * 0.04, 2) for k in range(26)]      # 1.00 … 0.00


def _tam(rango, t: float) -> int:
    mx, mn = rango
    return round(mn + (mx - mn) * t)


class Maquetador:
    def __init__(self, estilo: dict):
        self.e = estilo
        self.f = Fuentes(estilo)
        c = estilo["colores"]
        self.c_fondo = _rgb(c["fondo"])
        self.c_texto = _rgb(c["texto"])
        self.c_suave = _rgb(c.get("texto_suave", c["texto"]))
        self.c_detalle = _rgb(c.get("detalle", c["texto"]))
        self.c_acento = _rgb(c["acento"])
        self.W, self.H = config.CARRUSEL_W, config.CARRUSEL_H
        self.mx = int(estilo.get("margen_lateral", 110))
        self.top = int(estilo.get("margen_superior", 190))
        self.bottom = self.H - int(estilo.get("margen_inferior", 180))
        self.ancho = self.W - 2 * self.mx
        self.tam = estilo["tamanos"]
        self.il = estilo.get("interlineado") or {}
        self.barra = estilo.get("barra_acento") or [96, 8]
        self.centro = self.H * float(estilo.get("centro_optico", 0.46))
        self.modo_portada = "centro"
        self.zona_gancho = (self.top, self.bottom)

    def configurar_portada(self, con_foto: bool, modo: str | None = None):
        """Con foto y modo "abajo", el gancho vive en la mitad inferior
        [portada_texto_desde·H .. margen inferior]; si no, en el centro óptico."""
        modo = (modo or self.e.get("portada_texto") or "abajo") if con_foto else "centro"
        self.modo_portada = modo
        if modo == "abajo":
            desde = round(self.H * float(self.e.get("portada_texto_desde", 0.55)))
            self.zona_gancho = (desde, self.bottom)
        else:
            self.zona_gancho = (self.top, self.bottom)

    def _y_centrado(self, alto: float) -> float:
        """Arriba de un bloque de `alto` centrado en el centro óptico, sin salirse."""
        return min(max(self.centro - alto / 2, self.top), self.bottom - alto)

    # -- pila de elementos para una t dada; None si algo no cabe en ancho
    def _pila(self, slide: dict, idx_valor: int | None, t: float):
        rol = slide["rol"]
        g = lambda px: round(px * (0.55 + 0.45 * t))          # huecos que encogen
        T, il = self.tam, self.il
        pila: list = []                                       # [_Pieza | int(hueco)]

        def add(p):
            if p is None:
                raise _NoAncho()
            pila.append(p)

        if rol == "gancho":
            add(_texto(slide["titulo"], self.f.get("titulo", _tam(T["gancho_titulo"], t)),
                       self.ancho, self.c_texto, self.c_acento, "center",
                       il.get("titulo", 1.12), True))
            if (slide.get("texto") or "").strip():
                pila.append(g(46))
                add(_barra(self.barra[0], self.barra[1], self.c_acento, "center"))
                pila.append(g(44))
                add(_texto(slide["texto"], self.f.get("texto", _tam(T["gancho_texto"], t)),
                           self.ancho, self.c_suave, self.c_acento, "center",
                           il.get("texto", 1.38), True))
            return pila, "center"

        if rol == "valor":
            num = self._numero(slide, idx_valor)
            if num:
                add(_linea_simple(num, self.f.get("titulo", _tam(T["numero"], t)),
                                  self.c_acento, "left"))
                pila.append(g(44))
            add(_texto(slide["titulo"], self.f.get("titulo", _tam(T["titulo"], t)),
                       self.ancho, self.c_texto, self.c_acento, "left",
                       il.get("titulo", 1.12), True))
            pila.append(g(38))
            add(_barra(self.barra[0], self.barra[1], self.c_acento, "left"))
            pila.append(g(38))
            add(_texto(slide["texto"], self.f.get("texto", _tam(T["texto"], t)),
                       self.ancho, self.c_suave, self.c_acento, "left",
                       il.get("texto", 1.38), False))
            return pila, "left"

        # cierre
        add(_texto(slide["titulo"], self.f.get("titulo", _tam(T["cierre_titulo"], t)),
                   self.ancho, self.c_texto, self.c_acento, "left",
                   il.get("titulo", 1.12), True))
        pila.append(g(34))
        add(_barra(self.barra[0], self.barra[1], self.c_acento, "left"))
        puntos = [p for p in (slide.get("puntos") or []) if isinstance(p, str) and p.strip()]
        if puntos:
            pila.append(g(44))
            tp = _tam(T["punto"], t)
            add(_lista(puntos, self.f.get("titulo", tp), self.f.get("texto", tp),
                       self.e.get("numero_formato", "{n:02d}"), self.c_acento, self.c_texto,
                       self.c_acento, self.ancho, il.get("punto", 1.25)))
        if (slide.get("texto") or "").strip():
            pila.append(g(46 if puntos else 40))
            add(_texto(slide["texto"], self.f.get("texto", _tam(T["cierre_texto"], t)),
                       self.ancho, self.c_suave, self.c_acento, "left",
                       il.get("texto", 1.38), False))
        if (slide.get("peticion") or "").strip():
            pila.append(g(48))
            add(_texto(slide["peticion"], self.f.get("titulo", _tam(T["peticion"], t)),
                       self.ancho, self.c_acento, self.c_acento, "left",
                       il.get("titulo", 1.12), False))
        return pila, "left"

    def _numero(self, slide: dict, idx_valor: int | None) -> str:
        if "numero" in slide:
            v = slide["numero"]
            if v is False or v is None or v == "":
                return ""
            return self.e.get("numero_formato", "{n:02d}").format(n=v) if isinstance(v, int) \
                else str(v)
        return self.e.get("numero_formato", "{n:02d}").format(n=idx_valor or 0)

    def maquetar(self, slide: dict, idx_valor: int | None = None, t_max: float = 1.0):
        """Busca la mayor escala (≤ t_max) con la que todo cabe.
        Devuelve (pila, align, t, alto)."""
        z0, z1 = self.zona_gancho if slide["rol"] == "gancho" else (self.top, self.bottom)
        zona = z1 - z0
        exceso = None
        for t in _PASOS:
            if t > t_max + 1e-9:
                continue
            try:
                pila, align = self._pila(slide, idx_valor, t)
            except _NoAncho:
                continue
            alto = sum(x if isinstance(x, int) else x.alto for x in pila)
            if alto <= zona:
                return pila, align, t, alto
            exceso = alto - zona
        if exceso is None:
            raise NoCabe("hay una palabra más ancha que la columna incluso al tamaño mínimo")
        raise NoCabe(f"no cabe ni al tamaño mínimo: sobran ~{exceso} px de alto. "
                     f"Recorta el texto")

    def ajustes(self, slides: list[dict]) -> dict[int, tuple[float, float | None, int | None]]:
        """Ajuste de TODO el carrusel → {n: (t, y_top, idx_valor)}.

        Las slides de valor comparten escala (la menor que necesite cualquiera) y
        caja: la de la más alta (o la mediana, con `valor_referencia` = "mediana"),
        centrada en el centro óptico; el contenido de cada una va alineado arriba
        dentro de esa caja, para que número, título y texto
        no cambien de tamaño ni de sitio al deslizar. Gancho y cierre se ajustan y
        centran por su cuenta. Lanza NoCabe si alguna no cabe.
        """
        out, valor, idx = {}, [], 0
        for s in slides:
            if s["rol"] == "valor":
                idx += 1
                _, _, t, _ = self.maquetar(s, idx)
                valor.append((s, idx, t))
            else:
                self.maquetar(s, None)
                out[s["n"]] = (1.0, None, None)
        if valor:
            t_comun = min(t for _, _, t in valor)
            altos = {}
            for s, i, _ in valor:
                _, _, t, alto = self.maquetar(s, i, t_comun)
                altos[s["n"]] = (t, i, alto)
            alturas = sorted(a for _, _, a in altos.values())
            # Caja de referencia: la más alta (def.) o la mediana (`valor_referencia`).
            if self.e.get("valor_referencia", "mas_alta") == "mediana":
                ref = statistics.median(alturas)
            else:
                ref = alturas[-1]
            y_top = min(self._y_centrado(ref), self.bottom - alturas[-1])
            for n, (t, i, _) in altos.items():
                out[n] = (t, y_top, i)
        return out

    # -- pintado
    def render(self, slide: dict, idx: int, total: int, idx_valor: int | None,
               credito: str = "", portada: Image.Image | None = None,
               t_max: float = 1.0, y_top: float | None = None) -> Image.Image:
        pila, align, _, alto = self.maquetar(slide, idx_valor, t_max)
        if portada is not None and slide["rol"] == "gancho":
            img = portada.copy()
        else:
            img = Image.new("RGB", (self.W, self.H), self.c_fondo)
        d = ImageDraw.Draw(img)

        if y_top is not None:
            y = y_top
        elif slide["rol"] == "gancho" and self.modo_portada == "abajo":
            y = self.zona_gancho[1] - alto      # pegado abajo: la cara queda libre arriba
        else:
            y = self._y_centrado(alto)
        for x in pila:
            if isinstance(x, int):
                y += x
            else:
                x.pintar(d, self.mx, y, self.ancho)
                y += x.alto

        pie = self.H - int(self.e.get("pie_y", 110))
        handle = (self.e.get("handle") or "").strip()
        if handle and not handle.startswith("@"):
            handle = "@" + handle
        f_det = self.f.get("detalle", self.tam.get("handle", 28))

        if slide["rol"] == "gancho":
            self._desliza(d, pie)
            if handle:
                d.text((self.mx, pie), handle, font=f_det, fill=self.c_suave, anchor="ls")
            return img

        # contador «n/N» arriba a la derecha
        f_cont = self.f.get("detalle", self.tam.get("contador", 30))
        cap = -f_cont.getbbox("H", anchor="ls")[1]
        y_cont = int(self.e.get("pie_y", 110)) + cap
        d.text((self.W - self.mx, y_cont), f"{idx}/{total}", font=f_cont,
               fill=self.c_detalle, anchor="rs")

        if slide["rol"] == "cierre":
            if credito:
                f_cred = self.f.get("detalle", self.tam.get("credito", 28))
                d.text((self.mx, pie), credito, font=f_cred, fill=self.c_detalle, anchor="ls")
            if handle:
                d.text((self.W - self.mx, pie), handle, font=f_det, fill=self.c_suave,
                       anchor="rs")
        elif handle:
            d.text((self.mx, pie), handle, font=f_det, fill=self.c_detalle, anchor="ls")
        return img

    def _desliza(self, d: ImageDraw.ImageDraw, base: int):
        """«desliza →» en el color de acento; la flecha se dibuja (Montserrat no trae →)."""
        f = self.f.get("detalle", self.tam.get("desliza", 34))
        txt = (self.e.get("textos") or {}).get("desliza", "desliza")
        s = f.size
        flecha_w, hueco, grosor, punta = round(s * 1.25), round(s * 0.45), max(3, round(s * 0.11)), round(s * 0.34)
        x_fin = self.W - self.mx
        x_ini = x_fin - flecha_w
        y_mid = base - round(-f.getbbox("x", anchor="ls")[1] / 2)
        d.text((x_ini - hueco, base), txt, font=f, fill=self.c_acento, anchor="rs")
        d.rectangle([x_ini, y_mid - grosor // 2, x_fin - punta // 2, y_mid - grosor // 2 + grosor - 1],
                    fill=self.c_acento)
        d.polygon([(x_fin, y_mid), (x_fin - punta, y_mid - punta), (x_fin - punta, y_mid + punta)],
                  fill=self.c_acento)


class _NoAncho(Exception):
    pass


# ------------------------------------------------------------------ portada
def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def fotograma(video: Path, segundo: float) -> Image.Image:
    cmd = [_ffmpeg(), "-v", "error", "-ss", f"{float(segundo):.3f}", "-i", str(video),
           "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"no se pudo sacar el fotograma del segundo {segundo} de "
                           f"{video.name}: {(r.stderr or b'').decode('utf-8', 'ignore')[-300:]}")
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def preparar_portada(valor, plan_dir: Path | None, estilo: dict,
                     modo: str = "abajo") -> Image.Image | None:
    """Imagen o fotograma de vídeo → cover 1080x1350 oscurecido.

    modo "abajo": degradado del color de fondo que sube desde abajo
    (`portada_degradado`: `base` arriba, sube entre `desde` y `hasta` y se queda
    en `max`), para que la cara se vea arriba y el texto se lea abajo.
    modo "centro": oscurecido plano (`portada_oscurecer`, ~0,6).
    """
    port = normalizar_portada(valor, plan_dir)
    if not port or "_error" in port:
        return None
    path: Path = port["_path"]
    if path.suffix.lower() in IMAGEN_EXTS:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    else:
        img = fotograma(path, port.get("segundo", 0) or 0)
    W, H = config.CARRUSEL_W, config.CARRUSEL_H
    escala = max(W / img.width, H / img.height)
    img = img.resize((max(W, round(img.width * escala)), max(H, round(img.height * escala))),
                     Image.LANCZOS)
    foco = float(port.get("foco_y", estilo.get("portada_foco_y", 0.5)))
    x = (img.width - W) // 2
    y = round((img.height - H) * min(1.0, max(0.0, foco)))
    img = img.crop((x, y, x + W, y + H))
    capa = Image.new("RGB", (W, H), _rgb(estilo["colores"]["fondo"]))
    if modo != "abajo":
        oscuro = float(estilo.get("portada_oscurecer", 0.6))
        return Image.blend(img, capa, max(0.0, min(1.0, oscuro)))
    g = estilo.get("portada_degradado") or {}
    base, maximo = float(g.get("base", 0.12)), float(g.get("max", 0.93))
    desde, hasta = float(g.get("desde", 0.35)), float(g.get("hasta", 0.70))
    filas = []
    for fy in range(H):
        u = min(1.0, max(0.0, (fy / H - desde) / max(1e-6, hasta - desde)))
        u = u * u * (3 - 2 * u)                                  # smoothstep
        filas.append(round(255 * (base + (maximo - base) * u)))
    mascara = Image.new("L", (1, H))
    mascara.putdata(filas)
    return Image.composite(capa, img, mascara.resize((W, H)))


def nitidez(img: Image.Image, caja: tuple = (0.32, 0.10, 0.68, 0.42)) -> float:
    """Varianza del laplaciano (en gris) dentro de `caja` (fracciones x0, y0, x1, y1)."""
    from PIL import ImageFilter, ImageStat
    w, h = img.size
    x0, y0, x1, y1 = caja
    zona = img.convert("L").crop((round(w * x0), round(h * y0), round(w * x1), round(h * y1)))
    lap = zona.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1,
                                         offset=128))
    return ImageStat.Stat(lap).var[0]


def candidatos_portada(video: Path, paso: float = 0.5, n: int = 8,
                       caja: tuple = (0.32, 0.10, 0.68, 0.42),
                       separacion: float = 1.0) -> list[tuple[float, float, Image.Image]]:
    """Fotogramas más NÍTIDOS del vídeo: varianza del laplaciano en `caja` (por
    defecto la zona de la cara en un vertical de busto: centro, mitad superior;
    así no puntúan las estanterías del fondo ni los rótulos). Devuelve
    hasta `n` (segundo, nitidez, imagen) separados al menos `separacion` s. El
    gesto se elige mirando la hoja (`carruseles.py --candidatos-portada`)."""
    cmd = [_ffmpeg(), "-v", "error", "-i", str(video), "-vf", f"fps={1 / paso:g}",
           "-f", "image2pipe", "-vcodec", "bmp", "-"]
    r = subprocess.run(cmd, capture_output=True)
    datos, i, frames = r.stdout, 0, []
    while i + 6 <= len(datos) and datos[i:i + 2] == b"BM":
        tam = int.from_bytes(datos[i + 2:i + 6], "little")
        frames.append(Image.open(io.BytesIO(datos[i:i + tam])).convert("RGB"))
        i += tam
    puntuados = sorted(((k * paso, nitidez(f, caja), f) for k, f in enumerate(frames)),
                       key=lambda x: -x[1])
    elegidos: list = []
    for seg, nit, f in puntuados:
        if all(abs(seg - s2) >= separacion for s2, _, _ in elegidos):
            elegidos.append((seg, nit, f))
        if len(elegidos) >= n:
            break
    return elegidos


# ------------------------------------------------------------------ salida
def perfil_srgb() -> bytes | None:
    try:
        from PIL import ImageCms
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        return None


def guardar_jpg(img: Image.Image, path: Path, calidad: int, icc: bytes | None,
                max_bytes: int = config.CARRUSEL_MAX_BYTES) -> int:
    """Guarda en JPEG (4:4:4, sRGB). Si pasara del límite, baja la calidad."""
    q = int(calidad)
    while True:
        kw = {"quality": q, "subsampling": 0, "optimize": True}
        if icc:
            kw["icc_profile"] = icc
        img.convert("RGB").save(path, "JPEG", **kw)
        size = path.stat().st_size
        if size < max_bytes or q <= 70:
            return size
        q -= 5


def hoja_contacto(imgs: list[Image.Image], fondo=(11, 13, 18), etiqueta=(139, 145, 161),
                  fuente: ImageFont.FreeTypeFont | None = None) -> Image.Image:
    """Todas las slides en miniatura (1/3), hasta 5 por fila, con su número."""
    tw, th = config.CARRUSEL_W // 3, config.CARRUSEL_H // 3
    cols = min(5, len(imgs))
    filas = (len(imgs) + cols - 1) // cols
    pad, lab = 24, 40
    hoja = Image.new("RGB", (cols * tw + (cols + 1) * pad, filas * (th + lab) + (filas + 1) * pad),
                     fondo)
    d = ImageDraw.Draw(hoja)
    for i, im in enumerate(imgs):
        c, r = i % cols, i // cols
        x = pad + c * (tw + pad)
        y = pad + r * (th + lab + pad)
        hoja.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        if fuente:
            d.text((x, y + th + 10), f"{i + 1:02d}", font=fuente, fill=etiqueta)
    return hoja

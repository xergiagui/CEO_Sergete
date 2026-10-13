"""
CALENDARIO DE PUBLICACIÓN de un proyecto (proyecto.json → "calendario").

Adaptado de sergebulaev/instagram-skills (MIT), skill ig-content-planner: Reels
para alcance, carruseles para guardados, historias para la relación; 4–5 posts
de feed por semana con una mezcla equilibrada de formatos, objetivos y pilares.
Explicación para personas: referencias/calendario.md.

Antes de nada, `copys.py calendario …` mira las carpetas del proyecto (la misma detección
que `sincronizar`): lo que está en *publicados* es Publicado, así que nunca sale como
ATRASADO ni lo mueve --replanificar-atrasados (`hoy` y `ver` solo en memoria; `planificar`
lo guarda en el Excel).

`copys.py calendario planificar`:
  1. Lee el registro. Una PIEZA = un ID (sus filas por plataforma comparten fecha).
  2. Respeta TODAS las fechas ya puestas: es ESTABLE (volver a ejecutarlo no
     recoloca nada). Las fechas MANUALES (las que no coinciden con lo que apuntó
     el planificador en la hoja oculta _calendario) no se mueven nunca; con
     --replanificar-atrasados se mueven solo las atrasadas que puso él.
  3. Coloca las piezas Pendientes sin fecha en los huecos libres desde mañana:
     `publicaciones_semana` por semana, en los `dias` del calendario y a la hora
     de su franja. Para cada hueco elige, de las que esperan, la que menos reglas
     rompe (orden de prioridad):
       a) deja sitio al mínimo de cada formato (≥ 2 Reels y ≥ 2 carruseles): en
          los primeros `reserva_formatos_dias` solo si hay piezas de ese formato;
          después, aunque no las haya (el hueco queda libre para encargarlas);
       b) no más de `formula_max` carruseles de la misma fórmula por semana;
       c) no pasar de `pilar_max` (promoción ≤ 2);
       d) lo que lleva más de `prioridad_tras_dias` esperando pasa delante;
       e) cubrir los mínimos de objetivo (≥ 3 guardados, ≥ 2 compartidos) cuando
          ya no quedan huecos de sobra;
       f) no poner seguidas dos piezas del mismo vídeo de origen ni de la misma
          oferta (la genérica no cuenta);
       g) alternar formato con la pieza anterior;
       h) a igualdad, la más antigua (por ID).
  4. Reparte las historias de la carpeta de historias (`por_dia_min`–`por_dia_max`
     al día) de forma estable y sin moverlas (hoja Historias del Excel).
  5. Balance y huecos por semana → Excel + calendario/<AAAA>-W<ss>.md.
"""
from __future__ import annotations

import bisect
import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import config
from lib import carrusel as car
from lib.registro import formato_de_fila
from lib.util import normalizar

UNA_SEMANA = dt.timedelta(days=7)
RECORDATORIO = "Comparte en historias el post del día cuando lo publiques."
RECORDATORIO_SIN_POST = "Hoy no hay post: vuelve a compartir en historias el último."


# ------------------------------------------------------------------ fechas
def a_fecha(v) -> dt.date | None:
    """Fecha de una celda: date/datetime, '20/10/2026', '2026-10-20', '20-10-26'… o None."""
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, (int, float)) and 20000 < v < 80000:  # nº de serie de Excel
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    s = str(v).strip()
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s[:10] if f.startswith("%Y") else s, f).date()
        except ValueError:
            continue
    return None


def a_hora(v) -> dt.time | None:
    """Hora de una celda: time/datetime, '13:30', '13.30', '13h30', 0.5625 (fracción de día)…"""
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v.time().replace(second=0, microsecond=0)
    if isinstance(v, dt.time):
        return v.replace(second=0, microsecond=0)
    if isinstance(v, dt.timedelta):
        m = int(v.total_seconds() // 60) % (24 * 60)
        return dt.time(m // 60, m % 60)
    if isinstance(v, (int, float)) and 0 <= v < 1:
        m = round(v * 24 * 60) % (24 * 60)
        return dt.time(m // 60, m % 60)
    m = re.fullmatch(r"\s*(\d{1,2})\s*[:.hH]\s*(\d{2})?\s*(?:h)?\s*", str(v))
    if m and int(m.group(1)) < 24 and int(m.group(2) or 0) < 60:
        return dt.time(int(m.group(1)), int(m.group(2) or 0))
    return None


def hhmm(t: dt.time | None) -> str:
    return t.strftime("%H:%M") if t else ""


def lunes(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def semana_iso(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def lunes_de_semana(txt: str) -> dt.date:
    m = re.fullmatch(r"\s*(\d{4})-?W(\d{1,2})\s*", str(txt), re.IGNORECASE)
    if not m:
        raise ValueError(f"Semana '{txt}': usa el formato AAAA-Www (p. ej. 2026-W42).")
    return dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)


def dia_corto(d: dt.date) -> str:
    return f"{config.DIAS[d.weekday()]} {d:%d/%m}"


def hoy_en(zona: str) -> dt.date:
    """Hoy en la zona del calendario (si el sistema no tiene la base de zonas, la hora local del PC)."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(zona)).date()
    except Exception:
        return dt.date.today()


# ------------------------------------------------------------------ configuración
class Conf:
    """proyecto.json → calendario, con valores por defecto."""

    def __init__(self, proyecto):
        c = proyecto.calendario
        self.activo = bool(c.get("activo"))
        self.provisional = bool(c.get("_nota"))
        self.nota = c.get("_nota") or ""
        self.zona = c.get("zona_horaria") or "Europe/Madrid"
        self.pub_semana = int(c.get("publicaciones_semana") or 5)
        self.dias = list(c.get("dias") or ["lun", "mar", "jue", "vie", "dom"])
        self.franjas = {k: a_hora(v) for k, v in (c.get("franjas") or {}).items() if not k.startswith("_")}
        self.segunda = a_hora(c.get("segunda_franja")) if c.get("segunda_franja") else None
        self.semanas = int(c.get("semanas_por_defecto") or 2)
        self.reserva_dias = int(c.get("reserva_formatos_dias", 7))
        self.prioridad_dias = int(c.get("prioridad_tras_dias", 14))
        b = c.get("balance") or {}
        limpio = lambda d: {k: int(v) for k, v in (d or {}).items() if not str(k).startswith("_")}
        self.formato_min = limpio(b.get("formato_min"))
        self.objetivo_min = limpio(b.get("objetivo_min"))
        self.pilar_max = limpio(b.get("pilar_max"))
        self.formula_max = int(b["formula_max"]) if b.get("formula_max") else None
        self.evitar = set(b.get("evitar_seguidas") or [])
        h = c.get("historias") or {}
        self.hist_min = int(h.get("por_dia_min", 2))
        self.hist_max = int(h.get("por_dia_max", 4))
        self.recordatorio = h.get("recordatorio") or RECORDATORIO
        self.recordatorio_sin_post = h.get("recordatorio_sin_post") or RECORDATORIO_SIN_POST

    def dia(self, d: dt.date) -> str:
        return config.DIAS[d.weekday()]

    def franja(self, d: dt.date) -> dt.time:
        return self.franjas.get(self.dia(d)) or self.segunda or dt.time(13, 30)


# ------------------------------------------------------------------ piezas
@dataclass
class Pieza:
    id: str
    clip: str
    formato: str                       # reel | carrusel
    ruta: str = ""
    tema: str = ""
    oferta: str | None = None          # id canónico
    oferta_nombre: str = ""
    objetivo: str | None = None
    pilar: str | None = None
    estado: str = "Pendiente"
    fecha: dt.date | None = None       # Fecha prevista
    hora: dt.time | None = None        # Hora prevista
    fecha_pub: dt.date | None = None
    fecha_alta: dt.date | None = None
    filas: list[int] = field(default_factory=list)
    manual: bool = False               # fecha puesta a mano (no la puso el planificador)
    formula: str | None = None
    origen: str | None = None
    orden: tuple = (10 ** 9, "")
    nueva: bool = False                # fecha puesta en esta ejecución
    fecha_antes: dt.date | None = None  # atrasada que se ha replanificado
    en_publicados: bool = False        # la pieza está en la carpeta de publicados

    @property
    def cuando(self) -> dt.date | None:
        return self.fecha or (self.fecha_pub if self.estado == "Publicado" else None)

    @property
    def momento(self) -> dt.datetime:
        return dt.datetime.combine(self.cuando or dt.date.max, self.hora or dt.time(0, 0))

    @property
    def fmt(self) -> str:
        return config.FORMATOS.get(self.formato, self.formato)

    def atrasada(self, hoy: dt.date) -> bool:
        """Fecha pasada y sin publicar. Lo que está en publicados nunca está atrasado."""
        return (self.estado == "Pendiente" and not self.en_publicados and bool(self.fecha)
                and self.fecha < hoy)

    def resumen(self) -> dict:
        return {"id": self.id, "pieza": self.clip, "formato": self.formato, "fecha": self.fecha.isoformat()
                if self.fecha else None, "hora": hhmm(self.hora) or None, "objetivo": self.objetivo,
                "pilar": self.pilar, "oferta": self.oferta, "formula": self.formula, "estado": self.estado,
                "manual": self.manual, "ruta": self.ruta}


def _estado(estados: list[str]) -> str:
    e = [x or "Pendiente" for x in estados]
    for cual in ("Pendiente", "Publicado"):
        if cual in e:
            return cual
    if all(x == "Descartado" for x in e):
        return "Descartado"
    return "No encontrado" if "No encontrado" in e else e[0]


def _origen_clip(stem: str, buscador) -> str:
    carpeta = buscador.origen(stem) if buscador is not None else None
    return "video:" + normalizar(carpeta) if carpeta else "clip:" + normalizar(stem)


def _origen(p: Pieza, buscador) -> str | None:
    """Vídeo (o fuente) del que sale la pieza. Solo se consulta para no poner seguidas dos
    piezas del mismo origen; no se guarda en el registro. `buscador` = BuscadorMetadatos
    del proyecto (solo mira sus carpetas de contexto)."""
    if p.formato == "reel":
        return _origen_clip(Path(p.clip).stem, buscador)
    f = car.fuente(Path(p.ruta)) if p.ruta else {}
    tipo, ruta = str(f.get("tipo") or "").lower(), str(f.get("ruta") or "")
    if tipo == "clip" and ruta:
        return _origen_clip(Path(ruta).stem, buscador)
    if tipo == "video" and ruta:
        # el MP4 del vídeo largo o su carpeta de transcripción (TheEditor/proyectos/<id>/transcripciones, _Historico/<id>)
        r = Path(ruta)
        return "video:" + normalizar(r.stem if r.suffix.lower() in config.EXT_VIDEO else r.name)
    if ruta:
        return f"{tipo or 'fuente'}:" + normalizar(ruta)
    return None


def piezas_de_registro(proyecto, reg, buscador=None) -> list[Pieza]:
    """Piezas del registro. Con `buscador` (BuscadorMetadatos del proyecto) se calcula su origen."""
    grupos: dict[str, list[dict]] = {}
    filas: dict[str, list[int]] = {}
    for fila, d in reg.filas():
        key = str(d.get("ID") or d.get("Clip") or "").strip()
        if key:
            grupos.setdefault(key, []).append(d)
            filas.setdefault(key, []).append(fila)
    plan = reg.plan_auto()
    c_of, c_obj, c_pil = proyecto.campo("oferta"), proyecto.campo("objetivo"), proyecto.campo("pilar")
    generico = (proyecto.ofertas.get("generico") or {}).get("id", "generico")

    def primero(ds, col, conv=lambda v: v):
        for d in ds:
            v = conv(d.get(col))
            if v not in (None, ""):
                return v
        return None

    out = []
    for key, ds in grupos.items():
        oferta_nombre = primero(ds, c_of["columna"]) if c_of else None
        oferta = proyecto.canon_valor(c_of, oferta_nombre) if (c_of and oferta_nombre) else None
        p = Pieza(
            id=key, clip=str(primero(ds, "Clip") or key), formato=formato_de_fila(ds[0]),
            ruta=str(primero(ds, "Ruta") or ""), tema=str(primero(ds, "Tema") or ""),
            oferta=None if oferta == generico else oferta, oferta_nombre=str(oferta_nombre or ""),
            objetivo=proyecto.canon_valor(c_obj, primero(ds, c_obj["columna"])) if c_obj else None,
            pilar=proyecto.canon_valor(c_pil, primero(ds, c_pil["columna"])) if c_pil else None,
            estado=_estado([d.get("Estado") for d in ds]),
            fecha=primero(ds, "Fecha prevista", a_fecha), hora=primero(ds, "Hora prevista", a_hora),
            fecha_pub=primero(ds, "Fecha publicación", a_fecha), fecha_alta=primero(ds, "Fecha alta", a_fecha),
            filas=filas[key])
        m = re.search(r"(\d+)$", key)
        p.orden = (int(m.group(1)) if m else 10 ** 9, p.clip.lower())
        p.manual = bool(p.fecha) and plan.get(key) != (p.fecha.isoformat(), hhmm(p.hora))
        if p.formato == "carrusel":
            p.formula = car.formula(Path(p.ruta)) if p.ruta else None
        if buscador is not None:
            p.origen = _origen(p, buscador)
        out.append(p)
    return out


# ------------------------------------------------------------------ huecos
def slots_libres(w: dt.date, en_semana: list[Pieza], cfg: Conf, desde: dt.date, hasta: dt.date
                 ) -> list[tuple[dt.date, dt.time]]:
    """Huecos de la semana `w` (lunes) entre `desde` y `hasta`, en orden de llenado:
    primero la franja de cada día de publicación sin post; la segunda franja solo si
    la semana pide más posts que días de publicación."""
    por_dia = Counter(p.cuando for p in en_semana)
    horas = {(p.cuando, p.hora) for p in en_semana}
    dias = [w + dt.timedelta(days=i) for i in range(7)]
    dias = [d for d in dias if cfg.dia(d) in cfg.dias and desde <= d <= hasta]
    out = [(d, cfg.franja(d)) for d in dias if por_dia[d] == 0]
    if cfg.pub_semana > len(cfg.dias) and cfg.segunda:
        out += [(d, cfg.segunda) for d in dias
                if cfg.segunda != cfg.franja(d) and por_dia[d] <= 1 and (d, cfg.segunda) not in horas]
    return out


def _conflictos(p: Pieza, q: Pieza | None, cfg: Conf) -> list[str]:
    if q is None:
        return []
    out = []
    if "origen" in cfg.evitar and p.origen and p.origen == q.origen:
        out.append("mismo vídeo de origen")
    if "oferta" in cfg.evitar and p.oferta and p.oferta == q.oferta:
        out.append("misma oferta")
    return out


def _vecinos(timeline: list[Pieza], momento: dt.datetime) -> tuple[Pieza | None, Pieza | None]:
    prev = next((p for p in reversed(timeline) if p.momento < momento), None)
    nxt = next((p for p in timeline if p.momento > momento), None)
    return prev, nxt


def _elegir(pool: list[Pieza], d: dt.date, h: dt.time, quedan: int, en_semana: list[Pieza],
            timeline: list[Pieza], cfg: Conf, inicio: dt.date) -> Pieza | None:
    """La pieza del `pool` que mejor encaja en el hueco (d, h). None = dejar el hueco libre."""
    fmt = Counter(p.formato for p in en_semana)
    falta_fmt = {f: max(0, m - fmt[f]) for f, m in cfg.formato_min.items()}
    hay = Counter(p.formato for p in pool)
    estricto = d >= inicio + dt.timedelta(days=cfg.reserva_dias)
    reservado = {f: (n if estricto else min(n, hay[f])) for f, n in falta_fmt.items()}
    obj = Counter(p.objetivo for p in en_semana)
    falta_obj = {o: max(0, m - obj[o]) for o, m in cfg.objetivo_min.items()}
    justo = sum(falta_obj.values()) >= quedan
    pil = Counter(p.pilar for p in en_semana)
    formulas = Counter(p.formula for p in en_semana if p.formato == "carrusel" and p.formula)
    prev, nxt = _vecinos(timeline, dt.datetime.combine(d, h))

    mejores = []
    for p in pool:
        otros = sum(n for f, n in reservado.items() if f != p.formato)
        if otros > quedan - 1 and not falta_fmt.get(p.formato):
            continue  # el hueco se guarda para el formato que falta
        clave = (
            int(bool(p.formato == "carrusel" and p.formula and cfg.formula_max
                     and formulas[p.formula] >= cfg.formula_max)),
            int(bool(p.pilar in cfg.pilar_max and pil[p.pilar] >= cfg.pilar_max[p.pilar])),
            0 if (p.fecha_alta and (d - p.fecha_alta).days >= cfg.prioridad_dias) else 1,
            int(justo and not falta_obj.get(p.objetivo)),
            len(_conflictos(p, prev, cfg)) + len(_conflictos(p, nxt, cfg)),
            int(bool(prev and prev.formato == p.formato)),
            p.orden,
        )
        mejores.append((clave, p))
    return min(mejores, key=lambda x: x[0])[1] if mejores else None


# ------------------------------------------------------------------ planificar
def planificar(proyecto, piezas: list[Pieza], inicio: dt.date, semanas: int, hoy: dt.date,
               replanificar_atrasados: bool = False) -> dict:
    """Pone fecha y hora a las piezas Pendientes sin fecha. Modifica las Pieza en sitio."""
    cfg = Conf(proyecto)
    fin = lunes(inicio) + dt.timedelta(days=7 * max(1, semanas) - 1)
    res = {"cfg": cfg, "inicio": inicio, "fin": fin, "hoy": hoy, "asignadas": [], "horas": [],
           "movidas": [], "atrasadas": [], "atrasadas_manuales": [], "sin_hueco": []}
    vivas = [p for p in piezas if p.estado != "Descartado"]

    # 1) atrasadas: se mueven solo con --replanificar-atrasados y si las puso el planificador
    for p in sorted(vivas, key=lambda p: p.orden):
        if p.atrasada(hoy):
            if replanificar_atrasados and not p.manual:
                p.fecha_antes, p.fecha, p.hora = p.fecha, None, None
                res["movidas"].append(p)
            elif replanificar_atrasados:
                res["atrasadas_manuales"].append(p)
            else:
                res["atrasadas"].append(p)

    # 2) fecha puesta a mano sin hora → la franja de ese día (o la segunda si está ocupada)
    ocupado = {(p.cuando, p.hora) for p in vivas if p.cuando and p.hora}
    for p in sorted(vivas, key=lambda p: p.orden):
        if p.fecha and not p.hora:
            h = cfg.franja(p.fecha)
            if (p.fecha, h) in ocupado and cfg.segunda:
                h = cfg.segunda
            p.hora = h
            ocupado.add((p.fecha, h))
            res["horas"].append(p)

    # 3) huecos libres desde `inicio`, semana a semana
    colocadas = [p for p in vivas if p.cuando]
    timeline = sorted(colocadas, key=lambda p: p.momento)
    pool = sorted((p for p in vivas if p.estado == "Pendiente" and not p.fecha), key=lambda p: p.orden)
    w = lunes(inicio)
    while w <= fin and pool:
        en_semana = [p for p in colocadas if lunes(p.cuando) == w]
        cap = cfg.pub_semana - len(en_semana)
        libres = slots_libres(w, en_semana, cfg, inicio, fin)
        for k, (d, h) in enumerate(libres):
            if cap <= 0 or not pool:
                break
            p = _elegir(pool, d, h, min(cap, len(libres) - k), en_semana, timeline, cfg, inicio)
            if p is None:
                continue  # hueco reservado para un formato que falta
            p.fecha, p.hora, p.nueva = d, h, True
            pool.remove(p)
            en_semana.append(p)
            colocadas.append(p)
            bisect.insort(timeline, p, key=lambda x: x.momento)
            cap -= 1
            res["asignadas"].append(p)
        w += UNA_SEMANA
    res["sin_hueco"] = pool
    return res


# ------------------------------------------------------------------ historias
def archivos_historias(carpeta: Path | None) -> list[Path]:
    if not carpeta or not Path(carpeta).exists():
        return []
    fs = [f for f in Path(carpeta).iterdir()
          if f.is_file() and f.suffix.lower() in config.EXT_HISTORIA and not f.name.startswith(("_", "~$", "."))]
    return sorted(fs, key=lambda f: (f.stat().st_mtime, f.name.lower()))


def asignar_historias(existentes: list[dict], archivos: list[Path], desde: dt.date, hasta: dt.date,
                      hoy: dt.date, cfg: Conf, replanificar_atrasados: bool = False) -> dict:
    """Reparte las historias por día de forma ESTABLE: lo ya asignado (o cambiado a mano en la
    hoja Historias) se queda; lo nuevo rellena primero hasta `por_dia_min` y luego hasta
    `por_dia_max`. Las que ya no están en la carpeta (publicadas o borradas) salen del plan."""
    presentes = {f.name: f for f in archivos}
    asign: dict[str, dt.date] = {}
    for d in existentes:
        nombre, fecha = str(d.get("Archivo") or "").strip(), a_fecha(d.get("Fecha prevista"))
        if nombre in presentes and fecha:
            asign[nombre] = fecha
    atrasadas = sorted(a for a, f in asign.items() if f < hoy)
    if replanificar_atrasados:
        for a in atrasadas:
            del asign[a]
    pool = [f.name for f in archivos if f.name not in asign]
    cuenta = Counter(asign.values())
    dias = [desde + dt.timedelta(days=i) for i in range((hasta - desde).days + 1)]
    nuevas = 0
    for limite in (cfg.hist_min, cfg.hist_max):
        for d in dias:
            while cuenta[d] < limite and pool:
                asign[pool.pop(0)] = d
                cuenta[d] += 1
                nuevas += 1
    por_dia: dict[dt.date, list[str]] = {}
    for a, f in sorted(asign.items(), key=lambda x: (x[1], x[0].lower())):
        por_dia.setdefault(f, []).append(a)
    return {"asignacion": asign, "por_dia": por_dia, "nuevas": nuevas, "sin_dia": pool,
            "atrasadas": [] if replanificar_atrasados else atrasadas,
            "movidas": atrasadas if replanificar_atrasados else []}


def historias_por_dia(existentes: list[dict]) -> dict[dt.date, list[str]]:
    out: dict[dt.date, list[str]] = {}
    for d in existentes:
        f = a_fecha(d.get("Fecha prevista"))
        if f and d.get("Archivo"):
            out.setdefault(f, []).append(str(d["Archivo"]))
    return out


# ------------------------------------------------------------------ balance
def _repartir(huecos: int, falta: dict[str, int]) -> dict[str, int]:
    """Reparte los huecos libres entre los formatos que faltan (alternando, empezando por el
    que más falta; a igualdad, carrusel). Lo que sobra = 'cualquiera'."""
    out = {f: 0 for f in config.FORMATOS}
    resto = dict(falta)
    orden = sorted(resto, key=lambda f: (-resto[f], f != "carrusel"))
    h = huecos
    while h > 0 and any(resto.values()):
        for f in orden:
            if h > 0 and resto.get(f, 0) > 0:
                out[f] += 1
                resto[f] -= 1
                h -= 1
    out["cualquiera"] = h
    return out


def balance(w: dt.date, piezas: list[Pieza], cfg: Conf, desde: dt.date, hasta: dt.date,
            hist_por_dia: dict[dt.date, list[str]] | None = None, hist_desde: dt.date | None = None) -> dict:
    """Balance de la semana `w` (lunes): formatos, objetivos, pilares, fórmulas, seguidas, huecos."""
    en = sorted((p for p in piezas if p.estado != "Descartado" and p.cuando and lunes(p.cuando) == w),
                key=lambda p: p.momento)
    fmt = Counter(p.formato for p in en)
    obj = Counter(p.objetivo or "sin objetivo" for p in en)
    pil = Counter(p.pilar or "sin pilar" for p in en)
    formulas = Counter(p.formula for p in en if p.formato == "carrusel" and p.formula)
    cap = max(0, cfg.pub_semana - len(en))
    huecos = slots_libres(w, en, cfg, desde, hasta)[:cap]
    falta_fmt = {f: max(0, m - fmt[f]) for f, m in cfg.formato_min.items()}
    faltan = _repartir(len(huecos), falta_fmt)

    avisos = []
    for f, m in cfg.formato_min.items():
        if fmt[f] < m:
            avisos.append(f"{config.FORMATOS_PLURAL[f]}: {fmt[f]} (mín. {m})")
    for o, m in cfg.objetivo_min.items():
        if obj[o] < m:
            avisos.append(f"objetivo {o}: {obj[o]} (recomendado ≥ {m})")
    for pl, m in cfg.pilar_max.items():
        if pil[pl] > m:
            avisos.append(f"pilar {pl}: {pil[pl]} (recomendado ≤ {m})")
    if cfg.formula_max:
        for f, n in formulas.items():
            if n > cfg.formula_max:
                avisos.append(f"fórmula {f}: {n} carruseles (máx. {cfg.formula_max} por semana)")
    anterior = _ultimo_post(piezas, w)  # la última de la semana anterior también cuenta
    for a, b in zip([anterior] + en if anterior else en, en if anterior else en[1:]):
        c = _conflictos(b, a, cfg)
        if c:
            avisos.append(f"{a.id} y {b.id} van seguidas: {' y '.join(c)}")
    if len(en) > cfg.pub_semana:
        avisos.append(f"{len(en)} publicaciones (el calendario pide {cfg.pub_semana})")

    dias = [w + dt.timedelta(days=i) for i in range(7)]
    hist_desde = hist_desde or desde
    hist = {d: len((hist_por_dia or {}).get(d, [])) for d in dias}
    hist_faltan = sum(max(0, cfg.hist_min - hist[d]) for d in dias if hist_desde <= d <= hasta)
    return {
        "semana": semana_iso(w), "lunes": w, "piezas": en, "publicaciones": len(en),
        "objetivo_publicaciones": cfg.pub_semana, "reels": fmt["reel"], "carruseles": fmt["carrusel"],
        "objetivos": dict(obj), "pilares": dict(pil), "formulas": dict(formulas),
        "huecos": huecos, "faltan": faltan, "avisos": avisos,
        "historias": sum(hist.values()), "historias_faltan": hist_faltan, "historias_por_dia": hist,
    }


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def texto_faltan(b: dict) -> str:
    f = b["faltan"]
    partes = []
    if f.get("reel"):
        partes.append(_plural(f["reel"], "Reel", "Reels"))
    if f.get("carrusel"):
        partes.append(_plural(f["carrusel"], "carrusel", "carruseles"))
    if f.get("cualquiera"):
        partes.append(_plural(f["cualquiera"], "pieza más", "piezas más") + " (Reel o carrusel)")
    if not partes:
        if b["publicaciones"] >= b["objetivo_publicaciones"]:
            return "semana completa"
        return "sin más huecos libres"
    return "faltan " + (", ".join(partes[:-1]) + " y " + partes[-1] if len(partes) > 1 else partes[0])


def linea_semana(b: dict) -> str:
    fin = b["lunes"] + dt.timedelta(days=6)
    return (f"Semana {b['semana']} ({b['lunes']:%d/%m}–{fin:%d/%m}): {b['publicaciones']}/{b['objetivo_publicaciones']} "
            f"publicaciones · {_plural(b['reels'], 'Reel', 'Reels')} · "
            f"{_plural(b['carruseles'], 'carrusel', 'carruseles')} · {texto_faltan(b)}"
            + (f" · historias: faltan {b['historias_faltan']}" if b["historias_faltan"] else ""))


def linea_faltan(balances: list[dict]) -> str:
    """Línea final parseable: FALTAN 2026-W42 reels=0 carruseles=1 cualquiera=1 huecos=2 historias=0 | …"""
    partes = [f"{b['semana']} reels={b['faltan']['reel']} carruseles={b['faltan']['carrusel']} "
              f"cualquiera={b['faltan']['cualquiera']} huecos={len(b['huecos'])} historias={b['historias_faltan']}"
              for b in balances]
    return "FALTAN " + " | ".join(partes)


def balance_json(b: dict, md: Path | None = None) -> dict:
    return {
        "semana": b["semana"], "desde": b["lunes"].isoformat(),
        "hasta": (b["lunes"] + dt.timedelta(days=6)).isoformat(),
        "publicaciones": b["publicaciones"], "objetivo_publicaciones": b["objetivo_publicaciones"],
        "reels": b["reels"], "carruseles": b["carruseles"],
        "faltan": {"reels": b["faltan"]["reel"], "carruseles": b["faltan"]["carrusel"],
                   "cualquiera": b["faltan"]["cualquiera"]},
        "huecos": [{"fecha": d.isoformat(), "hora": hhmm(h)} for d, h in b["huecos"]],
        "historias": b["historias"], "historias_faltan": b["historias_faltan"],
        "objetivos": b["objetivos"], "pilares": b["pilares"], "formulas": b["formulas"],
        "avisos": b["avisos"], "piezas": [p.resumen() for p in b["piezas"]],
        **({"md": str(md)} if md else {}),
    }


# ------------------------------------------------------------------ salidas
def _marca(p: Pieza, hoy: dt.date) -> str:
    if p.estado == "Publicado":
        return " · publicado" + (f" el {p.fecha_pub:%d/%m}" if p.fecha_pub else "")
    if p.estado == "No encontrado":
        return " · NO ENCONTRADO"
    if p.atrasada(hoy):
        return " · ATRASADO"
    return " · fecha manual" if p.manual else ""


def _ultimo_post(piezas: list[Pieza], d: dt.date) -> Pieza | None:
    antes = [p for p in piezas if p.estado != "Descartado" and p.cuando and p.cuando < d]
    return max(antes, key=lambda p: p.momento) if antes else None


def recordatorio(piezas: list[Pieza], d: dt.date, cfg: Conf, hoy: dt.date | None = None) -> str:
    del_dia = [p for p in piezas if p.estado != "Descartado" and p.cuando == d]
    if del_dia:
        return f"{cfg.recordatorio.rstrip('. ')} ({', '.join(p.id for p in del_dia)})."
    # el último post que de verdad estará publicado: lo publicado o lo previsto de hoy en adelante
    hoy = hoy or d
    ult = _ultimo_post([p for p in piezas if p.estado == "Publicado" or (p.cuando and p.cuando >= hoy)], d)
    if not ult:
        return "Hoy no hay post de feed."
    return f"{cfg.recordatorio_sin_post.rstrip('. ')} ({ult.id})."


def md_semana(proyecto, cfg: Conf, b: dict, piezas: list[Pieza], hist_por_dia: dict[dt.date, list[str]],
              carpeta_hist: Path | None, hoy: dt.date, desde: dt.date) -> str:
    w = b["lunes"]
    fin = w + dt.timedelta(days=6)
    L = [f"# {proyecto.nombre} · semana {b['semana']} ({w:%d/%m} – {fin:%d/%m/%Y})", "",
         f"> Generado el {dt.datetime.now():%d/%m/%Y %H:%M} con `copys.py calendario planificar`. "
         f"Se rehace en cada planificación: los cambios, en el Excel (Fecha prevista / Hora prevista).", ""]
    if cfg.provisional:
        L += [f"> **Calendario:** {cfg.nota}", ""]
    L += [f"**{linea_semana(b)}**", "", "## Día a día", ""]
    huecos_dia = {}
    for d, h in b["huecos"]:
        huecos_dia.setdefault(d, []).append(h)
    for i in range(7):
        d = w + dt.timedelta(days=i)
        del_dia = [p for p in b["piezas"] if p.cuando == d]
        titulo = f"### {config.NOMBRES_DIA[i].capitalize()} {d:%d/%m}"
        if not del_dia and not huecos_dia.get(d):
            titulo += " · sin post de feed"
        L.append(titulo)
        for p in del_dia:
            L.append(f"- **{hhmm(p.hora) or '--:--'} · {p.fmt} · {p.id}** `{p.clip}`{_marca(p, hoy)}")
            datos = [f"Objetivo: {p.objetivo or '—'}", f"Pilar: {p.pilar or '—'}"]
            if p.oferta_nombre:
                datos.append(f"Oferta: {p.oferta_nombre}")
            if p.formula:
                datos.append(f"Fórmula: {p.formula}")
            L.append("  - " + " · ".join(datos))
            if p.tema:
                L.append(f"  - Tema: {p.tema}")
            L.append(f"  - Ruta: `{p.ruta}`")
        for h in huecos_dia.get(d, []):
            L.append(f"- **{hhmm(h)} · hueco libre** (falta pieza)")
        if d >= desde:
            hs = hist_por_dia.get(d, [])
            if hs:
                L.append(f"- Historias ({len(hs)}): " + ", ".join(f"`{x}`" for x in hs))
            else:
                L.append(f"- Historias: ninguna asignada (faltan {cfg.hist_min})")
            L.append(f"- Recordatorio: {recordatorio(piezas, d, cfg, hoy)}")
        L.append("")

    obj, pil = b["objetivos"], b["pilares"]
    fila = lambda a, v, r: f"| {a} | {v} | {r} |"
    L += ["## Balance de la semana", "", "| | Semana | Recomendado |", "|---|---|---|",
          fila("Publicaciones de feed", b["publicaciones"], cfg.pub_semana)]
    for f, m in cfg.formato_min.items():
        n = b["reels"] if f == "reel" else b["carruseles"]
        L.append(fila(config.FORMATOS_PLURAL[f], n, f"≥ {m}" + ("" if n >= m else f" (faltan {m - n})")))
    for o, m in cfg.objetivo_min.items():
        L.append(fila(f"Objetivo {o}", obj.get(o, 0), f"≥ {m}"))
    for pl, m in cfg.pilar_max.items():
        L.append(fila(f"Pilar {pl}", pil.get(pl, 0), f"≤ {m}"))
    if cfg.formula_max:
        txt = ", ".join(f"{k} ×{v}" for k, v in sorted(b["formulas"].items())) or "—"
        L.append(fila("Fórmulas de carrusel", txt, f"≤ {cfg.formula_max} de cada"))
    L.append(fila("Historias", b["historias"], f"{cfg.hist_min}–{cfg.hist_max} al día"))
    L += ["", "Objetivos: " + (", ".join(f"{k} {v}" for k, v in sorted(obj.items())) or "—")
          + " · Pilares: " + (", ".join(f"{k} {v}" for k, v in sorted(pil.items())) or "—"), ""]
    if b["avisos"]:
        L += ["Avisos (recomendaciones):", ""] + [f"- {a}" for a in b["avisos"]] + [""]
    L += ["## Huecos", ""]
    if b["huecos"]:
        t = texto_faltan(b)
        L.append(f"- {t[:1].upper() + t[1:]}.")
        L.append("- Huecos libres: " + ", ".join(f"{dia_corto(d)} {hhmm(h)}" for d, h in b["huecos"]) + ".")
    else:
        L.append("- Sin huecos de feed.")
    if b["historias_faltan"]:
        L.append(f"- Historias: faltan {b['historias_faltan']} para llegar a {cfg.hist_min} al día"
                 + (f" (carpeta: `{carpeta_hist}`)." if carpeta_hist else "."))
    return "\n".join(L) + "\n"


def texto_hoy(proyecto, cfg: Conf, piezas: list[Pieza], fecha: dt.date, hoy: dt.date,
              hist_por_dia: dict[dt.date, list[str]], carpeta_hist: Path | None) -> str:
    from lib import txt as txtmod
    L = [f"{proyecto.nombre} · {config.NOMBRES_DIA[fecha.weekday()]} {fecha:%d/%m/%Y}", ""]
    del_dia = sorted((p for p in piezas if p.estado != "Descartado" and p.cuando == fecha), key=lambda p: p.momento)
    if not del_dia:
        L.append("Feed: hoy no toca post.")
        sig = sorted((p for p in piezas if p.estado == "Pendiente" and p.fecha and p.fecha > fecha),
                     key=lambda p: p.momento)
        if sig:
            p = sig[0]
            L.append(f"  Siguiente: {dia_corto(p.fecha)} {hhmm(p.hora)} · {p.fmt} · {p.id} {p.clip}")
        L.append("")
    for p in del_dia:
        L.append(f"FEED · {hhmm(p.hora) or '--:--'} · {p.fmt} · {p.id} · {p.clip}{_marca(p, hoy)}")
        L.append(f"  Objetivo: {p.objetivo or '—'} · Pilar: {p.pilar or '—'}"
                 + (f" · Oferta: {p.oferta_nombre}" if p.oferta_nombre else ""))
        L.append(f"  Ruta: {p.ruta}")
        ruta_txt = txtmod.ruta_txt(p.ruta, p.formato) if p.ruta else None
        if ruta_txt and ruta_txt.exists():
            L += [f"  Texto listo para pegar ({ruta_txt.name}):", "", ruta_txt.read_text(encoding="utf-8").rstrip(), ""]
        else:
            L += [f"  (no encuentro el .txt{': ' + str(ruta_txt) if ruta_txt else ''}; "
                  "copys.py sincronizar lo rehace)", ""]
    hs = hist_por_dia.get(fecha, [])
    L.append(f"HISTORIAS ({len(hs)})" + (f" · {carpeta_hist}" if carpeta_hist else ""))
    for h in hs:
        existe = bool(carpeta_hist) and (Path(carpeta_hist) / h).exists()
        L.append(f"  - {h}" + ("" if existe or not carpeta_hist else "  (ya no está en la carpeta)"))
    if not hs:
        L.append(f"  - ninguna asignada (recomendado {cfg.hist_min}–{cfg.hist_max}): copys.py calendario planificar")
    L.append(f"  - {recordatorio(piezas, fecha, cfg, hoy)}")
    atras = sorted((p for p in piezas if p.atrasada(hoy)), key=lambda p: p.momento)
    if atras:
        L += ["", f"ATRASADOS ({len(atras)}): previstos antes de hoy ({hoy:%d/%m}) y sin publicar"]
        L += [f"  - {dia_corto(p.fecha)} {hhmm(p.hora)} · {p.fmt} · {p.id} {p.clip}"
              + (" (fecha manual)" if p.manual else "") for p in atras]
    return "\n".join(L)

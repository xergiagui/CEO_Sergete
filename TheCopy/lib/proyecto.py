"""
Carga de un PROYECTO (cliente/marca) desde `proyectos/<id>/`.

La IDENTIDAD del proyecto (cuenta, landing, afiliado, voz: persona/tono/idioma/emojis,
palabras prohibidas, marca) NO está aquí: se lee del índice del CEO
(`CEO_Sergete/proyectos.json` → proyectos[].identidad), que es su fuente única.
Sin ella, error de configuración.

Lo propio de TheCopy, en la carpeta del proyecto:
  proyecto.json     reglas del copy, CTA, carpetas, plataformas, campos propios, calendario
  ofertas.json      productos/ofertas a los que puede apuntar un copy
  hashtags.json     fijos por plataforma + banco temático (por tamaño: nicho/medio/amplio)
  banco_copys.json  copys de referencia (tono) y de reserva
  fuentes/          documentos originales de los que salió todo lo anterior
  registro_<id>.xlsx  el registro clip ↔ copy ↔ hashtags (lo crea el script)
  calendario/       el plan semanal (lo crea `calendario planificar`)

Las rutas de proyecto.json son relativas a PruebasIA/ (o absolutas) y admiten `<id>`.
`_plantilla` no es un proyecto: no se lista ni se puede abrir.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import config
from lib.util import leer_json, escribir_json, normalizar, normalizar_hashtag

ARCHIVOS = ("proyecto.json", "ofertas.json", "hashtags.json", "banco_copys.json")

# Tamaño de un hashtag por nº de publicaciones (estimado: la API no lo da).
#   nicho < 50k · medio 50k–500k · amplio > 500k
TAMANOS = ("nicho", "medio", "amplio")
RE_TAG = re.compile(r"#[^\s#]+")


class ErrorProyecto(Exception):
    pass


def ruta(p: str, pid: str) -> Path:
    """Ruta de proyecto.json: `<id>` → id del proyecto; absoluta o relativa a PruebasIA/."""
    path = Path(str(p).replace("<id>", pid))
    return path if path.is_absolute() else (config.PRUEBAS_IA / path)


def dentro_de(ruta_hija: Path | str, carpeta: Path | str) -> bool:
    """True si `ruta_hija` es `carpeta` o está dentro (sin distinguir mayúsculas, como Windows)."""
    try:
        h, c = Path(ruta_hija).resolve(), Path(carpeta).resolve()
    except OSError:
        return False
    hs, cs = str(h).lower(), str(c).lower().rstrip("\\/")
    return hs == cs or hs.startswith(cs + "\\") or hs.startswith(cs + "/")


def _lleva_id(carpeta: Path, pid: str) -> bool:
    """True si el id del proyecto es una de las carpetas de la ruta (…/REELS/<id>/…)."""
    return pid.lower() in (x.lower() for x in Path(carpeta).parts)


def valida_id(pid: str) -> None:
    if not re.fullmatch(config.RE_ID_PROYECTO, pid or ""):
        raise ErrorProyecto(f"Id de proyecto '{pid}' no válido: minúsculas y sin espacios (ej. 'mi_marca').")
    if pid == config.PLANTILLA:
        raise ErrorProyecto(f"'{config.PLANTILLA}' es la plantilla, no un proyecto.")


class Proyecto:
    def __init__(self, pid: str, exigir_identidad: bool = True):
        self.dir = config.PROYECTOS_DIR / pid
        if pid == config.PLANTILLA or not (self.dir / "proyecto.json").exists():
            raise ErrorProyecto(
                f"No existe el proyecto '{pid}'. Disponibles: {', '.join(listar()) or '(ninguno)'}")
        faltan = [a for a in ARCHIVOS if not (self.dir / a).exists()]
        if faltan:
            raise ErrorProyecto(f"Al proyecto '{pid}' le faltan: {', '.join(faltan)}")

        self.conf = leer_json(self.dir / "proyecto.json")
        self.ofertas = leer_json(self.dir / "ofertas.json")
        self.hashtags = leer_json(self.dir / "hashtags.json")
        self.banco = leer_json(self.dir / "banco_copys.json")

        # El id es el de la carpeta: un proyecto.json copiado de otro no puede mezclar registros.
        if self.conf.get("id") not in (None, "", pid):
            raise ErrorProyecto(f"proyectos/{pid}/proyecto.json dice \"id\": \"{self.conf.get('id')}\": "
                                f"tiene que ser \"{pid}\" (el nombre de su carpeta).")
        self.id = pid
        self.nombre = self.conf.get("nombre") or pid
        self.prefijo_id = self.conf.get("prefijo_id") or pid.strip("_")[:2].upper()
        self.identidad = cargar_identidad(pid, exigir_identidad)
        self._tamanos, self._conflictos_tamano = self._indexar_tamanos()
        self._comprobar()

    # ---------- identidad (CEO_Sergete/proyectos.json → identidad) ----------
    @property
    def voz(self) -> dict:
        return self.identidad.get("voz") or {}

    @property
    def tono(self) -> str:
        return str(self.voz.get("tono") or "")

    @property
    def idioma(self) -> str:
        return str(self.voz.get("idioma") or "")

    @property
    def landing(self) -> str:
        return str(self.identidad.get("landing") or "")

    @property
    def afiliado(self) -> str:
        return str(self.identidad.get("afiliado") or "")

    @property
    def palabras_prohibidas(self) -> list[str]:
        return [str(x) for x in (self.identidad.get("palabras_prohibidas") or []) if str(x).strip()]

    # ---------- validación de la configuración ----------
    def _comprobar(self) -> None:
        errores = []
        if self.tipo and self.tipo not in config.TIPOS:
            errores.append(f"tipo '{self.tipo}' desconocido (usa {', '.join(config.TIPOS)}).")
        plats = self.conf.get("plataformas") or {}
        if not plats:
            errores.append("proyecto.json no define 'plataformas'.")
        if not self.plataformas_activas():
            errores.append("No hay ninguna plataforma con \"activa\": true.")
        for pid in self.plataformas_activas():
            for tag in self.fijos(pid):
                if not RE_TAG.fullmatch(tag):
                    errores.append(f"hashtags.json: fijo inválido en {pid}: '{tag}'")
        for campo in self.campos_extra():
            if "id" not in campo or "columna" not in campo:
                errores.append(f"campos_extra mal definido: {campo}")
        for pid in plats:
            for fmt in self.formatos(pid):
                if fmt not in config.FORMATOS:
                    errores.append(f"plataformas.{pid}.formatos: formato desconocido '{fmt}' "
                                   f"(usa {', '.join(config.FORMATOS)}).")
            errores += self._comprobar_cuotas(pid)
        errores += self._comprobar_calendario()
        errores += self._comprobar_tipos()
        for propia in self.carpetas_propias():
            for ajena, otro in carpetas_ajenas(self.id, internas=False).items():
                if dentro_de(propia, ajena) or dentro_de(ajena, propia):
                    if _lleva_id(propia, self.id) and not _lleva_id(ajena, otro):
                        continue  # la carpeta es de este proyecto: el mal configurado es el otro
                    errores.append(f"la carpeta {propia} coincide con una del proyecto '{otro}' ({ajena}): "
                                   "cada proyecto usa las suyas (pon <id> en la ruta).")
        # banco temático: formato antiguo (tema → lista) o nuevo (tema → {nicho/medio/amplio: lista})
        for tema, val in (self.hashtags.get("tematicos") or {}).items():
            if tema.startswith("_"):
                continue
            if isinstance(val, dict):
                raras = [k for k in val if k not in TAMANOS and not k.startswith("_")]
                if raras:
                    errores.append(f"hashtags.json: tema '{tema}' con tamaños desconocidos {raras} "
                                   f"(usa {', '.join(TAMANOS)}).")
            elif not isinstance(val, list):
                errores.append(f"hashtags.json: tema '{tema}' debe ser una lista o {{nicho/medio/amplio: lista}}.")
        for tema, tags in self.banco_tematico().items():
            malos = [t for t in tags if not RE_TAG.fullmatch(t) or t != t.lower()]
            if malos:
                errores.append(f"hashtags.json: etiquetas mal formadas en '{tema}': {' '.join(malos)}")
        for tag, tam in (self.hashtags.get("tamano_fijos") or {}).items():
            if tam not in TAMANOS:
                errores.append(f"hashtags.json: tamano_fijos['{tag}'] = '{tam}' (usa {', '.join(TAMANOS)}).")
        for tag, tams in self._conflictos_tamano.items():
            errores.append(f"hashtags.json: {tag} aparece con tamaños distintos ({', '.join(sorted(tams))}).")
        if errores:
            raise ErrorProyecto(f"Configuración de '{self.id}' incorrecta:\n  - " + "\n  - ".join(errores))

    # ---------- plataformas ----------
    def plataformas_activas(self) -> list[str]:
        return [p for p, c in (self.conf.get("plataformas") or {}).items() if c.get("activa")]

    def plataforma(self, pid: str) -> dict:
        try:
            return self.conf["plataformas"][pid]
        except KeyError:
            raise ErrorProyecto(f"La plataforma '{pid}' no está definida en {self.id}/proyecto.json")

    def nombre_plataforma(self, pid: str) -> str:
        return self.plataforma(pid).get("nombre") or pid.capitalize()

    # ---------- formatos (Reel / carrusel) ----------
    def formatos(self, pid: str) -> dict[str, dict]:
        """{formato: conf propia} que admite la plataforma. Sin `formatos` → solo Reel."""
        f = self.plataforma(pid).get("formatos")
        return {k: (v or {}) for k, v in f.items() if not k.startswith("_")} if isinstance(f, dict) else {"reel": {}}

    def admite(self, pid: str, formato: str) -> bool:
        return formato in self.formatos(pid)

    def conf_formato(self, pid: str, formato: str = "reel") -> dict:
        """Configuración efectiva: identidad (emojis_max de la voz) < plataforma < formato.

        `emojis_max` sale de identidad.voz.emojis_max salvo que la plataforma o el formato lo
        sobrescriban; lo propio del formato (guia, copy_recomendado…) va encima de la plataforma.
        """
        base = {}
        if self.voz.get("emojis_max") is not None:
            base["emojis_max"] = self.voz["emojis_max"]
        base.update({k: v for k, v in self.plataforma(pid).items() if k != "formatos"})
        return {**base, **{k: v for k, v in self.formatos(pid).get(formato, {}).items() if not k.startswith("_")}}

    def reglas_hashtags(self, pid: str) -> dict:
        """plataformas.<p>.hashtags: FUENTE ÚNICA de las cifras de hashtags."""
        return dict(self.plataforma(pid).get("hashtags") or {})

    def texto_reglas_hashtags(self, pid: str) -> str:
        """Las cifras de hashtags tal y como las comprueba lib/tanda.py."""
        r = self.reglas_hashtags(pid)
        partes = []
        if "tematicos_min" in r or "tematicos_max" in r:
            partes.append(f"temáticos {r.get('tematicos_min', 0)}–{r.get('tematicos_max', '…')} (error)")
        tmax = r.get("total_max") or r.get("max_total")
        if r.get("total_min") or tmax:
            partes.append(f"total {r.get('total_min', 0)}–{tmax or '…'} con los fijos (error)")
        if "nicho_min" in r:
            partes.append(f"≥ {r['nicho_min']} de nicho contando los fijos (aviso)")
        if "amplios_max" in r:
            partes.append(f"≤ {r['amplios_max']} amplio (error)")
        n = int(r.get("rotacion_ultimos", config.ROTACION_ULTIMOS) or 0)
        if n:
            partes.append(f"rotar: conjunto distinto de los {n} últimos y del resto de la tanda (aviso)")
        return " · ".join(partes) or "sin reglas"

    def _comprobar_cuotas(self, pid: str) -> list[str]:
        """Las cuotas de hashtags tienen que poder cumplirse con los fijos de la plataforma."""
        r = self.reglas_hashtags(pid)
        nf = len(self.fijos(pid))
        tmin, tmax = r.get("tematicos_min", 0), r.get("tematicos_max")
        total_min, total_max = r.get("total_min"), r.get("total_max") or r.get("max_total")
        err = []
        if tmax is not None and tmin > tmax:
            err.append(f"plataformas.{pid}.hashtags: tematicos_min ({tmin}) > tematicos_max ({tmax}).")
        if total_min and tmax is not None and tmax + nf < total_min:
            err.append(f"plataformas.{pid}.hashtags: con {nf} fijo(s) y como mucho {tmax} temáticos no se llega "
                       f"a total_min {total_min}.")
        if total_max and tmin + nf > total_max:
            err.append(f"plataformas.{pid}.hashtags: con {nf} fijo(s) y al menos {tmin} temáticos se pasa "
                       f"de total_max {total_max}.")
        return err

    # ---------- hashtags ----------
    def fijos(self, pid: str) -> list[str]:
        return [normalizar_hashtag(t) for t in (self.hashtags.get("fijos") or {}).get(pid, [])]

    # ---------- tipos de clip (opcional, por proyecto): caption y hashtags fijos por tipo ----------
    # proyecto.json → "tipos_clip": {"patron": "^([a-e])_", "tipos": {"a": {"caption": "...",
    # "hashtags": ["#A", "#B"]}}}. El tipo sale del nombre del clip (grupo 1 del patrón, en
    # minúsculas). Sin "tipos_clip" no cambia nada (p. ej. mongemalo).
    @property
    def tipos_clip(self) -> dict:
        return self.conf.get("tipos_clip") or {}

    def tipo_de_clip(self, nombre: str) -> str | None:
        """Letra/id de tipo del clip según tipos_clip.patron (None si no encaja o no hay tipos)."""
        patron = self.tipos_clip.get("patron")
        if not patron:
            return None
        m = re.match(patron, Path(str(nombre)).name, re.IGNORECASE)
        t = (m.group(1) if m and m.groups() else "").lower()
        return t if t in self.tipos_clip.get("tipos", {}) else None

    def hashtags_de_tipo(self, tipo: str) -> list[str]:
        """Hashtags del tipo, tal y como se escriben (con sus mayúsculas), en su orden."""
        return [t if t.startswith("#") else "#" + t for t in self.tipos_clip["tipos"][tipo].get("hashtags", [])]

    def literal_hashtag(self, tag: str) -> str:
        """Hashtag con las mayúsculas de tipos_clip/fijos (internamente todo va en minúsculas)."""
        mapa = getattr(self, "_literales", None)
        if mapa is None:
            mapa = {}
            for t in self.tipos_clip.get("tipos", {}):
                for h in self.hashtags_de_tipo(t):
                    mapa.setdefault(normalizar_hashtag(h), h)
            self._literales = mapa
        return mapa.get(normalizar_hashtag(tag), tag)

    def banco_por_tamano(self) -> dict[str, dict[str, list[str]]]:
        """tema → {nicho: [...], medio: [...], amplio: [...], sin_tamano: [...]}.

        Acepta los dos formatos de `tematicos` en hashtags.json:
          antiguo: "tema": ["#a", "#b"]                      (todo queda en sin_tamano)
          nuevo:   "tema": {"nicho": [...], "medio": [...], "amplio": [...]}
        """
        out: dict[str, dict[str, list[str]]] = {}
        for tema, val in (self.hashtags.get("tematicos") or {}).items():
            if tema.startswith("_"):
                continue
            grupos = {k: [] for k in (*TAMANOS, "sin_tamano")}
            if isinstance(val, dict):
                for tam in TAMANOS:
                    grupos[tam] = [normalizar_hashtag(t) for t in val.get(tam) or []]
            elif isinstance(val, list):
                grupos["sin_tamano"] = [normalizar_hashtag(t) for t in val]
            out[tema] = grupos
        return out

    def banco_tematico(self) -> dict[str, list[str]]:
        """tema → etiquetas (sin distinguir tamaño), en los dos formatos."""
        return {tema: [t for k in (*TAMANOS, "sin_tamano") for t in g[k]]
                for tema, g in self.banco_por_tamano().items()}

    def pool_tematico(self) -> set[str]:
        return {t for tags in self.banco_tematico().values() for t in tags}

    def _indexar_tamanos(self) -> tuple[dict[str, str], dict[str, set[str]]]:
        """{etiqueta: tamaño} del banco (formato nuevo) + `tamano_fijos`; y los conflictos."""
        mapa: dict[str, str] = {}
        vistos: dict[str, set[str]] = {}
        for g in self.banco_por_tamano().values():
            for tam in TAMANOS:
                for t in g[tam]:
                    vistos.setdefault(t, set()).add(tam)
        for t, tam in (self.hashtags.get("tamano_fijos") or {}).items():
            vistos.setdefault(normalizar_hashtag(t), set()).add(tam)
        conflictos = {t: s for t, s in vistos.items() if len(s) > 1}
        for t, s in vistos.items():
            if len(s) == 1:
                mapa[t] = next(iter(s))
        return mapa, conflictos

    def tamano_hashtag(self, tag: str) -> str | None:
        """'nicho' | 'medio' | 'amplio' (ESTIMADO, según hashtags.json) o None si no se conoce."""
        return self._tamanos.get(normalizar_hashtag(tag))

    # ---------- campos propios del proyecto (p. ej. Oferta) ----------
    def campos_extra(self) -> list[dict]:
        return self.conf.get("campos_extra") or []

    def campo(self, cid: str) -> dict | None:
        return next((c for c in self.campos_extra() if c.get("id") == cid), None)

    def canon_valor(self, campo: dict, valor) -> str | None:
        """Valor canónico de un campo con lista de valores ('Interacción ' → 'interaccion').

        Acepta el id o el nombre visible, sin importar mayúsculas ni tildes. None si no encaja.
        """
        vals = self.valores_campo(campo)
        if vals is None:
            return str(valor).strip() if valor not in (None, "") else None
        n = normalizar(str(valor or ""))
        for k, nombre in vals.items():
            if n and n in (normalizar(k), normalizar(nombre)):
                return k
        return None

    def valores_campo(self, campo: dict) -> dict[str, str] | None:
        """{valor_id: nombre_legible} o None si el campo es texto libre."""
        if campo.get("valores") == "ofertas":
            vals = {o["id"]: o["nombre"] for o in self.ofertas.get("ofertas", [])}
            gen = self.ofertas.get("generico")
            if gen:
                vals[gen.get("id", "generico")] = gen.get("nombre", "Genérico")
            return vals
        if isinstance(campo.get("valores"), list):
            return {v: v for v in campo["valores"]}
        return None

    # ---------- tipo / carpetas / registro ----------
    @property
    def tipo(self) -> str | None:
        """'largos' | 'clipping' (config.TIPOS) o None si proyecto.json no lo dice."""
        return self.conf.get("tipo") or None

    def _carpeta(self, clave: str) -> Path | None:
        carpetas = self.conf.get("carpetas") or {}
        p = carpetas[clave] if clave in carpetas else config.CARPETAS_POR_DEFECTO.get(clave)
        return ruta(p, self.id) if p else None

    @property
    def carpeta_pendiente(self) -> Path | None:
        return self._carpeta("pendiente")

    @property
    def carpeta_publicado(self) -> Path | None:
        return self._carpeta("publicado")

    def carpetas_contexto(self) -> list[Path]:
        """Carpetas donde buscar cortes.json/.srt o textos/ de los clips (proyecto.json → carpetas.contexto)."""
        propias = (self.conf.get("carpetas") or {}).get("contexto")
        if propias is None:
            propias = config.CONTEXTO_POR_DEFECTO
        return [ruta(p, self.id) for p in propias]

    def carpetas_propias(self) -> list[Path]:
        """Carpetas de piezas del proyecto (pendiente, publicado, historias)."""
        return [c for c in (self.carpeta_pendiente, self.carpeta_publicado, self.carpeta_historias) if c]

    @property
    def registro_path(self) -> Path:
        return self.dir / (self.conf.get("registro") or f"registro_{self.id}.xlsx")

    # ---------- calendario de publicación ----------
    @property
    def calendario(self) -> dict:
        return self.conf.get("calendario") or {}

    @property
    def calendario_activo(self) -> bool:
        return bool(self.calendario.get("activo"))

    @property
    def carpeta_historias(self) -> Path | None:
        hist = self.calendario.get("historias") or {}
        p = hist["carpeta"] if "carpeta" in hist else config.CARPETAS_POR_DEFECTO["historias"]
        return ruta(p, self.id) if p else None

    # ---------- lo que sigue igual que en la plantilla (sin rellenar) ----------
    def sin_rellenar(self) -> list[str]:
        """Qué conserva aún los valores de la plantilla (para avisar tras `nuevo-proyecto`)."""
        try:
            pl = {a: leer_json(config.PLANTILLA_DIR / a) for a in ARCHIVOS}
        except Exception:
            return []
        pc, falta = pl["proyecto.json"], []
        if not self.identidad:
            falta.append(f"identidad (voz, tono, emojis, landing, palabras prohibidas) en "
                         f"{config.INDICE_PROYECTOS} → proyectos[{self.id}].identidad: la añade el CEO")
        for clave, que in (("descripcion", "descripcion (qué es el proyecto)"),
                           ("como_reconocerlo", "como_reconocerlo (pistas para saber que un clip es suyo)"),
                           ("reglas_copy", "reglas_copy (siguen las genéricas: revísalas)")):
            if self.conf.get(clave) == pc.get(clave):
                falta.append(que)
        if not self.tipo:
            falta.append(f"tipo ({' / '.join(config.TIPOS)})")
        if self.ofertas.get("ofertas") == pl["ofertas.json"].get("ofertas"):
            falta.append("ofertas.json (ofertas y cuándo usar cada una; vacío si no vende nada)")
        if self.ofertas.get("generico") == pl["ofertas.json"].get("generico"):
            falta.append("ofertas.json → generico.cta (CTA genérico)")
        h, ph = self.hashtags, pl["hashtags.json"]
        if h.get("fijos") == ph.get("fijos"):
            falta.append("hashtags.json → fijos por plataforma")
        if h.get("tematicos") == ph.get("tematicos"):
            falta.append("hashtags.json → banco temático por tamaño (nicho/medio/amplio)")
        plats, pplats = self.conf.get("plataformas") or {}, pc.get("plataformas") or {}
        for pid in self.plataformas_activas():
            if plats.get(pid) == pplats.get(pid):
                falta.append(f"plataformas.{pid}: CTA (cta_patrones, cta_ejemplo), nº de hashtags y guía "
                             "(siguen los de la plantilla)")
        if not self.calendario_activo:
            falta.append("calendario (desactivado: días, franjas y nº de posts cuando Sergio los dé)")
        if self.banco == pl["banco_copys.json"]:
            falta.append("banco_copys.json (opcional: copys de referencia de tono)")
        return falta

    def _comprobar_tipos(self) -> list[str]:
        tc = self.tipos_clip
        if not tc:
            return []
        err = []
        try:
            re.compile(tc.get("patron") or "")
        except re.error as e:
            err.append(f"tipos_clip.patron no es una expresión regular válida ({e}).")
        if not tc.get("patron") or not tc.get("tipos"):
            err.append("tipos_clip necesita 'patron' (con un grupo) y 'tipos'.")
        for t, d in (tc.get("tipos") or {}).items():
            if t != t.lower():
                err.append(f"tipos_clip.tipos: el id '{t}' va en minúsculas.")
            if not (d.get("caption") or "").strip() or not d.get("hashtags"):
                err.append(f"tipos_clip.tipos.{t}: faltan 'caption' o 'hashtags'.")
        return err

    def _comprobar_calendario(self) -> list[str]:
        cal = self.calendario
        if not cal:
            return []
        err = []
        dias = cal.get("dias") or []
        malos = [d for d in dias if d not in config.DIAS]
        if malos:
            err.append(f"calendario.dias: {malos} no valen (usa {', '.join(config.DIAS)}).")
        for k in ("inicio", "fin"):
            if cal.get(k) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cal[k])):
                err.append(f"calendario.{k} = '{cal[k]}' (formato AAAA-MM-DD).")
        franjas = cal.get("franjas") or {}
        for d, h in franjas.items():
            if d.startswith("_"):
                continue
            if d not in config.DIAS:
                err.append(f"calendario.franjas: día '{d}' desconocido.")
            if not re.fullmatch(r"\d{1,2}:\d{2}", str(h)):
                err.append(f"calendario.franjas.{d} = '{h}' (formato HH:MM).")
        if cal.get("segunda_franja") and not re.fullmatch(r"\d{1,2}:\d{2}", str(cal["segunda_franja"])):
            err.append(f"calendario.segunda_franja = '{cal['segunda_franja']}' (formato HH:MM).")
        for d in dias:
            if d in config.DIAS and d not in franjas and not cal.get("segunda_franja"):
                err.append(f"calendario: el día '{d}' no tiene franja (calendario.franjas).")
        bal = cal.get("balance") or {}
        for fmt in (bal.get("formato_min") or {}):
            if fmt not in config.FORMATOS:
                err.append(f"calendario.balance.formato_min: formato '{fmt}' desconocido.")
        for clave, cid in (("objetivo_min", "objetivo"), ("pilar_max", "pilar")):
            campo = self.campo(cid)
            vals = self.valores_campo(campo) if campo else None
            for k in (bal.get(clave) or {}):
                if vals is not None and k not in vals:
                    err.append(f"calendario.balance.{clave}: '{k}' no es un valor de '{cid}' ({', '.join(vals)}).")
        return err


def listar() -> list[str]:
    """Ids de los proyectos (carpetas con proyecto.json), sin contar la plantilla."""
    if not config.PROYECTOS_DIR.exists():
        return []
    return sorted(d.name for d in config.PROYECTOS_DIR.iterdir()
                  if d.is_dir() and d.name != config.PLANTILLA and (d / "proyecto.json").exists())


def elegir(pid: str | None) -> "Proyecto":
    """Regla común de todos los departamentos: `--proyecto <id>`; sin él, el único que haya.

    Con varios proyectos y sin `--proyecto`, error con la lista (nunca se elige uno al azar).
    """
    if pid:
        return Proyecto(pid)
    disponibles = listar()
    if not disponibles:
        raise ErrorProyecto("No hay ningún proyecto. Crea uno con: copys.py nuevo-proyecto <id>")
    if len(disponibles) > 1:
        raise ErrorProyecto(f"Hay {len(disponibles)} proyectos ({', '.join(disponibles)}): "
                            "indica cuál con --proyecto <id>.")
    return Proyecto(disponibles[0])


def carpetas_ajenas(pid: str, internas: bool = True) -> dict[Path, str]:
    """{carpeta: id} de las carpetas de los OTROS proyectos (para no mezclar nunca): las de
    piezas (pendiente, publicado, historias) y, con `internas`, su carpeta de TheCopy
    (registro, calendario) y sus tandas. Se lee proyecto.json en crudo: un proyecto a medio
    configurar también cuenta.
    """
    out: dict[Path, str] = {}
    for otro in listar():
        if otro == pid:
            continue
        try:
            conf = leer_json(config.PROYECTOS_DIR / otro / "proyecto.json")
        except Exception:
            continue
        carpetas = conf.get("carpetas") or {}
        hist = (conf.get("calendario") or {}).get("historias") or {}
        for clave in ("pendiente", "publicado"):
            p = carpetas[clave] if clave in carpetas else config.CARPETAS_POR_DEFECTO[clave]
            if p:
                out[ruta(p, otro)] = otro
        p = hist["carpeta"] if "carpeta" in hist else config.CARPETAS_POR_DEFECTO["historias"]
        if p:
            out[ruta(p, otro)] = otro
        if internas:
            out[config.PROYECTOS_DIR / otro] = otro  # su registro y su calendario
            out[config.TANDAS_DIR / otro] = otro
    return out


def de_otro_proyecto(pid: str, ruta_x: Path | str | None) -> str | None:
    """Id del otro proyecto al que pertenece `ruta_x` (o None si no es de ninguno)."""
    if not ruta_x:
        return None
    for carpeta, otro in carpetas_ajenas(pid).items():
        if dentro_de(ruta_x, carpeta):
            return otro
    return None


def cargar_identidad(pid: str, exigir: bool = True) -> dict:
    """identidad del proyecto en el índice del CEO (fuente única). Sin ella, ErrorProyecto si `exigir`."""
    motivo = ""
    try:
        data = leer_json(config.INDICE_PROYECTOS)
    except FileNotFoundError:
        data, motivo = {}, f"no existe {config.INDICE_PROYECTOS}"
    except Exception as e:
        data, motivo = {}, f"no se puede leer {config.INDICE_PROYECTOS} ({e})"
    entrada = next((x for x in (data.get("proyectos") or []) if isinstance(x, dict) and x.get("id") == pid), None)
    ident = (entrada or {}).get("identidad")
    if not motivo and entrada is None:
        motivo = f"'{pid}' no está en {config.INDICE_PROYECTOS.name}"
    elif not motivo and not isinstance(ident, dict):
        motivo = f"'{pid}' no tiene bloque «identidad» en {config.INDICE_PROYECTOS.name}"
    if not motivo:
        errores = []
        voz = ident.get("voz")
        if not isinstance(voz, dict) or not voz.get("tono"):
            errores.append("identidad.voz.tono")
        elif voz.get("emojis_max") is not None and not isinstance(voz["emojis_max"], int):
            errores.append("identidad.voz.emojis_max (número entero)")
        if not isinstance(ident.get("palabras_prohibidas", []), list):
            errores.append("identidad.palabras_prohibidas (lista)")
        if errores:
            motivo = f"identidad de '{pid}' incompleta o mal formada: {', '.join(errores)}"
    if motivo:
        if exigir:
            raise ErrorProyecto(f"Configuración: {motivo}. La identidad (cuenta, landing, voz, tono, emojis, "
                                "palabras prohibidas) se lee de CEO_Sergete/proyectos.json → proyectos[].identidad "
                                "y la mantiene el CEO.")
        return {}
    return ident


def indice_ceo() -> dict[str, dict]:
    """{id: entrada} del índice común de proyectos del CEO (solo lectura; {} si no está)."""
    try:
        data = leer_json(config.INDICE_PROYECTOS)
    except Exception:
        return {}
    return {str(p.get("id")): p for p in (data.get("proyectos") or []) if isinstance(p, dict) and p.get("id")}


def crear(pid: str, nombre: str | None = None, prefijo: str | None = None,
          tipo: str | None = None) -> tuple[Path, dict]:
    """Da de alta un proyecto nuevo copiando la plantilla (solo dentro de TheCopy).

    Lo que no se pase se toma del índice del CEO (proyectos.json) si el id está allí.
    Devuelve (carpeta, entrada del índice o {}).
    """
    valida_id(pid)
    destino = config.PROYECTOS_DIR / pid
    if destino.exists():
        raise ErrorProyecto(f"Ya existe el proyecto '{pid}' ({destino}).")
    ceo = indice_ceo().get(pid) or {}
    nombre = nombre or ceo.get("nombre")
    if not nombre:
        raise ErrorProyecto(f"'{pid}' no está en el índice del CEO ({config.INDICE_PROYECTOS.name}): "
                            "indica --nombre \"Nombre\".")
    tipo = tipo or ceo.get("tipo")
    if tipo and tipo not in config.TIPOS:
        raise ErrorProyecto(f"tipo '{tipo}' desconocido (usa {', '.join(config.TIPOS)}).")
    prefijo = (prefijo or ceo.get("prefijo_id") or re.sub(r"[^A-Z]", "", nombre.upper())[:3]
               or pid.strip("_")[:2]).upper()

    shutil.copytree(config.PLANTILLA_DIR, destino, ignore=shutil.ignore_patterns("calendario", "registro_*.xlsx"))
    conf_path = destino / "proyecto.json"
    conf = leer_json(conf_path)
    nuevo = {"id": pid, "nombre": nombre}
    for k, v in conf.items():  # mismo orden de claves que la plantilla
        if k not in nuevo:
            nuevo[k] = v
    nuevo["prefijo_id"] = prefijo
    nuevo["registro"] = f"registro_{pid}.xlsx"
    if tipo:
        nuevo["tipo"] = tipo
    if ceo.get("descripcion"):
        nuevo["descripcion"] = ceo["descripcion"]
    escribir_json(conf_path, nuevo)
    return destino, ceo


def prefijos_usados(excepto: str | None = None) -> dict[str, str]:
    """{prefijo_id: id} de los proyectos existentes (para no repetir prefijo)."""
    out = {}
    for pid in listar():
        if pid == excepto:
            continue
        try:
            pref = leer_json(config.PROYECTOS_DIR / pid / "proyecto.json").get("prefijo_id")
        except Exception:
            continue
        if pref:
            out[str(pref).upper()] = pid
    return out

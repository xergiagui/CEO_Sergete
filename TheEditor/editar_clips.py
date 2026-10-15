#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 4 — Edicion final con la skill Editor_Sergio (solo Fase C).

GENERICO: funciona con cualquier video. La imagen-gancho de cada clip se toma
del `hook_query` del cortes.json (el mismo que uso clips.py); si un clip no lo
trae, se deriva del nombre. Asi el flujo es 100% automatico sin tocar codigo.

Trabaja por PROYECTO (`--proyecto <id>`, ver proyecto.py) y SOLO con los
recursos que permite su `proyecto.json → recursos`.

Por cada clip de proyectos/<id>/transcripciones/<video>/clips/ aplica:
  gancho visual (mini-video de Pexels / imagen libre; solo si el proyecto tiene
  gancho_visual=pexels e internet) + gancho de TEXTO en la franja superior los
  primeros ~2,5 s (`gancho_texto` del cortes.json; si falta, el clip sale SIN
  gancho y se avisa: nunca se usa el `titulo` ni otro texto mecánico) +
  b-roll (banco común superposiciones/ o el propio del proyecto) + música (banco
  común musicas/ o la propia) + de-click + subtitulos palabra a palabra (una sola
  vez, enmascarando palabrotas).
  Antes de todo eso, si el proyecto lo pide (`proyecto.json → subs_fuente`), se
  tapan los rótulos/subtítulos que la FUENTE trae incrustados en la franja
  inferior, solo mientras están en pantalla (ver subs_fuente.py;
  `--sin-tapar-subs` lo desactiva en una ejecución).

Reproducible: la música y el b-roll al azar salen de una semilla con el nombre
del clip, así que re-renderizar un clip (--solo) da lo mismo y no cambia los
demás. Los word-timestamps de cada clip se guardan en clips/<nombre>.words.json
y se reutilizan en los re-renders (clips.py los borra si vuelve a cortar el clip).

Trabaja en una carpeta ASCII ÚNICA por proceso (whisper/_edit_XXXX via mkdtemp)
para evitar problemas de rutas con tildes en el filtro de subtitulos de ffmpeg y
para no pisar ediciones en paralelo. Salida en
proyectos/<id>/transcripciones/<video>/finales/.

Uso:
    python editar_clips.py --proyecto mongemalo "Mi Adicción"
    python editar_clips.py --proyecto mongemalo "video" --cortes cortes.json
    python editar_clips.py --proyecto x "video" --sin-gancho-texto   # sin texto de gancho
    python editar_clips.py --proyecto x "video" --sin-frases         # no guarda en viral_phrases
    python editar_clips.py --proyecto x "video" --solo 03_nombre --sin-frases   # corregir un clip
    python editar_clips.py --proyecto x "video" --sin-musica / --sin-broll   # sin ese recurso
Si solo hay un proyecto, --proyecto se puede omitir.

Solo se renderizan los clips de cortes.json, y antes se VALIDA (validar.py): si
hay errores en los clips a renderizar, para. Con --quiet (por defecto si la
salida no es una terminal) la consola recibe una línea por clip y el RESUMEN.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# La consola de Windows (cp1252) no puede imprimir '→' y otros chars que usa
# pipeline_core -> UnicodeEncodeError que aborta cada clip. Forzamos UTF-8 en la
# salida para que el flujo sea robusto al invocarse desde bash/venv (subagente).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / ".claude" / "skills" / "Editor_Sergio"))
import pipeline_core as pc  # noqa: E402
import herramientas  # noqa: E402
import proyecto  # noqa: E402
import subs_fuente  # noqa: E402
import validar  # noqa: E402

# Raíz ASCII bajo la que se crea el work dir ÚNICO por ejecución (ver main()).
# whisper-cli/ffmpeg abren rutas ANSI, así que el intermedio va bajo whisper/
# con nombre ASCII garantizado.
WORKBASE = RAIZ / "whisper"


EXT_VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".mts"}


def resolver_nombre(arg: str) -> str:
    """Nombre del video (para ubicar transcripciones/<nombre>/)."""
    p = Path(arg)
    return p.stem if p.suffix.lower() in EXT_VIDEO else p.name


def guardar_frases_virales(nombre: str, cortes_path: Path,
                           source_url: str = None, env: dict = None,
                           proyecto_obj=None) -> dict:
    """Lee cortes.json y guarda las frases virales en Supabase (best-effort).

    Por cada corte usa `frase_viral` (texto verbatim); si falta, el `titulo`
    (nunca el `hook_query`, que es una búsqueda de Pexels). Pasa también angle/virality/category/
    rationale/tags si el corte los trae. avatar_name = slug del video (nombre).
    Con `proyecto_obj`, cada frase lleva la etiqueta `proyecto:<id>`.
    Nunca lanza: si no hay env/Supabase o falla la red, avisa y continua. El
    dedup por phrase_hash en store_viral_phrases evita duplicados al re-ejecutar.
    """
    if env is None:
        env = pc.cargar_env()
    if not (env.get("SUPABASE_URL") and env.get("SUPABASE_ANON_KEY")):
        print("   [frases] sin credenciales Supabase -> no se guardan (best-effort).", flush=True)
        return {"ok": False, "reason": "sin Supabase"}
    if not cortes_path.exists():
        print(f"   [frases] no hay {cortes_path.name}; nada que guardar.", flush=True)
        return {"ok": False, "reason": "sin cortes.json"}
    try:
        cortes = json.loads(cortes_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"   [frases] no pude leer cortes.json ({e}); se omite.", flush=True)
        return {"ok": False, "reason": str(e)}

    phrases = []
    for c in (cortes or []):
        texto = (c.get("frase_viral") or c.get("titulo") or "").strip()
        if not texto:
            continue
        phrases.append({
            "phrase": texto,
            "category": c.get("category"),
            "angle": c.get("angle"),
            "virality": c.get("virality"),
            "rationale": c.get("rationale"),
            "tags": (proyecto_obj.etiquetas_frases(c.get("tags")) if proyecto_obj
                     else (c.get("tags") or [])),
        })
    if not phrases:
        print("   [frases] ningun corte trae frase_viral/titulo; nada que guardar.", flush=True)
        return {"ok": False, "reason": "sin frases"}

    try:
        res = pc.store_viral_phrases(env, phrases, source_url=source_url,
                                     lang=(proyecto_obj.idioma if proyecto_obj else "es"),
                                     avatar=nombre,
                                     proyecto=(proyecto_obj.id if proyecto_obj else None))
    except Exception as e:  # blindaje extra: jamas rompe el pipeline
        print(f"   [frases] guardado fallo (ignorado): {e}", flush=True)
        return {"ok": False, "reason": str(e)}

    if res.get("ok"):
        print(f"   [frases] {res['stored']} frases virales guardadas en Supabase "
              f"(avatar={nombre}).", flush=True)
    else:
        print(f"   [frases] no guardado (best-effort): {res.get('reason')}", flush=True)
    return res


def cargar_hooks(cortes_path: Path) -> dict:
    """Mapa nombre_clip -> hook_query desde cortes.json (si existe)."""
    hooks = {}
    if cortes_path.exists():
        try:
            for c in json.loads(cortes_path.read_text(encoding="utf-8")):
                if c.get("hook_query"):
                    hooks[c["nombre"]] = c["hook_query"]
        except Exception:
            pass
    return hooks


def cargar_cortes_meta(cortes_path: Path) -> dict:
    """Mapa nombre_clip -> corte (dict completo) desde cortes.json.

    Sirve para derivar por clip la `tipologia_musica` (mood explícito) y el
    texto del clip (`frase_viral`/`titulo`) con el que inferir el mood cuando no
    hay anotación. Devuelve {} si no hay cortes.json."""
    meta = {}
    if cortes_path.exists():
        try:
            for c in json.loads(cortes_path.read_text(encoding="utf-8")):
                if c.get("nombre"):
                    meta[c["nombre"]] = c
        except Exception:
            pass
    return meta


def cargar_o_transcribir_words(clip: Path, ascii_in: Path, lang: str) -> list:
    """Word-timestamps del clip: los de clips/<nombre>.words.json si existen y no
    son más viejos que el clip; si no, Whisper sobre la copia ASCII y se guardan
    (así corregir el gancho o la música no repite la transcripción)."""
    wj = clip.with_suffix(".words.json")
    if wj.exists() and wj.stat().st_mtime >= clip.stat().st_mtime:
        try:
            words = json.loads(wj.read_text(encoding="utf-8")).get("words")
            if isinstance(words, list) and words:
                print(f"   [words] reutilizo {wj.name}", flush=True)
                return words
        except Exception:
            pass
    words = pc.transcribe_words(ascii_in, lang=lang)
    try:
        wj.write_text(json.dumps({"words": words}, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"   [words] no pude guardar {wj.name} ({e})", flush=True)
    return words


def linea_clip(name: str, info: dict, visual: bool) -> str:
    """Línea corta por clip para el LLM (lo demás va al log)."""
    mus = info.get("musica")
    mus = re.sub(r"^\s*\d+\s*[.\-)]?\s*", "", mus) if mus else "no"
    out = (f"OK {name}.mp4 · {info.get('duracion', 0):.0f} s · "
           f"gancho {'sí' if info.get('gancho_texto') else 'no'} · "
           f"b-roll {info.get('broll', 0)} ({info.get('broll_sem', 0)} sem) · música {mus}")
    if visual:
        out += f" · visual {info.get('gancho_visual') or 'no'}"
    if info.get("subs_fuente") is not None:
        out += f" · subs fuente tapados {info['subs_fuente']}"
    return out


def main():
    ap = argparse.ArgumentParser(description="Edicion final (Fase C) de los clips de un video.")
    ap.add_argument("video", help="Nombre del video (o ruta) cuyos clips se editan.")
    proyecto.add_argumento(ap)
    proyecto.add_salida(ap)
    ap.add_argument("--cortes", help="Ruta al cortes.json (por defecto "
                                     "proyectos/<id>/transcripciones/<video>/cortes.json).")
    ap.add_argument("--work-dir", help="Work dir ASCII para intermedios (por defecto uno único por proceso bajo whisper/). "
                                       "Si se suministra, NO se borra al terminar.")
    ap.add_argument("--sin-gancho-texto", action="store_true",
                    help="No quema el texto de gancho (gancho_texto) al inicio.")
    ap.add_argument("--sin-frases", action="store_true",
                    help="No guarda las frases en viral_phrases (pruebas o re-render de correcciones).")
    ap.add_argument("--sin-musica", action="store_true",
                    help="Sin música en esta ejecución (p. ej. un proyecto propio aún sin música).")
    ap.add_argument("--sin-broll", action="store_true",
                    help="Sin b-roll en esta ejecución.")
    ap.add_argument("--sin-tapar-subs", action="store_true",
                    help="No tapa los subtítulos incrustados de la fuente aunque el proyecto lo pida "
                         "(proyecto.json → subs_fuente).")
    ap.add_argument("--solo", action="append", metavar="NOMBRE",
                    help="Solo este clip (repetible o separado por comas): corrige uno sin tocar los demás.")
    args = ap.parse_args()
    p = proyecto.abrir(args.proyecto, "editar_clips", quiet=args.quiet)
    proyecto.decir(p.comprobar_recursos(args.sin_broll, args.sin_musica))
    MUSIC = None if args.sin_musica else p.music_dir
    OVERLAYS = None if args.sin_broll else p.overlays_dir
    # None = lo de siempre (banco común + internet)
    recursos = p.politica_render(sin_broll=args.sin_broll, sin_musica=args.sin_musica)
    sin_gancho_texto = args.sin_gancho_texto or not p.gancho_texto
    sin_frases = args.sin_frases or not p.guardar_frases
    # Subtítulos incrustados en la fuente: config del proyecto (None = no se tapan).
    try:
        tapar_cfg = None if args.sin_tapar_subs else subs_fuente.config(p.cfg)
    except ValueError as e:
        raise SystemExit(f"[!] {e}")
    if tapar_cfg:
        print(f"   [subs fuente] se tapan: {subs_fuente.describir(tapar_cfg)}", flush=True)

    nombre = resolver_nombre(args.video)
    base = p.transcripciones_dir / nombre
    clips_dir = base / "clips"
    out = base / "finales"
    cortes_path = Path(args.cortes) if args.cortes else (base / "cortes.json")
    if not cortes_path.exists():
        raise SystemExit(f"[!] Falta {cortes_path}: solo se renderizan los clips de cortes.json.")
    try:
        cortes_lista = json.loads(cortes_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"[!] {cortes_path} no es un JSON válido: {e}")
    hooks = cargar_hooks(cortes_path)
    cortes_meta = cargar_cortes_meta(cortes_path)

    if not clips_dir.exists():
        raise SystemExit(f"[!] No hay clips en {clips_dir}. Ejecuta antes clips.py.")

    env = pc.cargar_env()        # Pexels (gancho visual) + Supabase (catálogo y frases)
    if MUSIC:
        env["MUSIC_DIR"] = str(MUSIC)
    if OVERLAYS:
        env["OVERLAYS_DIR"] = str(OVERLAYS)
    out.mkdir(parents=True, exist_ok=True)

    clips_disco = {c.stem: c for c in sorted(clips_dir.glob("*.mp4"))}
    en_cortes = [n for n in cortes_meta if n in clips_disco]
    sobran = sorted(set(clips_disco) - set(cortes_meta))
    faltan = [n for n in cortes_meta if n not in clips_disco]
    if sobran:
        proyecto.decir(f"AVISO: clips/ sin corte en cortes.json (no se renderizan): {', '.join(sobran)}")
    if faltan:
        proyecto.decir(f"AVISO: cortes sin clip en clips/ (lanza clips.py): {', '.join(faltan)}")
    solo = proyecto.filtrar_solo(en_cortes, args.solo)
    nombres = [n for n in en_cortes if solo is None or n in solo]

    # Validación de lo que se va a renderizar (sobre todo, los ganchos de texto).
    inp = next((p.input_dir / f"{nombre}{e}" for e in proyecto.EXT_VIDEO
                if (p.input_dir / f"{nombre}{e}").exists()), None)
    res = validar.validar_cortes(cortes_lista, herramientas.duracion(inp) if inp else None,
                                 base / f"{nombre}.json", not sin_gancho_texto)
    if not validar.informar(res, "cortes.json", solo=set(nombres), decir=proyecto.decir):
        raise SystemExit("[!] cortes.json tiene errores en los clips a renderizar: corrígelos y relanza.")

    # CONCURRENCIA: work dir ÚNICO por ejecución (mkdtemp bajo whisper/, ASCII);
    # solo se limpia ESE al terminar. Se puede forzar con --work-dir / EDIT_WORK_DIR.
    WORKBASE.mkdir(parents=True, exist_ok=True)
    supplied = args.work_dir or os.environ.get("EDIT_WORK_DIR")
    if supplied:
        workroot = Path(supplied)
        workroot.mkdir(parents=True, exist_ok=True)
        _work_es_propio = False  # dir suministrado: no lo borramos al final
    else:
        workroot = Path(tempfile.mkdtemp(prefix="_edit_", dir=str(WORKBASE)))
        _work_es_propio = True

    print(f"{len(nombres)} clips a editar"
          + (f" (solo {', '.join(sorted(solo))})" if solo else "") + "\n", flush=True)
    sin_gancho, fallos, hechos = [], [], 0
    for name in nombres:
        clip = clips_disco[name]
        hook = hooks.get(name) or name.split("_", 1)[-1].replace("_", " ")
        if not p.usa_gancho_visual:
            hook = None                      # proyecto sin gancho visual (o sin internet)
        corte = cortes_meta.get(name, {})
        # Tipología de música explícita (mood) y texto del clip para inferirla.
        music_typology = corte.get("tipologia_musica")
        clip_text = (corte.get("frase_viral") or corte.get("titulo")
                     or hook or "").strip() or None
        # Gancho de TEXTO en pantalla: SOLO el gancho_texto que escribió el
        # editor. Sin él, el clip sale sin gancho (nunca el titulo ni nada mecánico).
        gancho_texto = None
        if not sin_gancho_texto:
            gancho_texto = (corte.get("gancho_texto") or "").strip() or None
        print(f"=== {name}   gancho='{hook}'"
              + (f"   mood='{music_typology}'" if music_typology else ""), flush=True)
        if not sin_gancho_texto and not gancho_texto:
            sin_gancho.append(name)
            print("   [gancho texto] AVISO: el corte no trae gancho_texto -> sale SIN gancho de texto",
                  flush=True)
        work = workroot / name
        work.mkdir(parents=True, exist_ok=True)
        ascii_in = work / "in.mp4"
        shutil.copy(str(clip), str(ascii_in))
        out_tmp = work / "out.mp4"
        info = {}
        try:
            words = cargar_o_transcribir_words(clip, ascii_in, p.idioma)
            base_in = ascii_in
            if tapar_cfg:
                # Paso previo: tapar los rótulos de la fuente en el plano del
                # ponente (el gancho, el b-roll y nuestros subtítulos van encima).
                # Si falla, se avisa y el clip sigue sin tapar (no rompe el render).
                tapado = work / "in_tapado.mp4"
                try:
                    tramos = subs_fuente.tapar(ascii_in, tapado, tapar_cfg)
                    print(f"   [subs fuente] {subs_fuente.resumen_tramos(tramos)}"
                          + "".join(f"\n      {t['t0']:.2f}-{t['t1']:.2f} s · y {t['y0']}-{t['y1']}"
                                    for t in tramos), flush=True)
                    if tramos:
                        base_in = tapado
                    info["subs_fuente"] = len(tramos)
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    proyecto.decir(f"AVISO {name}.mp4 · no pude tapar los subtítulos de la fuente "
                                   f"({herramientas.describir_error(e)}): sale sin tapar")
                    info["subs_fuente"] = "no (fallo)"
            pc.burn_subs_and_music(
                base_in, MUSIC, out_tmp,
                lang=p.idioma, env=env, overlays_dir=OVERLAYS, hook_query=hook,
                music_typology=music_typology, clip_text=clip_text,
                words=words,
                hook_text=gancho_texto, hook_text_dur=p.gancho_duracion,
                recursos=recursos, seed=name, info=info,
            )
            shutil.move(str(out_tmp), str(out / f"{name}.mp4"))
            hechos += 1
            print(f"   OK -> finales/{name}.mp4", flush=True)
            proyecto.decir(linea_clip(name, info, p.usa_gancho_visual))
        except Exception as e:
            fallos.append(name)
            traceback.print_exc(file=sys.stdout)       # al log (y a consola con --verbose)
            proyecto.decir(f"FALLO {name}.mp4 · {herramientas.describir_error(e)} (detalle en el log)")

    if _work_es_propio:
        shutil.rmtree(workroot, ignore_errors=True)

    # --- Banco de frases virales (Supabase, best-effort) ---------------------
    if sin_frases:
        motivo = "--sin-frases" if args.sin_frases else "el proyecto tiene guardar_frases=false"
        print(f"   [frases] {motivo}: no se guardan en viral_phrases.", flush=True)
    else:
        source_url = str(inp) if inp else str(args.video)
        guardar_frases_virales(nombre, cortes_path, source_url=source_url, env=env, proyecto_obj=p)

    proyecto.decir(f"RESUMEN: {hechos} OK · {len(fallos)} fallo(s)"
                   + (f" ({', '.join(fallos)})" if fallos else "")
                   + (f" · sin gancho de texto: {', '.join(sin_gancho)}" if sin_gancho else "")
                   + f" -> {out}")
    proyecto.decir(f"QC: .venv\\Scripts\\python.exe qc.py --proyecto {p.id} \"{nombre}\"  (y mira finales/_qc.jpg)")
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()

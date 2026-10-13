# TheHistoria — Departamento de historias y carruseles de Instagram

Genera **historias de IG (MP4 1080×1920)** —un texto sobre un fondo— y
**carruseles del feed (2–10 JPG 4:5, 1080×1350)** para **varios proyectos
independientes**. Lo dirige CEO_Sergete con el subagente `historia`. Opciones,
esquemas y diseño en [`README.md`](README.md). **Este archivo manda** sobre las
reglas de trabajo.

## Cuándo se usa
**A demanda**: solo cuando Sergio pide historias o carruseles, o cuando el CEO
detecta huecos de carruseles en el calendario. Nunca se lanza solo tras
descargar o editar vídeos.

## Entorno
- `..\TheEditor\.venv\Scripts\python.exe` (no instales nada; nunca `python3`).
- Credenciales: `.env` o, si no existe, `..\CEO_Sergete\.env`.

## Proyectos (lo primero en cada orden)
- Cada proyecto (cuenta o cliente) vive en `proyectos/<id>/`: `proyecto.json`
  (historias sí/no, filtro de frases, nº de historias…), `estilo.json` (marca de
  los carruseles), `especiales/` (fondos de las especiales), `planes/` (planes de
  carrusel) y **`reglas.md` (tono, crédito, fuentes y publicación del proyecto:
  léelo antes de escribir nada)**. `proyectos/_plantilla/` es la base de los nuevos.
- Todos los scripts aceptan **`--proyecto <id>`**. Si se omite y solo hay un
  proyecto, se usa ese; si hay varios, error con la lista. **Nunca mezcles
  proyectos** (frases, fondos, portadas, planes ni salidas).
- **Recursos**: la política es la de `..\TheEditor\proyectos\<id>\proyecto.json`
  → `recursos` (se lee, no se copia):

  | `broll` | Fondos de las historias normales |
  |---|---|
  | `banco_comun` | `..\TheEditor\superposiciones\` + `match_broll` (semántica) o azar |
  | `propio` | solo `..\TheEditor\proyectos\<id>\recursos\broll\` (semántica local con `_indice.json`; si no, azar) |
  | `ninguno` | fondo liso del color de marca |

  Con `internet: false` nunca se usa nada de fuera (ni los `pexels_*` del banco
  común). Proyectos de **clipping**: solo sus propios recursos.
- **Frases**: `viral_phrases` con la etiqueta `proyecto:<id>` en `tags` y
  `used_in_story = false`.
- Salidas siempre en `salidas/<id>/…`.

## Tres vías

| Vía | Script | Texto | Fondos | Salida |
|---|---|---|---|---|
| **Normal** | `historias.py` | Frases del proyecto (por viralidad); se marcan como usadas | Según la política de b-roll | `salidas/<id>/<AAAAMMDD_HHMMSS>/` + `manifest.json` |
| **Especiales** (promos, eventos) | `historias_especiales.py` | Lo da Sergio (`--texto`, repetible) | `proyectos/<id>/especiales/`; si está vacío: b-roll propio (`propio`) o liso (`ninguno`) | `salidas/<id>/especiales_<…>/` |
| **Carruseles** (feed) | `carruseles.py --plan <plan.json>` | Plan que escribes tú | Fondo liso de marca; portada opcional | `salidas/<id>/carrusel_<AAAAMMDD-HHMM>_<slug>/` |

- Si no quedan frases del proyecto o falta Supabase, dilo; para probar sin BBDD,
  `--phrase "…"` (y `--no-marcar` en pruebas).
- Especiales: el texto va en la banda superior y deja libre la franja de abajo
  (`--reserva-inferior`, def. 0,25) para el botón de IG.

## Reglas (historias)
- Minúsculas, pero **mayúscula en la primera letra y tras `.`, `?` y `!`** (ya lo
  aplica el render).
- Fondos siempre a pantalla completa.
- Las historias **no llevan copy ni hashtags** y no entran en el calendario.

## Carruseles
**Sí llevan copy y hashtags** (TheCopy, al dar OK) y **sí entran en el calendario**.

1. Escribe el plan en `proyectos/<id>/planes/<slug>.json` (con `"proyecto": "<id>"`)
   desde un clip o vídeo del proyecto (`..\_Historico\<id>\<video>\` o
   `..\TheEditor\proyectos\<id>\transcripciones\<video>\`), un artículo de TheTextos
   o un tema. Lo de `_Historico` solo se lee. Rutas del plan relativas a PruebasIA.
2. `carruseles.py --plan … --solo-validar` hasta que no haya errores; corrige
   también los avisos y la auditoría de estilo (TheCopy).
3. `carruseles.py --plan …` y mira `_vista.jpg` antes de entregar.

**Contenido** (lo propio del proyecto, en su `reglas.md`):
- Fórmula según el objetivo: `IG5_lista` y `IG8_metodo` → guardados;
  `IG6_antes_despues` → guardados/seguidores; `IG7_mitos` → compartidos.
- 6–10 slides es lo típico (2–10). **Nunca rellenes**: si da para 5, son 5.
- Slide 1 = **promesa + bucle abierto** (≤ 12 palabras), nunca un título a secas.
  **Lo más fuerte en las slides 2–3.** Una idea por slide (título ~8 palabras,
  texto ~25). Cierre = resumen que merezca guardarse (`puntos`) + **una sola
  petición** (`peticion`).
- Conserva las afirmaciones y cifras de la fuente: **nada inventado**.
- Sentence case con ortografía correcta (tildes, ¿?, ¡!); nunca TODO MAYÚSCULAS.
  El texto se pinta tal cual. `**palabra**` = destacada (máx. una por slide).
- Evita lo que marca el auditor de TheCopy: paralelismos negativos («no es X, es
  Y»), revelaciones («¿El resultado?»), anuncios de sinceridad, vocabulario de IA y
  cebos de interacción.
- **Portada** (`portada_fondo`): solo material del proyecto (sus carpetas en
  `_Historico`, `TheEditor\proyectos`, `TheDescarga\descargas`, `proyectos\<id>\`
  y publicación; el banco común solo con `banco_comun`). Nunca de internet ni de
  otro proyecto: el validador da ERROR. El fotograma, nunca a ojo:
  `carruseles.py --candidatos-portada <video>` (gesto natural, sin rótulos, cara
  arriba).
- No cambies el contrato de la salida (lo lee TheCopy; ver README).

## Al dar OK
- **Historias**: mover (no copiar) los MP4 de las tandas aprobadas de
  `salidas\<id>\<tanda>\` a `..\CEO_Sergete\HISTORIAS\<id>\1. Pte publicar\`
  (aplanados) y borrar esas carpetas de tanda (conserva `salidas\.gitkeep`).
- **Carruseles**: el CEO mueve la carpeta entera `salidas\<id>\carrusel_<…>\` a
  `..\CEO_Sergete\REVISADOS\<id>\1. pte Publicar\` y lanza `copy`. El plan se queda
  en `proyectos\<id>\planes\`.

En `salidas/` solo queda lo que está en curso o pendiente de revisar.

## Proyecto nuevo
`..\CEO_Sergete\nuevo_proyecto.py` copia `proyectos/_plantilla/` a
`proyectos/<id>/` (sustituye `<id>` y `<Nombre>`). Después: rellena `reglas.md`,
ajusta `estilo.json` (colores, fuentes, `handle`) y `proyecto.json`, y pon sus
vídeos en `especiales/`. La política de recursos se define en TheEditor.

# TheEditor — Departamento de edición

Convierte vídeo en **reels verticales 9:16 editados** (b-roll + música +
subtítulos) y genera **adaptaciones con avatar IA**, para **varios proyectos**
independientes. Lo dirige CEO_Sergete (subagente `editor` para lo scriptable;
skill `Editor_Sergio` en el hilo principal para el montaje interactivo). Este
archivo tiene las **reglas generales de Sergio**, que valen para todos los
proyectos; lo propio de cada uno está en `proyectos/<id>/reglas.md`.

---

## Entorno

- Python: **siempre** `.venv\Scripts\python.exe` de TheEditor (nunca el global
  ni `python3`, que en este equipo es el acceso directo de la Microsoft Store).
- Trabaja con el cwd en `C:\Users\ico858\Desktop\PruebasIA\TheEditor`.
- Banco común (git-ignored): `superposiciones/` (b-roll), `musicas/`; además
  `whisper/` (whisper.cpp + modelos). El código resuelve todo desde la raíz de
  TheEditor, no desde el cwd.
- Credenciales: `~/.viral-pipeline/env.json` (Supabase + Pexels); si faltan,
  `../CEO_Sergete/.env`. Nunca se suben a git.

## Proyectos

Un **proyecto** es una cuenta o cliente de contenido (`id` en minúsculas y sin
espacios). Todo lo suyo vive en `proyectos/<id>/`:

```
proyecto.json      tipo, idioma, recursos (política), encuadre, silencios, gancho, frases
reglas.md          reglas de edición propias (léelas antes de trabajar en el proyecto)
input/             buzón: vídeos largos, o clips ya cortados por subcarpetas
transcripciones/   trabajo y salidas: <video>/{clips,finales,cortes.json…}
logs/              un log por ejecución (lo crean los scripts solos)
recursos/broll/ recursos/musica/ recursos/sfx/   solo si tiene recursos propios
```

- **Elegir proyecto:** todos los scripts aceptan `--proyecto <id>`. Si se omite y
  solo hay uno (sin contar `_plantilla`), se usa ese; si hay varios, error con la
  lista. **Nunca mezcles material de proyectos distintos.**
- **Tipos:** `largos` (vídeos largos → vía 1, o vía 2 si vienen en extractos) y
  `clipping` (vídeos ya cortados → vía 2, solo con recursos propios).
- **Política de recursos** (`proyecto.json → recursos`), la hace cumplir el código:

  | Clave | Valores |
  |---|---|
  | `broll` | `banco_comun` (`superposiciones/` + catálogo `broll_assets`) · `propio` (solo `recursos/broll/`) · `ninguno` |
  | `musica` | `banco_comun` (`musicas/`) · `propia` (solo `recursos/musica/`) · `ninguna` |
  | `internet` | `false` = **nunca** Pexels, imágenes libres ni catálogo común (guarda en `pipeline_core`; modelos solo de la caché local; ni los `pexels_*` del banco común) |
  | `gancho_visual` | `pexels` (exige `internet: true`) · `ninguno` |
  | `gancho_texto` | `true` / `false` |
  | `guardar_frases` | `true` / `false` (`viral_phrases` con la etiqueta `proyecto:<id>`; no es un recurso: sale a Supabase aunque `internet` sea `false`) |

- **B-roll propio:** casación semántica **local** con `recursos/broll/_indice.json`
  (lo crea `indexar_broll.py`, ver README); sin índice, al azar **sin repetir**
  dentro del clip. Nunca el catálogo común. Lo que empieza por `_` se ignora.
- **Proyecto nuevo:** `proyecto.py nuevo <id> --nombre "…"` (o el
  `nuevo_proyecto.py` del CEO); rellenar `proyecto.json` y `reglas.md` y dejar los
  recursos en `recursos/`. `proyecto.py ver <id>` enseña la configuración.
- **Reglas nuevas:** si son de un proyecto, a su `reglas.md` (y, si el código lo
  usa, a su `proyecto.json`); si valen para todos, aquí.

## Las tres vías

### 1. Vídeo largo → clips (lo típico tras TheDescarga)
Buzón: `proyectos/<id>/input/`. Todo automático; no se edita código por vídeo.

1. `transcribir.py --proyecto <id> "<video>.mp4"` →
   `transcripciones/<video>/<video>.{txt,srt,json}`. **Se salta** lo ya transcrito
   (en `transcripciones/`) o ya aprobado (en `_Historico/`), salvo con `--forzar`.
2. **Generar `cortes.json`** (el único paso con criterio) desde la transcripción
   con tiempos (ver «Recorte y hook»; esquema en `cortes.example.json`), con un
   **`gancho_texto`** por corte; si no hay uno bueno, déjalo vacío: el clip sale
   **sin gancho** y el script lo avisa (nunca se usa el `titulo` ni nada mecánico).
   `hook_query` solo si el proyecto tiene gancho visual. Por defecto ~1 clip cada
   3 min (mín. 3, máx. 6).
3. `clips.py --proyecto <id> "<video>"` → recorte 9:16 + quitar silencios → `…/clips/`.
   No vuelve a cortar un vídeo ya archivado en `_Historico/` (salvo `--forzar`).
4. `editar_clips.py --proyecto <id> "<video>"` → Fase C (gancho visual si lo hay +
   gancho de texto + b-roll + música + subs) → `…/finales/`. Guarda frases si el
   proyecto lo permite. `--sin-gancho-texto` y `--sin-frases` (pruebas o
   re-render de una corrección). Guarda los tiempos de palabra en
   `clips/<nombre>.words.json` y los reutiliza al re-renderizar (no repite Whisper).
5. **QC** (ver «Exportación y QC»): `qc.py --proyecto <id> "<video>"` y mirar
   `finales/_qc.jpg`.

`transcribir.py` y `editar_clips.py` usan una carpeta de trabajo **única por
proceso**: se pueden lanzar en paralelo para vídeos distintos.

### 2. Clips ya cortados → reels (batch)
`procesar_batch_clip.py --proyecto <id> [RAIZ] [CARPETA] [MODO] [--solo-transcribir] [--sin-frases] [--solo CLIP] [--umbral 3%] [--margen 0.3s] [--forzar]`
- `RAIZ`: por defecto `proyectos/<id>/input/` (cada subcarpeta = un lote). Solo
  hace falta para otra raíz (si el primer argumento no es una ruta, es la `CARPETA`).
- `MODO` de encuadre: `right` · `left` · `center` · `auto` · `auto-right` ·
  `follow` · `<fracción>` (p. ej. `0.81`). Si no se da, el de la carpeta en
  `proyecto.json → encuadre.carpetas` o su `modo_por_defecto`.
- Por cada MP4: reencuadre 9:16 → quitar silencios → Fase C **sin gancho visual**
  y con gancho de texto. Transcribe una sola vez. Es reanudable: salta los
  finales que ya existen en vertical. Sin `CARPETA`, **salta los lotes ya
  aprobados** (`_Historico/<id>/<carpeta>/`); `--forzar` lo rehace todo.
- **Siempre en tres pasos** (si el proyecto lleva gancho de texto):
  1. `… "<CARPETA>" --solo-transcribir` → deja `transcripciones/<CARPETA>/textos/<clip>.txt`
     y el 9:16 + tiempos en `_prep/`. No renderiza.
  2. El editor (LLM) lee los textos y escribe `transcripciones/<CARPETA>/ganchos.json`:
     `{"<clip>.mp4": "¿Texto que abre el bucle?", ...}`.
  3. `… "<CARPETA>"` → renderiza reutilizando `_prep/` y quema el gancho.
  - Clip **sin texto** en `ganchos.json` → sale sin gancho y el batch lo avisa.
    **Nunca** pongas un gancho mecánico (primera frase, nombre de archivo…).
  - `_prep/` **se conserva hasta archivar** (lo borra `proyecto.py aprobar`): corregir
    un gancho no repite reencuadre ni Whisper. Cada clip guarda con qué `MODO` y
    silencios se preparó; si cambian, ese clip se rehace solo.
- Usa `whisper/_edit_batch` **compartido**: **no lances dos batch a la vez**
  (tampoco un `--solo-transcribir` con otro batch en marcha), ni de proyectos distintos.

### 3. Adaptaciones con avatar IA (skill `Editor_Sergio`)
Parte del **link** del viral, con popups y gates por fases (audio → HeyGen →
edición). Se lanza desde el **hilo principal** del CEO, no desde el subagente.
Código en `.claude/skills/Editor_Sergio/`. `phase_c_edit(…, proyecto="<id>")` y
`step1b_store_viral_phrases(…, proyecto="<id>")` (por defecto `mongemalo`) usan
los recursos y la etiqueta del proyecto. Salida en
`~/Desktop/viral_pipeline_output/<Avatar>/<slug>/`. **No lleva gancho de texto.**
- Python: el de TheEditor (`.venv\Scripts\python.exe`); no hace falta bootstrap.
  La descarga usa `..\TheDescarga\tools\yt-dlp.exe` (el venv no trae `yt_dlp`).
- El setup solo se salta si `env.json` tiene las claves de HeyGen y ElevenLabs:
  `setup.py faltan` (desde la carpeta de la skill) dice `SETUP_OK` o cuáles faltan.
  Las claves las pone Sergio (en octubre de 2026 faltaban `HEYGEN_API_KEY`,
  `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` y `HEYGEN_ENGINE` + su ID de avatar).

---

## Reglas de edición de Sergio (obligatorias, todos los proyectos)

### Encuadre 9:16
- **Nunca un tramo con solo piernas/cuerpo sin la cara.** Encuadre tipo
  **busto**: recorte también vertical hacia cara + torso. Si no se puede, tapar
  el tramo con b-roll más largo.
  - **Excepción deliberada:** los modos del batch `right`, `left`, `center`,
    `auto` (y `auto-right`) y `<fracción>` recortan a **altura completa** (solo
    franja horizontal). En un plano a dos **sentado**, la altura completa
    encuadra cabeza y torso y no deja «solo piernas», y un zoom vertical
    cortaría la cabeza o daría un busto inestable. No es un fallo: no lo
    «arregles». El busto con zoom vertical es el de `follow` y la vía 1.
- **Un solo recorte FIJO por plano** (por corte de cámara). Nunca sub-ventanas ni
  microrreajustes dentro del mismo plano.
- En primeros planos, centrar la **cara dominante** (detección con filtro de piel
  YCrCb para descartar falsos positivos; también en `clips._detectar_cara`, la
  de la vía 1 y `follow`).
- La detección de hablante por movimiento de boca **está desactivada** (poco
  fiable). No la reactives sin que Sergio lo pida.
- Mantener grande el elemento principal: priorizar al protagonista del proyecto
  (ver su `reglas.md`).

### B-roll
- **Siempre a pantalla completa.** Nunca un parche recortado (p. ej. tapar un
  banner con un trozo de b-roll): b-roll a pantalla completa esos segundos, o un
  zoom/reencuadre que lo deje fuera de plano.
- Con intención: entra sincronizado con la voz (al empezar una frase, sale en la
  pausa) e ilustra lo que se dice. Si quitarlo no cambia nada, sobra. Selección
  semántica (umbral 0,30; descarta `aviso-*`): banco común → `broll_assets` +
  `match_broll`; propio → índice local. Sin match, azar.
- Nunca bajo el gancho ni en la cola del clip.
- Solo los recursos que permite el proyecto (ver «Proyectos»).

### Subtítulos
- Minúsculas, pero **mayúscula en la primera letra y tras `.`, `?` y `!`**. Los
  números de miles no se parten («10.000»).
- Se queman **una sola vez**, en la Fase C. Palabrotas enmascaradas (`P***`).
- Unidad de sentido: 3 palabras como máximo. El código corta el grupo **tras un
  fin de frase** (`.`, `?`, `!`, `…`) y tras una pausa larga, y **un grupo nunca
  acaba en palabra débil** (artículo, preposición, «que», «y»…: `_HOOK_WEAK`) si
  hay otra detrás: esa palabra pasa al grupo siguiente.

### Gancho de texto en pantalla
El **primer fotograma ya lleva un texto que abre un bucle** y el clip lo cumple.
- **Texto** (lo escribe el editor, LLM; nunca uno mecánico): **2 líneas como
  máximo** (~45 caracteres); **con tildes, ñ y signos de apertura** (`¿`, `¡`);
  abre un bucle **sin dar la respuesta**; **se cumple dentro del clip** (nada de
  cifras o promesas que el clip no dé); no repite literal la primera frase; sin emojis.
- Va en `cortes.json → gancho_texto` (vía 1) o `ganchos.json` (vía 2); la vía 3
  no lleva. Sale 2,5 s desde el primer fotograma en la franja superior, con el
  estilo y las reglas de texto de los subtítulos (`render_hook_text_png`).

### Silencios
- Ajuste global: `auto-editor` con umbral **6 %** y margen **0,15 s** (o el de
  `proyecto.json → silencios`).
- Si un clip queda atropellado, reprocesa **solo ese** con **3 % / 0,3 s**.
  `--umbral`/`--margen` valen solo para esa ejecución: **nunca** escriben en
  `proyecto.json`. **No cambies el ajuste global.**
  - Vía 1: `clips.py --proyecto <id> "<video>" --solo <clip> --umbral 3% --margen 0.3s`
    y después `editar_clips.py --proyecto <id> "<video>" --solo <clip> --sin-frases`.
  - Vía 2: `procesar_batch_clip.py --proyecto <id> "<CARPETA>" --solo "<clip>" --umbral 3% --margen 0.3s --sin-frases`
    (rehace su `_prep/` porque cambian los silencios).

### Correcciones: solo lo pedido
Una corrección sobre un clip concreto se aplica **solo a ese clip**; nunca la
conviertas en comportamiento global. Con `--solo` (repetible, o nombres separados
por comas) se re-renderiza solo ese clip y se sustituye su MP4 en `finales/`; el
resto no se toca. La música y el b-roll al azar salen de una **semilla con el
nombre del clip**: el re-render da la misma música y el mismo b-roll, y solo
cambia lo corregido.
- **Gancho** (vía 1): edita su `gancho_texto` en `cortes.json` →
  `editar_clips.py --proyecto <id> "<video>" --solo <clip> --sin-frases`.
- **Gancho** (vía 2): edita `ganchos.json` →
  `procesar_batch_clip.py --proyecto <id> "<CARPETA>" --solo "<clip>" --sin-frases`
  (reutiliza `_prep/`: ni reencuadre ni Whisper).
- **Tramo o encuadre** (vía 1): ajusta `inicio`/`fin` en `cortes.json` →
  `clips.py … --solo <clip>` → `editar_clips.py … --solo <clip> --sin-frases`.
- Tras corregir: `qc.py` de nuevo.

### Recorte y hook
- **Empieza tarde y termina pronto:** entra una frase más tarde y sal justo tras
  el remate; fuera saludos, muletillas y cierres.
- **El hook debe cumplirse:** test «Después de ver esto, la audiencia entenderá que ___».
- Nada de teaser + repetir la misma frase después.

### Audio
- Música claramente por debajo de la voz (**6–12 dB**), sin clipping, con
  de-click. La voz se tiene que entender en el altavoz de un móvil. La música no
  es obligatoria si no encaja.
- La mezcla termina en un limitador (`…normalize=0,alimiter=limit=0.95:level=0`):
  pico por debajo de 0 dBFS. Salida AAC 192k, **48 kHz estéreo**.

### Zona segura e higiene visual
- Cara, texto y elementos clave en una zona central conservadora; aire abajo y en
  el borde derecho (interfaz de IG/TikTok).
- Sin tabaco, alcohol, logos o marcas ajenas, matrículas, datos privados ni
  marcas de agua.

### Exportación y QC
- 1080×1920, MP4 H.264, fps de la fuente, 8–12 Mb/s, AAC 48 kHz estéreo. Las
  tres vías exportan igual (`pipeline_core.VIDEO_ENC`/`AUDIO_ENC`): objetivo
  10 Mb/s con VBV a 12 (`-b:v 10M -maxrate 12M -bufsize 24M`; con CRF 18 un busto
  reescalado se quedaba en ~6,5 Mb/s).
- **Tras renderizar, `qc.py` y mira `_qc.jpg`:**
  `qc.py --proyecto <id> "<video|carpeta>"` (o una ruta, p. ej. la salida de la
  vía 3). Una línea por clip: resolución, códec, fps frente a la fuente,
  bitrate, audio, pico, negros (`blackdetect` 0,25 s), congelados
  (`freezedetect` 2 s) y silencios (`silencedetect` −40 dB 1,5 s); `FALLA` si no
  cumple la exportación, `REVISAR` si hay algo que mirar. Deja
  `finales/_qc.jpg` con el primer y el último fotograma de cada clip: revisa el
  gancho, la cola y restos de superposiciones antes de dar los clips.

---

## Bancos de recursos

- **Banco común** (solo para proyectos que lo permiten): `superposiciones/`
  (b-roll + Pexels `pexels_<tema>_NN.mp4`; cómo bajar más y reindexar, en el
  README) y `musicas/` (subcarpetas por tipología).
- **`broll_assets`** (Supabase): catálogo del banco común con embeddings 384d
  (`paraphrase-multilingual-MiniLM-L12-v2`, `fastembed`).
- **`viral_phrases`** (Supabase): frases para TheHistoria, con la etiqueta
  `proyecto:<id>` en `tags`. SQL en `../TheLanding/supabase/viral_phrases.sql`.
- **Recursos propios:** `proyectos/<id>/recursos/` (ver «Proyectos»).

## Al dar OK

Por script, nunca a mano:

```
proyecto.py aprobar <id> --video "<video|carpeta>" [--clips a.mp4,b.mp4] [--cerrar] [--destino-pruebas <dir>]
```

- **Mueve** esos MP4 (sin `--clips`, todos) de `transcripciones/<v>/finales/` a
  `../CEO_Sergete/REVISADOS/<id>/1. pte Publicar/`. Si ya hay uno con el mismo
  nombre, añade `_2`, `_3`… y avisa.
- Si `finales/` queda vacío (o con `--cerrar`), **archiva**
  `transcripciones/<v>/` en `../_Historico/<id>/<v>/` (borra `_prep/`) y la fuente
  de `input/` en `../_Historico/<id>/<v>/_fuente/`. Si ya existe ese archivo, no
  mueve nada y avisa.
- Imprime la orden siguiente para TheCopy (`copys.py pendientes --proyecto <id>`).
- `--destino-pruebas <dir>`: lo mismo, pero en `<dir>/REVISADOS` y
  `<dir>/_Historico` (pruebas; no toca los reales).

En `transcripciones/` solo queda lo que está en curso o pendiente de revisar.

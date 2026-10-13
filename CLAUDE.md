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
   `transcripciones/<video>/<video>.{txt,srt,json}`.
2. **Generar `cortes.json`** (el único paso con criterio) desde la transcripción
   con tiempos (ver «Recorte y hook»; esquema en `cortes.example.json`), con un
   **`gancho_texto`** por corte (si falta, el `titulo`); `hook_query` solo si el
   proyecto tiene gancho visual. Por defecto ~1 clip cada 3 min (mín. 3, máx. 6).
3. `clips.py --proyecto <id> "<video>"` → recorte 9:16 + quitar silencios → `…/clips/`.
4. `editar_clips.py --proyecto <id> "<video>"` → Fase C (gancho visual si lo hay +
   gancho de texto + b-roll + música + subs) → `…/finales/`. Guarda frases si el
   proyecto lo permite. `--sin-gancho-texto` y `--sin-frases` (pruebas o
   re-render de una corrección).

`transcribir.py` y `editar_clips.py` usan una carpeta de trabajo **única por
proceso**: se pueden lanzar en paralelo para vídeos distintos.

### 2. Clips ya cortados → reels (batch)
`procesar_batch_clip.py --proyecto <id> [RAIZ] [CARPETA] [MODO] [--solo-transcribir] [--sin-frases]`
- `RAIZ`: por defecto `proyectos/<id>/input/` (cada subcarpeta = un lote). Solo
  hace falta para otra raíz (si el primer argumento no es una ruta, es la `CARPETA`).
- `MODO` de encuadre: `right` · `left` · `center` · `auto` · `auto-right` ·
  `follow` · `<fracción>` (p. ej. `0.81`). Si no se da, el de la carpeta en
  `proyecto.json → encuadre.carpetas` o su `modo_por_defecto`.
- Por cada MP4: reencuadre 9:16 → quitar silencios → Fase C **sin gancho visual**
  y con gancho de texto. Transcribe una sola vez. Es reanudable: salta los
  finales que ya existen en vertical.
- **Siempre en tres pasos** (si el proyecto lleva gancho de texto):
  1. `… "<CARPETA>" --solo-transcribir` → deja `transcripciones/<CARPETA>/textos/<clip>.txt`
     y el 9:16 + tiempos en `_prep/`. No renderiza.
  2. El editor (LLM) lee los textos y escribe `transcripciones/<CARPETA>/ganchos.json`:
     `{"<clip>.mp4": "¿Texto que abre el bucle?", ...}`.
  3. `… "<CARPETA>"` → renderiza reutilizando `_prep/` y quema el gancho.
  - Clip **sin texto** en `ganchos.json` → sale sin gancho y el batch lo avisa.
    **Nunca** pongas un gancho mecánico (primera frase, nombre de archivo…).
  - Si cambias el `MODO` tras el paso 1, borra antes `_prep/<clip>.*`.
- Usa `whisper/_edit_batch` **compartido**: **no lances dos batch a la vez**
  (tampoco un `--solo-transcribir` con otro batch en marcha), ni de proyectos distintos.

### 3. Adaptaciones con avatar IA (skill `Editor_Sergio`)
Parte del **link** del viral, con popups y gates por fases (audio → HeyGen →
edición). Se lanza desde el **hilo principal** del CEO, no desde el subagente.
Código en `.claude/skills/Editor_Sergio/`. `phase_c_edit(…, proyecto="<id>")` y
`step1b_store_viral_phrases(…, proyecto="<id>")` (por defecto `mongemalo`) usan
los recursos y la etiqueta del proyecto. Salida en
`~/Desktop/viral_pipeline_output/<Avatar>/<slug>/`. **No lleva gancho de texto.**

---

## Reglas de edición de Sergio (obligatorias, todos los proyectos)

### Encuadre 9:16
- **Nunca un tramo con solo piernas/cuerpo sin la cara.** Encuadre tipo
  **busto**: recorte también vertical hacia cara + torso. Si no se puede, tapar
  el tramo con b-roll más largo.
- **Un solo recorte FIJO por plano** (por corte de cámara). Nunca sub-ventanas ni
  microrreajustes dentro del mismo plano.
- En primeros planos, centrar la **cara dominante** (detección con filtro de piel
  YCrCb para descartar falsos positivos).
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
- Unidad de sentido: 3 palabras por defecto, agrupando por idea si mejora la
  lectura; no dejar artículos o preposiciones sueltos al final.

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
- Si un clip queda atropellado, reprocesa **solo ese** con **3 % / 0,3 s** y
  reemplaza su MP4 en `finales/`. **No cambies el ajuste global.**

### Correcciones: solo lo pedido
Una corrección sobre un clip concreto se aplica **solo a ese clip** (carpeta
temporal y sustituir su MP4). Nunca la conviertas en comportamiento global.

### Recorte y hook
- **Empieza tarde y termina pronto:** entra una frase más tarde y sal justo tras
  el remate; fuera saludos, muletillas y cierres.
- **El hook debe cumplirse:** test «Después de ver esto, la audiencia entenderá que ___».
- Nada de teaser + repetir la misma frase después.

### Audio
- Música claramente por debajo de la voz (**6–12 dB**), sin clipping, con
  de-click. La voz se tiene que entender en el altavoz de un móvil. La música no
  es obligatoria si no encaja.

### Zona segura e higiene visual
- Cara, texto y elementos clave en una zona central conservadora; aire abajo y en
  el borde derecho (interfaz de IG/TikTok).
- Sin tabaco, alcohol, logos o marcas ajenas, matrículas, datos privados ni
  marcas de agua.

### Exportación y QC
- 1080×1920, MP4 H.264, fps de la fuente, 8–12 Mb/s, AAC 48 kHz estéreo.
- Revisar el **archivo exportado**: primer y último fotograma, negros,
  congelados, restos de superposiciones, segundos vacíos.

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

Los MP4 aprobados se **mueven** a `../CEO_Sergete/REVISADOS/<id>/1. pte Publicar/`
y su carpeta `proyectos/<id>/transcripciones/<video>/` a `../_Historico/<id>/`.
Lo orquesta el CEO (después, TheCopy escribe el copy). En `transcripciones/` solo
queda lo que está en curso o pendiente de revisar.

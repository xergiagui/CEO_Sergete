# TheEditor — Departamento de edición

Convierte vídeo en **reels verticales 9:16 editados** (b-roll + música +
subtítulos) y genera **adaptaciones con avatar IA**. Lo dirige CEO_Sergete
(subagente `editor` para lo scriptable; skill `Editor_Sergio` en el hilo principal
para el montaje interactivo). **Este archivo es la fuente de verdad de las
reglas de edición de Sergio**: si te dan una regla nueva, apúntala aquí.

---

## Entorno

- Python: **siempre** `.venv\Scripts\python.exe` de TheEditor (nunca el global
  ni `python3`, que en este equipo es el acceso directo de la Microsoft Store).
- Trabaja con el cwd en `C:\Users\ico858\Desktop\PruebasIA\TheEditor`.
- Assets locales (git-ignored): `superposiciones/` (b-roll), `musicas/`,
  `whisper/` (whisper.cpp + modelos), `fonts/`. El pipeline los resuelve por
  `PROJECT_ROOT`, no por el cwd.
- Credenciales: primero `~/.viral-pipeline/env.json` (`SUPABASE_URL`,
  `SUPABASE_ANON_KEY`, `PEXELS_API_KEY`); si faltan, `../CEO_Sergete/.env`.
  `TheEditor/.env` guarda la `PEXELS_API_KEY` para bajar stock. Nunca se suben a git.

## Las tres vías

### 1. Vídeo largo local → clips (lo típico tras TheDescarga)
Buzón de entrada: `input/`. Todo automático; no se edita código por vídeo.

1. `transcribir.py "input/<video>.mp4"` → `transcripciones/<video>/<video>.{txt,srt,json}`.
2. **Generar `cortes.json`** (el único paso con criterio): leer la transcripción
   con tiempos y elegir los momentos con gancho (ver «Recorte y hook»). Esquema
   en `cortes.example.json`: `[{"nombre","inicio","fin","titulo","hook_query"}]`.
   Nº de clips por defecto: ~1 por cada 3 min, mínimo 3 y máximo 6.
3. `clips.py "<video>"` → recorte 9:16 + quitar silencios → `…/clips/`.
4. `editar_clips.py "<video>"` → Fase C (b-roll + gancho + música + subs) →
   `…/finales/`. Guarda frases en `viral_phrases` (best-effort).

`transcribir.py` y `editar_clips.py` usan una carpeta de trabajo **única por
proceso**: se pueden lanzar en paralelo para vídeos distintos.

### 2. Clips ya cortados → reels (batch)
`procesar_batch_clip.py [RAIZ] [CARPETA] [MODO]`
- `RAIZ`: carpeta con subcarpetas de clips (por defecto `C:\Users\ico858\Desktop\Clip`).
- `CARPETA`: procesar solo esa subcarpeta (opcional).
- `MODO` de encuadre: `right` (por defecto) · `left` · `center` · `auto` ·
  `auto-right` · `follow` · `<fracción>` (p. ej. `0.81`).
- Por cada MP4: reencuadre 9:16 → quitar silencios → Fase C sin gancho → guarda la
  transcripción en `viral_phrases`. Transcribe una sola vez y reutiliza los
  tiempos (`words=` en `burn_subs_and_music`). Es reanudable: salta los finales que
  ya existen en vertical.
- Usa `whisper/_edit_batch` **compartido**: **no lances dos batch a la vez**.

### 3. Adaptaciones con avatar IA (skill `Editor_Sergio`)
Parte del **link** del viral (se descarga sola), con popups y gates por fases
(audio → HeyGen → edición). Se lanza desde el **hilo principal** del CEO, no desde
el subagente. Código en `.claude/skills/Editor_Sergio/` (`generate_from_link.py`,
`pipeline_core.py`). Salida en `~/Desktop/viral_pipeline_output/<Avatar>/<slug>/`.
Al analizar un viral guarda 2–6 frases en `viral_phrases`.

---

## Reglas de edición de Sergio (obligatorias)

### Encuadre 9:16
- **Nunca un tramo con solo piernas/cuerpo sin la cara.** Encuadre tipo
  **busto**: recorte también vertical hacia cara + torso (en planos abiertos no
  basta con mover la franja en horizontal). Si no se puede, tapar el tramo con
  b-roll más largo.
- **Un solo recorte FIJO por plano** (por corte de cámara). Nunca sub-ventanas ni
  microrreajustes dentro del mismo plano. Si el sujeto se descentra un poco, no
  pasa nada: el plano debe estar centrado en él y estable.
- En primeros planos de una persona, centrar la **cara dominante**. La detección
  de caras lleva **filtro de piel** (YCrCb) para descartar falsos positivos
  (cojines, micros, fondo).
- La detección de hablante por movimiento de boca **está desactivada** (poco
  fiable: elegía al que escucha). No la reactives sin que Sergio lo pida.
- Mantener grande el elemento principal: priorizar al hablante en vez de
  conservar un plano horizontal minúsculo.

### B-roll
- **Siempre a pantalla completa.** Nunca un parche recortado (p. ej. tapar un
  banner con un trozo de b-roll). Para tapar un rótulo: b-roll a pantalla completa
  esos segundos, o un zoom/reencuadre que lo deje fuera de plano.
- Con intención: entra sincronizado con la voz (al empezar una frase, sale en la
  pausa) y debe ilustrar o demostrar lo que se dice. Si quitarlo no cambia nada,
  sobra. Selección semántica con `broll_assets` + RPC `match_broll` (umbral 0.30;
  descarta los clips con `aviso-*`). Sin match, azar local.
- Nunca bajo el gancho ni en la cola del clip.

### Subtítulos
- Estilo en minúsculas, pero **mayúscula en la primera letra del texto y tras
  `.`, `?` y `!`**. Los números de miles no se parten («10.000»).
- Se queman **una sola vez**, en la Fase C. Palabrotas enmascaradas (`P***`).
- Unidad de sentido: 3 palabras por defecto, pero agrupar por idea si mejora la
  lectura; no dejar artículos o preposiciones sueltos al final.
- Idea pendiente (no implementada): resaltar en color 1 palabra clave por bloque.

### Silencios
- Ajuste global de `clips.quitar_silencios`: `auto-editor` con umbral **6 %** y
  margen **0,15 s**.
- Si Sergio dice que un clip queda atropellado o «no se entiende», reprocesa
  **solo ese clip** con un ajuste suave (**3 % / 0,3 s**) y reemplaza su MP4 en
  `finales/`. **No cambies el ajuste global.** Comprobación: con el ajuste suave
  apenas se recortan 1–5 s respecto al original.

### Correcciones: solo lo pedido
Una corrección sobre un clip concreto se aplica **solo a ese clip**: reprocesarlo
aparte (carpeta temporal) y sustituir su MP4. Nunca la conviertas en
comportamiento global que cambie clips que ya estaban bien, salvo que Sergio lo
pida expresamente.

### Recorte y hook
- **Empieza tarde y termina pronto:** entra una frase más tarde y sal justo tras
  el remate; fuera saludos, muletillas y cierres que siguen después.
- **El hook debe cumplirse:** lo que promete la apertura tiene que llegar en el
  clip. Test: «Después de ver esto, la audiencia entenderá que ___».
- Nada de teaser + repetir la misma frase después. Si se busca bucle, que el
  final conduzca de forma natural al principio, sin repetir el gancho literal.

### Audio
- Música claramente por debajo de la voz (**6–12 dB**), picos por debajo de
  0 dBFS, sin clipping, con de-click. La voz se tiene que entender en el altavoz
  de un móvil. La música no es obligatoria si no encaja.

### Zona segura e higiene visual
- Cara, texto y elementos clave en una zona central conservadora; dejar aire
  abajo y en el borde derecho (interfaz de IG/TikTok).
- Revisar que no salgan tabaco, alcohol, logos o marcas ajenas, matrículas, datos
  privados ni marcas de agua.

### Exportación y QC
- 1080×1920, MP4 H.264, fps de la fuente, 8–12 Mb/s, AAC 48 kHz estéreo.
- Revisar el **archivo exportado** (no el proyecto): primer y último fotograma,
  negros, congelados, restos de superposiciones, segundos vacíos.

---

## Bancos de recursos

- **`superposiciones/`**: b-roll propio + stock de Pexels (`pexels_<tema>_NN.mp4`,
  verticales, ≤ 10 s). Para bajar más: `https://api.pexels.com/videos/search`
  con cabecera `Authorization: <PEXELS_API_KEY>` **y** `User-Agent: Mozilla/5.0`
  (sin User-Agent devuelve 403). Al añadir clips, reindexar en `broll_assets` con
  los scripts de `.claude/skills/Editor_Sergio/broll_index/` (idempotentes).
- **`broll_assets`** (Supabase): catálogo del b-roll con embeddings 384d
  (`paraphrase-multilingual-MiniLM-L12-v2` vía `fastembed`; en runtime, el mismo
  modelo). SQL en `../TheLanding/supabase/broll_assets.sql`.
- **`viral_phrases`** (Supabase): frases virales que usa TheHistoria. SQL en
  `../TheLanding/supabase/viral_phrases.sql`.

---

## Proyecto MongeMalo (perfil de afiliado de Luis Monge)

- Perfil **independiente**, no la cuenta oficial de Luis: no imitar su identidad.
  Transparencia de afiliación y nada de prometer resultados económicos.
- **Luis Monge** = hombre de pelo oscuro, barba corta, ropa North Face (no el
  calvo ni el señor canoso). Todos sus clips centrados en él.
- Encuadre de los clips de `Desktop/Clip` («Largo N Extractos»):

  | Carpeta | Plano | Modo |
  |---|---|---|
  | Largo 1 | a dos, estático, Luis a la derecha | `right` |
  | Largo 2, 3, 6, 7 | Luis solo | `follow` |
  | Largo 4 | multicámara a 3 (Luis a la izquierda) | `auto` |
  | Largo 5 | multicámara a 2, primeros planos alternos | `follow` |

---

## Al dar OK

Los MP4 aprobados se **mueven** (no se copian) a
`../CEO_Sergete/REVISADOS/1. pte Publicar/`, y su carpeta de
`transcripciones/<video>/` se **mueve** a `../_Historico/`. Lo orquesta el CEO
(después, TheCopy escribe el copy). En `transcripciones/` solo queda lo que está en
curso o pendiente de revisar.

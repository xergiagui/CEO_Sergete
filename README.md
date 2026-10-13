# TheEditor: transcripción → clips virales, por proyectos

Flujo local para convertir vídeo en clips verticales listos para publicar, para
**varios proyectos** (cuentas o clientes) que no se mezclan. Cada proyecto tiene
su buzón, sus salidas, sus reglas y su **política de recursos** (banco común o
recursos propios, con o sin internet).

> Lo que decide el editor (órdenes de cada vía, recorte, ganchos, correcciones)
> está en [`CLAUDE.md`](CLAUDE.md); lo que ya hace el código (encuadre, b-roll,
> subtítulos, audio, exportación, política de recursos), en
> [`REGLAS_CODIGO.md`](REGLAS_CODIGO.md); lo de cada proyecto, en
> `proyectos/<id>/reglas.md`.

## Estructura

```
proyecto.py                    proyectos: elegir, ver, crear, aprobar (CLI) + salida --quiet
herramientas.py                un solo ffmpeg/ffprobe (+ dimensiones con la rotación aplicada)
validar.py                     validación de cortes.json y ganchos.json antes de renderizar
qc.py                          QC de los finales exportados (+ hoja _qc.jpg)
proyectos/
  _plantilla/                  base de los proyectos nuevos (pensada para clipping)
  <id>/
    proyecto.json              tipo, idioma, recursos, encuadre, silencios, gancho, frases
    reglas.md                  reglas de edición del proyecto
    input/                     buzón: vídeos largos, o clips cortados en subcarpetas
    transcripciones/<video>/
      <video>.cortes.txt       Paso 1: lo que lee el editor para elegir cortes
      <video>.txt/.srt/.json   Paso 1
      cortes.json              Paso 3 (momentos + titulo + gancho_texto)
      clips/                   Paso 3 (9:16 sin subs; <clip>.words.json del Paso 4)
      finales/                 Paso 4 (reels listos + _qc.jpg)
    logs/                      un log por ejecución
    recursos/broll|musica|sfx  recursos propios (si su política lo dice)
superposiciones/  musicas/     BANCO COMÚN (git-ignored), solo para quien lo permita
whisper/                       whisper.cpp: bin/ + models/ (git-ignored, ~3 GB)
```

Todos los scripts aceptan **`--proyecto <id>`**. Si se omite y solo hay un
proyecto (sin contar `_plantilla`), se usa ese; si hay varios, error con la lista.
`transcribir.py`, `clips.py`, `editar_clips.py` y el batch dan **una línea por
clip y un RESUMEN** cuando su salida no es una terminal (`--quiet`; `--verbose`
para verlo todo); el detalle queda en `proyectos/<id>/logs/`.

## Política de recursos (`proyecto.json → recursos`)

| Clave | Valores | MongeMalo | `_plantilla` (clipping) |
|---|---|---|---|
| `broll` | `banco_comun` · `propio` · `ninguno` | `banco_comun` | `propio` |
| `musica` | `banco_comun` · `propia` · `ninguna` | `banco_comun` | `propia` |
| `internet` | `true` · `false` | `true` | `false` |
| `gancho_visual` | `pexels` (exige internet) · `ninguno` | `pexels` | `ninguno` |
| `gancho_texto` | `true` · `false` | `true` | `true` |
| `guardar_frases` | `true` · `false` | `true` | `false` |

- `internet: false` es una **guarda en el código** (`pipeline_core`): Pexels,
  imágenes libres y el catálogo común lanzan `RecursoExternoBloqueado` en vez de
  salir a la red, y los modelos (Whisper, fastembed) se cargan solo de la caché
  local (`HF_HUB_OFFLINE`). Guardar frases en `viral_phrases` no es un recurso.
- Con política propia, el render **nunca** cae al banco común: sin b-roll propio
  no hay b-roll; sin música propia, sin música (con aviso); el click de entrada
  del b-roll solo sale de `recursos/sfx/`.
- Las frases se guardan con la etiqueta **`proyecto:<id>`** en `tags`.

## Paso 1 — Transcribir (`transcribir.py`)

WAV 16 kHz mono + **whisper.cpp** sin DTW (`ggml-large-v3-turbo*.bin` si está en
`whisper/models/`; si no, `large-v3`). Por encima de 35 min trocea en fragmentos
de ~10 min cortados en silencios (o con 2 s de solape).

```bat
.venv\Scripts\python.exe transcribir.py --proyecto <id>                 :: todo su input\
.venv\Scripts\python.exe transcribir.py --proyecto <id> "video.mp4"     :: uno de su input\ (o una ruta)
.venv\Scripts\python.exe transcribir.py --cortes-txt "<ruta>\video.json" [--salida <dir>]
```
Además de `.txt/.srt/.json` escribe **`<video>.cortes.txt`** (cabecera con la
duración y los clips sugeridos; una línea por frase `[612.3–618.9] texto`; línea
en blanco = pausa > 1,5 s): es lo único que lee el editor. Salta lo ya transcrito
o ya aprobado (`_Historico/`), salvo con `--forzar`; `--cortes-txt` solo
(re)genera ese archivo desde un JSON de whisper.cpp.

## Paso 2 — Limpiar transcripción (`revisar_srt.py` + revisión manual)

`revisar_srt.py --proyecto <id> "<video>"` → `revisadas/<video> - revisado.srt`
con los mismos tiempos (ajusta sus `REEMPLAZOS` a cada vídeo).

## Paso 3 — Cortar clips (`clips.py`)

El editor elige los momentos (≈ 1 cada 3 min, mín. 3 y máx. 6) y los escribe en
`transcripciones/<video>/cortes.json` (esquema en `cortes.example.json`), con su
`gancho_texto`. Luego:

```bat
.venv\Scripts\python.exe clips.py --proyecto <id> "<video>" --validar   :: solo valida cortes.json
.venv\Scripts\python.exe clips.py --proyecto <id> "<video>"
```
Antes de cortar valida `cortes.json` (`validar.py`: nombres, tramos de 15–90 s
sin solapes, ganchos de ≤ 2 líneas con `¿¡`, sin emojis ni cifras que no salgan en
el clip) y para si hay errores. Una fuente ya vertical solo se escala.

Recorte 9:16 con seguimiento de cara y encuadre de busto + quitar silencios
(auto-editor, `silencios` del proyecto; por defecto 6 % / 0,15 s). Salida en
`clips/` **sin subtítulos**.

## Paso 4 — Edición final (`editar_clips.py`, motor de la skill `Editor_Sergio`)

```bat
.venv\Scripts\python.exe editar_clips.py --proyecto <id> "<video>" [--sin-gancho-texto] [--sin-frases] [--sin-musica] [--sin-broll] [--solo <clip>]
```
Solo renderiza los clips de `cortes.json` (y lo valida antes).

Capas: gancho visual (Pexels, solo si el proyecto lo tiene) → b-roll a pantalla
completa sincronizado con la voz → música + de-click → gancho de texto (2,5 s) →
subtítulos palabra a palabra, una sola vez. Salida en `finales/`. Exporta
1080x1920 H.264 a 10 Mb/s (VBV 12), AAC 48 kHz estéreo con limitador.

## QC (`qc.py`) y aprobar (`proyecto.py aprobar`)

```bat
.venv\Scripts\python.exe qc.py --proyecto <id> "<video|carpeta>"      :: una línea por clip + finales\_qc.jpg
.venv\Scripts\python.exe proyecto.py aprobar <id> --video "<video|carpeta>" [--clips a.mp4,b.mp4] [--cerrar]
```
`aprobar` mueve los finales a `CEO_Sergete/REVISADOS/<id>/1. pte Publicar/` y, si
`finales/` queda vacío, archiva el vídeo (y su fuente) en `_Historico/<id>/<v>/`.

## Corregir un solo clip (`--solo`)

`--solo <clip>` (repetible) en `clips.py`, `editar_clips.py` y el batch; con
`--umbral`/`--margen` para los silencios de esa ejecución (no tocan
`proyecto.json`). Música y b-roll salen de una semilla con el nombre del clip:
re-renderizar da lo mismo. Órdenes exactas en `CLAUDE.md` → «Correcciones».

## Batch de clips ya cortados (`procesar_batch_clip.py`, vía 2)

Cada subcarpeta de `proyectos/<id>/input/` es un lote (clips `.mp4`, `.mov`,
`.m4v` o `.mkv`); los clips sueltos de `input/` son el lote `_sueltos` (en los
proyectos de clipping, o pidiendo esa CARPETA). El modo de encuadre sale del
argumento o de `proyecto.json → encuadre` (por carpeta); una fuente ya vertical
solo se escala. Al empezar cuenta los recursos y para si falta b-roll o música
propios (`--sin-broll` / `--sin-musica`). En tres pasos:

```bat
:: 1) reencuadre + silencios + transcripción (sin render) -> textos/, _prep/,
::    _para_ganchos.md (todos los textos) y plantilla ganchos.json
.venv\Scripts\python.exe procesar_batch_clip.py --proyecto <id> "<CARPETA>" --solo-transcribir
:: 2) el editor lee _para_ganchos.md y rellena ganchos.json
::    {"clip 1.mp4": "¿Texto que abre el bucle?", "clip 2.mp4": "..."}
.venv\Scripts\python.exe procesar_batch_clip.py --proyecto <id> "<CARPETA>" --validar-ganchos
:: 3) render reutilizando _prep/ (valida antes y para si hay errores)
.venv\Scripts\python.exe procesar_batch_clip.py --proyecto <id> "<CARPETA>"
```

Otra raíz: `procesar_batch_clip.py --proyecto <id> "C:/otra/raiz" "<CARPETA>" <MODO>`.
No lances dos batch a la vez (comparten `whisper/_edit_batch`). `_prep/` se
conserva hasta archivar; sin `CARPETA` se saltan los lotes ya aprobados (`--forzar`).

## B-roll propio: índice semántico local (`indexar_broll.py`)

Para proyectos con `broll: propio`. Mismo modelo que el catálogo común
(`paraphrase-multilingual-MiniLM-L12-v2`, fastembed), sin Supabase:

```bat
:: 1) montajes de 3 fotogramas en recursos\broll\_frames\ + plantilla _descripciones.json
.venv\Scripts\python.exe indexar_broll.py --proyecto <id> --frames
:: 2) describir cada clip en recursos\broll\_descripciones.json
::    {"clip.mp4": {"descripcion": "qué se ve", "logical_tags": []}}   (aviso-* = excluir)
:: 3) embeddings -> recursos\broll\_indice.json
.venv\Scripts\python.exe indexar_broll.py --proyecto <id>
```

Sin índice no hay casación por significado: como mucho 1 b-roll al azar por clip.

## Proyecto nuevo

```bat
.venv\Scripts\python.exe proyecto.py nuevo <id> --nombre "Nombre" [--tipo clipping|largos]
.venv\Scripts\python.exe proyecto.py ver <id>
```

Copia `proyectos/_plantilla/` (o lo hace el `nuevo_proyecto.py` del CEO). Después:
1. `proyecto.json`: `tipo`, `recursos`, `encuadre` (modo por defecto y por carpeta);
   qué significa cada clave, en `REGLAS_CODIGO.md`.
2. `reglas.md`: protagonista, tono, lo que evitar.
3. Recursos propios: b-roll en `recursos/broll/`, música en `recursos/musica/`
   (suelta o en subcarpetas por tipología: «motivacion», «epica»…), click opcional
   en `recursos/sfx/`; y el índice del b-roll.
4. Vídeos en `input/` (largos sueltos; clips cortados en subcarpetas).

## Banco común

- `superposiciones/`: b-roll + stock de Pexels (`pexels_<tema>_NN.mp4`,
  verticales, ≤ 10 s). Para bajar más: `https://api.pexels.com/videos/search` con
  `Authorization: <PEXELS_API_KEY>` **y** `User-Agent: Mozilla/5.0` (sin él, 403).
  `indexar_broll.py --faltan` lista lo que aún no está en `broll_assets` (sin
  catálogo, ese b-roll solo sale al azar, máx. 1 por clip); se indexa con
  `.claude/skills/Editor_Sergio/broll_index/` (idempotente).
- `musicas/`: subcarpetas por tipología («9. MOTIVACIÓN», «15. ÉPICA»…).

## Vía 3 — avatar IA (skill `Editor_Sergio`)

`phase_c_edit(…, proyecto="<id>")` y `step1b_store_viral_phrases(…, proyecto="<id>")`
(por defecto `mongemalo`) usan los recursos y la etiqueta del proyecto. Corre con
el `.venv` de TheEditor y baja los reels con `..\TheDescarga\tools\yt-dlp.exe`.
Necesita las claves de HeyGen y ElevenLabs en `~/.viral-pipeline/env.json`
(`setup.py faltan` dice cuáles faltan).

## Instalación

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install faster-whisper auto-editor opencv-python-headless httpx Pillow imageio-ffmpeg fastembed
```
whisper.cpp: binario `whisper-blas-bin-x64.zip` (release de ggml-org/whisper.cpp)
en `whisper/bin/` y modelo `ggml-large-v3.bin` (o `ggml-large-v3-turbo.bin`, más
rápido) en `whisper/models/`. ffmpeg/ffprobe: los de `..\TheDescarga\tools\`
(o `FFMPEG`/`FFPROBE`, imageio-ffmpeg o el PATH; ver `herramientas.py`). Los
proyectos sin internet necesitan los modelos de Whisper y fastembed ya en la
caché local (`whisper/models/fastembed`; basta con haberlos usado una vez con red).

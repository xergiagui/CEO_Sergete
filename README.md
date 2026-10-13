# TheEditor: transcripción → clips virales, por proyectos

Flujo local para convertir vídeo en clips verticales listos para publicar, para
**varios proyectos** (cuentas o clientes) que no se mezclan. Cada proyecto tiene
su buzón, sus salidas, sus reglas y su **política de recursos** (banco común o
recursos propios, con o sin internet).

> Las **reglas de edición** generales y las tres vías están en
> [`CLAUDE.md`](CLAUDE.md); las de cada proyecto, en `proyectos/<id>/reglas.md`.

## Estructura

```
proyecto.py                    proyectos: elegir, validar, crear (CLI)
proyectos/
  _plantilla/                  base de los proyectos nuevos (pensada para clipping)
  <id>/
    proyecto.json              tipo, idioma, recursos, encuadre, silencios, gancho, frases
    reglas.md                  reglas de edición del proyecto
    input/                     buzón: vídeos largos, o clips cortados en subcarpetas
    transcripciones/<video>/
      <video>.txt/.srt/.json   Paso 1
      cortes.json              Paso 3 (momentos + titulo + gancho_texto)
      clips/                   Paso 3 (9:16 sin subs)
      finales/                 Paso 4 (reels listos)
    logs/                      un log por ejecución
    recursos/broll|musica|sfx  recursos propios (si su política lo dice)
superposiciones/  musicas/     BANCO COMÚN (git-ignored), solo para quien lo permita
whisper/                       whisper.cpp: bin/ + models/ (git-ignored, ~3 GB)
```

Todos los scripts aceptan **`--proyecto <id>`**. Si se omite y solo hay un
proyecto (sin contar `_plantilla`), se usa ese; si hay varios, error con la lista.

## Política de recursos (`proyecto.json → recursos`)

| Clave | Valores | MongeMalo | `_plantilla` (clipping) |
|---|---|---|---|
| `broll` | `banco_comun` · `propio` · `ninguno` | `banco_comun` | `propio` |
| `musica` | `banco_comun` · `propia` · `ninguna` | `banco_comun` | `propia` |
| `internet` | `true` · `false` | `true` | `false` |
| `gancho_visual` | `pexels` (exige internet) · `ninguno` | `pexels` | `ninguno` |
| `gancho_texto` | `true` · `false` | `true` | `true` |
| `guardar_frases` | `true` · `false` | `true` | `true` |

- `internet: false` es una **guarda en el código** (`pipeline_core`): Pexels,
  imágenes libres y el catálogo común lanzan `RecursoExternoBloqueado` en vez de
  salir a la red, y los modelos (Whisper, fastembed) se cargan solo de la caché
  local (`HF_HUB_OFFLINE`). Guardar frases en `viral_phrases` no es un recurso.
- Con política propia, el render **nunca** cae al banco común: sin b-roll propio
  no hay b-roll; sin música propia, sin música (con aviso); el click de entrada
  del b-roll solo sale de `recursos/sfx/`.
- Las frases se guardan con la etiqueta **`proyecto:<id>`** en `tags`.

## Paso 1 — Transcribir (`transcribir.py`)

WAV 16 kHz mono + **whisper.cpp large-v3 + DTW** (troceo automático de vídeos de
más de 35 min).

```bat
.venv\Scripts\python.exe transcribir.py --proyecto <id>                 :: todo su input\
.venv\Scripts\python.exe transcribir.py --proyecto <id> "video.mp4"     :: uno de su input\ (o una ruta)
```

## Paso 2 — Limpiar transcripción (`revisar_srt.py` + revisión manual)

`revisar_srt.py --proyecto <id> "<video>"` → `revisadas/<video> - revisado.srt`
con los mismos tiempos (ajusta sus `REEMPLAZOS` a cada vídeo).

## Paso 3 — Cortar clips (`clips.py`)

El editor elige los momentos (≈ 1 cada 3 min, mín. 3 y máx. 6) y los escribe en
`transcripciones/<video>/cortes.json` (esquema en `cortes.example.json`), con su
`gancho_texto`. Luego:

```bat
.venv\Scripts\python.exe clips.py --proyecto <id> "<video>"
```

Recorte 9:16 con seguimiento de cara y encuadre de busto + quitar silencios
(auto-editor, `silencios` del proyecto; por defecto 6 % / 0,15 s). Salida en
`clips/` **sin subtítulos**.

## Paso 4 — Edición final (`editar_clips.py`, motor de la skill `Editor_Sergio`)

```bat
.venv\Scripts\python.exe editar_clips.py --proyecto <id> "<video>" [--sin-gancho-texto] [--sin-frases]
```

Capas: gancho visual (Pexels, solo si el proyecto lo tiene) → b-roll a pantalla
completa sincronizado con la voz → música + de-click → gancho de texto (2,5 s) →
subtítulos palabra a palabra, una sola vez. Salida en `finales/`.

## Batch de clips ya cortados (`procesar_batch_clip.py`, vía 2)

Cada subcarpeta de `proyectos/<id>/input/` es un lote. El modo de encuadre sale
del argumento o de `proyecto.json → encuadre` (por carpeta). En tres pasos:

```bat
:: 1) reencuadre + silencios + transcripción (sin render) -> textos/ y _prep/
.venv\Scripts\python.exe procesar_batch_clip.py --proyecto <id> "<CARPETA>" --solo-transcribir
:: 2) el editor escribe proyectos\<id>\transcripciones\<CARPETA>\ganchos.json
::    {"clip 1.mp4": "¿Texto que abre el bucle?", "clip 2.mp4": "..."}
:: 3) render reutilizando _prep/
.venv\Scripts\python.exe procesar_batch_clip.py --proyecto <id> "<CARPETA>"
```

Otra raíz: `procesar_batch_clip.py --proyecto <id> "C:/otra/raiz" "<CARPETA>" <MODO>`.
No lances dos batch a la vez (comparten `whisper/_edit_batch`).

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

Sin índice, el b-roll propio va al azar sin repetir dentro del clip.

## Proyecto nuevo

```bat
.venv\Scripts\python.exe proyecto.py nuevo <id> --nombre "Nombre" [--tipo clipping|largos]
.venv\Scripts\python.exe proyecto.py ver <id>
```

Copia `proyectos/_plantilla/` (o lo hace el `nuevo_proyecto.py` del CEO). Después:
1. `proyecto.json`: `tipo`, `recursos`, `encuadre` (modo por defecto y por carpeta).
2. `reglas.md`: protagonista, tono, lo que evitar.
3. Recursos propios: b-roll en `recursos/broll/`, música en `recursos/musica/`
   (suelta o en subcarpetas por tipología: «motivacion», «epica»…), click opcional
   en `recursos/sfx/`; y el índice del b-roll.
4. Vídeos en `input/` (largos sueltos; clips cortados en subcarpetas).

## Banco común

- `superposiciones/`: b-roll + stock de Pexels (`pexels_<tema>_NN.mp4`,
  verticales, ≤ 10 s). Para bajar más: `https://api.pexels.com/videos/search` con
  `Authorization: <PEXELS_API_KEY>` **y** `User-Agent: Mozilla/5.0` (sin él, 403).
  Al añadir clips, reindexar `broll_assets` con
  `.claude/skills/Editor_Sergio/broll_index/` (idempotente).
- `musicas/`: subcarpetas por tipología («9. MOTIVACIÓN», «15. ÉPICA»…).

## Vía 3 — avatar IA (skill `Editor_Sergio`)

`phase_c_edit(…, proyecto="<id>")` y `step1b_store_viral_phrases(…, proyecto="<id>")`
(por defecto `mongemalo`) usan los recursos y la etiqueta del proyecto.

## Instalación

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install faster-whisper auto-editor opencv-python-headless httpx Pillow imageio-ffmpeg fastembed
```
whisper.cpp: binario `whisper-blas-bin-x64.zip` (release de ggml-org/whisper.cpp)
en `whisper/bin/` y modelo `ggml-large-v3.bin` en `whisper/models/`. Los proyectos
sin internet necesitan los modelos de Whisper y fastembed ya en la caché local
(basta con haberlos usado una vez con red).

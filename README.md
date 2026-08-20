# Transcripción → Clips virales

Flujo local (sin coste ni API de pago) para convertir un vídeo largo en clips
verticales listos para publicar. **Siempre se trabaja igual**, en 4 pasos.

## Estructura

```
input/                         vídeos/audios de entrada
transcripciones/
  └── <nombre>/
      ├── <nombre>.txt/.srt/.json   Paso 1 (originales)
      ├── revisadas/                Paso 2 (.txt y .srt revisados)
      └── clips/                    Paso 3 (clips verticales SIN subs)
musicas/                       música local para el Paso 4 (git-ignored)
superposiciones/               vídeos b-roll locales para el Paso 4 (git-ignored)
whisper/                       whisper.cpp: bin/ + models/ (git-ignored, ~3GB)
```

## Paso 1 — Transcribir  (`transcribir.py`)

Convierte a **WAV 16 kHz mono** y transcribe con **whisper.cpp large-v3 + DTW**
(`-dtw large.v3 -nfa`). Genera `.txt`, `.srt` y `.json` en `transcripciones/<nombre>/`.

```bat
.venv\Scripts\python.exe transcribir.py                 :: todo input\
.venv\Scripts\python.exe transcribir.py "input\v.mp4"   :: un archivo
```

Requiere `whisper/bin/whisper-cli.exe` y `whisper/models/ggml-large-v3.bin`.

## Paso 2 — Limpiar transcripción  (`revisar_srt.py` + revisión manual)

- Corrige **puntuación**, quita **muletillas** y **enmascara palabrotas** (`P***`).
- Produce **dos** ficheros en `transcripciones/<nombre>/revisadas/`:
  - `<nombre> - revisado.txt` — versión de lectura (párrafos).
  - `<nombre> - revisado.srt` — subtítulo con los **mismos timestamps** (no se
    fusionan cues), vía `revisar_srt.py`.

## Paso 3 — Cortar clips  (`clips.py`)

- Se eligen los momentos con más **gancho** (≈ **1 cada 3 min** de vídeo; si
  salen menos, no se fuerza), con inicio/fin en segundos.
- **Duraciones**: ~30 s por defecto; opcionalmente también **60 s y 90 s**
  (independientes o extendiendo el de 30 s).
- Por cada uno: **recorte vertical 9:16** (ffmpeg) + **quitar silencios**
  (auto-editor, umbral 8 %, margen 0.1 s).
- Salida en `transcripciones/<nombre>/clips/` **SIN subtítulos** (se ponen en el
  Paso 4). Los intermedios (`_tmp/`) se borran siempre.

## Paso 4 — Edición final  (skill `Editor_Sergio`)

Por cada clip, en este orden de capas:

1. **Gancho**: una **imagen libre** de stock online (Openverse, CC, sin API key;
   fallback Lorem Picsum) superpuesta a pantalla completa los primeros ~1.8 s.
   La imagen debe tener **fuerte gancho visual** y **relación clara** con el
   clip → se analiza el contenido para elegir bien la búsqueda (query en inglés).
2. **B-roll** a pantalla completa a intervalos, desde `superposiciones/` (local).
3. **Música** desde `musicas/` (local) + **de-click**.
4. **Subtítulos palabra a palabra** quemados **una sola vez**, encima de todo.

Salida: vídeo final local, listo para publicar.

## Encuadre y zonas seguras (RRSS)

- El **locutor** debe quedar en la **ZONA ROJA** (banda central segura del 9:16).
- El vídeo y los **subtítulos** deben quedar **fuera de las ZONAS GRISES** (áreas
  que cada red social tapa con su UI: barra superior, pie con texto/usuario,
  botones laterales) para que se vean bien en todas las RRSS.
- ⏳ **Medidas exactas pendientes** de la imagen de referencia del usuario.

## Reglas clave

- **Subtítulos: una sola vez** — solo en el Paso 4 (nunca en el Paso 3).
- **Recursos locales** en el Paso 4 (b-roll `superposiciones/`, música `musicas/`);
  no se usa Pexels.
- **Intermedios**: se borran siempre por defecto.

## Instalación

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install faster-whisper auto-editor
```
whisper.cpp: binario `whisper-blas-bin-x64.zip` (release de ggml-org/whisper.cpp)
en `whisper/bin/` y modelo `ggml-large-v3.bin` en `whisper/models/`.
La skill `Editor_Sergio` trae su propio bootstrap (venv aparte con `httpx`,
`faster-whisper`, `imageio-ffmpeg`, `Pillow`, `yt-dlp`).

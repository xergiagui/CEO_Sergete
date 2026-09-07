# TheHistoria

Departamento de **CEO_Sergete** que genera **historias de Instagram (9:16)** a
partir de las **frases virales** que **TheEditor** va guardando en Supabase.

La idea es simple: coger una frase → ponerle un **fondo** → exportar un MP4
vertical listo para subir como historia.

> **Proceso independiente.** Descargar y editar vídeos (TheDescarga / TheEditor)
> **no** dispara la creación de historias. TheHistoria se ejecuta **a demanda**,
> cuando se pida expresamente.

## De dónde salen las frases y los fondos

- **Frases** → tabla `viral_phrases` de Supabase (la puebla TheEditor al analizar
  cada viral). Se leen las que tienen `used_in_story = false`, ordenadas por
  viralidad. Tras generar la historia, la frase se marca como usada.
  Esquema: `TheLanding/supabase/viral_phrases.sql`.
- **Fondos** → **el mismo banco de b-roll que TheEditor**:
  `../TheEditor/superposiciones/`, catalogado en Supabase (`broll_assets`, con
  embeddings). Para cada frase se elige el fondo **más afín semánticamente** con
  la RPC `match_broll`; si no hay Supabase/embeddings o nada supera el umbral, se
  coge un fondo **al azar**. No se duplican assets.

## Cómo se ejecuta

Reutiliza el `.venv` de **TheEditor** (ya trae `httpx`, `Pillow`,
`imageio-ffmpeg` y `fastembed`), así que **no hay que instalar nada**:

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheHistoria
..\TheEditor\.venv\Scripts\python.exe historias.py
```

Ejemplos:

```powershell
# 5 historias desde la BBDD (por defecto)
..\TheEditor\.venv\Scripts\python.exe historias.py

# 3 historias de una categoría, con viralidad mínima
..\TheEditor\.venv\Scripts\python.exe historias.py --n 3 --categoria dinero --min-virality 70

# Una frase suelta (no toca la BBDD) — útil para probar el render
..\TheEditor\.venv\Scripts\python.exe historias.py --phrase "El dinero es una consecuencia, no un objetivo"

# Sin marcar como usada / duración distinta
..\TheEditor\.venv\Scripts\python.exe historias.py --no-marcar --duracion 7
```

### Opciones

| Flag | Qué hace |
|---|---|
| `--n N` | nº de historias desde la BBDD (def. 5) |
| `--categoria X` | filtra por `category` |
| `--min-virality N` | solo frases con `virality >= N` |
| `--phrase "..."` | genera una historia con esa frase sin leer/escribir la BBDD |
| `--duracion S` | segundos por historia (def. 6) |
| `--orientation vertical\|horizontal` | prefiere fondos con esa orientación |
| `--no-marcar` | no marca `used_in_story` |

## Salida

`salidas/<AAAAMMDD_HHMMSS>/` con un MP4 por frase (`NN_slug.mp4`, 1080×1920,
H.264) y un `manifest.json` (frase, fondo usado, método, si se marcó). La carpeta
`salidas/` está en `.gitignore`.

## Credenciales

Supabase (anon key) desde `./.env` o, si no existe, `../CEO_Sergete/.env`.
Copia `.env.example` a `.env` solo si quieres claves propias.

## Estructura

```
TheHistoria/
  historias.py          # CLI/orquestador
  config.py             # rutas y constantes del lienzo
  lib/
    env.py              # carga de credenciales
    supabase_phrases.py # leer frases sin usar / marcar usadas
    fondos.py           # elegir fondo (match_broll semántico o azar)
    embeddings.py       # modelo de embeddings (el mismo que indexó el catálogo)
    render.py           # componer fondo + texto -> MP4 9:16 (Pillow + ffmpeg)
  fonts/                # Montserrat (texto de la historia)
  salidas/              # MP4 generados (gitignored)
```

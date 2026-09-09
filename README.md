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

## Historias especiales (vía aparte)

Además del flujo normal (frases de Supabase), hay una **vía aparte** para
promos/anuncios donde **tú das el texto** y el fondo sale de un **banco propio**:

- **Texto**: lo pasas por `--texto` (soporta acentos/UTF-8). **No** toca Supabase
  ni `viral_phrases`.
- **Fondos**: vídeos de **`BRells especiales/`** (NO `superposiciones/`). Se
  eligen por **rotación/azar sin repetir** dentro de la tanda. Sin semántica.
- **Espacio para el botón de IG**: el texto **no** se centra en toda la pantalla,
  sino en la **zona superior**, dejando libre una **franja inferior** (por defecto
  el **25 %**, `--reserva-inferior`) para el botón/enlace de la historia.
- **Variaciones**: `--variaciones N` genera N historias del mismo tema, cada una
  con un **fondo distinto**. Puedes pasar **varios `--texto`** (uno por variación);
  si hay menos textos que variaciones, los textos **se ciclan** y varía el fondo.
  Con **1 solo texto y N>1**, todas comparten texto y solo cambia el fondo.

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheHistoria

# 3 variaciones (mismo texto, 3 fondos distintos)
..\TheEditor\.venv\Scripts\python.exe historias_especiales.py `
  --texto "descuento exclusivo del 30% solo este fin de semana" --variaciones 3

# Varios textos (uno por variación) + duración y reserva inferior a medida
..\TheEditor\.venv\Scripts\python.exe historias_especiales.py `
  --texto "oferta flash" --texto "ultimas horas" --variaciones 4 `
  --duracion 5 --reserva-inferior 0.30
```

### Opciones (especiales)

| Flag | Qué hace |
|---|---|
| `--texto "..."` | texto de la historia. **REPETIBLE** (uno por variación). Al menos uno. |
| `--variaciones N` | nº de historias del mismo tema, cada una con otro fondo (def. 3) |
| `--duracion S` | segundos por historia (def. 6) |
| `--reserva-inferior F` | fracción 0..0.6 reservada abajo para el botón de IG (def. 0.25) |

Salida en `salidas/especiales_<AAAAMMDD_HHMMSS>/` con `NN_slug.mp4` (1080×1920,
H.264) + `manifest.json` (texto, fondo, variación, reserva inferior, duración).

## Credenciales

Supabase (anon key) desde `./.env` o, si no existe, `../CEO_Sergete/.env`.
Copia `.env.example` a `.env` solo si quieres claves propias.

## Estructura

```
TheHistoria/
  historias.py            # CLI/orquestador (frases de Supabase)
  historias_especiales.py # CLI vía aparte (texto propio + BRells especiales/)
  config.py               # rutas y constantes del lienzo
  lib/
    env.py                # carga de credenciales
    supabase_phrases.py   # leer frases sin usar / marcar usadas
    fondos.py             # elegir fondo normal (match_broll semántico o azar)
    fondos_especiales.py  # fondos de BRells especiales/ (rotación/azar, sin repetir)
    embeddings.py         # modelo de embeddings (el mismo que indexó el catálogo)
    render.py             # componer fondo + texto -> MP4 9:16 (Pillow + ffmpeg)
  fonts/                  # Montserrat (texto de la historia)
  BRells especiales/      # banco de fondos propio para historias especiales
  salidas/                # MP4 generados (gitignored)
```

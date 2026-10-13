# TheHistoria

Departamento de **CEO_Sergete** que genera **historias de Instagram (9:16)** a
partir de las **frases virales** que **TheEditor** va guardando en Supabase, y
**carruseles del feed (4:5)** a partir de un plan slide a slide.

La idea es simple: coger una frase → ponerle un **fondo** → exportar un MP4
vertical listo para subir como historia. Para los carruseles: plan.json →
`carruseles.py` → 2–10 JPG 1080×1350 listos para publicar (ver
[Carruseles](#carruseles-tercera-vía)).

> **Proceso independiente.** Descargar y editar vídeos (TheDescarga / TheEditor)
> **no** dispara la creación de historias ni de carruseles. TheHistoria se
> ejecuta **a demanda**, cuando se pida expresamente.

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

## Carruseles (tercera vía)

Post del feed de **2–10 imágenes 4:5 (1080×1350)**, el formato que más guardados
genera. A diferencia de las historias, **lleva copy y hashtags** (TheCopy, al
dar OK) y **entra en el calendario de publicación**. Reglas de contenido y de
diseño en [`CLAUDE.md`](CLAUDE.md#carruseles-tercera-vía).

1. El subagente escribe un **plan** (`carruseles/planes/<slug>.json`) a partir de
   un clip/vídeo (`_Historico/` o `TheEditor/transcripciones/`), un artículo de
   TheTextos o un tema.
2. `carruseles.py` lo **valida** (estructura, longitudes, emojis, si el texto
   cabe), lo **audita** con TheCopy (opcional), **renderiza** y hace el **QC**.

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheHistoria

# Validar sin escribir nada (repite hasta que no haya errores)
..\TheEditor\.venv\Scripts\python.exe carruseles.py --plan carruseles\planes\clientes-toxicos.json --solo-validar

# Generar
..\TheEditor\.venv\Scripts\python.exe carruseles.py --plan carruseles\planes\clientes-toxicos.json
```

| Flag | Qué hace |
|---|---|
| `--plan RUTA` | plan.json de entrada (obligatorio) |
| `--solo-validar` | valida, comprueba que el texto cabe y audita; no escribe nada |
| `--auditar` / `--no-auditar` | auditoría de estilo con TheCopy (def.: sí, si TheCopy existe) |
| `--estilo RUTA` | otro `estilo.json` (def. `carruseles/estilo.json`) |
| `--candidatos-portada VIDEO` | sin plan: lista los fotogramas más nítidos del vídeo (varianza del laplaciano en la zona de la cara) y guarda una hoja para elegir `portada_fondo.segundo` |
| `--n N` / `--hoja RUTA` | nº de candidatos (def. 8) / dónde guardar la hoja (def. carpeta temporal) |

Códigos de salida: `0` OK · `1` errores de validación o QC · `2` fichero ilegible.

### Esquema del plan

```json
{
  "tipo": "carrusel",
  "proyecto": "mongemalo",
  "slug": "clientes-toxicos",
  "tema": "Cómo filtrar clientes tóxicos antes de venderles",
  "formula": "IG5_lista | IG6_antes_despues | IG7_mitos | IG8_metodo",
  "objetivo": "guardados | compartidos | comentarios | seguidores",
  "pilar": "educativo | historia | interaccion | promocion",
  "fuente": {"tipo": "clip | video | articulo | tema", "ruta": "...", "credito": "Ideas de Luis Monge"},
  "portada_fondo": {"ruta": "...mp4 o .jpg", "segundo": 6.5, "foco_y": 0.0},
  "portada_texto": "abajo | centro",
  "slides": [
    {"n": 1, "rol": "gancho", "titulo": "8 filtros contra **clientes tóxicos**", "texto": "Casi nadie se atreve con el segundo"},
    {"n": 2, "rol": "valor", "titulo": "Sube los precios", "texto": "..."},
    {"n": 10, "rol": "cierre", "titulo": "Los 8 filtros, de un vistazo",
     "puntos": ["Sube los precios", "..."], "texto": "...", "peticion": "Guárdalo y repásalo antes de tu próxima venta."}
  ]
}
```

- Roles: la 1.ª `gancho`, la última `cierre` y el resto `valor`.
- Obligatorios: `tema`, `formula`, `objetivo`, `pilar`, `fuente.tipo` (y
  `fuente.ruta` salvo en `tema`), `titulo` de cada slide, `texto` de las de
  valor, y `texto` o `puntos` en el cierre. `proyecto` y `slug` se completan
  solos si faltan.
- Opcionales: `portada_fondo` (ruta a imagen, o vídeo + `segundo`; `foco_y` 0–1
  elige qué franja vertical se ve), `portada_texto` (`abajo`: texto en la mitad
  inferior con degradado y la cara arriba, por defecto con foto; `centro`: centro
  óptico con oscurecido plano), `numero` en una slide de valor (otro número o
  `false` para ocultarlo), `puntos` y `peticion` en el cierre.
- `**palabra**` = destacada en dorado (máx. una por slide). `\n` = salto de línea.

### Salida (contrato con TheCopy)

```
salidas/carrusel_<AAAAMMDD-HHMM>_<slug>/
  01.jpg … NN.jpg     1080×1350, JPEG ~92 (4:4:4), sRGB, < 8 MB, en orden
  carrusel.json       el plan normalizado + "creado"
  _vista.jpg          hoja de contacto con todas las slides (solo para revisar)
```

Al dar OK, el CEO mueve la carpeta entera a
`CEO_Sergete/REVISADOS/1. pte Publicar/` y lanza `copy`.

### Diseño

`carruseles/estilo.json`: colores (fondo `#14171f`, blanco, dorado `#f59e0b`),
fuentes, márgenes (110 px a los lados), rangos de tamaño `[max, min]` del ajuste
automático, calidad JPEG, longitudes orientativas y `handle` (vacío = no se
pinta). Posición y portada:

- `centro_optico` (0,46): altura a la que se centran los bloques. Las slides de
  valor comparten caja (la de la más alta, o la mediana con
  `valor_referencia: "mediana"`) y van alineadas arriba dentro de ella, así el
  número no salta al deslizar.
- `portada_texto` (`abajo` por defecto con foto), `portada_texto_desde` (0,55),
  `portada_degradado` (`base`, `desde`, `hasta`, `max`) y `portada_oscurecer`
  (0,6, solo en modo `centro`).

## Credenciales

Supabase (anon key) desde `./.env` o, si no existe, `../CEO_Sergete/.env`.
Copia `.env.example` a `.env` solo si quieres claves propias.

## Estructura

```
TheHistoria/
  historias.py            # CLI/orquestador (frases de Supabase)
  historias_especiales.py # CLI vía aparte (texto propio + BRells especiales/)
  carruseles.py           # CLI carruseles (plan.json -> JPG 4:5 + carrusel.json)
  config.py               # rutas y constantes de los lienzos
  lib/
    env.py                # carga de credenciales
    supabase_phrases.py   # leer frases sin usar / marcar usadas
    fondos.py             # elegir fondo normal (match_broll semántico o azar)
    fondos_especiales.py  # fondos de BRells especiales/ (rotación/azar, sin repetir)
    embeddings.py         # modelo de embeddings (el mismo que indexó el catálogo)
    render.py             # componer fondo + texto -> MP4 9:16 (Pillow + ffmpeg)
    texto.py              # capitalización de las historias
    carrusel_plan.py      # carruseles: esquema y validación del plan
    carrusel_render.py    # carruseles: maquetación, ajuste, portada, JPG y vista
    carrusel_auditoria.py # carruseles: auditor de estilo de TheCopy (proceso aparte)
  carruseles/
    estilo.json           # diseño de los carruseles (marca MongeMalo)
    planes/               # planes de cada carrusel (en git)
  fonts/                  # Montserrat (Bold + SemiBold)
  BRells especiales/      # banco de fondos propio para historias especiales
  salidas/                # MP4 y carruseles generados (gitignored)
```

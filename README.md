# TheHistoria

Departamento de **CEO_Sergete** que genera, para **varios proyectos
independientes** (cuentas o clientes de contenido):

- **historias de Instagram (9:16)**: una frase viral del proyecto (Supabase
  `viral_phrases`) o un texto de Sergio sobre un **fondo** → MP4 vertical;
- **carruseles del feed (4:5)**: plan slide a slide → 2–10 JPG 1080×1350 (ver
  [Carruseles](#carruseles-tercera-vía)).

> **Proceso independiente.** Descargar y editar vídeos (TheDescarga / TheEditor)
> **no** dispara historias ni carruseles. TheHistoria se ejecuta **a demanda**.
> Reglas de trabajo en [`CLAUDE.md`](CLAUDE.md).

## Proyectos

```
proyectos/<id>/
  proyecto.json   historias sí/no, filtro de frases, nº de historias, fondo liso…
  estilo.json     marca de los carruseles
  reglas.md       tono, crédito, fuentes y publicación del proyecto
  especiales/     fondos de las historias especiales (vídeos, git-ignored)
  planes/         planes de carrusel (en git)
proyectos/_plantilla/   base de los proyectos nuevos (no cuenta como proyecto)
salidas/<id>/<AAAAMMDD_HHMMSS | especiales_… | carrusel_…>/
```

- **Elección**: todos los scripts aceptan `--proyecto <id>`. Si se omite y solo hay
  un proyecto, se usa ese; si hay varios, error con la lista. En los carruseles
  manda el `proyecto` del plan (`--proyecto`, si se da, debe coincidir).
- **Índice común**: `../CEO_Sergete/proyectos.json` (solo se lee: nombre y tipo,
  `largos` o `clipping`).
- **Política de recursos** (fuente de verdad: TheEditor, no se duplica):
  `../TheEditor/proyectos/<id>/proyecto.json` → `recursos`:

  | `broll` | Fondos de las historias normales |
  |---|---|
  | `banco_comun` | `../TheEditor/superposiciones/` (catálogo `broll_assets`): la RPC `match_broll` elige el más afín a la frase; si no hay Supabase/embeddings o nada supera el umbral, al azar |
  | `propio` | solo `../TheEditor/proyectos/<id>/recursos/broll/` (incluye subcarpetas). Si hay `_indice.json`, semántica **local** (mismo modelo de embeddings, sin Supabase ni catálogo común); si no, al azar |
  | `ninguno` | fondo liso del color de marca (`fondo_liso` del `proyecto.json` o `colores.fondo` del estilo) |

  Con `internet: false` no se usa nada de fuera: ni clips `pexels_*` del banco
  común, ni portadas de internet, y el modelo de embeddings se lee solo de la caché
  local. Mientras TheEditor no tenga la política de un proyecto se usa
  `recursos_respaldo` de su `proyecto.json` (y, si falta, `propio` sin internet).
- **Frases**: `viral_phrases` con `proyecto:<id>` en `tags` y
  `used_in_story = false`, por viralidad (filtros extra en `proyecto.json` →
  `historias.frases`). Tras generar la historia se marca como usada.

### `_indice.json` del b-roll propio (opcional)

Lo lee tal cual de `recursos/broll/`. Admite una lista de entradas o
`{"items": [...]}` (también `assets`, `clips`, `broll`…) o `{archivo: entrada}`.
Cada entrada: el archivo (`archivo` / `filename` / `ruta`, relativo a `broll/`) y
un `embedding` de 384 dimensiones o texto descriptivo (`descripcion`, `tags`…)
que se convierte en embedding al vuelo. Se saltan las que tienen etiquetas
`aviso*` y, si se pide orientación, las que no coinciden.

## Cómo se ejecuta

Reutiliza el `.venv` de **TheEditor** (ya trae `httpx`, `Pillow`,
`imageio-ffmpeg` y `fastembed`): **no hay que instalar nada**.

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheHistoria

# Historias desde la BBDD (nº por defecto del proyecto)
..\TheEditor\.venv\Scripts\python.exe historias.py --proyecto mongemalo

# 3 de una categoría, con viralidad mínima
..\TheEditor\.venv\Scripts\python.exe historias.py --proyecto mongemalo --n 3 --categoria dinero --min-virality 70

# Frase suelta (no toca la BBDD), sin marcar
..\TheEditor\.venv\Scripts\python.exe historias.py --proyecto mongemalo --phrase "El dinero es una consecuencia" --no-marcar
```

| Flag | Qué hace |
|---|---|
| `--proyecto ID` | proyecto (obligatorio si hay más de uno) |
| `--n N` | nº de historias desde la BBDD (def. `historias.n_por_defecto`, o 5) |
| `--categoria X` | filtra por `category` |
| `--min-virality N` | solo frases con `virality >= N` |
| `--phrase "..."` | una historia con esa frase sin leer/escribir la BBDD |
| `--duracion S` | segundos por historia (def. la del proyecto, o 6) |
| `--orientation vertical\|horizontal` | prefiere fondos con esa orientación |
| `--no-marcar` | no marca `used_in_story` |
| `--max-len N` | descarta frases de más de N caracteres (por defecto no filtra) |

Salida: `salidas/<id>/<AAAAMMDD_HHMMSS>/` con un MP4 por frase (`NN_slug.mp4`,
1080×1920, H.264) y `manifest.json` (proyecto, frase, fondo, método, política, si
se marcó).

## Historias especiales (vía aparte)

Promos y anuncios donde **Sergio da el texto**:

- **Texto**: `--texto` (repetible, uno por variación). No toca Supabase.
- **Fondos**: vídeos de `proyectos/<id>/especiales/`, por rotación/azar sin
  repetir dentro de la tanda. Si la carpeta está vacía: b-roll propio (`propio`),
  fondo liso (`ninguno`) o error (`banco_comun`: las especiales nunca usan el banco
  común).
- **Botón de IG**: el texto se centra en la zona superior y deja libre la franja
  inferior (`--reserva-inferior`, def. 0,25).
- **Variaciones**: `--variaciones N` historias, cada una con otro fondo; si hay
  menos textos que variaciones, los textos se ciclan.

```powershell
..\TheEditor\.venv\Scripts\python.exe historias_especiales.py --proyecto mongemalo `
  --texto "descuento exclusivo del 30% solo este fin de semana" --variaciones 3

..\TheEditor\.venv\Scripts\python.exe historias_especiales.py --proyecto mongemalo `
  --texto "oferta flash" --texto "ultimas horas" --variaciones 4 --duracion 5 --reserva-inferior 0.30
```

| Flag | Qué hace |
|---|---|
| `--proyecto ID` | proyecto (obligatorio si hay más de uno) |
| `--texto "..."` | texto de la historia, repetible (al menos uno) |
| `--variaciones N` | nº de historias, cada una con otro fondo (def. la del proyecto, o 3) |
| `--duracion S` | segundos por historia (def. la del proyecto, o 6) |
| `--reserva-inferior F` | fracción 0–0,6 reservada abajo (def. la del proyecto, o 0,25) |

Salida: `salidas/<id>/especiales_<AAAAMMDD_HHMMSS>/` con `NN_slug.mp4` +
`manifest.json`.

## Carruseles (tercera vía)

Post del feed de **2–10 imágenes 4:5 (1080×1350)**. **Lleva copy y hashtags**
(TheCopy, al dar OK) y **entra en el calendario**. Reglas de contenido en
[`CLAUDE.md`](CLAUDE.md#carruseles) y en `proyectos/<id>/reglas.md`.

```powershell
# Validar sin escribir nada (repite hasta que no haya errores)
..\TheEditor\.venv\Scripts\python.exe carruseles.py --plan proyectos\mongemalo\planes\clientes-toxicos.json --solo-validar

# Generar
..\TheEditor\.venv\Scripts\python.exe carruseles.py --plan proyectos\mongemalo\planes\clientes-toxicos.json
```

| Flag | Qué hace |
|---|---|
| `--plan RUTA` | plan.json de entrada (obligatorio) |
| `--proyecto ID` | opcional: manda el `proyecto` del plan y debe coincidir; si el plan no lo trae, se usa este (o el único que haya) |
| `--solo-validar` | valida, comprueba que el texto cabe y audita; no escribe nada |
| `--auditar` / `--no-auditar` | auditoría de estilo con TheCopy (def.: sí, si TheCopy existe) |
| `--estilo RUTA` | otro `estilo.json` (def. `proyectos/<id>/estilo.json`; debe ser del mismo proyecto) |
| `--candidatos-portada VIDEO` | sin plan: fotogramas más nítidos (varianza del laplaciano en la zona de la cara) y una hoja para elegir `portada_fondo.segundo` |
| `--n N` / `--hoja RUTA` | nº de candidatos (def. 8) / dónde guardar la hoja (def. carpeta temporal) |

Códigos de salida: `0` OK · `1` errores de validación o QC · `2` uso, proyecto o
fichero ilegible.

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
  "fuente": {"tipo": "clip | video | articulo | tema", "ruta": "_Historico/mongemalo/<video>", "credito": "Ideas de Luis Monge"},
  "portada_fondo": {"ruta": "_Historico/mongemalo/<video>/clips/<clip>.mp4", "segundo": 6.5, "foco_y": 0.0},
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
  `fuente.ruta` salvo en `tema`), `titulo` de cada slide, `texto` de las de valor,
  y `texto` o `puntos` en el cierre. `slug` se completa solo; `proyecto`, con
  `--proyecto` o el único proyecto.
- Rutas relativas: junto al plan, en TheHistoria o en PruebasIA.
- Opcionales: `portada_fondo` (imagen, o vídeo + `segundo`; `foco_y` 0–1 elige la
  franja vertical), `portada_texto`, `numero` en una slide de valor (otro número o
  `false`), `puntos` y `peticion` en el cierre.
- `**palabra**` = destacada en el color de acento (máx. una por slide). `\n` = salto.

### Validación

- **ERROR (no renderiza):** menos de 2 o más de 10 slides; roles fuera de orden;
  texto que no cabe ni al tamaño mínimo; obligatorios vacíos; `formula`,
  `objetivo`, `pilar`, `fuente.tipo` o `portada_texto` fuera de sus valores; `**`
  sin cerrar; emojis (si `emojis_max` es 0); `portada_fondo` inexistente, **de
  internet, del banco común (sin `banco_comun`), de otro proyecto o fuera del
  material del proyecto**; `fuente.ruta` de otro proyecto. Plan, `--proyecto` o
  estilo de proyectos distintos → código 2.
- **AVISO:** menos de 4 slides; longitudes por encima de las orientativas; más de
  una palabra destacada; minúscula al empezar o tras punto; mayúsculas sostenidas;
  falta «¿»/«¡»; primera persona; fórmula poco afín al objetivo; vídeo sin
  `credito`; cierre sin `peticion`.
- **Material del proyecto** (portada): `proyectos/<id>/`, `_Historico/<id>/`,
  `TheEditor/proyectos/<id>/`, `TheDescarga/descargas/<id>/`,
  `CEO_Sergete/{REVISADOS,HISTORIAS}/<id>/`, el banco común si la política es
  `banco_comun` y las carpetas de `carruseles.material_extra` del `proyecto.json`.
- **Auditoría de estilo (TheCopy):** por slide,
  `TheCopy\.venv\Scripts\python.exe TheCopy\copys.py auditar --solo-estilo --json --texto "<texto>" --proyecto <id>`.
  Solo avisa; si no está disponible, sigue.
- **QC de la salida:** cada JPG 1080×1350, RGB/sRGB, < 8 MB y numerados en orden;
  `carrusel.json` y `_vista.jpg` presentes.

### Salida (contrato con TheCopy: no cambiarlo)

```
salidas/<id>/carrusel_<AAAAMMDD-HHMM>_<slug>/
  01.jpg … NN.jpg     1080×1350, JPEG ~92 (4:4:4), sRGB, < 8 MB, en orden
  carrusel.json       el plan normalizado + "creado"
  _vista.jpg          hoja de contacto (solo para revisar)
```

`carrusel.json` = `tipo` («carrusel»), `proyecto`, `slug`, `tema`, `formula`,
`objetivo`, `pilar`, `fuente {tipo, ruta, credito}`, `slides [{n, rol, titulo,
texto, …}]`, `creado` y los extras del plan (`portada_fondo`, `portada_texto`;
en las slides `numero`, `puntos`, `peticion`). Los textos conservan `**…**`.

Al dar OK, el CEO mueve la carpeta entera a
`CEO_Sergete/REVISADOS/<id>/1. pte Publicar/` y lanza `copy`.

### Diseño (`proyectos/<id>/estilo.json`)

Colores (fondo, texto, texto suave, detalle, acento), fuentes de `fonts/`,
márgenes (lateral ≥ 100 px: la cuadrícula del perfil recorta ~45 px por lado),
rangos de tamaño `[max, min]` del ajuste automático, calidad JPEG, longitudes
orientativas, `emojis_max` y `handle` (vacío = no se pinta). `proyecto` debe ser
el id del proyecto.

- `centro_optico` (0,46): altura a la que se centran los bloques. Las slides de
  valor comparten escala y caja (la de la más alta, o la mediana con
  `valor_referencia: "mediana"`) y van alineadas arriba, así el número no salta.
- Slide 1: título grande centrado y «desliza →» abajo a la derecha. Con foto,
  `portada_texto` `abajo` (def.: texto desde `portada_texto_desde` sobre un
  degradado `portada_degradado` que sube desde abajo, cara arriba) o `centro`
  (oscurecido plano `portada_oscurecer`). Sin foto, centro óptico.
- Valor: número grande en el color de acento, título, barra y texto; contador
  «n/N». Cierre: título, `puntos`, texto, petición y crédito en pequeño.

## Proyecto nuevo

1. `..\CEO_Sergete\nuevo_proyecto.py <id> --nombre "…" --tipo clipping|largos`
   copia `proyectos/_plantilla/` a `proyectos/<id>/` sustituyendo `<id>` y
   `<Nombre>` (a mano: copia la carpeta y sustituye esos dos marcadores en
   `proyecto.json`, `estilo.json` y `reglas.md`).
2. Rellena `reglas.md`; ajusta `estilo.json` (colores, fuentes, `handle`,
   `emojis_max`) y `proyecto.json` (historias sí/no, nº, filtros de frases).
3. Pon los vídeos de las especiales en `especiales/`.
4. La política de recursos y el b-roll propio se definen en TheEditor
   (`proyectos/<id>/proyecto.json` y `proyectos/<id>/recursos/broll/`).
5. Prueba: `historias.py --proyecto <id> --phrase "prueba" --no-marcar`.

## Credenciales

Supabase (anon key) desde `./.env` o, si no existe, `../CEO_Sergete/.env`.

## Estructura

```
TheHistoria/
  historias.py            # CLI historias normales (frases del proyecto en Supabase)
  historias_especiales.py # CLI especiales (texto propio + especiales/ del proyecto)
  carruseles.py           # CLI carruseles (plan.json -> JPG 4:5 + carrusel.json)
  config.py               # rutas y constantes comunes
  lib/
    proyectos.py          # proyectos: regla --proyecto, configuración y política de recursos
    env.py                # credenciales
    supabase_phrases.py   # frases sin usar del proyecto / marcar usadas
    fondos.py             # fondo según la política (banco común, propio o liso)
    fondos_especiales.py  # fondos de las especiales (rotación sin repetir)
    embeddings.py         # modelo de embeddings (el mismo del catálogo)
    render.py             # fondo + texto -> MP4 9:16 (Pillow + ffmpeg)
    texto.py              # capitalización de las historias
    carrusel_plan.py      # carruseles: esquema, validación y material del proyecto
    carrusel_render.py    # carruseles: maquetación, portada, JPG y vista
    carrusel_auditoria.py # carruseles: auditor de estilo de TheCopy (proceso aparte)
  proyectos/
    _plantilla/           # base de los proyectos nuevos
    mongemalo/            # proyecto.json, estilo.json, reglas.md, especiales/, planes/
  fonts/                  # Montserrat (Bold + SemiBold)
  salidas/<id>/           # historias y carruseles generados (gitignored)
```

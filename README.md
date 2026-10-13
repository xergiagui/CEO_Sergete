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
  proyecto.json   historias sí/no, filtro de frases, nº de historias, crédito, fondo liso…
  estilo.json     maquetación (fuentes, tamaños, márgenes, posiciones)
  reglas.md       recursos, fuentes y publicación del proyecto
  especiales/     fondos de las historias especiales (vídeos, git-ignored)
  planes/         planes de carrusel (en git)
proyectos/_plantilla/   base de los proyectos nuevos (no cuenta como proyecto)
salidas/<id>/<AAAAMMDD_HHMMSS | especiales_… | carrusel_…>/
```

- **Elección**: todos los scripts aceptan `--proyecto <id>`. Si se omite y solo hay
  un proyecto, se usa ese; si hay varios, error con la lista. En los carruseles
  manda el `proyecto` del plan (`--proyecto`, si se da, debe coincidir).
- **Índice común e IDENTIDAD**: `../CEO_Sergete/proyectos.json` (solo se lee):
  nombre, tipo (`largos` o `clipping`) y `identidad` → `cuenta_ig` (handle de los
  carruseles), `voz.emojis_max`, `palabras_prohibidas` (las aplica la auditoría de
  TheCopy) y `marca` {`fondo`, `texto`, `acento`} (colores de historias y
  carruseles; el texto secundario y los detalles se derivan mezclando el texto
  hacia el fondo, salvo que la marca traiga `texto_suave`/`detalle`). Es la fuente
  única: no se copia en `estilo.json` ni en `reglas.md`. Si falta, valores neutros
  (`config.MARCA_NEUTRA`, sin handle, 0 emojis) con aviso.
- **Política de recursos** (fuente de verdad: TheEditor, no se duplica):
  `../TheEditor/proyectos/<id>/proyecto.json` → `recursos`:

  | `broll` | Fondos de las historias normales |
  |---|---|
  | `banco_comun` | `../TheEditor/superposiciones/` (catálogo `broll_assets`): la RPC `match_broll` elige el más afín a la frase; si no hay Supabase/embeddings o nada supera el umbral, al azar |
  | `propio` | solo `../TheEditor/proyectos/<id>/recursos/broll/` (incluye subcarpetas). Si hay `_indice.json`, semántica **local** (mismo modelo de embeddings, sin Supabase ni catálogo común); si no, al azar |
  | `ninguno` | fondo liso del color de marca (`fondo_liso` del `proyecto.json` o `identidad.marca.fondo`) |

  Con `internet: false` no se usa nada de fuera: ni clips `pexels_*` del banco
  común, ni portadas de internet, y el modelo de embeddings se lee solo de la caché
  local. Mientras TheEditor no tenga la política de un proyecto se usa
  `recursos_respaldo` de su `proyecto.json` (y, si falta, `propio` sin internet).
- **Frases**: `viral_phrases` con `proyecto:<id>` en `tags` y
  `used_in_story = false`, por viralidad (filtros extra en `proyecto.json` →
  `historias.frases`). **Se marcan como usadas al aprobar** (`--aprobar`), no al
  generar: una tanda rechazada no gasta frases. Las frases de tandas pendientes en
  `salidas/<id>/` no se repiten en una tanda nueva.

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

# Frase suelta (no toca la BBDD)
..\TheEditor\.venv\Scripts\python.exe historias.py --proyecto mongemalo --phrase "El dinero es una consecuencia"

# OK a unas tandas (o --todas): mover a publicar, marcar frases, log y borrar
..\TheEditor\.venv\Scripts\python.exe historias.py --proyecto mongemalo --aprobar 20261013_190745 especiales_20261013_190839
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
| `--max-len N` | descarta frases de más de N caracteres (por defecto no filtra) |
| `--aprobar TANDA…` | OK a esas tandas (normales o `especiales_…`; nombre en `salidas/<id>/` o ruta) |
| `--todas` | OK a todas las tandas de historias pendientes del proyecto |
| `--no-marcar` | con `--aprobar`: no marca `used_in_story` (al generar nunca se marca) |
| `--destino DIR` | con `--aprobar`: otra carpeta destino (pruebas) |

Salida: `salidas/<id>/<AAAAMMDD_HHMMSS>/` con un MP4 por frase (`NN_slug.mp4`,
1080×1920, H.264) y `manifest.json` (proyecto, frase, `phrase_id`, fondo, método,
política). Fuente: `fuentes.titulo` del `estilo.json`; colores: velo y fondo liso
en `identidad.marca.fondo`, texto en `identidad.marca.texto`. La rotación del
vídeo de fondo se aplica a los píxeles y se borra de la salida (si no, el
reproductor la giraría otra vez).

**Aprobar** (`--aprobar` / `--todas`): mueve los MP4 a
`../CEO_Sergete/HISTORIAS/<id>/1. Pte publicar/` aplanados y con nombre único (si
choca: `<nombre>_<tanda>.mp4`), marca como usadas las frases del `manifest.json`
(si hay frases que marcar y no hay Supabase, no aprueba nada), añade una línea a
`salidas/<id>/_aprobadas.log` (jsonl: tanda, destino, archivos, frases marcadas y
el manifest) y borra la tanda. Rechazar = borrar la carpeta de la tanda.

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
`manifest.json`. Misma fuente y colores que las normales. Se aprueban igual:
`historias.py --aprobar especiales_<…>`.

## Carruseles (tercera vía)

Post del feed de **2–10 imágenes 4:5 (1080×1350)**. **Lleva copy y hashtags**
(TheCopy, al dar OK) y **entra en el calendario**. Reglas de contenido en
[`CLAUDE.md`](CLAUDE.md#carruseles) y en `proyectos/<id>/reglas.md`.

```powershell
# Qué hay hecho (plan / en salidas / en REVISADOS / publicado) y vídeos de _Historico
..\TheEditor\.venv\Scripts\python.exe carruseles.py --listar --proyecto mongemalo

# Material para escribir el plan (texto sin tiempos + cortes + clips + campos válidos)
..\TheEditor\.venv\Scripts\python.exe carruseles.py --fuente "clientes toxicos" --proyecto mongemalo

# Generar (valida, audita y renderiza; con errores no escribe nada)
..\TheEditor\.venv\Scripts\python.exe carruseles.py --plan proyectos\mongemalo\planes\clientes-toxicos.json

# OK: a REVISADOS/<id>/1. pte Publicar/ (imprime la orden de TheCopy)
..\TheEditor\.venv\Scripts\python.exe carruseles.py --aprobar carrusel_20261013-1741_clientes-toxicos --proyecto mongemalo
```

| Flag | Qué hace |
|---|---|
| `--plan RUTA` | plan.json de entrada |
| `--fuente VIDEO\|RUTA` | imprime la fuente compacta: el `.txt` de la transcripción en párrafos sin tiempos (o los `textos/*.txt` de una carpeta de extractos; el `.srt` sin tiempos solo si no hay `.txt`), títulos y frases de `cortes.json`, clips para la portada y los campos válidos. Admite ruta (relativa a PruebasIA), nombre exacto o aproximado de un vídeo de `_Historico/<id>/` o `TheEditor/proyectos/<id>/transcripciones/`, o un `articulo.md` de `TheTextos/textos/<id>/` |
| `--listar` | carruseles del proyecto (slug, tema, fórmula, fuente, fecha y estado: plan / en salidas / en REVISADOS / publicado) y vídeos de `_Historico/<id>` por fecha con cuántos carruseles tiene cada uno |
| `--aprobar CARPETA` | mueve la carpeta entera a `CEO_Sergete/REVISADOS/<id>/1. pte Publicar/` (nombre único; comprueba proyecto y QC) e imprime `copys.py pendientes --proyecto <id> --clip <carpeta>` |
| `--proyecto ID` | con `--plan`, opcional: manda el `proyecto` del plan y debe coincidir; en el resto, obligatorio si hay más de un proyecto |
| `--destino DIR` | pruebas: carpeta base de la salida (`--plan`) o destino (`--aprobar`) |
| `--solo-validar` | valida, comprueba que el texto cabe y audita; no escribe nada (no hace falta antes del render: el render ya valida) |
| `--auditar` / `--no-auditar` | auditoría de estilo con TheCopy (def.: sí, si TheCopy existe) |
| `--estilo RUTA` | otro `estilo.json` (def. `proyectos/<id>/estilo.json`; debe ser del mismo proyecto) |
| `--candidatos-portada VIDEO` | sin plan: fotogramas más nítidos (varianza del laplaciano en la zona de la cara) y una hoja para elegir `portada_fondo.segundo` |
| `--n N` / `--hoja RUTA` | nº de candidatos (def. 8) / dónde guardar la hoja (def. carpeta temporal) |

**Re-render del mismo slug**: si en la carpeta de salida hay otra
`carrusel_<fecha>_<slug>/` sin aprobar, se borra tras un render correcto (no se
acumulan carpetas). Las aprobadas ya están en REVISADOS y no se tocan.

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
- Obligatorios: `tema`, `formula`, `pilar`, `fuente.tipo` (y `fuente.ruta` salvo
  en `tema`), `titulo` de cada slide, `texto` de las de valor, y `texto` o `puntos`
  en el cierre.
- **Se deducen** (si vienen, se validan): `n` y `rol` por la posición; `objetivo`
  si la fórmula solo admite uno; `fuente.credito` (clip/vídeo, si falta la clave)
  = `carruseles.credito` del `proyecto.json`; `slug` = nombre del archivo del plan
  (o el tema); `proyecto` = la carpeta del plan, `--proyecto` o el único proyecto;
  `tipo` = «carrusel». El `carrusel.json` de salida lleva todo ya completado.
- Fórmulas, objetivos, pilares y fórmula → objetivos: los da TheCopy
  (`copys.py campos --json --proyecto <id>`); la última respuesta se guarda en
  `.cache/campos_<id>.json` y, si TheCopy no responde, se usa esa caché o las
  listas de respaldo de `lib/carrusel_plan.py`.
- Rutas relativas: junto al plan, en TheHistoria o en PruebasIA.
- Opcionales: `portada_fondo` (imagen, o vídeo + `segundo`; `foco_y` 0–1 elige la
  franja vertical), `portada_texto`, `numero` en una slide de valor (otro número o
  `false`), `puntos` y `peticion` en el cierre.
- `**palabra**` = destacada en el color de acento (máx. una por slide). `\n` = salto.

### Validación

- **ERROR (no renderiza):** menos de 2 o más de 10 slides; roles fuera de orden;
  texto que no cabe ni al tamaño mínimo; obligatorios vacíos; `formula`,
  `objetivo`, `pilar`, `fuente.tipo` o `portada_texto` fuera de sus valores; `**`
  sin cerrar; emojis (si `identidad.voz.emojis_max` es 0); `portada_fondo` inexistente, **de
  internet, del banco común (sin `banco_comun`), de otro proyecto o fuera del
  material del proyecto**; `fuente.ruta` de otro proyecto. Plan, `--proyecto` o
  estilo de proyectos distintos, o `estilo.json` con `_rellenar` → código 2.
- **AVISO:** menos de 4 slides; longitudes por encima de las orientativas; más de
  una palabra destacada; minúscula al empezar o tras punto; mayúsculas sostenidas;
  falta «¿»/«¡»; primera persona; fórmula poco afín al objetivo; vídeo sin
  `credito`; cierre sin `peticion`.
- **Material del proyecto** (portada): `proyectos/<id>/`, `_Historico/<id>/`,
  `TheEditor/proyectos/<id>/`, `TheDescarga/descargas/<id>/`,
  `CEO_Sergete/{REVISADOS,HISTORIAS}/<id>/`, el banco común si la política es
  `banco_comun` y las carpetas de `carruseles.material_extra` del `proyecto.json`.
- **Auditoría de estilo (TheCopy):** una sola llamada para todo el carrusel,
  `TheCopy\.venv\Scripts\python.exe TheCopy\copys.py auditar --solo-estilo --json --proyecto <id> --stdin`
  (stdin: lista JSON con el texto de cada slide → lista de `{i, nivel, regla,
  fragmento, mensaje}`, `i` desde 0). Con `--proyecto` aplica también la identidad
  (palabras prohibidas, primera persona, emojis). Si la orden no admite `--stdin`,
  vuelve a una llamada por slide (`--texto`) y lo avisa. Solo informa; si TheCopy
  no está, sigue.
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

Al dar OK: `carruseles.py --aprobar <carpeta>` (mueve la carpeta entera a
`CEO_Sergete/REVISADOS/<id>/1. pte Publicar/`) y después `copy` con la orden que
imprime.

### Diseño (`proyectos/<id>/estilo.json` + identidad)

`estilo.json` = solo maquetación: fuentes de `fonts/` (`titulo`, `texto`,
`detalle`; `titulo` es también la de las historias), márgenes (lateral ≥ 100 px:
la cuadrícula del perfil recorta ~45 px por lado), rangos de tamaño `[max, min]`
del ajuste automático, calidad JPEG y longitudes orientativas. `proyecto` debe ser
el id del proyecto; con `_rellenar: true` (plantilla sin revisar) `carruseles.py`
da error e `historias.py` avisa. Los **colores** salen de `identidad.marca`, el
**handle** de `identidad.cuenta_ig` (sin cuenta, no se pinta) y `emojis_max` de
`identidad.voz`.

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
2. Rellena `reglas.md` y `proyecto.json` (historias sí/no, nº, filtros de frases,
   `carruseles.credito`); revisa la maquetación de `estilo.json` y quita
   `_rellenar`.
3. Pon los vídeos de las especiales en `especiales/`.
4. La identidad (cuenta, voz, marca) se define en `CEO_Sergete/proyectos.json`; la
   política de recursos y el b-roll propio, en TheEditor
   (`proyectos/<id>/proyecto.json` y `proyectos/<id>/recursos/broll/`).
5. Prueba: `historias.py --proyecto <id> --phrase "prueba"` (y borra la tanda).

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
    proyectos.py          # proyectos: regla --proyecto, configuración, identidad y política de recursos
    env.py                # credenciales
    supabase_phrases.py   # frases sin usar del proyecto / marcar usadas
    fondos.py             # fondo según la política (banco común, propio o liso)
    fondos_especiales.py  # fondos de las especiales (rotación sin repetir)
    embeddings.py         # modelo de embeddings (el mismo del catálogo)
    render.py             # fondo + texto -> MP4 9:16 (Pillow + ffmpeg), fuente y colores del proyecto
    aprobar.py            # al dar OK: nombre único y log jsonl
    texto.py              # capitalización de las historias
    carrusel_plan.py      # carruseles: esquema, validación y material del proyecto
    carrusel_render.py    # carruseles: maquetación, portada, JPG y vista
    carrusel_fuente.py    # carruseles: --fuente (texto compacto) y --listar
    thecopy.py            # contratos con TheCopy: campos y auditoría (proceso aparte)
  proyectos/
    _plantilla/           # base de los proyectos nuevos
    mongemalo/            # proyecto.json, estilo.json, reglas.md, especiales/, planes/
  fonts/                  # Montserrat (Bold + SemiBold)
  salidas/<id>/           # historias y carruseles pendientes + _aprobadas.log (gitignored)
  .cache/                 # última respuesta de `copys.py campos` (gitignored)
```

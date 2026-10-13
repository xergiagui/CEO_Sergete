# TheHistoria — Departamento de historias y carruseles de Instagram

Genera **historias de IG (MP4 vertical 1080×1920)**: un texto sobre un fondo de
vídeo. También genera **carruseles del feed (2–10 JPG 4:5, 1080×1350)**. Lo
dirige CEO_Sergete con el subagente `historia`. Detalle de opciones en
[`README.md`](README.md). **Este archivo manda** sobre las reglas de trabajo.

## Cuándo se usa
**Proceso independiente y a demanda**: solo cuando Sergio pide historias o
carruseles, o cuando el CEO detecta que faltan carruseles en la semana. Nunca se
lanza solo tras descargar o editar vídeos.

## Entorno
- Reutiliza el `.venv` de TheEditor, **no instales nada**:
  `..\TheEditor\.venv\Scripts\python.exe` (nunca `python3`, que en este equipo es
  el acceso directo de la Microsoft Store).
- Credenciales: `TheHistoria/.env` o, si no existe, `../CEO_Sergete/.env`.

## Tres vías

| Vía | Script | Texto | Fondos | Salida |
|---|---|---|---|---|
| **Normal** | `historias.py` | Frases de Supabase `viral_phrases` (`used_in_story=false`, por viralidad); se marcan como usadas al terminar | B-roll de `../TheEditor/superposiciones/` elegido por semántica (`match_broll`) o al azar | `salidas/<timestamp>/` + `manifest.json` |
| **Especiales** (promos, eventos) | `historias_especiales.py` | Lo da Sergio (`--texto`, repetible) | `BRells especiales/` (local, git-ignored) | `salidas/especiales_<timestamp>/` |
| **Carruseles** (feed) | `carruseles.py --plan <plan.json>` | Un `plan.json` que escribe el subagente desde un clip/vídeo, un artículo de TheTextos o un tema | Fondo liso de marca; portada con imagen o fotograma opcional | `salidas/carrusel_<AAAAMMDD-HHMM>_<slug>/` |

- Normal: `--n N`, `--categoria X`, `--min-virality N`, `--phrase "..."` (frase
  suelta sin tocar la BBDD), `--duracion S`, `--no-marcar`.
- Especiales: `--texto` (varios = un texto por variación), `--variaciones N`
  (def. 3, mismo texto con distinto fondo), `--duracion S` (def. 6),
  `--reserva-inferior F` (0–0,6; def. 0,25). El texto va en la banda superior y
  deja libre la franja de abajo para el botón de IG.
- Si no quedan frases sin usar o falta Supabase, dilo; para probar sin BBDD usa
  `--phrase`.

## Reglas (historias)
- Texto en minúsculas, pero **mayúscula en la primera letra y tras `.`, `?` y `!`**
  (`lib/texto.py::capitalizar_frase`, ya aplicado en el render).
- Fondos siempre a pantalla completa (mismo criterio que TheEditor).
- Las historias **no llevan copy ni hashtags** (TheCopy no interviene) y no
  entran en el calendario de publicación.

## Carruseles (tercera vía)

A diferencia de las historias, **los carruseles SÍ llevan copy y hashtags** (los
pone TheCopy al dar OK) y **SÍ entran en el calendario de publicación**.

### Flujo
1. **Tú (LLM) escribes el plan** en `carruseles/planes/<slug>.json` a partir de
   la fuente:
   - **clip o vídeo:** `..\_Historico\<video>\` o `..\TheEditor\transcripciones\<video>\`
     (`cortes.json` + `.srt`/`.txt`);
   - **artículo:** `..\TheTextos\textos\<fecha>_<slug>\articulo.md`;
   - **tema o notas** de Sergio.
   **No toques nada de `_Historico`**: solo se lee.
2. `carruseles.py --plan <plan.json> --solo-validar` hasta que no haya errores
   (y revisa los avisos y la auditoría).
3. `carruseles.py --plan <plan.json>` valida, audita, renderiza y hace el QC.
4. Mira `_vista.jpg` antes de entregar. El CEO lo revisa con Sergio.

### Reglas del contenido (al escribir el plan)
- **Fórmula según el objetivo:** `IG5_lista` (lista numerada) → guardados;
  `IG6_antes_despues` → guardados y seguidores; `IG7_mitos` → compartidos;
  `IG8_metodo` (método con nombre) → guardados.
- **Nº de slides:** 6–10 es lo típico (máximo 10, mínimo 2). **Nunca rellenes**:
  si la idea da para 5, son 5. Si la fuente trae más puntos de los que caben,
  fusiona los que sean la misma idea o elige los más fuertes, y cuenta en el
  gancho los que de verdad salen.
- **Slide 1 = promesa + bucle abierto** (p. ej. «casi nadie se atreve con el
  segundo»), nunca un título a secas. Unas 12 palabras como máximo entre
  `titulo` y `texto`.
- **Lo más fuerte en las slides 2–3**, no al final.
- **Una idea por slide**, legible en 2 s: título de ~8 palabras y texto de ~25.
- **Última slide (`cierre`):** resumen que merezca guardarse (mejor en `puntos`)
  + **una sola petición** en `peticion` según el objetivo (guárdalo / sígueme /
  link en la bio).
- **Repurposer:** conserva las afirmaciones y cifras de la fuente; cambia la
  forma, no el fondo. **Nada de cifras ni datos inventados.** De un vídeo, haz un
  carrusel con lo que aporta, no un resumen escena a escena.
- **Tono MongeMalo:** directo, en segunda persona (tú), español de España, **sin
  emojis**. Perfil independiente: **no hables en primera persona como si fueras
  Luis Monge**. Si la fuente es un vídeo de Luis, `fuente.credito` = «Ideas de
  Luis Monge» (se pinta en pequeño en la última slide).
- **Escritura:** sentence case con ortografía correcta (tildes, ñ, ¿?, ¡!),
  mayúscula al inicio y tras `.`, `?` y `!`, nombres propios en mayúscula. Nunca
  TODO EN MAYÚSCULAS. El texto se pinta **tal cual** (aquí no se aplica
  `capitalizar_frase`, que pasaría a minúsculas los nombres propios).
- **Palabra destacada:** `**así**` sale en dorado. Como mucho una por slide.
- Evita lo que el auditor de TheCopy marca: paralelismos negativos («no es X, es
  Y»), revelaciones («¿El resultado?»), anuncios de sinceridad, vocabulario de IA
  y cebos de interacción.

### Validación de `carruseles.py`
- **ERROR (no renderiza):** menos de 2 o más de 10 slides; la primera no es
  `gancho`, la última no es `cierre` o una intermedia no es `valor`; texto que no
  cabe ni al tamaño mínimo; campos obligatorios vacíos; `formula`, `objetivo`,
  `pilar` o `fuente.tipo` fuera de sus valores; `**` sin cerrar; emojis;
  `portada_fondo` inexistente.
- **AVISO:** menos de 4 slides; títulos/textos por encima de las longitudes
  orientativas; más de una palabra destacada; minúscula al empezar o tras punto;
  mayúsculas sostenidas; falta «¿»/«¡»; primera persona; fórmula poco afín al
  objetivo; vídeo sin `credito`; cierre sin `peticion`.
- **Auditoría de estilo (TheCopy):** `--auditar` (activa por defecto si TheCopy
  existe) llama, por slide, a
  `TheCopy\.venv\Scripts\python.exe TheCopy\copys.py auditar --solo-estilo --json --texto "<texto>"`.
  Solo avisa por slide; no bloquea. Si la orden no existe o falla, avisa y sigue.
  Los avisos de estilo se corrigen reescribiendo el plan.
- **QC de la salida:** cada JPG 1080×1350, RGB/sRGB, < 8 MB y numerados en orden;
  `carrusel.json` y `_vista.jpg` presentes.

### Diseño (configurable en `carruseles/estilo.json`)
- Fondo `#14171f`, texto blanco, acentos en dorado `#f59e0b` (número, barra y
  palabra destacada). Montserrat Bold (títulos y números) y SemiBold (texto).
- Margen lateral 110 px (≥ 100): nada importante en los ~45 px de cada lado, que
  la cuadrícula del perfil recorta a 3:4.
- Slide 1: título grande centrado; `portada_fondo` opcional (imagen, o vídeo +
  `segundo`, con `foco_y` 0–1 para el encuadre vertical) oscurecido al 60 %;
  «desliza →» en dorado abajo a la derecha.
- Valor: número grande dorado (`01`, `02`… o `numero` en la slide; `false` lo
  oculta), título, barra y texto; contador «n/N». Todas las slides de valor
  comparten tamaño de letra y altura para que nada salte al deslizar.
- `handle` (arroba) **vacío** hasta que Sergio lo dé; si está vacío no se pinta.

### Contrato de la salida (lo lee TheCopy: no lo cambies)
```
salidas\carrusel_<AAAAMMDD-HHMM>_<slug>\
  01.jpg … NN.jpg     1080×1350, JPEG calidad ~92, sRGB, < 8 MB, en orden
  carrusel.json       plan + `creado` (ISO)
  _vista.jpg          hoja de contacto (solo para revisar)
```
`carrusel.json` = `tipo` («carrusel»), `proyecto`, `slug`, `tema`, `formula`,
`objetivo`, `pilar`, `fuente {tipo, ruta, credito}`, `slides [{n, rol, titulo,
texto, …}]`, `creado`, más los extras opcionales del plan (`portada_fondo`, y en
las slides `numero`, `puntos`, `peticion`). Los textos conservan el marcado
`**…**` de la palabra destacada.

## Al dar OK a unas historias
1. **Mover** (no copiar) todos los MP4 de las tandas aprobadas de `salidas/` a
   `C:\Users\ico858\Desktop\PruebasIA\CEO_Sergete\HISTORIAS\1. Pte publicar\`
   (aplanados; los nombres no colisionan).
2. **Borrar** esas carpetas de tanda en `salidas/` (con su `manifest.json`),
   conservando `salidas/.gitkeep`.

## Al dar OK a un carrusel
1. El CEO **mueve la carpeta entera** `salidas\carrusel_<…>_<slug>\` (JPG,
   `carrusel.json` y `_vista.jpg`) a
   `C:\Users\ico858\Desktop\PruebasIA\CEO_Sergete\REVISADOS\1. pte Publicar\`.
2. El CEO lanza **`copy`** (TheCopy) sobre esa carpeta: caption y hashtags, y
   entra en el calendario.
3. El plan se queda en `carruseles/planes/` (en git) por si hay que rehacerlo.

En `salidas/` solo debe quedar lo que está en curso o pendiente de revisar.

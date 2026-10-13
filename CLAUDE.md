# TheCopy — Departamento de copys, hashtags y calendario

Escribe el copy y los hashtags de cada pieza aprobada (**Reel** = MP4 o
**carrusel** = carpeta de slides de TheHistoria), registra **pieza ↔ copy ↔
hashtags** (Excel por proyecto + `.txt` listo para pegar) y le pone **fecha y hora
de publicación**. Lo dirige CEO_Sergete con el subagente `copy`. Órdenes y detalle
en [`README.md`](README.md).

## Entorno
- `.venv\Scripts\python.exe` (solo `openpyxl`). Nunca `python3` (acceso directo de la Store).
- El script es **`copys.py`**, no `copy.py` (chocaría con el módulo `copy`).

## Proyectos (varios e independientes)
- **Proyecto** = cuenta o cliente; id en minúsculas y sin espacios. Índice común (solo
  lectura): `CEO_Sergete/proyectos.json`. **Todo lo específico vive en `proyectos/<id>/`**
  (`proyecto.json`, `ofertas.json`, `hashtags.json`, `banco_copys.json`): es la fuente de
  verdad, léelo antes de escribir y, si algo choca con este archivo, manda el proyecto.
  Común a todos: `referencias/auditoria_copy.md` y `referencias/calendario.md`.
- **Cada orden, un proyecto:** `--proyecto <id>`; sin él se usa el único que haya (sin
  contar `_plantilla`); con varios, error con la lista. **Nunca mezclar:** registro,
  tandas (`tandas/<id>/`), calendario y `.txt` son siempre del proyecto, y el script se
  niega a leer o escribir en carpetas, registros o tandas de otro.
- **Carpetas** (en `proyecto.json`, relativas a PruebasIA y con `<id>`):
  `CEO_Sergete/REVISADOS/<id>/1. pte Publicar` y `…/2. Publicados`,
  `CEO_Sergete/HISTORIAS/<id>/1. Pte publicar`; contexto de los clips en
  `TheEditor/proyectos/<id>/transcripciones/` y `_Historico/<id>/` (la ruta antigua
  `TheEditor/transcripciones/` solo se mira en la transición). Las carpetas del CEO
  **las crea el CEO**: si faltan, se avisa.
- **Tipos:** `largos` (contexto = `cortes.json` + `.srt`) y `clipping` (vídeos ya cortados:
  contexto = `textos/<clip>.txt` + `ganchos.json`).
- **Proyecto nuevo:** `copys.py nuevo-proyecto <id>` (nombre, tipo y prefijo salen del
  índice del CEO si está allí). Dice qué falta: tono, ofertas, hashtags, CTA, plataformas
  y calendario. **Lo que falte se pregunta a Sergio; no se inventa.**

## Reglas (decisiones de Sergio)
- **Cuándo:** al dar OK a unas piezas (cuando pasan a la carpeta *pendiente* del
  proyecto) y a demanda. Nunca al renderizar.
- **Solo pieza ↔ copy ↔ hashtags en el registro**, sin columnas del vídeo largo. El
  calendario solo consulta el origen (`cortes.json` del clip o `fuente` de
  `carrusel.json`) para no poner seguidas dos piezas del mismo vídeo.
- **Copys** a medida de cada pieza (el gancho sale de lo que se dice en el clip), distintos
  entre sí, sin hashtags dentro y sin cifras inventadas. Para cambiar un copy, solo el de la
  pieza pedida (`registrar --reemplazar`).
- **Hashtags:** los fijos los pone el script; se escriben solo los temáticos del banco por
  tamaño del proyecto, en el nº y tamaños de su `proyecto.json`, y **rotados** (`copys.py
  hashtags`). Ej.: MongeMalo/Instagram = `#grupoalfa` fijo + 2–4 temáticos.
- **Campos propios obligatorios** (`campos_extra`: oferta, objetivo, pilar…). En los
  carruseles vienen de `carrusel.json`. `promocion` solo si la pieza va sobre todo de vender.
- **Carruseles** (contrato con TheHistoria): carpeta con `01.jpg … NN.jpg` +
  `carrusel.json`; solo en plataformas que los admitan (`formatos`). El caption repite el
  gancho de la slide 1 en los primeros 125 caracteres, va corto y mantiene el CTA. El `.txt`
  va dentro de la carpeta. Mismo contador de IDs que los Reels.
- **Auditoría antes de registrar** (`copys.py auditar --entrada <tanda>`): los errores
  bloquean; los avisos de estilo se corrigen **reescribiendo** y solo se dejan si la frase
  es literal del clip o de las slides. `registrar` pasa la misma auditoría.
- **Contrato con TheHistoria:** `copys.py auditar --solo-estilo --json --texto "<texto>"
  [--proyecto <id>]` → lista JSON ASCII `{nivel, regla, fragmento, mensaje}`, sale con 0 si
  no hay errores; sin proyecto claro audita con 0 emojis. **No lo cambies** sin avisar al CEO.
- **Calendario** (si `calendario.activo`): después de registrar, `copys.py calendario
  planificar`. Es estable: no recoloca lo que ya tiene fecha y lo puesto a mano no se mueve
  nunca. Su última línea (`FALTAN …`) va al CEO. Valores provisionales hasta que Sergio los
  ajuste con las estadísticas. En la plantilla viene desactivado.
- **Plataformas:** no actives ninguna (`"activa": true`) sin que Sergio lo pida y confirme
  sus fijos y su CTA.
- Las **historias de IG no llevan copy** (el calendario solo las reparte por día).
- **El Excel tiene que estar cerrado** para escribir; si está abierto, avisa y no
  reintentes en bucle.

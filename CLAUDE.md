# CEO_Sergete — Centro de mando

Eres el **CEO**. El usuario (Sergio) **solo interactúa con este proyecto**. Tu
trabajo no es hacer todo tú mismo, sino **entender la orden y delegarla al
departamento correcto**, coordinar el resultado y darle una respuesta clara.

Cada departamento es una **carpeta hermana** dentro de
`C:\Users\ico858\Desktop\PruebasIA\` con su propio repo git. CEO_Sergete NO
contiene su código: lo **invoca por ruta** a través de un **subagente**
especializado (uno por departamento, en `.claude/agents/`).

El registro maestro está en [`departamentos.json`](departamentos.json). Es la
fuente de verdad: rutas, repos, disparadores y cómo se ejecuta cada uno.

**Cada departamento tiene su propio `CLAUDE.md`** con sus reglas de trabajo (las
de edición de Sergio están en `TheEditor/CLAUDE.md`, por ejemplo). Su subagente lo
lee siempre al empezar, porque los subagentes **no ven la memoria** de esta
conversación. Por eso, cuando Sergio dé una **regla nueva o una corrección que
deba repetirse**, apúntala en el `CLAUDE.md` del departamento (y haz commit), no
solo en la memoria.

---

## Departamentos actuales

| Departamento | Carpeta | Subagente | Para qué |
|---|---|---|---|
| **Descarga** | `../TheDescarga` | `descarga` | Bajar vídeos/audio (YouTube, IG, TikTok…) con yt-dlp local |
| **Editor** | `../TheEditor` | `editor` | Pipeline viral: link → avatar IA → b-roll + subs + música → vídeo final |
| **Landing** | `../TheLanding` | `landing` | Web de afiliación (Next.js + Supabase + Vercel) |
| **Historia** | `../TheHistoria` | `historia` | Historias de IG (9:16): frase de `viral_phrases` + fondo de b-roll · **Carruseles** de IG (4:5, 2–10 slides) |
| **Copy** | `../TheCopy` | `copy` | Copy + hashtags de cada pieza (Reel o carrusel), por proyecto; registro pieza ↔ copy ↔ hashtags (Excel + `.txt`) · **Calendario de publicación** |
| **Textos** | `../TheTextos` | `textos` | Textos largos para blog (>500 palabras) optimizados para SEO y para buscadores de IA (GEO/AEO) |

---

## Cómo diriges (protocolo)

1. **Enruta.** Lee la petición y decide el departamento por sus *disparadores*
   (ver `departamentos.json`). Si encaja con uno, **delega en su subagente** con
   la herramienta `Task`/Agent (`subagent_type` = el `id` del departamento).
2. **Da contexto completo al subagente.** El subagente arranca sin memoria de
   esta conversación: pásale la orden concreta, el link/URL, rutas, y lo que el
   usuario espera de vuelta.
3. **Varias tareas independientes → subagentes en paralelo** (un solo mensaje
   con varias llamadas Agent).
4. **Cadena entre departamentos.** Si una orden cruza departamentos (p. ej.
   «descarga este reel y móntame adaptaciones»), orquesta la secuencia:
   `descarga` → pasa la ruta del MP4 → `editor`.
5. **Reporta al usuario** en claro: qué se hizo, dónde quedó el archivo (ruta
   exacta), y qué falta. No vuelques logs crudos; resume.
   - **Varios vídeos → avisa por vídeo:** en tandas de varios vídeos (descarga,
     edición o retoques), da el parte de cada uno **en cuanto termina**, sin
     esperar a que estén todos. Sergio revisa sobre la marcha.
6. **Si la orden no encaja con ningún departamento**, dilo y propón crear uno
   nuevo (ver «Añadir un departamento»).
7. **Correcciones: solo lo pedido.** Si Sergio corrige un clip (o unos pocos),
   pide al departamento que aplique el cambio **solo a esos**, sin convertirlo en
   comportamiento global que altere lo que ya estaba bien.

### Reglas
- **No dupliques código** de los departamentos aquí. CEO_Sergete solo coordina.
- **Rutas absolutas** al invocar herramientas fuera de este proyecto (los
  subagentes ya las conocen). Estás en Windows: PowerShell + Bash disponibles.
- **Acciones externas o difíciles de revertir** (git push, deploy, borrar,
  enviar): confirma con el usuario salvo que ya lo haya autorizado.
- **Editor — tres vías** (detalle y reglas de edición en `TheEditor/CLAUDE.md`):
  - **Montaje viral completo (interactivo, con popups y gates)**: NO uses el
    subagente. Invoca la **skill `Editor_Sergio` desde el hilo principal**
    (herramienta `Skill`). Está enlazada por junction en
    `.claude/skills/Editor_Sergio` (fuente de verdad en TheEditor), así que está
    disponible aquí y sus popups funcionan como si abrieras TheEditor. Sus assets
    (`superposiciones/`, `musicas/`) se resuelven por la raíz de TheEditor
    (`PROJECT_ROOT`), no por el cwd — funciona sin importar desde dónde se lance.
  - **Tareas scriptables/batch** (transcribir, cortar clips, correr una fase con
    todos los parámetros dados, sin popups): delega en el subagente `editor`, que
    ejecuta con el `.venv` de TheEditor.
  - **Clips ya cortados → reels** (carpetas tipo `Desktop/Clip/Largo N
    Extractos`): subagente `editor` con `procesar_batch_clip.py` y el modo de
    encuadre de cada carpeta, en tres pasos (`--solo-transcribir` → el editor
    escribe `ganchos.json` → render). Nunca dos batch a la vez (comparten carpeta
    de trabajo). Las ediciones normales (`editar_clips.py`) sí pueden ir en paralelo.
  - **Gancho de texto en pantalla** (vías 1 y 2): los primeros 2,5 s llevan el
    `gancho_texto` del corte. La vía 3 (avatar) no lo lleva.
- **Historia — proceso independiente:** TheHistoria genera historias de IG.
  **NO se encadena** con descarga/edición: se lanza **solo cuando el usuario pide
  historias**. Delega en el subagente `historia` (usa el `.venv` de TheEditor; no
  instala nada). Dos vías:
  - **Normal:** frases de `viral_phrases` + fondo de `TheEditor/superposiciones/`.
  - **Especiales** (promos/eventos): texto que da Sergio + fondos de
    `TheHistoria/BRells especiales/`, con la franja inferior libre para el botón
    de IG.
- **Carruseles — tercera vía de TheHistoria, con reglas propias:** post de feed
  de 2–10 imágenes 4:5 (el formato que más guardados genera). A diferencia de las
  historias, **SÍ llevan copy** y **SÍ entran en el calendario**. Subagente
  `historia`: escribe el plan (fórmula lista/antes-después/mitos/método, objetivo,
  pilar) desde un **clip/vídeo** (`_Historico/` o `TheEditor/transcripciones/`),
  un **artículo de TheTextos** o un **tema** de Sergio, y renderiza con
  `carruseles.py` → `TheHistoria/salidas/carrusel_<fecha>_<slug>/`. Se lanzan:
  - **a demanda** («hazme un carrusel de…», «pasa este artículo a carrusel»);
  - **cuando el calendario marca huecos de carruseles** (ver «Calendario»).
  Sergio los revisa siempre antes del OK (enséñale el `_vista.jpg`).
- **Copy — al dar OK y a demanda:** TheCopy escribe el copy y los hashtags de
  cada pieza (Reel o carrusel) y los registra (Excel por proyecto en
  `TheCopy/proyectos/<id>/registro_<id>.xlsx` + `.txt` junto al MP4 o dentro de
  la carpeta del carrusel), con su **objetivo** y **pilar**. Se lanza
  **automáticamente al dar OK** (ver «Al dar OK») y cuando Sergio pida copys o
  cambios de copy. Delega en el subagente `copy`. Cada **proyecto** (hoy solo
  MongeMalo) tiene sus reglas en `TheCopy/proyectos/<id>/`; si hay varios y no
  está claro de cuál es la pieza, pregunta. Las **historias de IG no llevan copy**.
- **Calendario — después de cada registro y a demanda:** TheCopy
  (`copys.py calendario`) da fecha y hora a todo lo pendiente (ver «Calendario
  de publicación»).
- **Textos — a demanda, con revisión independiente:** TheTextos escribe textos
  largos de blog (>500 palabras) optimizados para SEO y GEO/AEO. Copys, captions
  y textos cortos **no** van aquí (eso es `copy`). Flujo:
  1. Delega en el subagente `textos` (tema/keyword, tipo de texto, público, blog
     de destino y lo que haya dicho Sergio). Hay **dos tipos de texto aún
     PENDIENTES** de especificar: si `textos` devuelve preguntas, pásaselas a
     Sergio en vez de inventar.
  2. Lanza el agente global **`blog-reviewer`** sobre su `articulo.md` (puntos de
     nivel sitio = N/A). Si sale `BLOCKING: true` o hay algún P0, devuelve la
     revisión a `textos` para corregir (máx. 2 vueltas).
  3. Reporta: ruta de `TheTextos/textos/<fecha>_<slug>/`, título, keyword, nº de
     palabras, resultados SEO/GEO/revisión y avisos (`[VERIFICAR]`).

---

## Flujo descarga → editor (encadenado principal)

Los vídeos que baja **TheDescarga** se **tratan después en TheEditor**. Handoff:

```
TheDescarga/descargas/<video>.mp4   →   TheEditor/input/<video>.mp4   →   tratamiento
```

`TheEditor/input/` es el **buzón** del editor. El editor tiene DOS tratamientos
según lo que se quiera:

1. **Vídeo local largo → clips verticales editados** (lo típico para un vídeo ya
   descargado): `transcribir.py` (→ .txt/.srt/.json) → **el editor genera
   `cortes.json`** eligiendo los momentos con gancho desde la transcripción →
   `clips.py` (recorte 9:16 + quita silencios) → `editar_clips.py` (b-roll +
   música + subs, Fase C). **Este es el flujo para los vídeos de TheDescarga**, y
   es **100% automático**: los scripts son genéricos y leen `cortes.json`; no se
   edita código por vídeo.
2. **Adaptaciones con avatar IA** (pipeline viral, skill `Editor_Sergio`): parte
   del **LINK**, no del archivo — se descarga solo. Si el usuario quiere avatar a
   partir de un reel, pásale la **URL** a la skill (no hace falta TheDescarga).

**Orquestación de «descarga esto y trátalo/edítalo»:**
1. Delega en el subagente `descarga` con la URL → devuelve la ruta del MP4 en
   `TheDescarga/descargas/`.
2. Delega en el subagente `editor` con esa ruta → copia el MP4 a
   `TheEditor/input/`, transcribe, **genera `cortes.json`** (elige los momentos
   con las reglas de Sergio) y ejecuta `clips.py` → `editar_clips.py`.
3. Reporta al usuario las rutas de salida (`transcripciones/<video>/…`,
   `…/clips/`, `…/finales/`).

> El único paso con criterio es **elegir los momentos de corte**, y lo hace el
> subagente `editor` (LLM) leyendo la transcripción y escribiendo `cortes.json`
> (esquema en `TheEditor/cortes.example.json`). Los scripts `clips.py` /
> `editar_clips.py` son genéricos: no se edita código por vídeo. Si el usuario
> quiere revisar/ajustar los cortes antes de renderizar, que edite `cortes.json`.

### Receta: «una sola orden» (URL → clips editados)

Cuando el usuario diga algo como *«descarga esto y sácame N clips»* (o solo pegue
una URL pidiendo clips), **ejecuta toda la cadena sin volver a preguntar** salvo
que falte información esencial:

1. **`descarga`** (subagente) baja la URL → ruta del MP4 en `TheDescarga/descargas/`.
2. **`editor`** (subagente), en un solo encargo, hace:
   `input/` ← copia · `transcribir.py` · **genera `cortes.json`** · `clips.py` ·
   `editar_clips.py` → `finales/`.
3. Reporta al usuario: nº de clips, rutas de `finales/` y un resumen de los
   momentos elegidos (para que pueda pedir ajustes).

**Nº de clips por defecto:** si el usuario no lo dice, elige según duración del
vídeo — orientación: **1 clip por cada ~3 min**, mínimo 3 y máximo 6. Si el
usuario da un número, respétalo.

**Antes de renderizar, punto de control ligero:** si el vídeo es largo o el
usuario parece querer control, ofrécele ver el `cortes.json` propuesto antes de
lanzar `editar_clips.py` (que es lo más costoso). Si pidió que sea directo, tira
del tirón.

### Al dar OK a unos clips (→ publicación con copy)

Cuando Sergio aprueba clips:
1. **Mueve** (no copies) los MP4 aprobados a `REVISADOS/1. pte Publicar/`.
2. **`copy`** (subagente): copy + hashtags de esos clips → fila en el Excel del
   proyecto + `<clip>.txt` al lado de cada MP4, y a continuación
   **`copys.py calendario planificar`**. Pásale los nombres de los clips (y el
   proyecto si hay más de uno).
3. **Archiva** sus carpetas de transcripción en `PruebasIA/_Historico/` (TheCopy
   también busca el contexto allí, así que el orden 2↔3 no rompe nada).
4. Reporta por clip: **ID** (`MM-0001`…), oferta, el texto final y la **fecha y
   hora previstas**, para que Sergio pueda pedir cambios («cámbiame el copy del
   03» → `copy`, solo ese clip).
5. Si el calendario marca **huecos de carruseles** en las semanas planificadas,
   aplica «Huecos del calendario» (abajo).

Cuando Sergio pase piezas a `REVISADOS/2. Publicados`, `copy` con
`copys.py sincronizar` las marca como *Publicado* (con fecha) en el Excel.

### Al dar OK a unos carruseles

1. **Mueve** (no copies) la carpeta **entera** de cada carrusel aprobado de
   `TheHistoria/salidas/carrusel_…/` a `REVISADOS/1. pte Publicar/`.
2. **`copy`** (subagente): caption + hashtags (fila *Carrusel* en el Excel +
   `<carpeta>.txt` dentro de la carpeta) y después `calendario planificar`.
3. Reporta por carrusel: ID, texto final y fecha y hora previstas. Para
   publicarlo, Sergio sube las imágenes `01.jpg…NN.jpg` en orden y pega el `.txt`.

### Al dar OK a unas historias

1. **Mueve** (no copies) todos los MP4 de las tandas aprobadas de
   `TheHistoria/salidas/<tanda>/` a `HISTORIAS/1. Pte publicar/` (aplanados).
2. **Borra** esas carpetas de tanda en `salidas/` (conserva `salidas/.gitkeep`).
3. Las historias **no llevan copy**: no lances `copy`. El calendario las reparte
   solo (2–4 al día) la próxima vez que se planifique.

---

## Calendario de publicación

Lo lleva TheCopy (`copys.py calendario`, reglas en
`TheCopy/referencias/calendario.md` y `proyectos/<id>/proyecto.json` →
`calendario`). Sergio publica a mano; el calendario le dice **qué y cuándo**.

- **Planificar:** tras cada registro (ver «Al dar OK») o cuando Sergio diga
  «planifica la semana»: `copy` con `calendario planificar` → fechas en el Excel +
  `TheCopy/proyectos/<id>/calendario/<AAAA>-W<ss>.md`. Es estable: no recoloca lo
  ya planificado ni lo que Sergio haya fechado a mano.
- **«¿Qué publico hoy?»:** `copy` con `calendario hoy` → pieza, hora, ruta, texto
  listo para pegar e historias del día. Respóndele con eso, sin logs.
- **Huecos del calendario:** si una semana planificada tiene menos carruseles del
  mínimo, lanza `historia` para hacer los que falten (máx. 2 por semana) a partir
  del material de los clips aprobados más recientes (`_Historico/`), con temas
  distintos a los ya publicados. Se los enseñas a Sergio para el OK; no entran en
  el calendario hasta que los aprueba. Si faltan **Reels** o **historias**, solo
  avísale (salen de vídeos o frases nuevas).
- **Atrasados:** si `calendario ver` marca piezas ATRASADAS (fecha pasada y sin
  publicar), avísale y ofrécele replanificarlas (`--replanificar-atrasados`).
- Los valores por defecto (5 posts/semana, días y franjas horarias) son
  **provisionales**: se ajustan con las estadísticas de la cuenta cuando Sergio
  las pase.

---

## Entorno y convenciones

- **Windows.** PowerShell 5.1 y Git Bash disponibles. **`python3` no funciona**
  (es el acceso directo de la Microsoft Store): usa `py`, `python` o el `.venv`
  del departamento.
- **Entornos Python:** TheEditor `.venv` (también lo usa TheHistoria) · TheCopy
  `.venv` · TheTextos `.venv`. TheDescarga no usa Python (binarios en `tools/`).
  TheLanding es Node (`npm`).
- **Carpetas de publicación** (aquí, fuera de git): `REVISADOS/1. pte Publicar`,
  `REVISADOS/2. Publicados`, `HISTORIAS/1. Pte publicar`, `HISTORIAS/2. Publicadas`.
  Archivo de transcripciones aprobadas: `PruebasIA/_Historico/`.
- **Skills globales** (`~/.claude/skills/`): `clean-user-facing-text` se aplica
  **siempre** a textos de más de 500 palabras (nunca a copys, hooks o captions;
  regla en `~/.claude/CLAUDE.md`). La suite `blog-*` de claude-blog y `ai-seo` las
  usa TheTextos, y los agentes `blog-*` (`blog-reviewer`, etc.) están disponibles
  aquí. `Editor_Sergio` está enlazada por junction en `.claude/skills/`.
- **Git:** cada departamento tiene su repo en `github.com/xergiagui/<Nombre>` y
  CEO_Sergete el suyo. Los commits terminan con la línea `Co-Authored-By` de
  Claude. **Push a TheLanding = deploy en Vercel**: confírmalo antes. Nunca se
  suben `.env`, `.venv/`, logs ni vídeos.

---

## Supabase (compartido)

Un único proyecto Supabase reutilizado (`akuykrrqmivrcjzcsksj.supabase.co`,
originalmente de *mis-finanzas*) sirve a TheLanding (leads/events/messages) y al
catálogo de b-roll de TheEditor (`broll_assets` + RPC `match_broll`).

- Credenciales en [`.env`](.env) (`SUPABASE_URL`, `SUPABASE_ANON_KEY`) — **no**
  se sube a git.
- Tabla opcional [`supabase/ceo_tasks.sql`](supabase/ceo_tasks.sql) para dejar un
  historial de órdenes que CEO_Sergete despacha (auditoría ligera). Úsala vía
  REST con la anon key si el usuario quiere registro; no es obligatoria.

---

## Añadir un departamento (funcionalidad nueva)

Cuando Sergio cree una subcarpeta nueva (funcionalidad concreta):

1. Crea la carpeta hermana en `PruebasIA/` con su repo git (rama `main`, remoto
   `github.com/xergiagui/<Nombre>`) y, si usa Python, su propio `.venv` +
   `requirements.txt`.
2. Escribe su **`CLAUDE.md`** (qué hace, entorno, reglas, flujo, salida) y su
   `README.md`.
3. Añade su entrada en [`departamentos.json`](departamentos.json)
   (`id`, `nombre`, `ruta`, `repo`, `disparadores`, `entrypoint`).
4. Crea su subagente en `.claude/agents/<id>.md` (copia la estructura de uno
   existente: describe **cuándo** usarlo, **cómo** ejecutar el proyecto y que lo
   primero sea leer su `CLAUDE.md`).
5. Añade la ruta a `additionalDirectories` en
   [`.claude/settings.local.json`](.claude/settings.local.json).
6. Añádelo a la tabla de arriba y a `README.md` (árbol, tabla y lista de repos).

Así el nuevo módulo queda «dirigible» desde aquí sin tocar el resto.

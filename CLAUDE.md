# TheCopy — Departamento de copys, hashtags y calendario

Escribe el copy y los hashtags de cada pieza aprobada (**Reel** = MP4 o
**carrusel** = carpeta de slides de TheHistoria), registra la relación
**pieza ↔ copy ↔ hashtags** (Excel por proyecto + `.txt` listo para pegar) y le
pone **fecha y hora de publicación** con el calendario. Lo dirige CEO_Sergete
con el subagente `copy`. Funcionamiento y órdenes en [`README.md`](README.md).

## Entorno
- Entorno propio: `.venv\Scripts\python.exe` (solo `openpyxl`). Nunca `python3`
  (en este equipo es el acceso directo de la Microsoft Store).
- El script es **`copys.py`**, no `copy.py` (chocaría con el módulo `copy`).

## Reglas (decisiones de Sergio)
- **Cuándo:** al dar OK a unas piezas (cuando pasan a
  `CEO_Sergete/REVISADOS/1. pte Publicar`) y a demanda. Nunca al renderizar.
- **Fuente de verdad por proyecto:** `proyectos/<id>/` (`proyecto.json`,
  `ofertas.json`, `hashtags.json`, `banco_copys.json`). Léelos antes de escribir;
  si algo choca con ellos, mandan ellos. Común a todos: `referencias/auditoria_copy.md`
  y `referencias/calendario.md`.
- **Solo pieza ↔ copy ↔ hashtags en el registro.** No se añaden columnas ni búsquedas
  del vídeo largo de origen. El calendario solo lo **consulta** (cortes.json del clip o
  `fuente` de carrusel.json) para no poner seguidas dos piezas del mismo vídeo.
- **Carruseles** (contrato con TheHistoria): carpeta con `01.jpg … NN.jpg` + `carrusel.json`
  (+ `_vista.jpg`, que se ignora). `pendientes` los detecta en la carpeta pendiente; el
  nombre de la pieza es el de la carpeta. **Solo Instagram** admite carrusel
  (`plataformas.<p>.formatos`). El caption **repite el gancho de la slide 1 en los primeros
  125 caracteres**, va corto y mantiene el **CTA a la bio** (manda siempre); si el objetivo
  es guardados, puede invitar a guardarlo. Mismas reglas de hashtags y auditoría que un Reel.
  Los textos de las slides pueden traer `**marcado**`: se quita al usarlos. El `.txt` va
  **dentro de la carpeta** (`<carpeta>.txt`) y el enlace del Excel apunta a la carpeta.
  Mismo contador de IDs que los Reels.
- **Objetivo y pilar, obligatorios en cada pieza** (`campos_extra`): objetivo =
  guardados / compartidos / comentarios / seguidores; pilar = educativo / historia /
  interaccion / promocion. En los carruseles vienen de `carrusel.json`; en los Reels los
  elige el subagente. `promocion` solo si la pieza va **sobre todo** de vender un producto
  (nombrar la oferta en el caption no la convierte en promoción).
- **MongeMalo · hashtags (Instagram):** solo `#grupoalfa` es **fijo** (lo pone el
  script); `#ventas`, `#dinero` y `#exitopersonal` pasan al banco rotativo. **3–5 en
  total contando el fijo** → se escriben 2–4 temáticos: **2–3 de nicho** (`#grupoalfa`
  ya cuenta como uno), **1–2 medios** y **como mucho 1 amplio**, del banco por tamaño de
  `hashtags.json` y acordes al tema. **Rotar** por tema: no repetir el conjunto de
  temáticos de otra pieza de la tanda ni de los 5 últimos registrados (`copys.py
  hashtags`). Los tamaños son **estimados**: Sergio los verifica en el buscador de IG.
  TikTok/YouTube conservan sus fijos de siempre (inactivas). CTA siempre a la bio.
- **Auditoría antes de registrar** (`copys.py auditar --entrada <tanda>`; checklist en
  `referencias/auditoria_copy.md`, adaptado de `sergebulaev/instagram-skills`, MIT):
  gancho (1.ª frase/línea) ≤ 125 caracteres en Instagram, sin cebos de interacción ni
  cierres vacíos (errores: bloquean) y sin paralelismos negativos, revelaciones,
  anuncios de sinceridad, vocabulario de IA ni emojis (avisos de estilo). **Los avisos
  de estilo se corrigen reescribiendo antes de registrar; solo se dejan si la frase es
  literal del clip (o de las slides del carrusel).** `registrar` pasa la misma auditoría.
- **Auditoría de solo estilo para TheHistoria:** `copys.py auditar --solo-estilo --json
  --texto "<texto>"` audita el texto de las slides: solo estilo y emojis, más cebos y
  cierres vacíos (sin gancho de 125, CTA, hashtags ni longitud). Saca una lista JSON de
  `{nivel, regla, fragmento, mensaje}` (ASCII puro) y sale con 0 si no hay errores.
  **No cambies ese contrato** sin avisar al CEO: TheHistoria depende de él.
- **Calendario (activo en MongeMalo):** **después de registrar se ejecuta
  `copys.py calendario planificar`**, que pone fecha y hora a lo registrado, pendiente y
  sin fecha (desde mañana), reparte las historias de `HISTORIAS/1. Pte publicar` (2–4 al
  día, sin moverlas) y deja `proyectos/<id>/calendario/<AAAA>-W<ss>.md`. Es **estable**:
  no recoloca lo que ya tiene fecha; las fechas que Sergio ponga a mano **no se mueven
  nunca** (ni con `--replanificar-atrasados`). Su última línea (`FALTAN …`, o `--json`)
  dice cuántos Reels y carruseles faltan por semana: pásasela al CEO.
  «¿Qué publico hoy?» → `copys.py calendario hoy`. Resumen y atrasados →
  `copys.py calendario ver`. Los valores (5 posts/semana, franjas 13:30/20:30, mínimos)
  son **provisionales** hasta que Sergio los ajuste con las estadísticas de la cuenta.
- **Plataformas:** hoy solo Instagram activa. TikTok y YouTube (Shorts) están
  preparadas con `"activa": false`, solo para Reels, y fijos/CTA provisionales: **no las
  actives sin que Sergio lo pida y confirme** sus fijos y su CTA.
- **Independiente por proyecto:** vendrán más proyectos además de MongeMalo
  (`copys.py nuevo-proyecto <id>`; el calendario de la plantilla viene desactivado). Lo
  que falte de un proyecto nuevo, se pregunta.
- Copys a medida de cada pieza, distintos entre sí, sin hashtags dentro del copy
  y sin cifras inventadas. Para cambiar un copy, solo el de la pieza pedida.
- Las **historias de IG no llevan copy** (el calendario solo las reparte por día).
- **El Excel tiene que estar cerrado** para escribir; si está abierto, avisa y no
  reintentes en bucle.

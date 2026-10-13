# TheCopy — Departamento de copys y hashtags

Escribe el copy y los hashtags de cada clip terminado y registra la relación
**clip ↔ copy ↔ hashtags** (Excel por proyecto + `<clip>.txt` junto al MP4). Lo
dirige CEO_Sergete con el subagente `copy`. Funcionamiento y órdenes en
[`README.md`](README.md).

## Entorno
- Entorno propio: `.venv\Scripts\python.exe` (solo `openpyxl`). Nunca `python3`
  (en este equipo es el acceso directo de la Microsoft Store).
- El script es **`copys.py`**, no `copy.py` (chocaría con el módulo `copy`).

## Reglas (decisiones de Sergio)
- **Cuándo:** al dar OK a unos clips (cuando pasan a
  `CEO_Sergete/REVISADOS/1. pte Publicar`) y a demanda. Nunca al renderizar.
- **Fuente de verdad por proyecto:** `proyectos/<id>/` (`proyecto.json`,
  `ofertas.json`, `hashtags.json`, `banco_copys.json`). Léelos antes de escribir;
  si algo choca con ellos, mandan ellos. Común a todos: `referencias/auditoria_copy.md`.
- **Solo clip ↔ copy ↔ hashtags.** No hace falta relacionar el vídeo largo de
  origen (no añadir columnas ni búsquedas de vídeo origen).
- **MongeMalo · hashtags (Instagram):** solo `#grupoalfa` es **fijo** (lo pone el
  script); `#ventas`, `#dinero` y `#exitopersonal` pasan al banco rotativo. **3–5 en
  total contando el fijo** → se escriben 2–4 temáticos: **2–3 de nicho** (`#grupoalfa`
  ya cuenta como uno), **1–2 medios** y **como mucho 1 amplio**, del banco por tamaño de
  `hashtags.json` y acordes al tema. **Rotar** por tema: no repetir el conjunto de
  temáticos de otro clip de la tanda ni de los 5 últimos registrados (`copys.py
  hashtags`). Los tamaños son **estimados**: Sergio los verifica en el buscador de IG.
  TikTok/YouTube conservan sus fijos de siempre (inactivas). CTA siempre a la bio.
- **Auditoría antes de registrar** (`copys.py auditar --entrada <tanda>`; checklist en
  `referencias/auditoria_copy.md`, adaptado de `sergebulaev/instagram-skills`, MIT):
  gancho (1.ª frase/línea) ≤ 125 caracteres en Instagram, sin cebos de interacción ni
  cierres vacíos (errores: bloquean) y sin paralelismos negativos, revelaciones,
  anuncios de sinceridad, vocabulario de IA ni emojis (avisos de estilo). **Los avisos
  de estilo se corrigen reescribiendo antes de registrar; solo se dejan si la frase es
  literal del clip.** `registrar` pasa la misma auditoría.
- **Plataformas:** hoy solo Instagram activa. TikTok y YouTube (Shorts) están
  preparadas con `"activa": false` y fijos/CTA provisionales: **no las actives sin
  que Sergio lo pida y confirme** sus fijos y su CTA.
- **Independiente por proyecto:** vendrán más proyectos además de MongeMalo
  (`copys.py nuevo-proyecto <id>`). Lo que falte de un proyecto nuevo, se pregunta.
- Copys a medida de cada clip, distintos entre sí, sin hashtags dentro del copy
  y sin cifras inventadas. Para cambiar un copy, solo el del clip pedido.
- Las **historias de IG no llevan copy**.
- **El Excel tiene que estar cerrado** para escribir; si está abierto, avisa y no
  reintentes en bucle.

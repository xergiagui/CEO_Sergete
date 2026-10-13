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
  si algo choca con ellos, mandan ellos.
- **Solo clip ↔ copy ↔ hashtags.** No hace falta relacionar el vídeo largo de
  origen (no añadir columnas ni búsquedas de vídeo origen).
- **MongeMalo:** 4 hashtags fijos (`#ventas #dinero #grupoalfa #exitopersonal`,
  los pone el script) + **1–2 temáticos** según el clip. CTA siempre a la bio.
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

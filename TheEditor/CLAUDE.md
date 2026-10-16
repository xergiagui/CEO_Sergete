# TheEditor — Departamento de edición

Reels 9:16 (b-roll + música + subtítulos) para varios proyectos. Aquí solo está
lo que decides tú. Lo que ya hace el código (encuadre, b-roll, subtítulos,
audio, zona segura, exportación, bancos, vía 3) está en
[`REGLAS_CODIGO.md`](REGLAS_CODIGO.md): no hace falta leerlo para trabajar.

## Entorno
- Python: `.venv\Scripts\python.exe` de TheEditor (nunca el global ni `python3`), con el cwd en TheEditor.
- Todas las órdenes llevan `--proyecto <id>`. Empieza con `proyecto.py ver <id>`: política de recursos resuelta, recursos en disco y su `reglas.md`, en una sola llamada.
- Salida corta: si no es una terminal, cada script da una línea por clip y un `RESUMEN`; el detalle va al log de `proyectos/<id>/logs/` (búscalo ahí solo si algo falla).
- Nunca mezcles material de proyectos. Regla nueva de Sergio: si es de un proyecto, a su `reglas.md`; si vale para todos, aquí.

## Vía 1 · Vídeo largo → clips
1. `transcribir.py --proyecto <id> "<video>.mp4"` (salta lo ya transcrito o aprobado; `--forzar`).
2. Lee **solo** `transcripciones/<video>/<video>.cortes.txt` (duración, nº de clips sugerido y una línea por frase con sus segundos) y escribe `cortes.json` (esquema en `cortes.example.json`): `nombre` (`[a-z0-9_]+`), `inicio`, `fin`, `titulo`, `gancho_texto`, `frase_viral`, `tipologia_musica` (opcional) y `hook_query` (en inglés, solo si el proyecto lleva gancho visual). Nº de clips: el sugerido (1 cada 3 min, mín. 3, máx. 6) salvo que Sergio diga otro.
3. `clips.py --proyecto <id> "<video>" --validar` hasta que salga `OK`.
4. `clips.py --proyecto <id> "<video>"` → `editar_clips.py --proyecto <id> "<video>"` → QC.

## Vía 2 · Clips ya cortados (y todo el clipping)
`procesar_batch_clip.py --proyecto <id> "<CARPETA>" [MODO]`: cada subcarpeta de `input/` es un lote; los clips sueltos de `input/` son el lote `_sueltos`.
1. `… --solo-transcribir`.
2. Lee **solo** `transcripciones/<CARPETA>/_para_ganchos.md` y rellena la plantilla `ganchos.json` (`{"<clip>.mp4": "¿…?"}`; vacío = sin gancho).
3. `… --validar-ganchos` hasta `OK`; después, sin flags (render) y QC.
- `MODO`: `right|left|center|auto|auto-right|follow|<fracción>`; si no se da, el de `proyecto.json → encuadre`. Carpeta nueva: mira el plano y añádela al mapa.
- Si faltan b-roll o música propios, el batch para: díselo a Sergio, o usa `--sin-musica`/`--sin-broll` si lo autoriza.
- Nunca dos batch a la vez (comparten `whisper/_edit_batch`).

## Modo tráiler (`proyecto.json → "modo": "trailer"`; hoy, `wicker`)
Clips montados solo con material oficial (un tráiler 9:16 + su póster), con `trailer.py`:
gancho y CTA literales, subtítulos de `dialogos.json`, portada `<clip>.portada.jpg`; sin
b-roll, sin música y sin recorte de silencios. Manda su `reglas.md` (las reglas de gancho
y de silencios de aquí no aplican).
1. Lee `…cortes.txt`, `dialogos.json` y `reglas.md`; escribe `cortes.json` (esquema en la cabecera de `trailer.py`).
2. `clips.py --proyecto <id> "<fuente>" --validar` hasta `OK` (no hay corte aparte).
3. `editar_clips.py --proyecto <id> "<fuente>" [--solo <clip>]` → QC.

## Vía 3 · Avatar IA
Skill `Editor_Sergio` desde el hilo principal del CEO (popups y gates). Si te la piden, devuélvele el control.

## Recorte y hook (vía 1)
- Empieza tarde y termina pronto: entra una frase más tarde y sal justo tras el remate; fuera saludos, muletillas y cierres.
- El hook se cumple: «Después de ver esto, la audiencia entenderá que ___».
- Nada de teaser + repetir la misma frase después.
- De 15 a 90 s por clip, sin solapes.

## Gancho de texto
El primer fotograma lleva un texto que abre un bucle, y el clip lo cumple. (En modo tráiler el gancho es el literal de su tipo y no se aplica lo de abajo.)
- Como mucho 2 líneas (~45 caracteres, máx. 50), con tildes, ñ y `¿`/`¡`; sin emojis.
- Abre el bucle sin dar la respuesta y se cumple dentro del clip: nada de cifras ni promesas que el clip no dé.
- No repite literal la primera frase.
- Si no hay uno bueno, déjalo vacío: el clip sale sin gancho. Nunca uno mecánico (título, primera frase, nombre de archivo).
- La validación comprueba la forma; el sentido es cosa tuya.

## Correcciones: solo lo pedido
Solo el clip pedido, con `--solo <clip>` y `--sin-frases`; el resto no se toca, y la semilla del clip repite su música y su b-roll.
- Gancho (vía 1): `cortes.json` → `editar_clips.py … --solo <clip> --sin-frases`.
- Gancho (vía 2): `ganchos.json` → `procesar_batch_clip.py … "<CARPETA>" --solo "<clip>" --sin-frases`.
- Tramo (vía 1): `inicio`/`fin` → `clips.py … --solo <clip>` → `editar_clips.py … --solo <clip> --sin-frases`.
- Después, QC otra vez.

## Silencios
Global: 6 % / 0,15 s (`proyecto.json → silencios`); nunca lo cambies. Excepción: un proyecto con `silencios.quitar: false` no recorta silencios (solo si Sergio lo aprueba para ese proyecto; hoy, `wicker`). Si un clip queda atropellado, reprocesa solo ese con 3 % / 0,3 s (no se guarda en `proyecto.json`):
- Vía 1: `clips.py … --solo <clip> --umbral 3% --margen 0.3s` → `editar_clips.py … --solo <clip> --sin-frases`.
- Vía 2: `procesar_batch_clip.py … "<CARPETA>" --solo "<clip>" --umbral 3% --margen 0.3s --sin-frases`.

## Subtítulos de la fuente
Si el vídeo largo trae subtítulos o rótulos incrustados, el render de la vía 1 los tapa solo (desenfoque mientras están en pantalla) cuando el proyecto lo tiene activo en `proyecto.json → subs_fuente` (`proyecto.py ver` lo enseña; hoy, `mongemalo`). La línea del clip dice `subs fuente tapados N`. Si en un clip se escapa alguno o el desenfoque molesta, corrige solo ese clip (`--solo <clip> --sin-frases`, y `--sin-tapar-subs` para quitarlo).

## QC
`qc.py --proyecto <id> "<video|carpeta>"`: una línea por clip (`OK`/`REVISAR`/`FALLA`) y `finales/_qc.jpg`. Mira la hoja: gancho en el primer fotograma, cola limpia y sin restos de superposiciones ni texto de la fuente bajo nuestros subtítulos. Nada con `FALLA` se entrega.

## Al dar OK
Por script, nunca a mano:
`proyecto.py aprobar <id> --video "<video|carpeta>" [--clips a.mp4,b.mp4] [--cerrar]`.
Mueve los finales (y su `<clip>.portada.jpg`, si la hay) a `../CEO_Sergete/REELS/<id>/1. pte Publicar/` y, si `finales/` queda vacío, archiva el vídeo y su fuente en `../_Historico/<id>/<v>/` (salvo `aprobar.archivar: false`: solo con `--cerrar`). Después va TheCopy (`copys.py pendientes --proyecto <id>`).

# TheCopy — copys, hashtags y calendario

Escribe el copy y los hashtags de cada pieza aprobada (**Reel** = MP4; **carrusel** = carpeta de
slides de TheHistoria), registra pieza ↔ copy ↔ hashtags (Excel por proyecto + `.txt` listo para
pegar) y le pone fecha y hora de publicación. Lo dirige CEO_Sergete con el subagente `copy`.
Órdenes y detalle: [`README.md`](README.md).

## Entorno
- `.venv\Scripts\python.exe copys.py <orden>` (solo `openpyxl`). Nunca `python3`. El script es
  `copys.py`, no `copy.py` (chocaría con el módulo `copy`).

## Flujo del agente
1. `copys.py brief --proyecto <id>`: identidad, reglas, ofertas, plataformas y hashtags. Es lo único
   que hay que leer, junto con la tanda.
2. `copys.py pendientes --proyecto <id> [--clip …]`: tanda con el contexto mínimo y `tema`,
   `extra.oferta` y `hashtags_temas` sugeridos. Se rellena objetivo, pilar y copy; `hashtags: []`.
3. `copys.py registrar --entrada <tanda> --simular`: corrige los errores y reescribe los avisos de estilo.
4. `copys.py registrar --entrada <tanda> --planificar`: Excel + `.txt` + calendario. Al CEO: ID,
   oferta, texto final y la última línea `FALTAN`.

`banco_copys.json`, solo si un clip trae `aviso`; `referencias/`, solo si un aviso no se entiende.

## Fuentes únicas (nada se copia en dos sitios)
- **Identidad** (cuenta, landing, afiliado, voz: persona, tono, idioma y `emojis_max`, palabras
  prohibidas, marca): `CEO_Sergete/proyectos.json` → `identidad`. La mantiene el CEO; sin ella,
  error de configuración.
- **Lo de TheCopy**, en `proyectos/<id>/`: `proyecto.json` (`reglas_copy`, `campos_extra` con su
  `ayuda`, plataformas y formatos con su guía y límites, cifras de hashtags en
  `plataformas.<p>.hashtags`, carpetas, calendario), `ofertas.json` (ofertas y CTA genérico),
  `hashtags.json` (fijos y banco por tamaño) y `banco_copys.json` (reserva).
- **Estilo**: lo aplica el auditor (`lib/auditoria.py`; checklist en `referencias/auditoria_copy.md`).
- **Fórmula → objetivo** de los carruseles: `config.FORMULA_OBJETIVOS` (`copys.py campos`).

## Reglas (decisiones de Sergio)
- **Cuándo:** al dar OK (las piezas pasan a la carpeta *pendiente* del proyecto) y a demanda.
- **Un proyecto por orden** (`--proyecto <id>`): registro, tandas, `.txt` y calendario nunca se mezclan.
- **Registro:** solo pieza ↔ copy ↔ hashtags, sin columnas del vídeo largo.
- **Copys** a medida, distintos entre sí, sin hashtags dentro y sin cifras inventadas. Para
  cambiar uno, solo el pedido (`registrar --reemplazar`).
- **Hashtags:** los fijos los pone el script; los temáticos los elige `registrar` desde
  `hashtags_temas` (a mano, solo para forzar alguno).
- **Auditoría:** los errores bloquean; los avisos de estilo se corrigen reescribiendo y solo se
  dejan si la frase es literal del clip (`--estricto` no registra si queda alguno).
- **Calendario:** estable; lo puesto a mano no se mueve; lo que está en *publicados* nunca sale
  como ATRASADO ni se replanifica. La línea `FALTAN` va al CEO.
- **Plataformas:** no actives ninguna sin que Sergio lo pida y confirme sus fijos y su CTA.
- Las **historias de IG** no llevan copy (el calendario solo las reparte por día).
- **Excel abierto:** avisa al CEO y no reintentes en bucle.
- **Proyecto nuevo:** `copys.py nuevo-proyecto <id>`; lo que falte se pregunta a Sergio, no se inventa.

## Opciones por proyecto (genéricas, opt-in; mongemalo no las usa)
- `tipos_clip` (proyecto.json): caption y hashtags FIJOS por tipo, según el nombre del clip
  (`patron`, p. ej. `^([a-e])_`). Los hashtags salen siempre los del tipo, literales y en orden;
  la 1.ª vez de cada tipo el caption debe ser el literal (si no, error). `pendientes` añade a
  cada pieza `tipo_clip` (literal, hashtags, `primera_vez`). Sin banco temático ni rotación.
- `plataformas.<p>.copy_reglas` (una_linea, debe_incluir, keyword, sin_url, prohibido[regex+motivo]),
  `permitir_cebos` (regex de cebos permitidos a propósito) y `checklist_publicacion` (bloque aparte
  en el `.txt`, con `{clip}` y `{ubicacion}`): ver `lib/auditoria.py` y `lib/txt.py`.
- `calendario.inicio` / `calendario.fin` (AAAA-MM-DD): ventana de la campaña; no se planifica fuera.
- Proyecto sin ofertas: quita `oferta` de `campos_extra`. Sin CTA: `cta_obligatorio: false`.

## Contratos con TheHistoria (no cambiar sin avisar al CEO)
- `copys.py auditar --solo-estilo --json --proyecto <id> --texto "a" [--texto "b" …]` o `… --stdin`
  (lista JSON de cadenas) → lista JSON ASCII de `{i, nivel, regla, fragmento, mensaje}`; sale con 0
  si no hay errores. Con `--proyecto` aplica la identidad; sin él, como siempre.
- `copys.py campos --json --proyecto <id>` → `{formulas, objetivos, pilares, formula_objetivos}`.
- Carpeta de carrusel: `01.jpg … NN.jpg` + `carrusel.json`; el `.txt` lo escribe TheCopy dentro.

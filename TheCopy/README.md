# TheCopy

Departamento de **CEO_Sergete** que escribe el **copy** y los **hashtags** de
cada pieza aprobada, deja registrada la relación **pieza ↔ copy ↔ hashtags** y le
pone **fecha y hora de publicación**.

- **Piezas:** **Reels** (un MP4) y **carruseles** (una carpeta de slides que genera
  TheHistoria, con su `carrusel.json`).
- **Un `.txt` listo para pegar** por pieza: junto al MP4 con el mismo nombre
  (`01_x.mp4` → `01_x.txt`) o, en un carrusel, **dentro de su carpeta** (`<carpeta>.txt`).
  Viaja con la pieza al moverla.
- **Un Excel por proyecto** (`proyectos/<id>/registro_<id>.xlsx`, fuera de git): una fila por
  pieza y plataforma, con ID, enlace al MP4 o a la carpeta, formato, fechas previstas, tema,
  campos propios (oferta, objetivo, pilar…), copy, hashtags, texto para pegar, estado y fecha
  de publicación.
- **Calendario:** fecha y hora para lo aprobado con una mezcla equilibrada, las historias del
  día y un `.md` por semana. «¿Qué publico hoy?» → `copys.py calendario hoy`.

> Se lanza **al dar OK** a unas piezas (cuando pasan a la carpeta *pendiente* del proyecto) o
> **a demanda**. Las historias de IG no llevan copy ni hashtags: el calendario solo las reparte.

## Flujo del agente

```
copys.py brief --proyecto <id>          → lo único que hay que leer (≈1,5k tokens)
copys.py pendientes --proyecto <id>     → tandas/<id>/<id>_<fecha>.json (contexto mínimo + sugerencias)
  (el subagente `copy` rellena objetivo, pilar y copy; revisa tema, oferta y hashtags_temas)
copys.py registrar --entrada <tanda> --simular      → errores y avisos; se corrige reescribiendo
copys.py registrar --entrada <tanda> --planificar   → Excel + .txt + calendario (línea FALTAN)
```

`banco_copys.json` solo hace falta si un clip trae `aviso` (sin contexto) y `referencias/` solo
si un aviso no se entiende.

## Fuentes únicas

Cada dato vive en un solo sitio; el brief, la auditoría y la validación lo leen de ahí.

| Qué | Dónde |
|---|---|
| **Identidad**: cuenta, landing, afiliado, posicionamiento, voz (`persona`, `tono`, `idioma`, `emojis_max`), `no_suplantar`, `transparencia_afiliacion`, `palabras_prohibidas`, `marca` | `CEO_Sergete/proyectos.json` → `proyectos[].identidad` (la mantiene el CEO; sin ella, error de configuración) |
| Reglas del copy | `proyecto.json` → `reglas_copy` (el estilo, en una línea: lo aplica el auditor) |
| Qué significa cada objetivo y pilar | `proyecto.json` → `campos_extra[].ayuda` |
| Guía y límites por plataforma y formato (caption de carrusel incluido) | `proyecto.json` → `plataformas.<p>` y `plataformas.<p>.formatos.<formato>` |
| **Cifras de hashtags** (temáticos, total con los fijos, nicho, amplios, rotación) | `proyecto.json` → `plataformas.<p>.hashtags` |
| Hashtags fijos y banco por tamaño | `hashtags.json` |
| Ofertas, cuándo usarlas y el CTA genérico | `ofertas.json` |
| Copys de reserva | `banco_copys.json` |
| Fórmula de carrusel → objetivo | `config.FORMULA_OBJETIVOS` (`copys.py campos --json`) |
| Reglas de estilo | `lib/auditoria.py` (checklist para personas: `referencias/auditoria_copy.md`) |

`emojis_max` sale de `identidad.voz.emojis_max` salvo que una plataforma (o un formato) lo
sobrescriba.

## Proyectos independientes

Un **proyecto** es una cuenta o cliente de contenido (id en minúsculas y sin espacios). Lo propio
de TheCopy vive en `proyectos/<id>/`:

| Archivo | Qué lleva |
|---|---|
| `proyecto.json` | **tipo** (`largos` / `clipping`), reglas del copy, **carpetas**, campos propios (oferta, objetivo, pilar), **plataformas** (activas o preparadas) con límites, CTA, guía, cifras de hashtags y `formatos`, y el **calendario** (con su carpeta de historias) |
| `ofertas.json` | productos a los que puede apuntar un copy (con sus `temas`, que sirven para sugerir la oferta) + el genérico con su CTA |
| `hashtags.json` | **fijos** por plataforma (se añaden solos) + banco **temático por tamaño** (`nicho` < 50k publicaciones, `medio` 50k–500k, `amplio` > 500k; **estimados**) + `tamano_fijos` |
| `banco_copys.json` | copys de reserva para piezas sin contexto (auditados con `auditar --banco`) |
| `fuentes/` | documentos originales (p. ej. el PDF de copys del cliente) |
| `registro_<id>.xlsx` | el registro (lo crea `registrar`; no va a git) |
| `calendario/` | lo genera `calendario planificar`: un `<AAAA>-W<ss>.md` por semana (no va a git) |

**Elegir el proyecto:** todas las órdenes aceptan `--proyecto <id>`. Sin él se usa el único
proyecto que haya (sin contar `_plantilla`); con varios, error con la lista. `registrar` y
`auditar --entrada` toman el proyecto de la tanda (si además das `--proyecto`, tiene que coincidir).

**Nunca se mezclan proyectos:** registro, tandas (`tandas/<id>/`), calendario y `.txt` son
siempre los del proyecto. El script se niega a usar como `--carpeta`, `--pendiente`,
`--publicado`, `--carpeta-historias`, `--excel` o `--salida` algo que sea de otro proyecto, y
`registrar` no escribe un `.txt` en las carpetas de otro. Un `proyecto.json` cuyo `id` no sea el
de su carpeta, o que reutilice las carpetas de otro proyecto, da error. También da error una
plataforma cuyas cifras de hashtags no cuadren con sus fijos (p. ej. `total_max` menor que
`tematicos_min` + nº de fijos).

**Carpetas** (en `proyecto.json`, relativas a `PruebasIA/`; `<id>` se sustituye por el id):

| Clave | Por defecto | Quién la crea |
|---|---|---|
| `carpetas.pendiente` | `CEO_Sergete/REELS/<id>/1. pte Publicar` | el CEO |
| `carpetas.publicado` | `CEO_Sergete/REELS/<id>/2. Publicados` | el CEO |
| `calendario.historias.carpeta` | `CEO_Sergete/HISTORIAS/<id>/1. Pte publicar` | el CEO |
| `carpetas.contexto` | `TheEditor/proyectos/<id>/transcripciones`, `_Historico/<id>` | TheEditor / el CEO al dar OK |

Si una carpeta del CEO no existe, TheCopy **avisa** (no la crea).

**Tipos de proyecto:** `largos` (vídeos largos que TheEditor corta en clips: contexto =
`cortes.json` + `.srt`) y `clipping` (vídeos ya cortados que entrega el proyecto: contexto =
`<carpeta>/textos/<clip>.txt` + el gancho de `ganchos.json`). Los dos se buscan siempre.

### Proyecto nuevo

```powershell
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> [--nombre "Nombre"] [--prefijo XX] [--tipo largos|clipping]
```

1. Copia `proyectos/_plantilla/` a `proyectos/<id>/` con el id, nombre, prefijo de IDs, tipo y
   nombre del registro. Si el id está en `CEO_Sergete/proyectos.json`, nombre, tipo, prefijo y
   descripción salen de allí (si no, `--nombre` es obligatorio). No deja repetir un prefijo.
2. Comprueba las carpetas (las del CEO no las crea: si faltan, avisa).
3. Lista **qué falta**: la **identidad** en el índice del CEO, descripción y `como_reconocerlo`,
   `reglas_copy`, ofertas y CTA genérico, hashtags fijos y banco, CTA, guía y cifras de cada
   plataforma activa y el calendario (desactivado en la plantilla). `copys.py proyectos` lo
   vuelve a enseñar.

Lo que no se sepa se pregunta a Sergio. **Plataformas:** cada proyecto define `instagram`,
`tiktok` y `youtube` (Shorts, con título); activar una = `"activa": true` (y revisar sus fijos en
`hashtags.json`), solo cuando Sergio lo pida. A una pieza ya registrada se le añade una plataforma
nueva con el mismo ID con `pendientes --plataformas <p>`; si la pieza ya está publicada, apunta a
su carpeta: `pendientes --plataformas <p> --carpeta "CEO_Sergete\REELS\<id>\2. Publicados"`.

## Carruseles (contrato con TheHistoria)

```
<carpeta_carrusel>\        al dar OK, el CEO la mueve entera a la carpeta pendiente del proyecto
  01.jpg … NN.jpg          1080×1350, en orden
  carrusel.json            tipo, proyecto, slug, tema, formula (IG5_lista | IG6_antes_despues |
                           IG7_mitos | IG8_metodo), objetivo, pilar, fuente {tipo, ruta, credito},
                           slides [{n, rol, titulo, texto, (puntos, peticion)}], creado
  _vista.jpg               hoja de contacto (se ignora)
  <carpeta>.txt            lo escribe TheCopy al registrar
```

`pendientes` toma de `carrusel.json` el tema, el objetivo y el pilar (ya rellenos en la tanda) y,
como contexto, la fórmula, la fuente (tipo y crédito) y el texto de las slides sin el
`**marcado**`. `contexto.gancho_slide1` es lo que el caption tiene que repetir. Al auditar, el
texto de las slides cuenta como literal de la pieza.

## La tanda

`pendientes` crea un bloque por pieza sin copy (por plataforma; un carrusel, solo en las que lo
admiten):

- **Contexto mínimo.** Reel de `largos`: `titulo`, `frase_viral`, `gancho_texto`, `angle`,
  `category` y la `transcripcion` del tramo (≤ `MAX_CHARS_TRANSCRIPCION`, 1000). Reel de
  `clipping`: `gancho_texto` y `transcripcion`. Sin rutas, tiempos ni justificaciones.
- **Sugerencias:** `tema` = título del corte (o tema del carrusel); `extra.oferta` = la oferta
  cuyos `temas` encajan claramente con la categoría y lo que se dice (vacía si no hay una clara);
  `hashtags_temas` = temas del banco que encajan. Se revisan; no se dan por buenas.
- **Hashtags automáticos:** con `"hashtags": []` y `hashtags_temas` (en la pieza o en el bloque de
  la plataforma), `registrar` elige un conjunto válido y rotado: cumple las cuotas, no repite los
  últimos `rotacion_ultimos` ni otro de la misma tanda, usa lo que menos ha salido y mezcla
  tamaños y temas. Si se escriben menos de los mínimos, los escritos se respetan y se completa
  el resto. Los elegidos quedan en la tanda al registrar.
- **Avisos de `pendientes`:** pieza sin contexto; nombre de clipping en varias carpetas; **dos
  carpetas de contexto con el mismo `.srt`** (mismo hash: una está mal copiada); y **nombre de
  pieza ya registrado con otra ruta** (se trataría como la misma pieza: renómbrala si es otra).

## Validación y auditoría

`registrar` (y `--simular`) valida todo antes de escribir nada; si hay un error, no se registra
nada. Solo imprime errores, avisos y un resumen corto por pieza (caracteres y hashtags finales);
`--verbose` enseña el texto entero.

| | Errores (bloquean) | Avisos (no bloquean) |
|---|---|---|
| Datos | tema y campos propios válidos, título si la plataforma lo pide (sin palabras prohibidas), la plataforma admite el formato | pieza no encontrada, fuera de las carpetas del proyecto, plataforma inactiva |
| Copy | sin CTA, hashtags dentro del copy, longitud máxima, copy repetido | longitud fuera de la recomendada, el caption de un carrusel no repite el gancho de la slide 1 |
| Auditoría (`lib/auditoria.py`) | gancho > `gancho_max`, cebo de interacción, cierre vacío, **palabra prohibida** de la identidad (sin tildes ni mayúsculas) | **de estilo:** paralelismo negativo, revelación, anuncio de sinceridad, ≥ 2 expresiones de IA en un párrafo, emojis > `emojis_max`, **primera persona del singular** (si la identidad tiene `voz.persona`; no cuenta lo que va entre comillas) |
| Hashtags | mal formados o repetidos, temáticos fuera de `tematicos_min/max`, total con fijos fuera de `total_min/total_max`, más amplios que `amplios_max`, `hashtags_temas` desconocido | menos de `nicho_min` de nicho, etiqueta sin tamaño o fuera del banco, conjunto repetido en la tanda o entre los `rotacion_ultimos` últimos |

Los avisos de estilo se corrigen **reescribiendo** antes de registrar; solo se dejan si la frase
es literal del clip (`frase_viral` / `transcripcion`) o de las slides, y entonces la auditoría la
marca como «literal del clip» y no avisa. `registrar --estricto` no escribe si queda alguno.

## Calendario

`calendario planificar` pone fecha y hora a lo registrado, pendiente y sin fecha, en los huecos
libres desde mañana; reparte las historias; escribe el Excel y `calendario/<AAAA>-W<ss>.md`. Es
estable (no recoloca lo que ya tiene fecha; lo manual no se mueve nunca) y termina con la línea
`FALTAN <semana> reels=… carruseles=… cualquiera=… huecos=… historias=…`. Reglas y valores: el
`calendario` de cada `proyecto.json`; explicación en
[`referencias/calendario.md`](referencias/calendario.md).

**Publicados:** todas las órdenes `calendario` empiezan con la misma detección por carpeta que
`sincronizar` (lo que está en *publicados* → Publicado). En `hoy` y `ver` es solo en memoria; en
`planificar` se guarda. Por eso lo publicado **nunca sale como ATRASADO** y
`--replanificar-atrasados` **nunca lo mueve**.

## Columnas del registro

| Columna | Qué es | ¿Se edita a mano? |
|---|---|---|
| ID | `XX-0001`… (una pieza = un ID, en todas sus plataformas) | no |
| Clip | nombre del MP4 o de la carpeta del carrusel, con enlace | no |
| Formato | Reel / Carrusel | sí, se respeta |
| Plataforma | Instagram, TikTok, YouTube | no |
| Estado | Pendiente / Publicado / Descartado / No encontrado | sí, se respeta |
| Fecha prevista · Hora prevista | las pone `calendario planificar` | **sí: lo manual no se mueve nunca** |
| Tema | resumen corto | sí |
| Campos propios (p. ej. Oferta · Objetivo · Pilar) | los de `campos_extra` | sí (cuentan para el calendario) |
| Título · Copy · Hashtags · Texto para pegar · Nº caracteres | lo registrado | mejor con `registrar --reemplazar` |
| Fecha alta · Fecha publicación | alta y día en que se vio publicado | sí, se respeta |
| Notas · Ruta | notas libres · ruta del MP4 o la carpeta | Notas, sí |

Las columnas se localizan por su cabecera: a un Excel antiguo se le **añaden al final** las que
le falten (con sus desplegables) sin tocar lo escrito. Hojas extra: **Historias** (plan por día;
lo que cambies a mano se respeta) y **_calendario** (oculta: las fechas que puso el planificador,
para distinguir las manuales).

## Órdenes

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheCopy
.venv\Scripts\python.exe copys.py brief [--proyecto <id>]
.venv\Scripts\python.exe copys.py pendientes [--proyecto <id>] [--clip 01_x | --clip carpeta_carrusel] [--plataformas instagram,tiktok] [--carpeta <ruta>] [--incluir-registrados]
.venv\Scripts\python.exe copys.py registrar --entrada tandas\<id>\<id>_....json [--simular] [--planificar] [--estricto] [--verbose] [--reemplazar]
.venv\Scripts\python.exe copys.py calendario planificar [--proyecto <id>] [--semanas N] [--desde AAAA-MM-DD] [--simular] [--replanificar-atrasados] [--json]
.venv\Scripts\python.exe copys.py calendario hoy [--proyecto <id>] [--fecha AAAA-MM-DD]
.venv\Scripts\python.exe copys.py calendario ver [--proyecto <id>] [--semana AAAA-Www]
.venv\Scripts\python.exe copys.py sincronizar [--proyecto <id>]
.venv\Scripts\python.exe copys.py ver [--proyecto <id>] [XX-0003 | nombre_pieza]
.venv\Scripts\python.exe copys.py banco [--proyecto <id>] [--oferta <id_oferta>]
.venv\Scripts\python.exe copys.py auditar (--entrada <tanda> | --texto "..." [--texto "..."] | --stdin | --banco) [--proyecto <id>] [--plataforma instagram] [--solo-estilo] [--json]
.venv\Scripts\python.exe copys.py hashtags [--proyecto <id>] [--plataforma instagram] [--tema <tema>]
.venv\Scripts\python.exe copys.py campos [--proyecto <id>] [--json]
.venv\Scripts\python.exe copys.py proyectos
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> [--nombre "Nombre"] [--prefijo XX] [--tipo largos|clipping]
```

| Orden | Qué hace |
|---|---|
| `brief` | Todo lo necesario para escribir: identidad (voz, tono, persona, CTA, landing), reglas, ofertas (`id: cuando_usarla`), guía y límites de las plataformas activas por formato, cifras de hashtags, banco por tema y tamaño y los últimos conjuntos usados. |
| `pendientes` | Crea la tanda con las piezas de la carpeta *pendiente* (o `--carpeta`) que aún no tienen copy. `--incluir-registrados` para cambiar un copy; `--plataformas` para añadir una plataforma a piezas ya registradas. |
| `registrar` | Valida la tanda y escribe Excel + `.txt`. `--simular` solo valida; `--planificar` encadena `calendario planificar` y termina con `FALTAN`; `--estricto` no escribe si quedan avisos de estilo; `--verbose` enseña los textos; `--reemplazar` cambia el copy de una pieza ya registrada (conserva ID, Estado, fechas y Notas). |
| `calendario planificar` | Ver «Calendario». `--json` da lo mismo en JSON. |
| `calendario hoy` | Qué toca ese día: pieza, hora, ruta, el `.txt` listo para pegar, las historias y el recordatorio de compartir el post. También los atrasados. |
| `calendario ver` | Resumen del plan por semanas (balance, huecos, historias); marca lo **ATRASADO**. |
| `sincronizar` | Detección por carpeta guardada en el Excel: en *Publicados* → `Publicado` + fecha; desaparecido → `No encontrado`. Actualiza el enlace, rehace el `.txt` si falta y rellena el Formato vacío. Nunca rebaja un estado puesto a mano. |
| `ver` | Resumen del registro o el texto de una pieza/ID. |
| `banco` | Copys de reserva y cuántas veces se han usado. |
| `auditar` | Solo informe (no reescribe): una tanda (`--entrada`, con la excepción de frases literales), textos sueltos (`--texto`, repetible, o `--stdin`) o el banco (`--banco`). `--solo-estilo`: estilo, emojis, cebos y cierres vacíos (sin gancho, CTA, hashtags ni longitud). `--json`: lista ASCII `[{i, nivel, regla, fragmento, mensaje}]`. Sale con 1 si hay errores. |
| `hashtags` | Cifras de la plataforma, banco por tamaño y los últimos conjuntos usados. |
| `campos` | Fórmulas de carrusel, objetivos, pilares y fórmula → objetivo. |
| `proyectos` | Lista los proyectos: tipo, prefijo, plataformas activas, calendario, carpetas que faltan y lo que queda por rellenar. |
| `nuevo-proyecto` | Crea `proyectos/<id>/` desde la plantilla y dice qué falta. |

Para pruebas: `--excel <ruta>` en `pendientes/registrar/sincronizar/ver/banco/hashtags/brief/calendario`
usa otro registro (los `.md` del calendario van a `<carpeta del Excel>/calendario/`);
`pendientes --carpeta` y `--salida`, `--pendiente/--publicado` (en `registrar`, `sincronizar` y
`calendario`) y `--carpeta-historias` (en `registrar` y `calendario`) usan otras carpetas. Ninguna
puede ser de otro proyecto.

**El Excel tiene que estar cerrado** cuando el script escribe; si está abierto, avisa y no
escribe nada.

## Contratos con TheHistoria

No se cambian sin avisar al CEO.

- **Auditoría de estilo:**
  `copys.py auditar --solo-estilo --json --proyecto <id> --texto "a" [--texto "b" …]` o
  `copys.py auditar --solo-estilo --json --proyecto <id> --stdin` (stdin = lista JSON de cadenas).
  Salida: lista JSON (ASCII) de `{i, nivel, regla, fragmento, mensaje}`, con `i` = índice del
  texto. Con `--proyecto` aplica también `palabras_prohibidas`, `primera_persona` y
  `voz.emojis_max` de la identidad; sin `--proyecto`, como siempre. Código de salida 0 si no hay
  errores, 1 si los hay, 2 si la orden o la configuración fallan.
- **Listas de campos:** `copys.py campos --json --proyecto <id>` →
  `{"formulas": [...], "objetivos": [...], "pilares": [...], "formula_objetivos": {"IG5_lista": ["guardados"], …}}`
  (de `campos_extra` del proyecto y `config.py`).
- **Carpeta de carrusel:** ver «Carruseles».

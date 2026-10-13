# TheCopy

Departamento de **CEO_Sergete** que escribe el **copy** y los **hashtags** de
cada pieza aprobada, deja registrada la relación **pieza ↔ copy ↔ hashtags** y le
pone **fecha y hora de publicación**.

- **Piezas:** **Reels** (un MP4) y **carruseles** (una carpeta de slides que genera
  TheHistoria, con su `carrusel.json`).
- **Un `.txt` listo para pegar** por pieza: junto al MP4 con el mismo nombre
  (`01_x.mp4` → `01_x.txt`) o, en un carrusel, **dentro de su carpeta** (`<carpeta>.txt`).
  Viaja con la pieza al moverla.
- **Un Excel por proyecto** (`proyectos/<id>/registro_<id>.xlsx`): una fila por pieza y
  plataforma, con ID, enlace al MP4 o a la carpeta (clic y se abre), formato, fechas
  previstas, tema, oferta, objetivo, pilar, copy, hashtags, texto para pegar, estado y
  fecha de publicación.
- **Calendario:** fecha y hora para todo lo aprobado con una mezcla equilibrada, las
  historias del día y un `.md` por semana. «¿Qué publico hoy?» → `copys.py calendario hoy`.

> Se lanza **al dar OK** a unas piezas (cuando pasan a `REVISADOS/<id>/1. pte Publicar`)
> o **a demanda**. Las historias de IG no llevan copy ni hashtags: el calendario solo
> las reparte por día.

## Proyectos independientes

Un **proyecto** es una cuenta o cliente de contenido (id en minúsculas y sin espacios,
p. ej. `mongemalo`). El índice común está en `CEO_Sergete/proyectos.json` (TheCopy solo lo
lee). El código es genérico; **todo lo específico vive en `proyectos/<id>/`**:

| Archivo | Qué lleva |
|---|---|
| `proyecto.json` | **tipo** (`largos` / `clipping`), tono, reglas del copy, **carpetas** (pendiente, publicado, contexto), campos propios (*Oferta*, *Objetivo*, *Pilar*), **plataformas** (activas o preparadas) con sus límites, CTA y `formatos` (reel / carrusel), y el **calendario** (con su carpeta de historias) |
| `ofertas.json` | productos a los que puede apuntar un copy (+ «genérico») y cuándo usar cada uno |
| `hashtags.json` | **fijos** por plataforma (se añaden solos) + banco **temático por tamaño** (`nicho` < 50k publicaciones, `medio` 50k–500k, `amplio` > 500k; **estimados**) + `tamano_fijos`. El formato antiguo (tema → lista, sin tamaños) sigue valiendo |
| `banco_copys.json` | copys de referencia de tono y de reserva (auditados con `auditar --banco`) |
| `fuentes/` | documentos originales (p. ej. el PDF de copys del cliente) |
| `registro_<id>.xlsx` | el registro (lo crea `registrar`) |
| `calendario/` | lo genera `calendario planificar`: un `<AAAA>-W<ss>.md` por semana (no va a git) |

Común a todos los proyectos (adaptado de `sergebulaev/instagram-skills`, MIT):
[`referencias/auditoria_copy.md`](referencias/auditoria_copy.md) (checklist del copy) y
[`referencias/calendario.md`](referencias/calendario.md) (cómo planifica el calendario).

**Elegir el proyecto:** todas las órdenes aceptan `--proyecto <id>`. Sin él se usa el único
proyecto que haya (sin contar `_plantilla`); con varios, error con la lista. `registrar` y
`auditar --entrada` toman el proyecto de la tanda (si además das `--proyecto`, tiene que
coincidir).

**Nunca se mezclan proyectos:** registro, tandas (`tandas/<id>/`), calendario y `.txt` son
siempre los del proyecto. El script se niega a usar como `--carpeta`, `--pendiente`,
`--publicado`, `--carpeta-historias`, `--excel` o `--salida` algo que sea de otro proyecto,
y `registrar` no escribe un `.txt` en las carpetas de otro. Un `proyecto.json` cuyo `id` no
sea el de su carpeta, o que reutilice las carpetas de otro proyecto, da error.

**Carpetas** (en `proyecto.json`, relativas a `PruebasIA/`; `<id>` se sustituye por el id):

| Clave | Por defecto | Quién la crea |
|---|---|---|
| `carpetas.pendiente` | `CEO_Sergete/REVISADOS/<id>/1. pte Publicar` | el CEO |
| `carpetas.publicado` | `CEO_Sergete/REVISADOS/<id>/2. Publicados` | el CEO |
| `calendario.historias.carpeta` | `CEO_Sergete/HISTORIAS/<id>/1. Pte publicar` | el CEO |
| `carpetas.contexto` | `TheEditor/proyectos/<id>/transcripciones`, `_Historico/<id>` | TheEditor / el CEO al dar OK |

Si una carpeta del CEO no existe, TheCopy **avisa** (no la crea). Durante la transición de
TheEditor también se mira su ruta antigua `TheEditor/transcripciones/` (sin proyecto), solo
si el clip no aparece en las del proyecto y con un aviso en el contexto.

**Tipos de proyecto:** `largos` (vídeos largos que TheEditor corta en clips: contexto =
`cortes.json` + `.srt`) y `clipping` (vídeos ya cortados que entrega el proyecto: contexto =
`<carpeta>/textos/<clip>.txt` + el gancho de `ganchos.json`). Los dos se buscan siempre; el
tipo es informativo.

### Proyecto nuevo

```powershell
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> [--nombre "Nombre"] [--prefijo XX] [--tipo largos|clipping]
```

1. Copia `proyectos/_plantilla/` a `proyectos/<id>/` con el id, nombre, prefijo de IDs,
   tipo y nombre del registro. Si el id está en `CEO_Sergete/proyectos.json`, nombre, tipo,
   prefijo y descripción salen de allí (si no, `--nombre` es obligatorio y avisa de que lo
   tiene que dar de alta el CEO). No deja repetir el prefijo de otro proyecto.
2. Comprueba las carpetas (las del CEO no las crea: si faltan, avisa).
3. Lista **qué falta rellenar** (lo que sigue igual que en la plantilla): descripción y
   `como_reconocerlo`, **tono** y `reglas_copy`, **ofertas** y CTA genérico (`ofertas.json`),
   **hashtags** fijos y banco temático (`hashtags.json`), **CTA y reglas de cada plataforma**
   activa (`cta_patrones`, `cta_ejemplo`, emojis, nº de hashtags, guía) y el **calendario**
   (desactivado en la plantilla). `copys.py proyectos` lo vuelve a enseñar.

Lo que no se sepa se pregunta a Sergio. **Plataformas:** cada proyecto define `instagram`,
`tiktok` y `youtube` (Shorts, con título); activar una = `"activa": true` (y revisar sus
fijos en `hashtags.json`), solo cuando Sergio lo pida. A una pieza ya registrada se le puede
añadir una plataforma nueva con el mismo ID (`pendientes --plataformas <p>`).

### Ejemplo: MongeMalo (`proyectos/mongemalo/`)
Tipo `largos`; Instagram activa (Reels y carruseles), TikTok y YouTube preparadas. Hashtags:
`#grupoalfa` fijo + 2–4 temáticos rotados (3–5 en total). CTA siempre a la bio; la oferta se
elige por tema. Calendario activo (5 posts/semana, provisional). IDs `MM-0001`… El detalle,
en sus JSON.

## Carruseles (contrato con TheHistoria)

```
<carpeta_carrusel>\        al dar OK, el CEO la mueve entera a REVISADOS\<id>\1. pte Publicar\
  01.jpg … NN.jpg          1080×1350, en orden
  carrusel.json            tipo, proyecto, slug, tema, formula (IG5_lista | IG6_antes_despues |
                           IG7_mitos | IG8_metodo), objetivo, pilar, fuente {tipo, ruta, credito},
                           slides [{n, rol, titulo, texto, (puntos, peticion)}], creado
  _vista.jpg               hoja de contacto (se ignora)
  <carpeta>.txt            lo escribe TheCopy al registrar
```

`pendientes` toma de `carrusel.json` el tema, el objetivo y el pilar (ya rellenos en la
tanda) y, como contexto, la fórmula, la fuente y el texto de las slides sin el `**marcado**`.
`contexto.gancho_slide1` es lo que el caption tiene que repetir.

## Cómo funciona

```
copys.py pendientes          → tandas/<id>/<id>_<fecha>.json
                                (Reels y carruseles sin copy + su contexto)
  (el subagente `copy` rellena: tema, oferta, objetivo, pilar, copy y hashtags temáticos;
   copys.py hashtags enseña el banco por tamaño y los últimos conjuntos usados)
copys.py auditar --entrada <tanda>     → informe de estilo; se corrige REESCRIBIENDO
copys.py registrar --entrada <tanda>   → valida + audita → Excel + .txt
copys.py calendario planificar         → fecha y hora + historias del día + .md semanal
copys.py calendario hoy                → qué se publica hoy, con el texto listo para pegar
copys.py sincronizar                   → Estado/ruta según dónde esté cada pieza
```

**Proceso de auditoría:** los **errores** bloquean el registro y los **avisos de estilo** se
corrigen reescribiendo **antes de registrar**; solo se dejan si la frase es literal del clip
(`contexto.frase_viral` / `contexto.transcripcion`) o de las slides del carrusel, y entonces la
auditoría la marca como «literal del clip» y no avisa.

El **contexto** de cada Reel sale de TheEditor, solo en las carpetas `contexto` del
proyecto. En `largos`, el clip `finales/<nombre>.mp4` es la entrada `nombre` de su
`cortes.json` (título, frase viral, ángulo, categoría) y de la transcripción `.srt` se extrae
lo que se dice en ese tramo. En `clipping`, la transcripción es `textos/<clip>.txt` y el
gancho, el de `ganchos.json`; si el mismo nombre de clip está en varias carpetas de clipping,
no se elige ninguna y se avisa. El de cada carrusel, de su `carrusel.json`.

**Validaciones** antes de escribir nada (si hay un error, no se registra nada):

| | Errores (bloquean) | Avisos (no bloquean) |
|---|---|---|
| Datos | tema y campos propios (oferta, objetivo, pilar) válidos, título si la plataforma lo pide, la plataforma admite el formato | pieza no encontrada, plataforma inactiva |
| Copy | sin CTA, hashtags dentro del copy, longitud máxima, copy repetido | longitud fuera de la recomendada (la del formato), el caption de un carrusel no repite el gancho de la slide 1 |
| Auditoría (`lib/auditoria.py`) | gancho > `gancho_max`, cebo de interacción, cierre vacío | paralelismo negativo, revelación, anuncio de sinceridad, ≥ 2 expresiones de IA en un párrafo, emojis > `emojis_max` (salvo frase literal) |
| Hashtags | mal formados o repetidos, temáticos fuera de `tematicos_min/max`, total (con fijos) fuera de `total_min/total_max`, más amplios que `amplios_max` | menos de `nicho_min` de nicho, etiqueta sin tamaño conocido o fuera del banco, mismo conjunto de temáticos que otra pieza de la tanda o que uno de los `rotacion_ultimos` (5) últimos registrados |

Claves por plataforma en `proyecto.json`: `gancho_max`, `emojis_max`, `formatos`
(`{"reel": {…}, "carrusel": {…}}`: lo de cada formato, p. ej. `guia` y `copy_recomendado`,
se pone encima de lo de la plataforma; sin `formatos`, solo Reel) y en `hashtags`
`tematicos_min`, `tematicos_max`, `total_min`, `total_max` (`max_total` = alias antiguo),
`nicho_min`, `amplios_max`, `rotacion_ultimos`. Las que falten no se comprueban. Los tamaños
cuentan el set completo (fijos incluidos) y salen de `hashtags.json`.

## Columnas del registro

| Columna | Qué es | ¿Se edita a mano? |
|---|---|---|
| ID | `MM-0001`… (una pieza = un ID, en todas sus plataformas) | no |
| Clip | nombre del MP4 o de la carpeta del carrusel, con enlace | no |
| Formato | Reel / Carrusel | sí, se respeta |
| Plataforma | Instagram, TikTok, YouTube | no |
| Estado | Pendiente / Publicado / Descartado / No encontrado | sí, se respeta |
| Fecha prevista · Hora prevista | las pone `calendario planificar` | **sí: lo manual no se mueve nunca** |
| Tema | resumen corto | sí |
| Oferta · Objetivo · Pilar | campos propios del proyecto | sí (cuentan para el calendario) |
| Título · Copy · Hashtags · Texto para pegar · Nº caracteres | lo registrado | mejor con `registrar --reemplazar` |
| Fecha alta · Fecha publicación | alta y día en que `sincronizar` lo vio publicado | sí, se respeta |
| Notas · Ruta | notas libres · ruta del MP4 o la carpeta | Notas, sí |

Las columnas se localizan por su cabecera: a un Excel antiguo se le **añaden al final** las
que le falten (con sus desplegables) sin tocar lo escrito, y se puede reordenar o añadir
columnas propias. Hojas extra: **Historias** (plan de historias por día; las fechas que
cambies a mano se respetan) y **_calendario** (oculta: las fechas que puso el planificador,
para distinguir las manuales).

## Órdenes

Entorno propio (solo `openpyxl`): `.venv\Scripts\python.exe`.
El script se llama `copys.py` (un `copy.py` chocaría con el módulo `copy` de Python).

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheCopy
.venv\Scripts\python.exe copys.py proyectos
.venv\Scripts\python.exe copys.py pendientes [--proyecto <id>] [--clip 01_x | --clip carpeta_carrusel] [--plataformas instagram,tiktok]
.venv\Scripts\python.exe copys.py registrar --entrada tandas\<id>\<id>_....json [--simular] [--reemplazar]
.venv\Scripts\python.exe copys.py calendario planificar [--proyecto <id>] [--semanas N] [--desde AAAA-MM-DD] [--simular] [--replanificar-atrasados] [--json]
.venv\Scripts\python.exe copys.py calendario hoy [--proyecto <id>] [--fecha AAAA-MM-DD]
.venv\Scripts\python.exe copys.py calendario ver [--proyecto <id>] [--semana AAAA-Www]
.venv\Scripts\python.exe copys.py sincronizar [--proyecto <id>]
.venv\Scripts\python.exe copys.py ver [--proyecto <id>] [MM-0003 | nombre_pieza]
.venv\Scripts\python.exe copys.py banco [--proyecto <id>] [--oferta grupo_alfa]
.venv\Scripts\python.exe copys.py auditar (--entrada tandas\<id>\....json | --texto "..." | --banco) [--proyecto <id>] [--plataforma instagram] [--solo-estilo] [--json]
.venv\Scripts\python.exe copys.py hashtags [--proyecto <id>] [--plataforma instagram] [--tema ventas]
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> [--nombre "Nombre"] [--prefijo XX] [--tipo largos|clipping]
```

| Orden | Qué hace |
|---|---|
| `pendientes` | Crea la tanda con los Reels y carruseles de la carpeta *pendiente* que aún no tienen copy (por plataforma; un carrusel solo en las plataformas que lo admiten). `--carpeta`, `--clip`, `--plataformas`, `--incluir-registrados`. |
| `registrar` | Valida la tanda rellena y escribe Excel + `.txt`. `--simular` solo valida y enseña el resultado. `--reemplazar` cambia el copy de una pieza ya registrada (conserva ID, Estado, fechas y Notas). |
| `calendario planificar` | Pone fecha y hora a lo registrado, pendiente y sin fecha, en los huecos libres desde mañana; reparte las historias; escribe el Excel y `calendario/<AAAA>-W<ss>.md`. Estable: no recoloca lo que ya tiene fecha. Termina con la línea `FALTAN <semana> reels=… carruseles=… cualquiera=… huecos=… historias=…`. `--json` da lo mismo en JSON. |
| `calendario hoy` | Qué toca ese día: pieza, hora, ruta, el `.txt` listo para pegar, las historias del día y el recordatorio de compartir el post en historias. También los atrasados. |
| `calendario ver` | Resumen del plan por semanas (balance, huecos, historias); marca lo **ATRASADO** (fecha pasada y sin publicar). |
| `sincronizar` | Mira dónde está cada MP4 o carpeta de carrusel: en *Publicados* → `Publicado` + fecha; desaparecido → `No encontrado`. Actualiza el enlace, rehace el `.txt` si falta y rellena el Formato vacío de filas antiguas. Nunca rebaja un estado puesto a mano. |
| `ver` | Resumen del registro o el texto de una pieza/ID. |
| `banco` | Copys del banco y cuántas veces se han usado (para tirar de reserva sin repetir). |
| `auditar` | Solo informe (no reescribe): audita los copys de una tanda (`--entrada`, con la excepción de frases literales), un texto suelto (`--texto`) o el banco del proyecto (`--banco`). `--solo-estilo`: solo estilo y emojis, más cebos y cierres vacíos (sin gancho de 125, CTA, hashtags ni longitud); lo usa TheHistoria con las slides. `--json`: lista `[{nivel, regla, fragmento, mensaje}]` por stdout (ASCII). Sale con código 1 si hay errores. |
| `hashtags` | Reglas de hashtags de la plataforma, banco temático por tamaño y los últimos conjuntos de temáticos usados (para rotar). |
| `proyectos` | Lista los proyectos: tipo, prefijo, plataformas activas, calendario, carpetas que faltan y lo que queda por rellenar. |
| `nuevo-proyecto` | Crea `proyectos/<id>/` desde la plantilla y dice qué falta (ver «Proyecto nuevo»). |

Para pruebas: `--excel <ruta>` en `pendientes/registrar/sincronizar/ver/banco/hashtags/calendario`
usa otro registro (los `.md` del calendario van a `<carpeta del Excel>/calendario/`);
`pendientes --carpeta`, `calendario … --carpeta-historias <ruta>` y
`sincronizar --pendiente/--publicado <ruta>` usan otras carpetas. Ninguna puede ser de otro
proyecto.

**El Excel tiene que estar cerrado** cuando el script escribe; si está abierto, avisa y
no escribe nada. Lo que edites a mano (Estado, Fecha prevista, Hora prevista, Notas,
Fecha publicación…) se respeta.

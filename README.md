# TheCopy

Departamento de **CEO_Sergete** que escribe el **copy** y los **hashtags** de
cada clip terminado y deja registrada la relación **clip ↔ copy ↔ hashtags**.

- **Un `.txt` junto a cada MP4**, con el mismo nombre (`01_x.mp4` → `01_x.txt`), con el
  texto listo para pegar en cada plataforma. Viaja con el vídeo al moverlo.
- **Un Excel por proyecto** (`proyectos/<id>/registro_<id>.xlsx`): una fila por clip
  y plataforma, con ID, enlace al MP4 (clic y se abre), tema, oferta, copy,
  hashtags, texto para pegar, estado y fecha de publicación.

> Se lanza **al dar OK** a unos clips (cuando pasan a `REVISADOS/1. pte Publicar`)
> o **a demanda**. Las historias de IG quedan fuera: no llevan copy ni hashtags.

## Proyectos independientes

El código es genérico; **todo lo específico vive en `proyectos/<id>/`**:

| Archivo | Qué lleva |
|---|---|
| `proyecto.json` | tono, reglas del copy, carpetas pendiente/publicado, campos propios (p. ej. *Oferta*), **plataformas** (activas o preparadas) con sus límites y CTA |
| `ofertas.json` | productos a los que puede apuntar un copy (+ «genérico») y cuándo usar cada uno |
| `hashtags.json` | **fijos** por plataforma (se añaden solos) + banco **temático por tamaño** (`nicho` < 50k publicaciones, `medio` 50k–500k, `amplio` > 500k; **estimados**) + `tamano_fijos`. El formato antiguo (tema → lista, sin tamaños) sigue valiendo |
| `banco_copys.json` | copys de referencia de tono y de reserva (auditados con `auditar --banco`) |
| `fuentes/` | documentos originales (p. ej. `Copys_MongeMalo.pdf`) |

Común a todos los proyectos: [`referencias/auditoria_copy.md`](referencias/auditoria_copy.md),
el checklist de auditoría del copy (adaptado de `sergebulaev/instagram-skills`, MIT).

**Proyecto nuevo:** `copys.py nuevo-proyecto <id> --nombre "Nombre" [--prefijo XX]`
copia `proyectos/_plantilla/` y luego se rellenan sus JSON.

**Plataformas:** cada proyecto define `instagram`, `tiktok` y `youtube` (Shorts, con
título). Activar una = `"activa": true` en su `proyecto.json` (y revisar sus fijos en
`hashtags.json`). A partir de ahí, cada tanda pide copy para todas las activas, y a un
clip ya registrado se le puede añadir la plataforma nueva con el mismo ID.

### MongeMalo (`proyectos/mongemalo/`)
- Instagram activa; TikTok y YouTube **preparadas** (sin activar, con sus fijos de siempre).
- Hashtags en Instagram: **3–5 en total** contando el único fijo `#grupoalfa` (lo pone el
  script): se escriben **2–4 temáticos** del banco → **2–3 de nicho** (`#grupoalfa` ya cuenta
  como uno), **1–2 medios** y **como mucho 1 amplio**. `#ventas`, `#dinero` y `#exitopersonal`
  pasan al banco rotativo. Se **rotan** por tema (aviso si se repite el conjunto de otro clip de
  la tanda o de los 5 últimos registrados).
- Copy: gancho ≤ 125 caracteres, sin emojis, sin paralelismos negativos ni cebos de interacción.
- CTA siempre a la bio; la oferta se elige por tema (Gestión de Objeciones, Grupo Alfa,
  Escuela de Afiliados, Mentoría, El Mejor Negocio Destripado, o genérico).
- IDs `MM-0001`, `MM-0002`…

## Cómo funciona (tanda)

```
copys.py pendientes          → tandas/<proyecto>_<fecha>.json
                                (clips sin copy + su contexto: cortes.json + transcripción)
  (el subagente `copy` rellena: tema, oferta, copy y hashtags temáticos;
   copys.py hashtags enseña el banco por tamaño y los últimos conjuntos usados)
copys.py auditar --entrada <tanda>     → informe de estilo; se corrige REESCRIBIENDO
copys.py registrar --entrada <tanda>   → valida + audita → Excel + <clip>.txt
copys.py sincronizar         → Estado/ruta según dónde esté cada MP4
```

**Proceso de auditoría:** los **errores** bloquean el registro y los **avisos de estilo** se
corrigen reescribiendo **antes de registrar**; solo se dejan si la frase es literal del clip
(lo que se dice en `contexto.frase_viral` / `contexto.transcripcion`), y entonces la auditoría la
marca como «literal del clip» y no avisa.

El **contexto** de cada clip sale de TheEditor: el clip `finales/<nombre>.mp4` es la
entrada `nombre` de su `cortes.json` (título, frase viral, ángulo, categoría) y de la
transcripción `.srt` se extrae lo que se dice en ese tramo. Se busca en
`TheEditor/transcripciones/` y en `_Historico/`.

**Validaciones** antes de escribir nada (si hay un error, no se registra nada):

| | Errores (bloquean) | Avisos (no bloquean) |
|---|---|---|
| Datos | tema y campos propios (oferta) válidos, título si la plataforma lo pide | MP4 no encontrado, plataforma inactiva |
| Copy | sin CTA, hashtags dentro del copy, longitud máxima, copy repetido | longitud fuera de la recomendada |
| Auditoría (`lib/auditoria.py`) | gancho > `gancho_max`, cebo de interacción, cierre vacío | paralelismo negativo, revelación, anuncio de sinceridad, ≥ 2 expresiones de IA en un párrafo, emojis > `emojis_max` (salvo frase literal del clip) |
| Hashtags | mal formados o repetidos, temáticos fuera de `tematicos_min/max`, total (con fijos) fuera de `total_min/total_max`, más amplios que `amplios_max` | menos de `nicho_min` de nicho, etiqueta sin tamaño conocido o fuera del banco, mismo conjunto de temáticos que otro clip de la tanda o que uno de los `rotacion_ultimos` (5) últimos registrados |

Claves por plataforma en `proyecto.json`: `gancho_max`, `emojis_max` y en `hashtags`
`tematicos_min`, `tematicos_max`, `total_min`, `total_max` (`max_total` = alias antiguo),
`nicho_min`, `amplios_max`, `rotacion_ultimos`. Las que falten no se comprueban. Los tamaños
cuentan el set completo (fijos incluidos) y salen de `hashtags.json`.

## Órdenes

Entorno propio (solo `openpyxl`): `.venv\Scripts\python.exe`.
El script se llama `copys.py` (un `copy.py` chocaría con el módulo `copy` de Python).

```powershell
cd C:\Users\ico858\Desktop\PruebasIA\TheCopy
.venv\Scripts\python.exe copys.py proyectos
.venv\Scripts\python.exe copys.py pendientes [--proyecto mongemalo] [--clip 01_x] [--plataformas instagram,tiktok]
.venv\Scripts\python.exe copys.py registrar --entrada tandas\mongemalo_....json [--simular] [--reemplazar]
.venv\Scripts\python.exe copys.py sincronizar
.venv\Scripts\python.exe copys.py ver [MM-0003 | nombre_clip]
.venv\Scripts\python.exe copys.py banco [--oferta grupo_alfa]
.venv\Scripts\python.exe copys.py auditar (--entrada tandas\....json | --texto "..." | --banco) [--plataforma instagram]
.venv\Scripts\python.exe copys.py hashtags [--plataforma instagram] [--tema ventas]
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> --nombre "Nombre"
```

| Orden | Qué hace |
|---|---|
| `pendientes` | Crea la tanda con los clips de la carpeta *pendiente* que aún no tienen copy (por plataforma). `--carpeta`, `--clip`, `--plataformas`, `--incluir-registrados`. |
| `registrar` | Valida la tanda rellena y escribe Excel + `.txt`. `--simular` solo valida y enseña el resultado. `--reemplazar` cambia el copy de un clip ya registrado (conserva ID, Estado, fechas y Notas). |
| `sincronizar` | Mira dónde está cada MP4: en *Publicados* → `Publicado` + fecha; desaparecido → `No encontrado`. Actualiza el enlace y rehace el `.txt` si falta. Nunca rebaja un estado puesto a mano. |
| `ver` | Resumen del registro o el texto de un clip/ID. |
| `banco` | Copys del banco y cuántas veces se han usado (para tirar de reserva sin repetir). |
| `auditar` | Solo informe (no reescribe): audita los copys de una tanda (`--entrada`, con la excepción de frases literales del clip), un texto suelto (`--texto`) o el banco del proyecto (`--banco`). Checklist en `referencias/auditoria_copy.md`. Sale con código 1 si hay errores. |
| `hashtags` | Reglas de hashtags de la plataforma, banco temático por tamaño y los últimos conjuntos de temáticos usados (para rotar). |

`--excel <ruta>` en `pendientes/registrar/sincronizar/ver/hashtags` usa otro registro (pruebas).

**El Excel tiene que estar cerrado** cuando el script escribe; si está abierto, avisa y
no escribe nada. Lo que edites a mano (Estado, Notas, Fecha publicación…) se respeta.

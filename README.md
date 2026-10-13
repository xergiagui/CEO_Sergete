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
| `hashtags.json` | **fijos** por plataforma (se añaden solos) + banco **temático** |
| `banco_copys.json` | copys de referencia de tono y de reserva |
| `fuentes/` | documentos originales (p. ej. `Copys_MongeMalo.pdf`) |

**Proyecto nuevo:** `copys.py nuevo-proyecto <id> --nombre "Nombre" [--prefijo XX]`
copia `proyectos/_plantilla/` y luego se rellenan sus JSON.

**Plataformas:** cada proyecto define `instagram`, `tiktok` y `youtube` (Shorts, con
título). Activar una = `"activa": true` en su `proyecto.json` (y revisar sus fijos en
`hashtags.json`). A partir de ahí, cada tanda pide copy para todas las activas, y a un
clip ya registrado se le puede añadir la plataforma nueva con el mismo ID.

### MongeMalo (`proyectos/mongemalo/`)
- Instagram activa; TikTok y YouTube **preparadas** (sin activar).
- Hashtags: **4 fijos** `#ventas #dinero #grupoalfa #exitopersonal` + **1–2 temáticos** según el clip.
- CTA siempre a la bio; la oferta se elige por tema (Gestión de Objeciones, Grupo Alfa,
  Escuela de Afiliados, Mentoría, El Mejor Negocio Destripado, o genérico).
- IDs `MM-0001`, `MM-0002`…

## Cómo funciona (tanda)

```
copys.py pendientes          → tandas/<proyecto>_<fecha>.json
                                (clips sin copy + su contexto: cortes.json + transcripción)
  (el subagente `copy` rellena: tema, oferta, copy y hashtags temáticos)
copys.py registrar --entrada <tanda>   → valida → Excel + <clip>.txt
copys.py sincronizar         → Estado/ruta según dónde esté cada MP4
```

El **contexto** de cada clip sale de TheEditor: el clip `finales/<nombre>.mp4` es la
entrada `nombre` de su `cortes.json` (título, frase viral, ángulo, categoría) y de la
transcripción `.srt` se extrae lo que se dice en ese tramo. Se busca en
`TheEditor/transcripciones/` y en `_Historico/`.

**Validaciones** antes de escribir nada: tema y oferta válidos, CTA presente, sin
hashtags dentro del copy, nº de temáticos dentro del rango, longitud máxima de la
plataforma, título si la plataforma lo pide, y copy no repetido. Si hay un error, no se
registra nada.

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
.venv\Scripts\python.exe copys.py nuevo-proyecto <id> --nombre "Nombre"
```

| Orden | Qué hace |
|---|---|
| `pendientes` | Crea la tanda con los clips de la carpeta *pendiente* que aún no tienen copy (por plataforma). `--carpeta`, `--clip`, `--plataformas`, `--incluir-registrados`. |
| `registrar` | Valida la tanda rellena y escribe Excel + `.txt`. `--simular` solo valida y enseña el resultado. `--reemplazar` cambia el copy de un clip ya registrado (conserva ID, Estado, fechas y Notas). |
| `sincronizar` | Mira dónde está cada MP4: en *Publicados* → `Publicado` + fecha; desaparecido → `No encontrado`. Actualiza el enlace y rehace el `.txt` si falta. Nunca rebaja un estado puesto a mano. |
| `ver` | Resumen del registro o el texto de un clip/ID. |
| `banco` | Copys del banco y cuántas veces se han usado (para tirar de reserva sin repetir). |

`--excel <ruta>` en `pendientes/registrar/sincronizar/ver` usa otro registro (pruebas).

**El Excel tiene que estar cerrado** cuando el script escribe; si está abierto, avisa y
no escribe nada. Lo que edites a mano (Estado, Notas, Fecha publicación…) se respeta.

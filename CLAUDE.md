# TheHistoria — Departamento de historias de Instagram

Genera **historias de IG (MP4 vertical 1080×1920)**: un texto sobre un fondo de
vídeo. Lo dirige CEO_Sergete con el subagente `historia`. Detalle de opciones en
[`README.md`](README.md). **Este archivo manda** sobre las reglas de trabajo.

## Cuándo se usa
**Proceso independiente y a demanda**: solo cuando Sergio pide historias. Nunca
se lanza solo tras descargar o editar vídeos.

## Entorno
- Reutiliza el `.venv` de TheEditor, **no instales nada**:
  `..\TheEditor\.venv\Scripts\python.exe` (nunca `python3`, que en este equipo es
  el acceso directo de la Microsoft Store).
- Credenciales: `TheHistoria/.env` o, si no existe, `../CEO_Sergete/.env`.

## Dos vías

| Vía | Script | Texto | Fondos | Salida |
|---|---|---|---|---|
| **Normal** | `historias.py` | Frases de Supabase `viral_phrases` (`used_in_story=false`, por viralidad); se marcan como usadas al terminar | B-roll de `../TheEditor/superposiciones/` elegido por semántica (`match_broll`) o al azar | `salidas/<timestamp>/` + `manifest.json` |
| **Especiales** (promos, eventos) | `historias_especiales.py` | Lo da Sergio (`--texto`, repetible) | `BRells especiales/` (local, git-ignored) | `salidas/especiales_<timestamp>/` |

- Normal: `--n N`, `--categoria X`, `--min-virality N`, `--phrase "..."` (frase
  suelta sin tocar la BBDD), `--duracion S`, `--no-marcar`.
- Especiales: `--texto` (varios = un texto por variación), `--variaciones N`
  (def. 3, mismo texto con distinto fondo), `--duracion S` (def. 6),
  `--reserva-inferior F` (0–0,6; def. 0,25). El texto va en la banda superior y
  deja libre la franja de abajo para el botón de IG.
- Si no quedan frases sin usar o falta Supabase, dilo; para probar sin BBDD usa
  `--phrase`.

## Reglas
- Texto en minúsculas, pero **mayúscula en la primera letra y tras `.`, `?` y `!`**
  (`lib/texto.py::capitalizar_frase`, ya aplicado en el render).
- Fondos siempre a pantalla completa (mismo criterio que TheEditor).
- Las historias **no llevan copy ni hashtags** (TheCopy no interviene).

## Al dar OK a unas historias
1. **Mover** (no copiar) todos los MP4 de las tandas aprobadas de `salidas/` a
   `C:\Users\ico858\Desktop\PruebasIA\CEO_Sergete\HISTORIAS\1. Pte publicar\`
   (aplanados; los nombres no colisionan).
2. **Borrar** esas carpetas de tanda en `salidas/` (con su `manifest.json`),
   conservando `salidas/.gitkeep`.

En `salidas/` solo debe quedar lo que está en curso o pendiente de revisar.

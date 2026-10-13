# TheHistoria — historias y carruseles de Instagram

**Historias de IG** (MP4 1080×1920: un texto sobre un fondo) y **carruseles del
feed** (2–10 JPG 4:5, 1080×1350) para varios proyectos. Lo dirige CEO_Sergete con
el subagente `historia`. **Este archivo manda.** El `README.md` es referencia:
no lo leas salvo para diseño o un esquema poco habitual.

## Cuándo y cómo
- **A demanda**: cuando Sergio pide historias o carruseles, o el CEO tiene huecos de
  carrusel en el calendario. Nunca se lanza solo tras descargar o editar.
- `..\TheEditor\.venv\Scripts\python.exe <script> --proyecto <id> …` (no instales
  nada; nunca `python3`). Credenciales: `.env` o `..\CEO_Sergete\.env`.

## Proyecto (siempre `--proyecto <id>`)
- `proyectos/<id>/`: `proyecto.json` (historias, especiales, `carruseles.credito`),
  `estilo.json` (solo maquetación), **`reglas.md` (recursos y fuentes: léelo)**,
  `especiales/` y `planes/`.
- **Identidad** (cuenta_ig, voz, emojis, no suplantar, palabras prohibidas y colores
  de marca): `..\CEO_Sergete\proyectos.json` → `identidad`. Fuente única: no la
  copies. Si falta, valores neutros con aviso.
- **Recursos**: los de `..\TheEditor\proyectos\<id>\proyecto.json` → `recursos`
  (`banco_comun` | `propio` | `ninguno`, `internet`). Nunca material de otro proyecto
  ni de internet si no está permitido. **Nunca mezcles proyectos.**

## Historias
| Vía | Orden | Texto · fondo |
|---|---|---|
| Normal | `historias.py [--n N] [--categoria X] [--min-virality N]` | frases del proyecto en `viral_phrases` · según la política de b-roll |
| Especial | `historias_especiales.py --texto "…" [--texto "…"] [--variaciones N]` | lo da Sergio · `proyectos/<id>/especiales/`; franja inferior libre (`--reserva-inferior`, def. 0,25) |

- Minúsculas con mayúscula al inicio y tras `.` `?` `!` (lo hace el render). Fondo a
  pantalla completa. Sin copy ni hashtags; no entran en el calendario.
- **Al generar no se marcan las frases.** Sin frases o sin Supabase: dilo (para
  probar: `--phrase "…"`).
- **OK**: `historias.py --aprobar <tanda…>` (o `--todas`): mueve los MP4 a
  `..\CEO_Sergete\HISTORIAS\<id>\1. Pte publicar\` (nombre único), marca las frases,
  apunta el manifest en `salidas/<id>/_aprobadas.log` y borra la tanda.
  **Rechazo**: borra la carpeta de la tanda (sus frases quedan libres).

## Carruseles (sí llevan copy y entran en el calendario)
1. **Material**: `carruseles.py --listar` (lo hecho y de dónde, para no repetir
   temas) y `carruseles.py --fuente <video|ruta>` (transcripción sin tiempos,
   cortes, clips y campos válidos; también un `articulo.md`). **Nunca leas el
   `.json` ni el `.srt` de Whisper.**
2. **Plan** en `proyectos/<id>/planes/<slug>.json` (esqueleto abajo).
3. **`carruseles.py --plan <plan>`**: valida, audita con TheCopy y renderiza; con
   errores no escribe nada, así que no hace falta `--solo-validar` antes. Corrige
   errores y avisos (también los de la auditoría) y repite: el re-render sustituye
   la salida anterior del mismo slug. Mira `_vista.jpg`.
4. **OK**: `carruseles.py --aprobar <carpeta>` la mueve a
   `..\CEO_Sergete\REVISADOS\<id>\1. pte Publicar\` e imprime la orden de TheCopy.

```json
{
  "proyecto": "<id>",
  "tema": "Qué aprende quien lo lee",
  "formula": "IG5_lista",
  "pilar": "educativo",
  "fuente": {"tipo": "video", "ruta": "_Historico/<id>/<video>"},
  "portada_fondo": {"ruta": "_Historico/<id>/<video>/clips/<clip>.mp4", "segundo": 6.5, "foco_y": 0.0},
  "slides": [
    {"titulo": "Promesa con **bucle abierto**", "texto": "Línea que obliga a deslizar"},
    {"titulo": "La idea más fuerte", "texto": "Explicación en ~25 palabras"},
    {"titulo": "Otra idea", "texto": "…"},
    {"titulo": "Resumen", "puntos": ["…", "…"], "texto": "…", "peticion": "Guárdalo para …"}
  ]
}
```
- Se deducen: `slug` (nombre del archivo), `n` y `rol` (1.ª gancho, última cierre,
  resto valor), `objetivo` (si la fórmula solo admite uno) y `fuente.credito`
  (vídeo: `carruseles.credito` del proyecto). `formula`, `objetivo` y `pilar`: los
  que imprime `--fuente`. `fuente.tipo`: `clip | video | articulo | tema`.
- Portada opcional, solo material del proyecto; el segundo se elige con
  `--candidatos-portada <clip>`, nunca a ojo.

**Contenido**
- 2–10 slides (lo típico, 6–10). Nunca rellenes.
- Slide 1 = promesa + bucle abierto (≤ 12 palabras). Lo más fuerte en la 2–3. Una
  idea por slide (título ~8 palabras, texto ~25). Cierre = resumen que merezca
  guardarse + **una sola** petición.
- Nada inventado: conserva las afirmaciones y cifras de la fuente.
- Voz de la identidad: de tú y sin hablar como el autor de la fuente; emojis según
  `emojis_max`.
- Sentence case con tildes, ¿? y ¡!. `**palabra**` = destacada (máx. una por slide).
- Evita lo que marca el auditor: «no es X, es Y», «¿El resultado?», anuncios de
  sinceridad, vocabulario de IA y cebos de interacción.
- No cambies el contrato de la salida (lo lee TheCopy).

## Proyecto nuevo
`..\CEO_Sergete\nuevo_proyecto.py` copia `proyectos/_plantilla/`. Después: `reglas.md`,
`proyecto.json` (`carruseles.credito`…) y revisar `estilo.json` quitando
`_rellenar` (mientras esté, `carruseles.py` da error). Identidad: CEO; recursos:
TheEditor.

## Pruebas
`--destino <dir>`: otro destino en `--aprobar` y otra carpeta de salida en `--plan`
(no toca HISTORIAS, REVISADOS ni las salidas pendientes). `--no-marcar` en
`--aprobar`: no marca frases.

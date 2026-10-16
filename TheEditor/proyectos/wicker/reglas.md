# WICKER: reglas de edición del proyecto

Proyecto `wicker`. Estas reglas se suman a las de `TheEditor/CLAUDE.md` y **mandan
sobre ellas** donde choquen (gancho, silencios, b-roll, música).

## Qué es
- Campaña de clipping de la película **WICKER** (Vértice 360 España; estreno en todos
  los cines de España el **30-oct-2026**). Reels para Instagram; objetivo: visitas y
  tráfico a @vertice360_spain. Página fan **no oficial**.
- **El briefing es obligatorio al 100 %**: no se hace nada que no venga en él
  (`CEO_Sergete/docs/wicker/Briefing_WICKER_ESPANA_Clippers_2026-10-14.docx.pdf`).
- El proyecto va en **modo tráiler** (`proyecto.json → "modo": "trailer"`, código en
  `trailer.py`): todo lo literal (ganchos A–E, CTA, títulos de portada, zonas y
  tramos vetados) está en `proyecto.json → trailer`. No lo copies a mano: el código lo
  lee de ahí.

## Flujo (no hay batch ni clips.py de corte)
1. La fuente ya está transcrita: `transcripciones/TRL_20_VE_RRSS_9x16_v03/` (se reutiliza
   en todas las tandas; si faltara: `transcribir.py --proyecto wicker
   "proyectos/wicker/recursos/oficial/TRL_20_VE_RRSS_9x16_v03.mp4"`).
2. Elige tramos con `…cortes.txt` y **`dialogos.json`** (frases revisadas, en segundos del
   tráiler) y escribe `transcripciones/TRL_20_VE_RRSS_9x16_v03/cortes.json` con el esquema
   de la cabecera de `trailer.py` (`nombre`, `tipo`, `tramos`, `portada_titulo`,
   `portada_t`, `portada_pos`, `momento`, `por_que`; `fecha` si se conoce).
   La tanda propuesta está en `plan_tanda_19-30oct.json` (mismo esquema).
3. `clips.py --proyecto wicker "TRL_20_VE_RRSS_9x16_v03" --validar` hasta `OK`.
4. `editar_clips.py --proyecto wicker "TRL_20_VE_RRSS_9x16_v03" [--solo <clip>]` →
   `finales/<clip>.mp4` + `finales/<clip>.portada.jpg`.
5. `qc.py --proyecto wicker "TRL_20_VE_RRSS_9x16_v03"` y mira `finales/_qc.jpg`
   (0 s, final del gancho, final con la CTA y portada).
- Corrección de un clip: cambia solo su entrada de `cortes.json` y relanza 3–5 con `--solo`.
- Al aprobar (lo hace el CEO), la portada viaja con su mp4 a `REELS/wicker/1. pte Publicar/`
  y **no se archiva nada** (`aprobar.archivar=false`): la fuente y la transcripción sirven
  para la siguiente tanda.

## Material (lo único permitido)
- `recursos/oficial/` (fuera de git; **nunca** se mueve, archiva ni borra):
  `TRL_20_VE_RRSS_9x16_v03.mp4` (tráiler VE ya en 9:16, **la base**), `WICKER_TRL_VE_ST_v01.mp4`
  (4K 16:9), `TRL_20_VE_RRSS_16x9_v01.mp4`, `TRL_20_VE_RRSS_4x5_v02.mp4` y
  `poster_oficial_es.jpg`. Son el mismo montaje (144,98 s) y el **audio es idéntico** en las
  cuatro (mismo MD5): castellano de España (aunque ffprobe diga «eng»).
- El 9:16 lleva fijo arriba a la izquierda el logo «WICKER · PRÓXIMAMENTE SOLO EN CINES»; la
  4K («ST») no. Las tarjetas de texto (citas de prensa, reparto, título) están en todas.
  Usa la 4K solo si un plano necesita otro encuadre (tramo con `"fuente": "4k", "x": …`):
  el logo aparecería y desaparecería.
- Nada de b-roll, música, SFX, internet, imágenes ajenas, IA generativa, TTS ni voz en off.

## Estructura de cada clip
gancho literal (0–3 s) → frase o momento clave del tráiler → remate (la frase o la
mirada que hace gracia) → CTA literal sobre el póster (4 s, con el remate musical
final del tráiler). Autocontenido: nada de cortes sueltos sin contexto. 15–90 s.
- **Nombre**: empieza por la letra del tipo en minúscula + `_` (`a_…`…`e_…`): TheCopy saca
  de ahí el caption y los hashtags.
- Los tramos no pueden partir una frase de `dialogos.json` (lo comprueba la validación).
- Se puede repetir material entre clips con enfoques distintos (OK de Sergio).
- Tipos: A = premisa (el gancho más fuerte), B = reparto, C = romantasy, D = la cama
  (tiene que contener el diálogo de la cama), E = «qué ver este finde» (publicar jueves
  29 y viernes 30, el finde del estreno).
- **Aviso tipo D**: en este tráiler el diálogo de la cama es «Voy a arreglar la cama esta
  tarde.» (126,6 s) … «Se ha vuelto a romper.» (132,8 s); «La cama está rota.» / «La
  arreglaré.» del briefing NO se oyen literalmente. El gancho D sale literal del briefing.

## Contenido
- No destripar el final; solo lo que enseña el tráiler oficial.
- Picante sí, explícito no. Planos íntimos (`trailer.evitar`): 105,55–108,40 (rostro en
  éxtasis) y 113,24–114,03 (en la cama con el de mimbre): valen a mitad de clip, **nunca**
  en el gancho (0–3 s) ni de portada. La cartela final del tráiler (141,4–145 s) no se usa.
- Citas de prensa del tráiler («Una sorpresa salvaje», «Irresistiblemente extraña y
  maravillosa», «Colman y Skarsgård están hechos el uno para el otro»): embargo hasta el
  17-oct 10:45 (`trailer.embargo_prensa`); con `fecha` anterior, la validación da error.
- Bajo las cartelas del reparto (114–120,7 s) solo hay música (Whisper alucina «Gracias
  por ver el vídeo»): sin subtítulos ahí.

## Look
- Tipografía: **Fraunces** (serif de cuento, variable) + **Noto Color Emoji**, ambas OFL, en
  `recursos/fuentes/` (licencias al lado). Montserrat no. Colores del póster: panel
  `#226a72` con filete crema, texto `#ead8cc`, WICKER y palabras en MAYÚSCULAS en `#f87870`.
- Gancho en panel arriba (desde y=355, bajo el logo oficial), máx. 3 líneas, con el
  reparto de líneas de `trailer.tipos.<X>.lineas` (literal). Si en un clip tapa la cara,
  `"gancho_pos": "abajo"`.
- Subtítulos crema con contorno oscuro abajo (y≈1340–1500), fuera de los rótulos
  oficiales (`trailer.zonas_protegidas`; el render los esquiva y el QC lo comprueba).
- Encuadre: el 9:16 oficial tal cual. Sin filtros ni LUT: la paleta es la del tráiler.
- Portada: fotograma del propio clip (`portada_t`, segundo del tráiler dentro de un tramo)
  + un título literal de `trailer.portadas`, en el centro de la pantalla (cabe en la
  cuadrícula 4:5 del perfil). No sobre rótulos oficiales (la validación lo comprueba).

## Audio
- Solo el original del tráiler. **Sin recorte de silencios** (`silencios.quitar=false`:
  excepción aprobada por Sergio; rompería el ritmo del tráiler).
- Micro-fundidos de 0,06 s en cada corte (0,2 s el último), ganancia estática hacia
  −16 LUFS con +3 dB como máximo y limitador: el tráiler llega a −19 LUFS con picos a
  0 dBFS y más ganancia aplasta los transitorios.

## QC propio (además del normal)
`qc.py` comprueba por clip: gancho literal visible del fotograma 0 a los 3 s, CTA literal
al final (≥ 3 s entera), subtítulos sin tapar el gancho ni los rótulos oficiales, audio =
el del tráiler (correlación ≥ 0,97/0,92: sin música ni voces añadidas), sin metadatos de
editores, 15–90 s y portada 1080×1920 con título literal. Los negros que trae el propio
tráiler, la cartela fija de la CTA y el silencio de su cola no cuentan.

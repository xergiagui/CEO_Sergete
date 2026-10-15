# TheEditor — reglas que ya cumple el código

Reglas de edición de Sergio que hacen cumplir los scripts (no hay que aplicarlas
a mano). Lo que decide el editor (LLM) está en [`CLAUDE.md`](CLAUDE.md). Si cambias
una de estas reglas, cambia el código y este archivo a la vez.

## Proyectos y política de recursos

Todo vive en `proyectos/<id>/` (`proyecto.json`, `reglas.md`, `input/`,
`transcripciones/`, `logs/`, `recursos/`). Los scripts aceptan `--proyecto <id>`;
si se omite y solo hay uno (sin contar `_plantilla`), se usa ese.

`proyecto.json`:

| Clave | Valores |
|---|---|
| `tipo` | `largos` (vía 1, o vía 2 si vienen en extractos) · `clipping` (vía 2 con recursos propios) |
| `idioma` | idioma de la transcripción y de los subtítulos (`es`, `en`…) |
| `recursos.broll` | `banco_comun` (`superposiciones/` + catálogo `broll_assets`) · `propio` (solo `recursos/broll/`, con índice local si hay `_indice.json`) · `ninguno` |
| `recursos.musica` | `banco_comun` (`musicas/`) · `propia` (solo `recursos/musica/`, suelta o por tipologías) · `ninguna` |
| `recursos.internet` | `false` = nunca Pexels, imágenes libres ni catálogo común (guarda en `pipeline_core`; modelos solo de la caché local con `HF_HUB_OFFLINE`; ni los `pexels_*` del banco común) |
| `recursos.gancho_visual` | `pexels` (mini-vídeo al inicio en la vía 1; exige `internet: true`) · `ninguno` |
| `recursos.gancho_texto` | `true` = texto de gancho los primeros segundos (`cortes.json` o `ganchos.json`) |
| `recursos.guardar_frases` | `true` = frases en `viral_phrases` con la etiqueta `proyecto:<id>` (sale a Supabase aunque `internet` sea `false`; en `_plantilla`, `false`) |
| `encuadre` | vía 2: `modo_por_defecto` y `carpetas` (`right\|left\|center\|auto\|auto-right\|follow\|<fracción>`). Un modo desconocido es un error |
| `silencios` | ajuste global de auto-editor (`umbral` %, `margen` s) |
| `gancho.texto_duracion_s` | segundos del gancho de texto en pantalla |
| `frases.etiquetas_extra` | etiquetas que se añaden a cada frase, además de `proyecto:<id>` |

- Si falta una clave de `recursos`, se toma lo más restrictivo (y se avisa).
- Con política propia el render nunca cae al banco común. Al empezar, el batch y
  `editar_clips.py` cuentan los recursos y **paran** si falta b-roll o música
  (salvo `--sin-broll` / `--sin-musica`, solo para esa ejecución).
- B-roll propio: casación semántica local con `recursos/broll/_indice.json`
  (`indexar_broll.py`); lo que empieza por `_` se ignora.

## Salida, validación y binarios

- `--quiet` (por defecto si stdout no es una terminal): una línea por clip y el
  `RESUMEN` (`proyecto.decir()`); el detalle, al log. `--verbose` lo enseña todo.
  Los comandos de ffmpeg no se imprimen; si fallan, solo el nombre del binario y
  la cola del error.
- `validar.py` (antes de renderizar; `clips.py --validar`,
  `procesar_batch_clip.py --validar-ganchos`): nombres `[a-z0-9_]+` únicos;
  tramos de 15–90 s dentro del vídeo y sin solapes; gancho ≤ 2 líneas (mismo
  cálculo que el render, `pipeline_core.hook_text_lines`) y ≤ 50 caracteres,
  `¿` con `?` y `¡` con `!`, sin emojis, cifras presentes en el texto del clip
  (en dígitos o en letra) y distinto de la primera frase; claves de
  `ganchos.json` = clips de la carpeta. Gancho vacío = aviso.
- `herramientas.py`: un solo `FFMPEG`/`FFPROBE` para todo (variable de entorno
  `FFMPEG`/`FFPROBE` → `..\TheDescarga\tools` → imageio-ffmpeg → PATH) y
  dimensiones de **pantalla** (con la rotación de los `.MOV` de móvil aplicada).
- Modelos: faster-whisper se carga una vez por proceso (`pipeline_core.whisper_model()`,
  vías 1, 2 y 3); la caché de fastembed está en `whisper/models/fastembed`.

## Transcripción (vía 1)

whisper.cpp sin DTW (`ggml-large-v3-turbo*.bin` si existe; si no, `large-v3`).
Por encima de 35 min se trocea en fragmentos de ~10 min cortados en el silencio
más cercano (±30 s) o, si no hay, con 2 s de solape. Además de `.txt/.srt/.json`
escribe `<video>.cortes.txt`: cabecera (duración y clips sugeridos) y una línea
por frase `[inicio–fin] texto` (agrupando por puntuación, máx. 20 s), con una
línea en blanco tras una pausa de más de 1,5 s.

## Encuadre 9:16

- **Nunca un tramo con solo piernas/cuerpo sin la cara.** Encuadre tipo busto
  (recorte también vertical hacia cara + torso) en `follow` y la vía 1; si no se
  puede, se tapa el tramo con b-roll.
  - **Excepción deliberada:** `right`, `left`, `center`, `auto`, `auto-right` y
    `<fracción>` recortan a **altura completa** (franja horizontal). En un plano
    a dos sentado eso encuadra cabeza y torso; un zoom vertical cortaría la
    cabeza o daría un busto inestable. No es un fallo: no lo «arregles».
- **Un solo recorte FIJO por plano** (por corte de cámara); nunca sub-ventanas
  ni microrreajustes. Los cortes de escena se detectan a 320 px.
- En primeros planos se centra la **cara dominante** (Haar + filtro de piel YCrCb).
  Si en un plano el filtro de piel descarta la cara real (gradación fría o
  contraluz: Cr < 133, p. ej. la terraza de Monge) y solo deja pasar falsos
  positivos del fondo (ladrillo), se usan las frontales **sin filtro**: solo si
  son ≥ 2× las filtradas (y ≥ 4), estables (MAD de cx ≤ 8 % del ancho) y no más
  pequeñas (`_usar_brutas` en `clips.py`). Con piel normal no cambia nada.
- La detección de hablante por movimiento de boca está **desactivada** (poco
  fiable). No se reactiva sin que Sergio lo pida.
- Fuente ya vertical (alto ≥ 1,7 × ancho, con la rotación aplicada): solo se
  escala, salvo con un MODO explícito (argumento o `encuadre.carpetas`).
- Rotación: ffmpeg endereza al decodificar. El b-roll entra como segunda entrada
  del overlay y no hereda la marca de rotación (comprobado con 7.1 y con el de
  TheDescarga); los reencuadres usan `-vf` simple, que tampoco la copia.

## B-roll

- **Siempre a pantalla completa**; nunca un parche recortado (p. ej. tapar un
  banner): b-roll a pantalla completa esos segundos, o un reencuadre.
- Con intención: entra al empezar una frase y sale en la pausa (ventanas de la
  voz, cada ~6,5 s), nunca bajo los ganchos (2,5 s o la duración real del gancho
  de texto) ni en el último segundo.
- Cada ventana lleva el clip que casa por significado (umbral 0,30; sin
  `aviso-*` y sin repetir): banco común → `broll_assets` + RPC `match_broll`;
  propio → índice local. **Sin coincidencia, uno al azar sin repetir** por
  ventana (`BROLL_AZAR_MAX = None`, decisión de Sergio del 14-oct-2026; un número
  lo limitaría por clip).
- `indexar_broll.py --faltan` lista lo que hay en `superposiciones/` y no está
  en `broll_assets` (solo lectura); se indexa con `broll_index/` (README).
- Click de entrada (`viral-pipeline-assets/sfx` o `recursos/sfx/` del proyecto).

## Subtítulos

- Minúsculas, con mayúscula en la primera letra y tras `.`, `?`, `!`, `…`. Los
  números de miles no se parten («10.000»). Palabrotas enmascaradas (`P***`).
- Se queman una sola vez, en la Fase C (Montserrat, blanco con reseguido negro,
  a la altura de la barbilla).
- Grupos de hasta 3 palabras; se corta tras fin de frase y tras pausa de 0,7 s;
  un grupo no acaba en palabra débil (`_HOOK_WEAK`) si hay otra detrás. Un grupo
  de una sola palabra se une al anterior (o al siguiente) si quedan ≤ 4, no
  cruza un fin de frase ni una pausa larga y cabe en la zona segura (920 px).
  Un grupo que no cabe en pantalla se parte. Dos grupos nunca se solapan.

## Subtítulos incrustados de la fuente (vía 1)

`subs_fuente.py`, paso previo de `editar_clips.py` si el proyecto lo pide
(`proyecto.json → subs_fuente.tapar`: `desenfoque` | `banda` | `no`; sin la
clave, no se hace nada). Lee el clip 9:16 a 30 fps en la franja `zona_y`
(1290–1920 de 1920, bajo nuestros subtítulos, que acaban en ~1280) y marca los
fotogramas con rótulo blanco sobre caja oscura; alarga cada tramo durante el
fundido del rótulo. Si el rótulo tiene varias líneas, la caja crece por las
contiguas del mismo rótulo (mediana por fila de blanco junto a oscuro ≥ 3, huecos
≤ 140 px), también hasta 300 px por encima de `zona_y`: antes asomaban la primera
línea por encima o una línea corta («ti») por debajo. Por tramo, tapa solo su altura (+40 px de margen) y solo
mientras dura: desenfoque fuerte con 24 px de borde suave (`sigma` 70) o banda
negra al 85 %. Va sobre el plano del ponente, antes del gancho visual, el b-roll,
el gancho de texto y nuestros subtítulos, que quedan encima. Audio, duración y
fotogramas no cambian; sin rótulos, el clip no se recodifica. Si falla, avisa y
el clip sale sin tapar. `--sin-tapar-subs` lo quita en una ejecución; prueba
suelta: `subs_fuente.py --proyecto <id> "<clip>.mp4" [--salida x.mp4] [--modo …]`.
La vía 2 no lo usa.

## Gancho de texto (render)

PNG transparente (`render_hook_text_png`) en la franja superior (bajo el 12,5 %
superior, 120 px a cada lado, por encima de los subtítulos), Montserrat Bold
blanca con reseguido sobre caja oscura, mismas reglas de texto que los
subtítulos, visible desde el primer fotograma `gancho.texto_duracion_s` (2,5 s)
con fundido de salida. La vía 3 no lleva.

## Audio

Música 6–12 dB por debajo de la voz (`volume=0.253`), de-click, `dynaudnorm` en
la voz y limitador final (`alimiter=limit=0.95`): pico < 0 dBFS. La música (mp3,
wav o m4a) se elige por tipología (anotada o inferida por embeddings) con una
semilla por clip. No es obligatoria si no encaja.

## Zona segura e higiene visual

Cara, texto y elementos clave en una zona central conservadora; aire abajo y en
el borde derecho (interfaz de IG/TikTok). Nada de tabaco, alcohol, logos o
marcas ajenas, matrículas, datos privados ni marcas de agua (los b-roll con
`aviso-*` no se usan).

## Exportación

1080×1920, H.264, fps de la fuente, 10 Mb/s con VBV a 12 (`-b:v 10M -maxrate 12M
-bufsize 24M`), AAC 192k 48 kHz estéreo (`pipeline_core.VIDEO_ENC`/`AUDIO_ENC`,
las tres vías). `qc.py` comprueba todo eso más negros (0,25 s), congelados (2 s)
y silencios (−40 dB, 1,5 s).
- Vía 1: `clips.py` pasa a auto-editor `--frame-rate` con la tasa nominal de la
  fuente (`fps_fuente`, solo si es constante). El concat por planos deja huecos
  de timestamps y, sin eso, el clip heredaba la media (29,92 en vez de 30).

## Bancos

- `superposiciones/` (b-roll + `pexels_<tema>_NN.mp4`; Pexels pide
  `Authorization` **y** `User-Agent: Mozilla/5.0`) y `musicas/` (por tipología).
- `broll_assets` (Supabase): catálogo con embeddings 384d
  (`paraphrase-multilingual-MiniLM-L12-v2`, fastembed).
- `viral_phrases` (Supabase): frases con `proyecto:<id>`; SQL en
  `../TheLanding/supabase/viral_phrases.sql`. La vía 1 guarda `frase_viral` o
  `titulo` (nunca `hook_query`); el batch no vuelve a subir los clips que salta.
- Credenciales (`pipeline_core.cargar_env()`): `~/.viral-pipeline/env.json`;
  lo que falte, de `../CEO_Sergete/.env` (Supabase) y `TheEditor/.env` (Pexels).

## Vía 3 · Avatar IA (skill `Editor_Sergio`)

Parte del link del viral, con popups y gates (audio → HeyGen → edición). Código
en `.claude/skills/Editor_Sergio/`; `phase_c_edit(…, proyecto="<id>")` y
`step1b_store_viral_phrases(…, proyecto="<id>")` (por defecto `mongemalo`).
Salida en `~/Desktop/viral_pipeline_output/<Avatar>/<slug>/`. Corre con el
`.venv` de TheEditor y baja con `..\TheDescarga\tools\yt-dlp.exe`. El setup solo
se salta si `env.json` tiene las claves de HeyGen y ElevenLabs (`setup.py
faltan` dice `SETUP_OK` o cuáles faltan).

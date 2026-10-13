---
name: Editor_Sergio
description: Sistema end-to-end (macOS, Linux, Windows) que toma UN link de viral (IG/TikTok/YouTube) y genera adaptaciones con avatar IA. Setup por popups (AskUserQuestion). Avatar HeyGen V (look subido por UI, mejor calidad) o IV (talking_photo, más barato). Salida 100% LOCAL en ~/Desktop/viral_pipeline_output/<Avatar>/<slug>/ (Airtable está fuera del flujo). Procesa POR FASES con gates (audio → HeyGen → edición). B-roll y música desde carpetas LOCALES (superposiciones/ y musicas/), no Pexels. Cuándo invocar — "Editor_Sergio", "editor de Sergio", "viral pipeline", "monta sistema viral", "setup viral", "adaptaciones de este reel".
argument-hint: [setup|link]
allowed-tools: AskUserQuestion, Bash, Read, Write, Edit, Grep, Glob, Skill
---

# Editor_Sergio — Viral Pipeline (cross-platform — macOS, Linux, Windows)

## ⚠️ REGLAS DE UX

### Regla 1 — Todo prompt va por `AskUserQuestion`
Cero texto plano. Cada pregunta al usuario aparece como popup azul nativo. Las API keys y los IDs se piden con opciones tipo `Abrir URL` / `Cancelar` + el usuario usa **"Other"** del popup para pegar el valor.

### Regla 2 — Sin numeración tipo "popup 1/5"
NUNCA digas "Popup 1/5". Habla de los popups por su nombre (`Config APIs`, `Voz`, `Avatar HeyGen`, `Preferencias`, `Descripción`, etc). La numeración rompe la sensación SaaS.

### Regla 3 — Tras setup: auto-popup Descripción → luego Link
Cuando termines el último popup del setup y guardes `env.json`, **NO esperes**. Lanza el popup `Descripción del avatar` y, tras él, el popup `Link del reel`.

### Regla 4 — Procesa SIEMPRE por fases con gates
NUNCA avances de una hasta el vídeo final. Tras aprobar guion(es): **Fase A (audio) → GATE → Fase B (HeyGen) → GATE → Fase C (edición)**. El usuario aprueba en cada gate (no se gasta HeyGen sin oír el audio; no se edita sin validar el avatar).

### Regla 5 — Links de CTA siempre clickable
Formato markdown obligatorio (nunca el URL pelado): el CTA de IG `[@mariokaizen](https://instagram.com/mariokaizen)` y, si aparece, `[Reservar llamada de descubrimiento](https://bit.ly/3RAAftB)`.

### Regla 6 — Avisa SIEMPRE la ruta del archivo en el chat
Cada vez que se cree un archivo (audio, vídeo HeyGen, vídeo final), DÍSELO al usuario en el chat con la ruta EXACTA, en lenguaje claro. Ej: `📁 Audio creado → En tu Escritorio, dentro de: ~/Desktop/viral_pipeline_output/<Avatar>/<slug>/Audio__audio_final.mp3`. Usa el `local_path` que devuelve cada fase (`phase_a/b/c`). NO cambia dónde se guarda nada; solo se menciona explícitamente.

### Regla 8 — Al analizar un viral, guarda SIEMPRE sus frases virales
Cada vez que se **analiza un viral** (tras `step1_download_and_transcribe`, sobre la transcripción del clip **original**, no del avatar), extrae las **frases más virales o interesantes** del clip y **almacénalas** en la tabla Supabase `viral_phrases` — es un banco para **más adelante** crear historias de Instagram. **De momento SOLO se almacenan; NO se generan historias** ni se muestran como entregable.
- **Qué frases**: 2-6 por clip, **verbatim** del transcript (limpias de muletillas), las que paran el scroll: hooks, remates, datos rotundos, frases lapidarias. No inventes frases nuevas.
- **Cómo**: llama a `step1b_store_viral_phrases(env, phrases, source_url=<link>, lang=<es|en>, avatar=env.get("AVATAR_NAME"), proyecto="<id>")` (proyecto de TheEditor; por defecto `mongemalo`: añade la etiqueta `proyecto:<id>` a los `tags` y respeta su `guardar_frases`). Si usas directamente `store_viral_phrases(...)`, pásale también `proyecto="<id>"`. `phrases` es una lista de dict `{phrase, category, angle, tags, virality, rationale}` (solo `phrase` es obligatoria; `angle` ∈ hook/remate/dato/frase-lapidaria; `virality` 1..100 tu estimación; `rationale` por qué engancha). El wrapper `step1b_store_viral_phrases(...)` hace lo mismo e imprime el resultado.
- **Cuándo**: en el paso 2 del popup `Link del reel` (al disecar el patrón), antes de reescribir los guiones. Va **una sola vez por link**.
- **Dedup y robustez**: se hace UPSERT por `phrase_hash` (misma frase no se duplica entre ejecuciones). Es **best-effort**: si no hay `SUPABASE_URL`/`SUPABASE_ANON_KEY`, no pasa nada y el flujo sigue. Requiere haber ejecutado `viral_phrases.sql` (en TheLanding/supabase) una vez.
- **NO** menciones esto como un entregable al usuario; basta un aviso breve tipo "🗂️ Guardadas N frases virales en el banco (para historias IG más adelante)".

### Regla 7 — El hook de inicio SIEMPRE vía skill `viral-hook-creator`
El **hook de inicio** (la 1ª frase de cada guion, la que para el scroll) NUNCA se redacta a mano ni se improvisa: se genera **SIEMPRE** invocando la skill `viral-hook-creator` (herramienta `Skill`).
- **Cuándo**: en el paso 3 del popup `Link del reel`, al reescribir cada uno de los 3 guiones (un hook por ángulo). Si el usuario pide cambios de hook en `Aprobación` ('Other'), se re-genera igualmente con la skill.
- **Cómo**: pásale el contexto del clip — tema, remate, `env["AVATAR_DESCRIPTION"]` (nicho/audiencia/tono) y el idioma (`es`/`en`) — y pídele varias opciones de hook. Elige la que mejor encaje con el ángulo del guion y úsala como 1ª frase.
- **Coherencia**: el hook debe respetar el tono de `AVATAR_DESCRIPTION` (promesa/cifra concreta u orden en la 1ª frase) y quedar en el idioma del avatar.
- Esto aplica **solo al hook de texto/hablado**; el **gancho visual** (mini-vídeo Pexels, `hook_query` de la Fase C) es independiente y NO lo cubre esta skill.

---

## Los popups del flujo

### Popup `Config APIs` (3 preguntas en un solo AskUserQuestion)
```
questions = [
  {question: "HEYGEN_API_KEY — pulsa 'Other' y pega la key.", header: "HeyGen key",
   options: [{label:"Abrir Space Settings", description:"app.heygen.com → Settings → API"}, {label:"Cancelar setup"}]},
  {question: "ELEVENLABS_API_KEY — pulsa 'Other' y pega la key.", header: "ElevenLabs key",
   options: [{label:"Abrir API Keys", description:"elevenlabs.io/app/settings/api-keys"}, {label:"Cancelar setup"}]},
  {question: "PEXELS_API_KEY — pulsa 'Other' y pega (gratis, instantánea).", header: "Pexels key",
   options: [{label:"Abrir pexels.com/api", description:"Free, registro instantáneo"}, {label:"Cancelar setup"}]}
]
```
Tras este popup: llama a ElevenLabs `GET /v1/voices` con la key → lista de voces de la cuenta. Continúa.

### Popup `Voz` (1 pregunta)
```
{question: "Selecciona la voz clonada que quieres usar.", header: "Voice ID",
 options: [<hasta 4 voces de category=cloned de la cuenta>]}
 // Si el API falla o no hay clones → 'Other' para pegar el voice_id a mano.
```

### Popup `Avatar HeyGen` (2 preguntas) — ⚠️ engine V vs IV
```
questions = [
  {question: "¿Qué engine de HeyGen? Avatar V = mejor calidad de lip-sync, más caro, EXIGE foto que mire a cámara y subida por la UI de heygen.com. Avatar IV = más barato, algo menos de calidad, vale aunque NO mire de frente.",
   header: "Engine",
   options: [
     {label:"Avatar V (mejor calidad)", description:"Look subido por UI heygen.com. Más caro. Debe mirar a cámara."},
     {label:"Avatar IV (más barato)", description:"talking_photo. Menos calidad. Vale aunque no mire a cámara."}
   ]},
  {question: "Pega el ID de HeyGen de tu cuenta (look_id si elegiste Avatar V; talking_photo_id si IV). ⚠️ Los avatares de EJEMPLO del paquete (avatar-1.png…) NO califican como Avatar V — solo sirven como IV; para Avatar V sube TU foto por la UI de heygen.com y coge su look_id.",
   header: "HeyGen ID",
   options: [
     {label:"Abrir heygen.com", description:"Sube tu foto por la UI y copia el look_id"},
     {label:"Usar avatar de ejemplo (IV)", description:"Sube avatar-1.png como talking_photo (solo IV)"}
   ]}
]
```
Tras este popup:
- Si **Avatar V**: `setup.verify_look_avatar_v(look_id, HEYGEN_API_KEY)`.
  - `True` → guarda `HEYGEN_ENGINE="avatar_v"`, `HEYGEN_LOOK_ID=<id>`.
  - `False` → **NO concluyas "no sirve"**: hay delay tras subir la foto (puede tardar minutos en habilitar `avatar_v`). Avisa, ofrece reintentar el mismo look_id en unos minutos o caer a Avatar IV.
- Si **Avatar IV** con look_id pegado → `HEYGEN_ENGINE="avatar_iv"`, `HEYGEN_TALKING_PHOTO_ID=<id>`.
- Si **Avatar IV con foto de ejemplo** → `setup.upload_avatar_to_heygen(env)` (sube la foto, setea `HEYGEN_TALKING_PHOTO_ID`), `HEYGEN_ENGINE="avatar_iv"`.

### Popup `Preferencias creativas` (3 preguntas)
```
questions = [
  {question:"Nombre del avatar (etiqueta + carpeta de salida).", header:"Avatar name",
   options:[{label:"Maria"},{label:"Luis"},{label:"Juan"},{label:"Marcos"}]},  // 'Other' para custom
  {question:"Estilo de audio.", header:"Audio style",
   options:[{label:"reel (recomendado)", description:"Corta silencios + 1.20x — ritmo viral"},
            {label:"natural", description:"Velocidad real, sin tocar silencios"}]},
  {question:"Idioma del avatar.", header:"Idioma",
   options:[{label:"Español"},{label:"Inglés"}]}
]
```
Tras este popup:
1. `env = setup.apply_audio_style(env)` (expande AUDIO_STYLE → TTS_TEMPO + SILENCE_AGGRESSIVE)
2. `pipeline_core.save_env(env)` (guarda `~/.viral-pipeline/env.json`)
3. Mensaje corto `✓ Setup completo` que INCLUYE el **aviso de soporte/feedback** (distinto del CTA de "SKILL"): _"Si te topas con cualquier fallo o bug usando la skill, escríbeme por IG a [@mariokaizen](https://instagram.com/mariokaizen) y me lo cuentas — me ayuda a mejorarla."_ Este aviso va SOLO aquí, en el onboarding (no se repite en cada vídeo).
4. Lanza **automáticamente** el popup `Descripción del avatar`.

### Popup `Descripción del avatar` (1 pregunta) — alimenta los ángulos
```
{question:"Describe tu avatar (nicho, audiencia, doctrina, tono, formato estrella, CTA). Esto guía cómo se adapta cada viral a ti. Pulsa 'Other' para pegar la tuya, o usa el ejemplo.",
 header:"Descripción",
 options:[
   {label:"Usar ejemplo (finanzas/bolsa)", description:"Plantilla genérica editable"},
   {label:"Escribir la mía", description:"Selecciona 'Other' y pega tu descripción"}
 ]}
```
**Ejemplo genérico que ofreces (neutral, editable)** — guárdalo en `env["AVATAR_DESCRIPTION"]`:
> Avatar IA de fitness y pérdida de grasa, en español. **Audiencia:** hombres de 28-45 ocupados (trabajo + familia) que han probado mil dietas, no tienen 2h para el gym y quieren perder barriga sin pasar hambre. Enseña déficit calórico sin contar obsesivamente, entrenos de fuerza de 30-40 min, hábitos sostenibles, proteína suficiente y por qué el cardio infinito no es la solución. **Doctrina:** constancia > intensidad, comer proteína suficiente, fuerza antes que cardio, un mal fin de semana no arruina la semana, medir con foto y cinturón y no solo con la báscula. **Tono:** hook con promesa o cifra concreta en la 1ª frase ("Pierde la barriga sin pisar el gym 5 días") y a menudo una orden ("Haz esto antes de desayunar", "Deja de hacer este ejercicio"); 1-2 analogías sencillas por vídeo (el metabolismo no es un interruptor, es un termostato); cercano y directo, sin postureo de gurú ni "transformaciones milagro". **Formato estrella:** "deja de hacer X, haz Y" → mito común → qué pasa de verdad → el cambio mínimo que sí funciona. **CTA:** comentario → DM.

Tras guardar la descripción → lanza popup `Link del reel`.

### Popup `Link del reel`
```
{question:"URL del reel viral del que sacar adaptaciones (IG/TikTok/YouTube).", header:"Link reel",
 options:[{label:"Pegar nueva URL", description:"Selecciona 'Other' y pega el link"}, {label:"Cancelar"}]}
```
Tras este popup:
1. `step1_download_and_transcribe(<url>)` — descarga (h264+audio) + transcripción
2. Diseca el patrón narrativo en chat (hook → desarrollo → CTA). **Aquí mismo**, extrae las **frases más virales** del clip y guárdalas con `store_viral_phrases(...)` / `step1b_store_viral_phrases(...)` en el banco `viral_phrases` (ver **Regla 8**) — banco para historias IG futuras; hoy SOLO se almacenan.
3. Reescribe usando `env["AVATAR_DESCRIPTION"]` → propone **3 guiones** (mismo patrón, 3 ángulos distintos). ⚠️ El **hook de inicio (1ª frase)** de CADA guion se genera **SIEMPRE** con la skill `viral-hook-creator` (ver Regla 7); nunca lo redactes a mano.
4. Lanza popup `Aprobación`

### Popup `Aprobación` (1 pregunta) — elegir cuántos, o pedir cambios
```
{question:"¿Con cuál avanzamos? Elige uno, los 3, o escribe en 'Other' qué cambiarías (p.ej. duración, hook, CTA) y te lo re-propongo.",
 header:"Avanzar",
 options:[
   {label:"Avanzar con 1", description:"Solo el guion 1"},
   {label:"Avanzar con 2", description:"Solo el guion 2"},
   {label:"Avanzar con 3", description:"Solo el guion 3"},
   {label:"Avanzar con los 3", description:"Procesa los tres"}
 ]}
 // 'Other' = el usuario escribe los cambios → re-propones y vuelves a preguntar.
```
La mayoría querrá UNO (no 3 casi iguales): por eso 1/2/3 son opciones primarias visibles, no un detalle.

---

## Procesamiento POR FASES (gates)

Para cada guion seleccionado, `avatar = env["AVATAR_NAME"]`, `slug = pipeline_core.slugify(<hook del guion>)`, `lang = "es"|"en"`.

**Fase A — Audio**
```
a = phase_a_audio(env, script, avatar, slug)
```
→ Enseña `a["local_path"]` (MP3) + `final_seconds`. **GATE**: popup pidiendo aprobar el audio antes de gastar HeyGen. Si hay erratas/entonación → regenera.

**Fase B — HeyGen** (solo tras aprobar A)
```
b = phase_b_heygen(env, a["audio_path"], avatar, slug)   # usa engine V o IV de env
```
HeyGen tarda; lánzalo en background y avisa. → Enseña `b["local_path"]`. **GATE**: popup para validar lip-sync/look antes de editar.

**Fase C — Edición final** (solo tras aprobar B)
```
c = phase_c_edit(env, b["heygen_path"], avatar, slug, lang=lang, hook_query="<query EN>", proyecto="<id>")  # b-roll local + gancho imagen libre
```
**Proyecto:** `proyecto` es el id de `TheEditor/proyectos/<id>/` (por defecto `mongemalo`). Con banco común (MongeMalo) todo va como siempre; un proyecto con recursos propios usa solo su `recursos/broll/` y `recursos/musica/`, y si tiene `internet: false` no hay gancho de Pexels ni imagen libre (el código lo bloquea).

**Gancho (MINI-VIDEO Pexels, OBLIGATORIO):** pasa SIEMPRE `hook_query`. Antes de fijarlo, **ANALIZA bien el clip** (su hook hablado, su tema y su remate) y elige una query que dé un clip con **muchísimo gancho visual** (impactante, emocional, que pare el scroll) y con **relación clara con lo que se ve/oye a continuación** — nada genérico ni aleatorio. Query en **inglés** (mejores resultados) y concreta/visual (p.ej. miedo a emprender → `"person standing edge cliff looking down"`; marca/Coca-Cola → `"pouring cola glass bubbles"`). Se descarga un MINI-VIDEO vertical de **Pexels** (`env['PEXELS_API_KEY']`) y se superpone a pantalla completa los primeros ~2.5s como gancho. Sin key Pexels → fallback a imagen libre (Openverse). Si no pasas `hook_query`, se deriva del slug (último recurso).

**B-roll (superposiciones LOCALES, SINCRONIZADO + SEMÁNTICO):** el b-roll a pantalla completa se coloca **alineado a la voz** — se transcribe el avatar con word-timestamps, se detectan las frases (por pausas y puntuación de cierre) y cada corte **entra al arrancar una frase y sale en la pausa siguiente**, con cadencia ~6.5s (no bajo el gancho inicial ni en la cola). Para cada ventana se elige el clip **por SIGNIFICADO**: se embebe la frase (`fastembed`, modelo `paraphrase-multilingual-MiniLM-L12-v2`, 384d, local) y se consulta la tabla `broll_assets` de Supabase vía RPC `match_broll` → el vídeo local más afín. Se **descartan** los clips marcados `aviso-*` (marca/persona ajena, marca de agua, baja calidad) y no se repite clip. Si la mejor similitud no llega al umbral (~0.30) o no hay Supabase/`fastembed`/creds, cae a un clip LOCAL **al azar** (best-effort, sin romper el flujo). Requiere `SUPABASE_URL` + `SUPABASE_ANON_KEY` en `env.json`. Los vídeos salen de `superposiciones/` (o `env['OVERLAYS_DIR']`) — NO Pexels. Si no se detectan frases, cae a intervalos regulares (legacy). Esa misma transcripción alimenta los subtítulos (una sola pasada de Whisper). El catálogo se genera/actualiza con `broll_assets.sql` (en TheLanding) + los scripts de indexación (analizar frames → embeddings → upsert).
→ Se compone: gancho (imagen libre ~1.8s) + cortes de b-roll + **subtítulos** encima de todo + música de la carpeta LOCAL `musicas/` (o `env['MUSIC_DIR']`) + de-click. Output local en `c["local_path"]`. Si `c["cta"]` no es None, imprímelo (markdown).

**Subtítulos (REGLAS DURAS, `_generate_ass_karaoke`):**
- **Fuente Montserrat** (en `fonts/`, se pasa `fontsdir` a ffmpeg), **blanco con reseguido negro grueso + sombra suave**. Nada de blanco sin borde, ni tipografías que se descuadren con acentos.
- **1 sola línea, máximo 3 palabras**, en **minúsculas** (mayúscula al inicio y tras `.`, `?`, `!`). El grupo se corta tras un fin de frase y nunca acaba en artículo, preposición o «que» si hay otra palabra detrás. Limpio y fácil de leer.
- **Ubicación: a la altura de la BARBILLA** (centrado horizontal, `Alignment=2` + `MarginV≈640`). NUNCA tapar boca ni ojos (conexión emocional), ni dejarlo al fondo de la pantalla.
- **Estáticos, SIN animación/movimiento** (aparecen y desaparecen). Nada de karaoke, zoom, letra en movimiento → más retención.
- Palabrotas enmascaradas (`_mask_profanidad`, p.ej. `j***`).
- Nota: `MarginV≈640` está calibrado para plano centrado de busto (cara centrada). Con encuadres muy distintos, ajustar o añadir detección de cara.

Si se eligió "los 3": haz Fase A de los 3 → un GATE → Fase B de los 3 → un GATE → Fase C de los 3.

---

## Salida: 100% LOCAL

Cada archivo (Audio, Video Heygen, Video Editado) se guarda en:
```
~/Desktop/viral_pipeline_output/<Avatar>/<slug-del-hook>/<campo>__<archivo>
```
- Carpeta por **avatar**, subcarpeta con **nombre legible** (slug del hook) — NO "Video 1/2", para que una serie descontinuada no se líe.
- Menciona SIEMPRE la ruta `~/Desktop/viral_pipeline_output/<Avatar>/` al cerrar.

### Airtable (opcional, fuera del flujo)
Esta versión NO sube a Airtable: la salida es local. El código Airtable queda **dormido** en `pipeline_core` (`airtable_create/airtable_patch/airtable_attach`) por si en el futuro se re-enchufa un backend (propio o Airtable). **Solo** menciónalo si el cliente pregunta explícitamente por Airtable; no lo metas en el onboarding.

---

## ⚙️ Python y setup

**En el equipo de Sergio (TheEditor) no hay que hacer bootstrap.** Todo se ejecuta
con el venv de TheEditor, con el cwd en la carpeta de la skill:
```
C:\Users\ico858\Desktop\PruebasIA\TheEditor\.venv\Scripts\python.exe
```
(nunca el Python global ni `python3`, que en Windows es el acceso directo de la
Microsoft Store). `download_reel` usa el `yt-dlp.exe` de TheDescarga
(`..\TheDescarga\tools\yt-dlp.exe`, con su `ffmpeg.exe`), porque el venv de
TheEditor no trae el módulo `yt_dlp`.

En otro equipo sin TheEditor (cross-platform):
```bash
bash <SKILL_DIR>/bootstrap.sh      # macOS / Linux
python <SKILL_DIR>/bootstrap.py    # Windows (o universal)
```
Crean venv en `~/.viral-pipeline/venv/` (`bin/python3` o `Scripts/python.exe`),
instalan `httpx`/`faster-whisper`/`Pillow`/`imageio-ffmpeg`/`yt-dlp` y verifican libass.

**¿Saltar el setup?** Solo si `env.json` tiene las claves de HeyGen y ElevenLabs.
Compruébalo (desde la carpeta de la skill):
```
<python> setup.py faltan     → «SETUP_OK» o «FALTAN: HEYGEN_API_KEY, …»
```
- `SETUP_OK` → SKIP setup: popup `Descripción del avatar` (si falta `AVATAR_DESCRIPTION`) o `Link del reel`.
- `FALTAN: …` → popups del setup solo para lo que falta (`Config APIs`, `Voz`,
  `Avatar HeyGen`), conservando lo que ya hay en `env.json` (Supabase, Pexels…).
  Que exista `env.json` **no** basta: hoy solo trae Supabase y Pexels.

---

## Sistema de CTA (sin pitch en onboarding)
**CTA único** = DM por IG con la palabra **SKILL** a [@mariokaizen](https://instagram.com/mariokaizen) (sustituye al de la llamada). `bump_success_counter()` lo devuelve con **frecuencia DECRECIENTE**: vídeo **1**, luego **3, 6, 12, 24, 48…** (el hueco dobla → cada vez menos, para no dar la vara). En cualquier otra cuenta devuelve `None`. El primer toque solo aparece cuando ya hay un vídeo hecho. `success_counter.txt` persiste. Imprime el CTA tal cual (link ya markdown).

---

## Costes (resumen)
- Avatar IV ~€1.40/vídeo 30s (HeyGen $0.05/s). Avatar V cuesta más por segundo (mejor calidad).
- Suscripciones ~€5/mes (ElevenLabs Starter). Pexels + hosts = €0. HeyGen pay-as-you-go.
- Desglose en [PRICING.md](PRICING.md).

---

## Trigger keywords
"viral pipeline" / "viral pipeline v4" / "monta sistema viral" / "setup viral" / "adaptaciones de este reel"

## Resumen del comportamiento
- Popups via AskUserQuestion: Config APIs · Voz · Avatar HeyGen (engine V/IV + ID) · Preferencias · Descripción · Link · Aprobación
- Avatar V (look UI, /v3 avatar_v) o IV (talking_photo, /v2) — dispatcher `heygen_generate_for_env`
- Procesa POR FASES con gates (A audio → B HeyGen → C edición)
- Hook de inicio de cada guion SIEMPRE generado con la skill `viral-hook-creator` (Regla 7)
- Al analizar cada viral, guarda sus frases más virales en Supabase `viral_phrases` (banco para historias IG futuras; hoy SOLO se almacenan) — Regla 8
- Aprobación: avanzar con 1 / 2 / 3 / los 3, o 'Other' para cambios
- Salida 100% LOCAL en `~/Desktop/viral_pipeline_output/<Avatar>/<slug>/` (Airtable dormido, solo si preguntan)
- Sin numeración "popup X/Y"; CTA tras 1er vídeo; links cal.com markdown
- Cross-platform (bootstrap.py en los tres OS)

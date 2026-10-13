# TheTextos — Departamento de textos largos para blog

Escribe **textos largos para blogs** (más de 500 palabras) optimizados a la vez
para **SEO clásico** (Google) y para **buscadores y crawlers de IA** (GEO/AEO:
ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews / AI Mode). Lo dirige
CEO_Sergete a través del subagente `textos`.

Idioma por defecto: **español de España**, salvo que Sergio pida otro.

---

## Tipos de texto — PENDIENTE de especificar

Habrá **dos tipos** de texto largo. Sergio dará las especificaciones; hasta
entonces no inventes cómo son: si te piden un texto de un tipo concreto y aquí
sigue pendiente, pregunta.

| Tipo | Para qué | Longitud | Plantilla base | Estado |
|---|---|---|---|---|
| Tipo 1 | _por definir_ | _por definir_ | _por definir_ | PENDIENTE |
| Tipo 2 | _por definir_ | _por definir_ | _por definir_ | PENDIENTE |

Plantillas disponibles en `~/.claude/skills/blog/templates/` (how-to-guide,
pillar-page, listicle, comparison, faq-knowledge, product-review, case-study,
tutorial, roundup, data-research, news-analysis, thought-leadership).

**También pendiente:** formato de entrega final (Markdown por defecto).

---

## Por proyecto

Cada proyecto (cuenta/cliente; índice en `CEO_Sergete/proyectos.json`) tiene
`proyectos/<id>/`:
- `proyecto.json`: blog de destino, nicho, autor que firma (E-E-A-T), idioma,
  enlaces internos y reglas del proyecto;
- `marca/BRAND.md` y `marca/VOICE.md` (voz).

Lee **solo** el del proyecto del texto. Si un campo dice `PENDIENTE`,
pregúntalo en vez de inventarlo. El proyecto se indica siempre; si no se dice y
solo hay uno, es ese; si hay varios, pregunta. Proyecto nuevo: copia
`proyectos/_plantilla/`.

---

## Skills que usa (instaladas a nivel global)

| Skill | Para qué en este flujo |
|---|---|
| `blog-brief` | Brief: keyword principal y secundarias, intención, estructura, datos a buscar |
| `blog-write` | Reglas de redacción y plantillas (answer-first, Key Takeaways, FAQ, E-E-A-T) |
| `ai-seo` | Principios GEO/AEO: cómo escribir para que las IAs te citen |
| `blog-geo` | Auditoría de citabilidad por IA (0–100) |
| `blog-seo-check` | Checklist SEO on-page (title, meta, H1–H3, keyword, enlaces, alt) |
| `blog-factcheck` | Verifica cada cifra y afirmación contra su fuente |
| `blog-schema` | JSON-LD (BlogPosting/Article + FAQPage + BreadcrumbList) |
| `clean-user-facing-text` | **Pasada final obligatoria** (Unicode invisible + reescritura natural) |

Los `SKILL.md` están en `C:\Users\ico858\.claude\skills\<skill>\SKILL.md`; sus
referencias, en `…\<skill>\references\` y, las comunes, en
`…\skills\blog\references\`.

### Cómo se ejecutan los scripts (Windows)

- Python: **siempre** `C:\Users\ico858\Desktop\PruebasIA\TheTextos\.venv\Scripts\python.exe`
  (trae `textstat` + `beautifulsoup4`). **Nunca** `python3`: en este equipo es
  el acceso directo de la Microsoft Store y no funciona.
- Cuando una skill diga `python3 scripts/<x>.py`, el script está en
  `C:\Users\ico858\.claude\scripts\<x>.py`. Los de una skill concreta, en
  `C:\Users\ico858\.claude\skills\<skill>\scripts\`.
- Antepón `PYTHONIOENCODING=utf-8` en Bash para que las tildes salgan bien.
- Limitación: `analyze_blog.py` y `ai_citation_score.py` solo están calibrados
  para inglés (y turco). En español, sus notas de legibilidad son
  **orientativas**; mandan los checklists de las skills.
- Las comprobaciones de `blog-write` de imagen de portada, PDF y capturas con
  Playwright **no se usan** hasta que Sergio defina el formato de entrega.

---

## Flujo por texto

Carpeta de trabajo: `textos/<proyecto>/<AAAA-MM-DD>_<slug>/`.

1. **Brief** (`blog-brief`) → `brief.md`: keyword principal + secundarias,
   intención de búsqueda, tipo de texto, plantilla, H2/H3 previstos, preguntas
   reales de la gente (FAQ) y datos que hay que buscar con fuente.
2. **Investigación**: busca datos y fuentes reales (WebSearch/WebFetch). Prioriza
   fuentes oficiales, estudios y medios de referencia; anota URL y fecha.
3. **Redacción** (`blog-write`) → `articulo.md` con frontmatter:
   `title` (≤ 60 caracteres, keyword al principio), `description` (140–160
   caracteres), `slug`, `keyword`, `lang: es`, `fecha`, `autor`.
4. **Optimización GEO** (`ai-seo` + `blog-geo`):
   - Respuesta directa en las 1–2 primeras frases del texto y de cada H2
     (*answer-first*), que se entienda sola si una IA la cita aislada.
   - Bloque de puntos clave o TL;DR al inicio.
   - Definiciones claras de las entidades (qué es X) y nombres consistentes.
   - Cifras con fuente y año, enlazadas. Afirmaciones citables y autocontenidas.
   - Listas, pasos numerados y tablas comparativas donde aporten.
   - FAQ con preguntas reales (las del brief) y respuestas cortas.
   - Señales E-E-A-T: autor, experiencia propia si la hay, fecha de actualización.
5. **SEO on-page** (`blog-seo-check`): un solo H1; jerarquía H2/H3 limpia; keyword
   en title, H1, primer párrafo, algún H2 y slug, sin forzarla; zonas de enlace
   interno marcadas; 2–5 enlaces externos de autoridad; alt text en imágenes.
6. **Verificación de datos** (`blog-factcheck`): **ninguna cifra inventada**. Si
   un dato no se puede verificar, se quita o se marca `[VERIFICAR]` y se avisa.
7. **Schema** (`blog-schema`) → `schema.json`: BlogPosting/Article + FAQPage (si
   hay FAQ) + BreadcrumbList. Solo con lo que aparece de verdad en el texto.
8. **Pasada final obligatoria — `clean-user-facing-text`** (siempre, por ser >500
   palabras; es lo **último** que toca el texto):
   Scripts en `C:\Users\ico858\.claude\skills\clean-user-facing-text\scripts\`.
   1. Medir antes: `inspect_text.py --stylometry --json articulo.md`.
   2. Layer A sobre el archivo: `clean_text.py articulo.md --in-place --stats --no-normalize-spaces`
      (deja `articulo.md.bak`; bórralo al terminar si todo va bien).
   3. Layer B (reescritura) **solo** si `density_tier` = `high`. Al reescribir,
      **no toques**: title, description, slug, headings, la keyword en sus
      posiciones, las preguntas de la FAQ, anclas de enlaces, cifras, nombres ni
      el frontmatter.
   4. Layer A otra vez y medir de nuevo. Si hubo Layer B, repasa `blog-seo-check`.
9. **Informe** → `informe.md`: keyword, nº de palabras, resultado del check SEO,
   puntuación GEO, fuentes usadas, stylometry antes/después, avisos y pendientes.

### Revisión independiente (la orquesta el CEO)

Tras el paso 9, el CEO pasa `articulo.md` al agente `blog-reviewer`. Los puntos
de nivel sitio (velocidad, robots.txt, imágenes optimizadas) se marcan N/A en un
borrador. Si sale `BLOCKING: true` o hay algún P0, vuelve a `textos` con la
revisión para corregirlo (máx. 2 vueltas) y se repite la pasada final (paso 8).

---

## Crawlers de IA: lo que NO depende del texto

Que los bots de IA puedan leer el blog es cosa **del sitio**, no del artículo:
`robots.txt` que permita GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot y
Google-Extended; HTML estático/SSR (sin contenido solo en JS); `llms.txt`;
sitemap actualizado. TheTextos lo **recomienda** en el informe; aplicarlo
corresponde al departamento que lleve la web (p. ej. TheLanding).

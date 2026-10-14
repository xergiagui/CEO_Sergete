# TheTextos

Departamento de **CEO_Sergete** que escribe **textos largos para blogs** (más de
500 palabras) optimizados para **SEO** (Google) y para **buscadores y crawlers de
IA** (GEO/AEO: ChatGPT, Perplexity, Claude, Gemini, AI Overviews).

> Se lanza **a demanda** desde CEO_Sergete («escríbeme un artículo de blog
> sobre…»). Las reglas completas están en [`CLAUDE.md`](CLAUDE.md).

## Estructura

| Carpeta / archivo | Qué lleva |
|---|---|
| `referencias/checklist.md` | resumen operativo de las skills (redacción, muletillas, GEO 7, SEO 12, factcheck, schema, reglas de proyecto); sustituye a los SKILL.md en el día a día |
| `plantillas/brief.md` | brief + investigación en un paso, con la tabla de datos verificados |
| `plantillas/schema.json` | JSON-LD base: BlogPosting + Person + Organization + BreadcrumbList (+ FAQPage si hay FAQ) |
| `textos/<proyecto>/<AAAA-MM-DD>_<slug>/` | un texto: `brief.md`, `articulo.md` (final), `schema.json`, `informe.md` |
| `proyectos/<id>/` | `proyecto.json` (blog, nicho, autor, `landing`, `afiliado`, enlaces internos, reglas) + `marca/BRAND.md`·`VOICE.md`; `_plantilla/` para proyectos nuevos |
| `.venv/` | Python propio (`textstat`, `beautifulsoup4`) para los scripts de las skills |
| `requirements.txt` | dependencias del `.venv` |

## Flujo

Arranque (solo `CLAUDE.md` + checklist + `proyecto.json`, con los PENDIENTES
comprobados) → **1** brief + investigación → **2** redacción → **3** autochequeo
único (GEO + SEO + proyecto + factcheck contra la tabla de datos) → **4**
`schema.json` → **5** pasada final `clean-user-facing-text` → **6** informe →
revisión independiente (`blog-reviewer`, la lanza el CEO).

## Skills (globales, en `~/.claude/skills/`)

El checklist resume lo que hace falta de ellas; los SKILL.md solo se leen en los
casos de «Leer solo cuando haga falta» de `CLAUDE.md`.

- **claude-blog** (`AgriciDaniel/claude-blog`): `blog-brief`, `blog-write`,
  `blog-geo`, `blog-seo-check`, `blog-factcheck`, `blog-schema` y el resto de la
  suite `blog-*`, además de sus agentes (`blog-reviewer`, etc.) en
  `~/.claude/agents/`. Se copió a mano (no se actualiza con `npx skills update`).
  Desde el 14-oct-2026 sus 32 `SKILL.md` llevan `disable-model-invocation: true`
  para no cargar su descripción en cada sesión: se leen por ruta y siguen
  funcionando como `/comando`. **Si se reinstala claude-blog, hay que volver a
  ponerlo.**
- **clean-user-facing-text** (`guillaumemeyer/watermarks-remover`): limpieza
  final de todo texto de más de 500 palabras (scripts en su carpeta `scripts/`).
- **ai-seo** (`coreyhaines31/marketingskills`): estrategia GEO de sitio; no se
  usa en los artículos.

## Pendiente

- Los **dos tipos de texto** (qué son, longitud, plantilla): los define Sergio.
- El formato de entrega final (Markdown por defecto).
- **Por proyecto** (en `proyectos/<id>/`): blog de destino, marca, voz y autor.
  En MongeMalo siguen PENDIENTES; mientras, se escribe con firma provisional,
  `{siteUrl}` como marcador y la voz provisional de TheCopy, con aviso en el
  informe.

## Recrear el entorno

```bash
py -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

# TheTextos

Departamento de **CEO_Sergete** que escribe **textos largos para blogs** (más de
500 palabras) optimizados para **SEO** (Google) y para **buscadores y crawlers de
IA** (GEO/AEO: ChatGPT, Perplexity, Claude, Gemini, AI Overviews).

> Se lanza **a demanda** desde CEO_Sergete («escríbeme un artículo de blog
> sobre…»). Las reglas completas están en [`CLAUDE.md`](CLAUDE.md).

## Estructura

| Carpeta / archivo | Qué lleva |
|---|---|
| `textos/<proyecto>/<AAAA-MM-DD>_<slug>/` | un texto: `brief.md`, `articulo.md` (final), `schema.json`, `informe.md` |
| `proyectos/<id>/` | `proyecto.json` (blog, nicho, autor, enlaces internos) + `marca/BRAND.md`·`VOICE.md`; `_plantilla/` para proyectos nuevos |
| `.venv/` | Python propio (`textstat`, `beautifulsoup4`) para los scripts de las skills |
| `requirements.txt` | dependencias del `.venv` |

## Flujo

brief → investigación → redacción → GEO → SEO on-page → verificación de datos
→ schema JSON-LD → **pasada final `clean-user-facing-text`** → informe →
revisión independiente (`blog-reviewer`, la lanza el CEO).

## Skills (globales, en `~/.claude/skills/`)

- **claude-blog** (`AgriciDaniel/claude-blog`): `blog-brief`, `blog-write`,
  `blog-geo`, `blog-seo-check`, `blog-factcheck`, `blog-schema` y el resto de la
  suite `blog-*`, además de sus agentes (`blog-writer`, `blog-researcher`,
  `blog-reviewer`, `blog-seo`, `blog-translator`) en `~/.claude/agents/` y sus
  scripts en `~/.claude/scripts/`.
- **ai-seo** (`coreyhaines31/marketingskills`): GEO/AEO.
- **clean-user-facing-text** (`guillaumemeyer/watermarks-remover`): limpieza
  final de todo texto de más de 500 palabras.

## Pendiente

Los **dos tipos de texto** (qué son, longitud, plantilla), el blog de destino,
la marca y la voz, el autor y el formato de entrega. Ver `CLAUDE.md`.

## Recrear el entorno

```bash
py -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

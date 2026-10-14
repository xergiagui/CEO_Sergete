# TheTextos — Departamento de textos largos para blog

Escribe **textos largos para blogs** (más de 500 palabras) optimizados para
**SEO** (Google) y para **buscadores de IA** (GEO/AEO: ChatGPT, Perplexity,
Claude, Gemini, AI Overviews). Lo dirige CEO_Sergete a través del subagente
`textos`. Idioma por defecto: **español de España**, salvo que Sergio pida otro.

> **Este archivo manda** sobre la descripción del subagente: los SKILL.md
> **no** se leen por defecto. El día a día va con `referencias/checklist.md`,
> que resume las skills `blog-*` y `clean-user-facing-text` para este caso.

---

## Tipos de texto — PENDIENTE de especificar

Habrá **dos tipos** de texto largo. Sergio dará las especificaciones; hasta
entonces no inventes cómo son.

| Tipo | Para qué | Longitud | Plantilla base | Estado |
|---|---|---|---|---|
| Tipo 1 | _por definir_ | _por definir_ | _por definir_ | PENDIENTE |
| Tipo 2 | _por definir_ | _por definir_ | _por definir_ | PENDIENTE |

Si no se pide un tipo, la estructura sale del brief (formato que domina la
SERP). **También pendiente:** formato de entrega final (Markdown por defecto).

---

## Por proyecto

Cada proyecto (índice en `CEO_Sergete/proyectos.json`) tiene `proyectos/<id>/`:
- `proyecto.json`: blog de destino, nicho, autor, idioma, enlaces internos y
  reglas propias del blog;
- `marca/BRAND.md` y `marca/VOICE.md` (voz del blog, si se definen).

La **identidad** del proyecto (landing y parámetro de afiliado para los CTA, voz,
palabras prohibidas, afiliación, no suplantar) es fuente única en
`CEO_Sergete/proyectos.json → identidad`: léela de ahí, no la copies aquí.

Blog, marca, voz y autor se definen **por proyecto**. Si no se dice el proyecto
y solo hay uno, es ese; si hay varios, pregunta. Proyecto nuevo: copia
`proyectos/_plantilla/`.

---

## Arranque: lo único que se lee

1. Este `CLAUDE.md`, `referencias/checklist.md`, `proyectos/<id>/proyecto.json`
   (y `marca/*.md` solo si existen y no están PENDIENTES) y la identidad:
   `"$PY" -c "import json;print(json.dumps([p['identidad'] for p in json.load(open('C:/Users/ico858/Desktop/PruebasIA/CEO_Sergete/proyectos.json',encoding='utf-8'))['proyectos'] if p['id']=='<id>'][0],ensure_ascii=False,indent=1))"`
2. **Comprueba los PENDIENTES antes de leer nada más:**
   - **Bloqueantes:** tema/keyword, público y, si se pide un tipo concreto, que
     ese tipo no siga PENDIENTE. Si falta uno, devuelve al CEO las preguntas
     concretas y no hagas nada más.
   - **No bloqueantes** (se sigue y se avisa en el informe):
     - autor → firma provisional `author: "[AUTOR PENDIENTE]"`;
     - blog de destino → `{siteUrl}` y `{organizacion}` se quedan como
       marcador en el schema; canonical N/A;
     - voz del blog → voz provisional = `identidad.voz` (persona y tono), con
       sus `palabras_prohibidas`.

## Cómo se ejecutan los scripts (Windows, Git Bash)

Cada llamada a Bash empieza con estas líneas (el estado del shell no se
conserva entre llamadas):

```bash
export PYTHONIOENCODING=utf-8
PY="/c/Users/ico858/Desktop/PruebasIA/TheTextos/.venv/Scripts/python.exe"
S="$HOME/.claude/skills/clean-user-facing-text/scripts"
T="/c/Users/ico858/Desktop/PruebasIA/TheTextos"
D="$T/textos/<proyecto>/<AAAA-MM-DD>_<slug>"
```

**Nunca** `python3`: en este equipo es el acceso directo de la Microsoft Store.

---

## Flujo por texto

Carpeta: `textos/<proyecto>/<AAAA-MM-DD>_<slug>/` con `brief.md`,
`articulo.md`, `schema.json` e `informe.md`.

### Paso 1 — Brief + investigación → `brief.md`

Un solo paso, sobre `plantillas/brief.md`:
- **SERP:** WebSearch de la keyword y trabajo con los snippets (formato
  dominante, preguntas PAA, AI Overview si se ve, huecos). Como mucho **2
  WebFetch de competidores**.
- **Datos:** fuentes T1–T3 (checklist §4). Cada dato se **verifica al
  recogerlo**: se abre la fuente y se copia el fragmento literal a la tabla.
  Lo que no se verifica no entra.
- La redacción **no vuelve a investigar**: si falta un dato, se escribe sin él
  o con `[VERIFICAR]`.

### Paso 2 — Redacción → `articulo.md`

Aplica desde el principio el checklist (§1 redacción, §6 proyecto, §7 autor).
Frontmatter:

```yaml
---
title: "…"
description: "…"
slug: "…"
keyword: "…"
lang: es-ES
date: AAAA-MM-DD
lastUpdated: AAAA-MM-DD
author: "…"
tags: ["…", "…", "…"]
---
```

### Paso 3 — Autochequeo único

1. Repasa **GEO 7 + SEO 12 + reglas del proyecto** (checklist §2, §3, §6) y
   corrige sobre la marcha (el punto 7 de GEO, en el paso 4).
2. Medidas y muletillas:
   ```bash
   "$PY" -c "import re,sys;t=open(sys.argv[1],encoding='utf-8').read();_,fm,b=t.split('---',2);g=lambda k:(re.search(r'^'+k+r':\s*\"?(.*?)\"?\s*$',fm,re.M) or [0,''])[1];print('title',len(g('title')),'| description',len(g('description')),'| H1',len(re.findall(r'^# ',b,re.M)),'| H2',len(re.findall(r'^## ',b,re.M)),'| URLs',len(set(re.findall(r'https?://[^\s)\"<>]+',b))),'| palabras',len(b.split()))" "$D/articulo.md"
   grep -n -i -E -f <(sed -n '/^```muletillas$/,/^```$/{/^```/!p}' "$T/referencias/checklist.md") "$D/articulo.md"
   ```
3. **Factcheck cruzando con la tabla de datos:** cada cifra o afirmación con
   fuente del artículo tiene que estar en la tabla con el mismo valor y la
   misma fuente. Solo se vuelven a descargar las **nuevas o cambiadas** (y se
   añaden a la tabla). Lo que no se pueda verificar se quita o se marca
   `[VERIFICAR]`.

### Paso 4 — `schema.json`

Desde `plantillas/schema.json` (checklist §5). `{organizacion}` es el nombre
del sitio que publica; `{autor-slug}`, el autor en minúsculas y con guiones.
Si no hay FAQ visible, se borra el nodo FAQPage. Se valida con
`"$PY" -m json.tool "$D/schema.json" > /dev/null`.

### Paso 5 — Pasada final `clean-user-facing-text`

Obligatoria y lo **último** que toca el texto. No se lee su SKILL.md salvo que
haga falta Layer B.

1. **Medir** el cuerpo sin frontmatter:
   ```bash
   awk 'NR==1&&/^---/{f=1;next} f&&/^---/{f=0;next} !f' "$D/articulo.md" | "$PY" "$S/inspect_text.py" --stylometry --json - | "$PY" -c "import json,sys;r=json.load(sys.stdin);s=r['stylometry'];print('invisibles',r['suspicious_total'],'| palabras',s.get('word_count'),'| score',s.get('score'),'| tier',s.get('density_tier'),'| burstiness_cv',s.get('burstiness_cv'))"
   ```
2. **Layer A:**
   ```bash
   "$PY" "$S/clean_text.py" "$D/articulo.md" --in-place --no-normalize-spaces && rm -f "$D/articulo.md.bak"
   ```
3. **Layer B** (regla global de Sergio en `~/.claude/CLAUDE.md`, adaptada al
   español el 14-oct-2026) si se cumple **cualquiera**: `tier` = `high`,
   `burstiness_cv` < 0,35, o 3+ muletillas en el grep del paso 3 del flujo.
   Entonces lee el SKILL.md de la skill y reescribe una vez sin tocar
   el frontmatter, los encabezados, la keyword en sus posiciones, las preguntas
   de la FAQ, las anclas, las cifras, los nombres ni el aviso de afiliación.
   Después, **Layer A otra vez, medir otra vez** y repetir las medidas del
   paso 3.
4. Si no hubo Layer B, se termina tras Layer A (stylometry después = antes).

### Paso 6 — `informe.md` corto

Keyword, palabras, `SEO X/12` (y qué falla), `GEO X/7`, stylometry
antes/después (score y tier), caracteres retirados en Layer A, 3–5 fuentes
clave, `[VERIFICAR]` y PENDIENTES usados (autor, `{siteUrl}`, voz
provisional), y lo que toque del sitio (ver «Crawlers»).

Al CEO se le devuelve lo que pide la descripción del subagente, sin pegar el
artículo.

---

## Leer solo cuando haga falta

- `~/.claude/skills/blog/templates/<x>.md`: la primera vez que se defina un tipo.
- `blog-factcheck/SKILL.md`: con fuentes de pago, PDF o dudosas.
- `blog-schema/SKILL.md`: si hace falta VideoObject, Product o Review.
- `blog/references/eeat-signals.md`: para la bio del autor.
- `blog/references/internal-linking.md`: con 5 o más enlaces internos.
- `clean-user-facing-text/SKILL.md`: solo si hay Layer B.
- `TheCopy/proyectos/<id>/ofertas.json`: si el CTA va a una oferta concreta
  (URL reales con el parámetro de afiliado).

**Nunca en un artículo:** `ai-seo` (es estrategia de sitio y se contradice con
`blog-geo` y `blog-schema`), `blog-reviewer.md` ni las fases visuales de
`blog-write` (portada, imágenes, SVG, YouTube, NotebookLM, PDF, preflight).

## Modo corrección

Cuando el texto vuelve con la revisión del CEO: lee **solo** la revisión,
`articulo.md` e `informe.md`; aplica los arreglos (cifras nuevas, verificadas
y añadidas a la tabla del brief), repite el **paso 5** y actualiza el informe.
Sin leer skills.

## Revisión independiente

La lanza el CEO (regla en `CEO_Sergete/CLAUDE.md`). Se le pasa la carpeta:
`articulo.md` + `schema.json` + tabla de datos.

## Crawlers de IA

Que los bots de IA lean el blog depende del sitio (robots.txt, SSR, `llms.txt`,
sitemap), no del artículo: se recomienda en el informe.
Si el destino es TheLanding (ya tiene `robots.ts` y `llms.txt`), solo se pide
añadir la URL al sitemap y a `llms.txt`.

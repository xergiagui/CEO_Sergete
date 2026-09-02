# CEO_Sergete

**Centro de mando.** Abres *solo* esta carpeta y le das órdenes en lenguaje
natural. CEO_Sergete entiende la petición y la **delega al departamento
correcto**, coordina y te responde. No contiene el código de los departamentos:
los **dirige por ruta** mediante subagentes.

```
PruebasIA/
├── CEO_Sergete/        ← ABRES SOLO ESTO
│   ├── CLAUDE.md            cerebro / protocolo de dirección
│   ├── departamentos.json   registro maestro (rutas, repos, disparadores)
│   ├── .claude/agents/      un subagente por departamento
│   ├── .env                 Supabase compartido (no en git)
│   └── supabase/            ceo_tasks.sql (historial opcional)
├── TheDescarga/        departamento: descarga de vídeo/audio (yt-dlp)
├── TheEditor/          departamento: pipeline viral (avatar IA + edición)
└── TheLanding/         departamento: web de afiliación (Next.js + Supabase)
```

## Departamentos

| Di algo como… | CEO delega en | Qué hace |
|---|---|---|
| «descárgame este reel» + URL | **TheDescarga** | Baja el vídeo/audio a `TheDescarga/descargas/` |
| «monta adaptaciones de este reel» | **TheEditor** | Link → avatar IA (HeyGen) → b-roll + subs + música |
| «cambia esto de la landing» | **TheLanding** | Edita/despliega la web (Vercel) |

También puedes encadenar: *«descarga este reel y móntame 3 adaptaciones»* →
CEO corre `descarga` y pasa el MP4 a `editor`.

## Añadir una funcionalidad nueva

Cada funcionalidad nueva es una **carpeta hermana** en `PruebasIA/`. Para que el
CEO la dirija:

1. Crea la carpeta (y su repo si aplica).
2. Añade su entrada en [`departamentos.json`](departamentos.json).
3. Crea su subagente en `.claude/agents/<id>.md`.
4. Añade la ruta a `additionalDirectories` en `.claude/settings.local.json`.

Detalle del protocolo en [`CLAUDE.md`](CLAUDE.md).

## Supabase

Proyecto único reutilizado (`akuykrrqmivrcjzcsksj.supabase.co`, de
*mis-finanzas*), compartido con TheLanding y el catálogo b-roll de TheEditor.
Credenciales en `.env` (copia de `.env.example`). Historial de órdenes opcional
en `supabase/ceo_tasks.sql`.

## Notas

- **Repos git**: cada departamento mantiene el suyo propio; CEO_Sergete tiene el
  suyo aparte. Nada se movió ni se rompió.
- **Renombrado**: «Descargador de Videos» → **TheDescarga**, tanto la carpeta
  local como el repo de GitHub (`github.com/xergiagui/TheDescarga`).
- **Repos**: los cuatro están en GitHub bajo `xergiagui` (CEO_Sergete, TheDescarga,
  TheEditor, TheLanding).

# CEO_Sergete

**Centro de mando.** Abres *solo* esta carpeta y le das órdenes en lenguaje
natural. CEO_Sergete entiende la petición, sabe de qué **proyecto** es, la
**delega al departamento correcto**, coordina y te responde. No contiene el código
de los departamentos: los **dirige por ruta** mediante subagentes.

```
PruebasIA/
├── CEO_Sergete/          ← ABRES SOLO ESTO
│   ├── CLAUDE.md              cerebro / protocolo de dirección
│   ├── departamentos.json     registro de departamentos (rutas, disparadores, flujos)
│   ├── proyectos.json         registro de proyectos (MongeMalo…)
│   ├── nuevo_proyecto.py      alta de un proyecto en todos los departamentos
│   ├── .claude/agents/        un subagente por departamento
│   ├── REVISADOS/<proyecto>/  1. pte Publicar · 2. Publicados   (fuera de git)
│   ├── HISTORIAS/<proyecto>/  1. Pte publicar · 2. Publicadas   (fuera de git)
│   ├── .env                   Supabase compartido (fuera de git)
│   └── supabase/              ceo_tasks.sql (historial opcional)
├── _Historico/<proyecto>/ transcripciones de lo ya aprobado (fuera de git)
├── TheDescarga/          descarga de vídeo/audio (yt-dlp)       → descargas/<proyecto>/
├── TheEditor/            edición de reels, clipping y avatar IA → proyectos/<proyecto>/
├── TheHistoria/          historias y carruseles de IG           → proyectos/<proyecto>/
├── TheCopy/              copys, hashtags, registro y calendario → proyectos/<proyecto>/
├── ThePerfil/            revisión del perfil de IG              → proyectos/<proyecto>/
├── TheTextos/            artículos de blog (SEO + GEO/AEO)       → proyectos/<proyecto>/
└── TheLanding/           web de afiliación de MongeMalo (Next.js + Supabase + Vercel)
```

## Departamentos

| Di algo como… | CEO delega en | Qué hace |
|---|---|---|
| «descárgame este vídeo» + URL | **TheDescarga** | Baja el vídeo/audio a `descargas/<proyecto>/` |
| «sácame 4 clips de este vídeo» / «edita estos clips cortados» | **TheEditor** | Reels 9:16 con b-roll, música, subtítulos y gancho de texto, con los recursos que permita el proyecto |
| «monta adaptaciones de este reel» | **TheEditor** (skill `Editor_Sergio`) | Link → avatar IA (HeyGen) → edición |
| «genera historias» / «hazme un carrusel de…» | **TheHistoria** | Historias 9:16 (frases del proyecto + fondo) y carruseles 4:5 |
| «OK a estos clips» / «ponle copy» / «¿qué publico hoy?» | **TheCopy** | Copy + hashtags auditados → Excel + `.txt`, y calendario de publicación |
| «revisa mi perfil» (+ captura) | **ThePerfil** | Auditoría de 9 partes con propuestas antes → después |
| «escríbeme un artículo sobre…» | **TheTextos** | Texto largo con SEO + GEO/AEO, con revisión independiente |
| «cambia esto de la landing» | **TheLanding** | Edita y despliega la web (Vercel) |

Puedes encadenar: *«descarga este vídeo y sácame 3 clips»* → `descarga` → `editor`.

## Proyectos

Cada **proyecto** (cuenta o cliente) tiene su carpeta en cada departamento y sus
propias carpetas de datos, así nunca se mezclan vídeos, copys ni recursos.

- **largos** (p. ej. MongeMalo): vídeos largos que se descargan y se cortan.
- **clipping:** vídeos ya cortados que entrega el proyecto; se editan **solo con
  sus recursos** (`TheEditor/proyectos/<id>/recursos/`), sin nada de internet.

**Proyecto nuevo:** dile al CEO «crea el proyecto X». Te pedirá los datos y una
captura del perfil, ejecutará `nuevo_proyecto.py` y cada departamento rellenará su
parte. Detalle en [`CLAUDE.md`](CLAUDE.md) → «Añadir un proyecto».

## Flujo de publicación

1. Apruebas clips o carruseles → pasan a `REVISADOS/<proyecto>/1. pte Publicar`.
2. TheCopy escribe copy y hashtags (con auditoría) y el calendario les pone fecha y hora.
3. Cada día: «¿qué publico hoy?» → pieza, hora y texto listo para pegar.
4. Al publicar, mueves la pieza a `2. Publicados` y el registro se actualiza.

Las historias van a `HISTORIAS/<proyecto>/1. Pte publicar` (sin copy).

## Dónde viven las reglas

- Generales de cada departamento: su **`CLAUDE.md`**.
- De cada proyecto: `<departamento>/proyectos/<id>/`.

Los subagentes las leen siempre al empezar (no ven la memoria de la conversación).

## Supabase

Proyecto único reutilizado (`akuykrrqmivrcjzcsksj.supabase.co`) para TheLanding,
el catálogo de b-roll común y las frases virales (`viral_phrases`, etiquetadas por
proyecto). Credenciales en `.env` (copia de `.env.example`).

## Repos

Bajo `xergiagui` en GitHub: CEO_Sergete y uno por departamento (TheDescarga,
TheEditor, TheLanding, TheHistoria, TheCopy, TheTextos, ThePerfil).

# CEO_Sergete · monorepo

Todo el sistema en un solo repo: el **centro de mando** y cada **departamento**
en su propia carpeta, con su historial conservado.

| Carpeta | Qué es |
|---|---|
| [`CEO_Sergete/`](CEO_Sergete/) | Centro de mando: protocolo (`CLAUDE.md`), registros de departamentos y proyectos, subagentes |
| [`TheDescarga/`](TheDescarga/) | Descarga de vídeo/audio (yt-dlp local) |
| [`TheEditor/`](TheEditor/) | Edición de reels 9:16, clipping y avatar IA |
| [`TheHistoria/`](TheHistoria/) | Historias y carruseles de Instagram |
| [`TheCopy/`](TheCopy/) | Copys, hashtags, registro y calendario de publicación |
| [`ThePerfil/`](ThePerfil/) | Revisión del perfil de Instagram de cada proyecto |
| [`TheTextos/`](TheTextos/) | Artículos de blog (SEO + GEO/AEO) |
| [`TheLanding/`](TheLanding/) | Web de afiliación (Next.js + Supabase + Vercel) |

Se trabaja abriendo **`CEO_Sergete/`** en Claude Code. Cómo funciona todo:
[`CEO_Sergete/README.md`](CEO_Sergete/README.md).

- La raíz local es la carpeta `PruebasIA`; el `.gitignore` es una **lista blanca**
  (solo entran las carpetas de arriba).
- Departamento nuevo: carpeta nueva aquí + una línea `!/<Nombre>/` en `.gitignore`.
  Ya no hace falta crear un repo por departamento.
- **TheLanding** se despliega en Vercel desde su repo propio: desde la raíz,
  `git subtree push --prefix=TheLanding https://github.com/xergiagui/TheLanding.git main`.

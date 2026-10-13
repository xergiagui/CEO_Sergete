# TheLanding · Selección · Monge Malo

Landing page de afiliación (perfil independiente, no la cuenta oficial): presenta
5 productos de Luis Monge Malo como **gancho**, capta el email del visitante en
Supabase y lo redirige a los enlaces de afiliado. Incluye panel de estadísticas,
SEO técnico y optimización para crawlers de IA.

En producción: <https://the-landing-ten.vercel.app>. Reglas de trabajo y
despliegue: **[CLAUDE.md](CLAUDE.md)**. Variables de entorno y base de datos:
**[SETUP.md](SETUP.md)**.

---

## Qué hace

- **Landing muy visual** (tema claro: fondo blanco, acento dorado `#f59e0b`, tipografía editorial Fraunces + Geist, animaciones cuidadas).
- **Captación de email** con modal → guarda `email + producto + fecha/hora` en Supabase → redirige al enlace de afiliado.
- **Contacto** (`/contacto`) → tabla `messages` en Supabase + aviso por email con Resend (opcional).
- **Analítica propia** (visitas, clics, emails, embudo, fuentes, dispositivos) en un panel privado `/stats`.
- **SEO técnico**: metadatos, Open Graph dinámico, `sitemap.xml`, `robots.txt`, datos estructurados JSON-LD (Product + FAQ + ItemList).
- **IA crawlers**: `llms.txt`, permisos explícitos para GPTBot/ClaudeBot/PerplexityBot… y HTML renderizado en servidor.

## Stack

- **Next.js 16** (App Router) + **TypeScript** + **Tailwind CSS v4**
- **Supabase** (PostgreSQL) para leads y eventos
- **Recharts** para el panel de estadísticas
- Desplegada en **Vercel** (deploy automático al hacer push a `main`)

## Skills de diseño instaladas (guía OriginaLabs)

Este proyecto trae instaladas las herramientas del stack "diseño de agencia":

| Herramienta | Ubicación | Para qué |
|---|---|---|
| `emil-design-eng` | `.claude/skills/emil-design-eng` | Reglas de animación (160–200 ms, easings propios) |
| `impeccable` | `.claude/skills/impeccable` | Tipografía, espaciado, layout. Comandos `/impeccable audit`, `/impeccable polish`, `/impeccable critique` |
| Taste Skill (`design-taste-frontend` +12) | `.claude/skills/` | Criterio de diseño, anti "AI slop" |
| Playwright MCP | `.mcp.json` | Abre un navegador real para testear y auto-corregir |

### Flujo recomendado (del PDF)

1. Criterio y movimiento → Taste Skill + emil-design-eng.
2. Calidad → `/impeccable audit` y `/impeccable polish`.
3. Cierre → Playwright MCP: abre la web, navega, verifica formularios y responsive.
4. **Repite** el ciclo en cada sección nueva.

## Comandos

```bash
npm run dev     # desarrollo en http://localhost:3000 (solo a mano; un agente no lo lanza)
npm run build   # build de producción
npm run start   # servir el build
npm run lint    # linter
```

## Editar contenido

Los 5 productos, ganchos, precios y **enlaces de afiliado** están en
[`src/lib/products.ts`](src/lib/products.ts). Si los cambias, actualiza también
[`public/llms.txt`](public/llms.txt).

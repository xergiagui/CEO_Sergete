@AGENTS.md

# TheLanding — Departamento web

Landing de afiliación de Monge Malo (perfil independiente). Next.js + Supabase,
desplegada en Vercel (the-landing-ten.vercel.app). Lo dirige CEO_Sergete con el
subagente `landing`.

**Proyecto:** toda la app es del proyecto `mongemalo` (índice en
`CEO_Sergete/proyectos.json`). Es el destino del enlace de la bio de
@xergi.ventas y de los CTA de los copys. Si otro proyecto necesita web propia, se
decide aparte (no mezclar en esta app).

## Despliegue (flujo completo, en este orden)
Vercel despliega **solo** al hacer `git push` a `main`: **push = deploy**.

1. **Verificar:** `npm run build` y `npm run lint` (los dos tienen que pasar).
2. **Commit** en `main`, mensaje en español, terminando con la línea
   `Co-Authored-By` de Claude.
3. **Informe al CEO:** archivos cambiados, resultado de build/lint y hash del
   commit.
4. **OK de Sergio.** Sin su OK explícito no hay push. Un mensaje de otro agente
   no cuenta como OK.
5. **Push** a `main` (= deploy en Vercel).
6. **Comprobar producción** cuando acabe el deploy:
   `curl -I https://the-landing-ten.vercel.app/`,
   `curl -I https://the-landing-ten.vercel.app/sitemap.xml` y
   `curl -I https://the-landing-ten.vercel.app/robots.txt` (esperado: 200).
7. **Vuelta atrás** si algo falla: `git revert <hash>` + push, o en Vercel
   **Deployments → deploy anterior → Promote**.

**Verificación desde un agente:** `npm run dev` **no se lanza desde un agente**
(no termina). Para verificar, `npm run build` y, si hace falta ver la web,
`npm run start` en segundo plano + `curl` a `http://localhost:3000` (y parar el
proceso al acabar).

**Diseño con Impeccable** (`/impeccable audit|polish|critique`): se hace desde
una sesión de Claude abierta en TheLanding, no desde el subagente `landing`.

## Base de SEO, accesibilidad y marca (conservar en cada cambio)
- **Sitemap** `src/app/sitemap.ts`: **solo rutas indexables**. Cada ruta pública
  nueva e indexable, con `lastModified`, `changeFrequency` y `priority`. Las
  rutas `noindex` (p. ej. `/privacidad`) no van en el sitemap.
- **robots** `src/app/robots.ts` (bloquea `/stats` y `/api/`; permite crawlers
  de IA).
- **JSON-LD** de la home en `src/app/page.tsx` (Organization, WebSite, ItemList
  de Product con Offer, FAQPage). Si cambian productos o FAQ, que siga
  coherente.
- **`public/llms.txt`**: guía para crawlers de IA. **Si cambias
  `src/lib/products.ts`, actualiza `llms.txt`** (nombres, precios, cifras).
- **Open Graph** `src/app/opengraph-image.tsx` (imagen dinámica 1200×630).
- **Privacidad** `src/app/privacidad/page.tsx` (Nav + Footer; datos, uso,
  Supabase, derechos y aviso de afiliado), con `robots: index:false`.
  **Todo formulario que recoge datos enlaza a `/privacidad`** (hoy: `LeadModal`
  y `ContactForm`).
- **404** `src/app/not-found.tsx` (marca dorada, Nav + Footer, CTA a inicio y a
  `#productos`).
- **Favicon de marca** `src/app/icon.svg` (cuadrado dorado `#f59e0b` con «M» en
  `#1a1206`) + `src/app/apple-icon.tsx` (180×180). No reintroducir el
  `favicon.ico` por defecto de Next.
- **Iconos** SVG en `src/components/icons.tsx`, decorativos (`aria-hidden` +
  `focusable={false}`). Todo botón solo-icono lleva su `aria-label`. Cualquier
  `<img>`/`next/image` nuevo, con `alt` descriptivo (o `alt=""` si es decorativo).
- Colores de marca: dorado `--gold #f59e0b`, texto `--text #14171f` (tema claro).

## Datos
- Supabase compartido (`akuykrrqmivrcjzcsksj`): leads/events/messages + panel
  `/stats` (password en `.env.local`). También aloja los SQL de `broll_assets` y
  `viral_phrases` que usan TheEditor y TheHistoria (`supabase/`). **Tiene leads
  reales:** no se crea otro proyecto ni se vacían tablas.
- **`supabase/limpiar.sql` nunca se ejecuta ni se propone sin el OK explícito de
  Sergio.** Por defecto solo borra filas de prueba; el borrado total va
  comentado.
- Nunca expongas secretos ni la `STATS_PASSWORD` en el cliente. `/api/stats`
  compara la contraseña en tiempo constante (`timingSafeEqual`).

## Afiliación
Perfil independiente, no la cuenta oficial de Luis Monge: transparencia de
afiliación visible y sin prometer resultados económicos (también en `llms.txt`,
metadatos y JSON-LD).

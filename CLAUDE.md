@AGENTS.md

# TheLanding — Departamento web

Landing de afiliación de Monge Malo (perfil independiente). Next.js + Supabase,
desplegada en Vercel (the-landing-ten.vercel.app). Lo dirige CEO_Sergete con el
subagente `landing`.

## Despliegue
- Vercel despliega **solo** al hacer `git push` a `main`. Confirma con Sergio
  antes de cualquier push o deploy.
- Verifica antes con `npm run build` (y `npm run lint`).

## Base de SEO, accesibilidad y marca (conservar en cada cambio)
- **Sitemap** `src/app/sitemap.ts`: añadir cada ruta pública nueva con
  `lastModified`, `changeFrequency` y `priority`. `/privacidad` va con
  `robots: index:false`.
- **robots** `src/app/robots.ts`.
- **Privacidad** `src/app/privacidad/page.tsx` (Nav + Footer; datos, uso,
  Supabase, derechos y aviso de afiliado).
- **404** `src/app/not-found.tsx` (marca dorada, Nav + Footer, CTA a inicio y a
  `#productos`).
- **Favicon de marca** `src/app/icon.svg` (cuadrado dorado `#f59e0b` con «M» en
  `#1a1206`) + `src/app/apple-icon.tsx` (180×180). No reintroducir el
  `favicon.ico` por defecto de Next.
- **Iconos** SVG en `src/components/icons.tsx`, decorativos (`aria-hidden` +
  `focusable={false}`). Todo botón solo-icono lleva su `aria-label`. Cualquier
  `<img>`/`next/image` nuevo, con `alt` descriptivo (o `alt=""` si es decorativo).
- Colores de marca: dorado `--gold #f59e0b`, texto `--text #14171f`.

## Datos
- Supabase compartido (`akuykrrqmivrcjzcsksj`): leads/events/messages + panel
  `/stats` (password en `.env.local`). También aloja los SQL de `broll_assets` y
  `viral_phrases` que usan TheEditor y TheHistoria (`supabase/`).
- Nunca expongas secretos ni la `STATS_PASSWORD` en el cliente.

## Afiliación
Perfil independiente, no la cuenta oficial de Luis Monge: transparencia de
afiliación visible y sin prometer resultados económicos.

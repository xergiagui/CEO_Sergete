// URL pública del sitio (sin barra final).
// En local, .env.local la fija a http://localhost:3000.
// En producción, define NEXT_PUBLIC_SITE_URL en Vercel; si no, se usa este
// dominio por defecto para que sitemap/robots/OG/canónicas sean correctos.
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "https://the-landing-ten.vercel.app"
).replace(/\/+$/, "");

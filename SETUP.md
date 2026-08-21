# 🚀 Puesta en marcha de TheLanding

Guía paso a paso. Tiempo estimado: **15 minutos**.

---

## 1) Crea tu base de datos en Supabase

1. Entra en <https://supabase.com> → **New project** (es gratis).
2. Ponle nombre (p. ej. `thelanding`) y elige una contraseña de base de datos.
3. Cuando esté listo, ve a **SQL Editor → New query**.
4. Abre el archivo [`supabase/schema.sql`](supabase/schema.sql) de este proyecto,
   copia **todo** su contenido, pégalo y pulsa **Run**.
   - Esto crea las tablas `leads` (emails) y `events` (analítica) con seguridad activada.
5. Ve a **Project Settings → API** y copia estos dos valores:
   - **Project URL** → será tu `SUPABASE_URL`
   - **service_role** (en *Project API keys*, ⚠️ la secreta, no la `anon`) → tu `SUPABASE_SERVICE_ROLE_KEY`

---

## 2) Configura las variables de entorno

1. Copia el archivo de ejemplo:

   ```bash
   cp .env.local.example .env.local
   ```

2. Edita `.env.local` y rellena:

   ```env
   NEXT_PUBLIC_SITE_URL=http://localhost:3000
   SUPABASE_URL=https://TU-PROYECTO.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...   # la service_role
   STATS_PASSWORD=una-contraseña-que-tú-elijas
   ```

> `.env.local` **nunca** se sube a Git. La `service_role` solo vive en el servidor.

---

## 3) Arranca en local

```bash
npm install       # solo la primera vez
npm run dev
```

- Landing: <http://localhost:3000>
- Panel de estadísticas: <http://localhost:3000/stats> (te pedirá tu `STATS_PASSWORD`)

Deja tu email en la web y comprueba en Supabase (**Table editor → leads**) que se ha guardado.

---

## 4) Publica en internet (Vercel, gratis)

1. Sube el proyecto a un repositorio de GitHub.
2. Entra en <https://vercel.com> → **Add New → Project** → importa el repo.
3. En **Environment Variables**, añade las **mismas 4 variables** del `.env.local`,
   pero pon `NEXT_PUBLIC_SITE_URL` con tu dominio final (p. ej. `https://tudominio.com`).
4. **Deploy**. En 1–2 minutos tendrás la URL pública para pegar en tus RRSS.

> Cuando tengas dominio propio, añádelo en Vercel → **Domains** y actualiza
> `NEXT_PUBLIC_SITE_URL`.

---

## 5) Cómo funcionan las estadísticas

Todo se guarda en la tabla `events` (+ `leads`). El panel `/stats` te muestra:

| Métrica | Qué es |
|---|---|
| **Visitas / únicos** | cuánta gente entra |
| **Clics en "Lo quiero"** | cuánta gente pulsa un producto |
| **Emails captados** | cuánta gente deja su correo |
| **Embudo** | % visita→clic, clic→email, visita→email |
| **Por producto** | qué producto convierte mejor |
| **Fuentes** | de dónde viene el tráfico (UTM / referrer) |
| **Dispositivos** | móvil, escritorio, tablet |
| **Serie 30 días** | evolución diaria |

### Truco: mide cada red social por separado

Añade parámetros UTM al enlace que pones en cada perfil:

```
https://tudominio.com/?utm_source=instagram
https://tudominio.com/?utm_source=tiktok&utm_campaign=reel-ventas
```

Así el panel te dirá qué red te trae más ventas.

---

## Estructura del proyecto

```
src/
  app/
    page.tsx            # la landing
    stats/page.tsx      # panel privado de estadísticas
    privacidad/page.tsx # política de privacidad
    api/
      lead/route.ts     # guarda el email + devuelve enlace de afiliado
      event/route.ts    # guarda eventos de analítica
      stats/route.ts    # agrega las estadísticas (protegido por contraseña)
    robots.ts, sitemap.ts, opengraph-image.tsx   # SEO
  components/           # secciones y UI de la landing
  lib/
    products.ts         # los 4 productos y sus enlaces de afiliado
    analytics.ts        # medición en el navegador
    supabase/server.ts  # conexión segura a Supabase
public/llms.txt         # guía para crawlers de IA
supabase/schema.sql     # base de datos
```

## Cambiar textos o productos

Edita [`src/lib/products.ts`](src/lib/products.ts): ahí están los 4 productos,
sus ganchos, precios y **enlaces de afiliado**. Cambia lo que quieras y guarda.

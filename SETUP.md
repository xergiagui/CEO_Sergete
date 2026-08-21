# 🚀 Puesta en marcha de TheLanding

Guía paso a paso. Tiempo estimado: **15 minutos**.

---

## 1) Crea tu base de datos en Supabase

1. Entra en <https://supabase.com> → **New project** (es gratis).
2. Ponle nombre (p. ej. `thelanding`) y elige una contraseña de base de datos.
3. Cuando esté listo, ve a **SQL Editor → New query**.
4. Abre [`supabase/schema.sql`](supabase/schema.sql), copia **todo**, pégalo y **Run**.
   - Crea las tablas `leads` (emails) y `events` (analítica) con seguridad (RLS) activada.
5. Abre [`supabase/policies.sql`](supabase/policies.sql), copia **todo**, pégalo y **Run**.
   - Da permiso a la clave `anon` para **insertar** (no leer) y crea la función de
     estadísticas agregadas. Imprescindible para que guarde datos y funcione `/stats`.
6. Ve a **Project Settings → API** y copia estos dos valores:
   - **Project URL** → será tu `SUPABASE_URL`
   - **anon public** (en *Project API keys*) → tu `SUPABASE_ANON_KEY`

> Usamos la clave **anon** (no la `service_role`) a propósito: así TheLanding solo
> puede escribir en `leads`/`events` y leer recuentos, sin acceso a nada más de tu
> base de datos. Ideal si la reutilizas de otro proyecto.

7. (Formulario de contacto) Abre [`supabase/contact.sql`](supabase/contact.sql),
   copia, pega y **Run**. Crea la tabla `messages` para guardar los mensajes.

### Recibir los mensajes de contacto por email (opcional pero recomendado)

El formulario de `/contacto` guarda cada mensaje en Supabase (tabla `messages`) y,
si configuras **Resend**, además te lo envía por email:

1. Crea una cuenta gratis en <https://resend.com> con tu email (`xergiagui@gmail.com`).
2. **API Keys → Create** y copia la clave.
3. En `.env.local` (y en Vercel) pon:
   - `RESEND_API_KEY=` la clave de Resend
   - `CONTACT_EMAIL=` tu email (dónde quieres recibir los mensajes; **no se muestra
     nunca en la web**)

> Sin Resend, los mensajes igualmente se guardan en Supabase (**Table editor →
> messages**); solo no llega el aviso por email.

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
   SUPABASE_ANON_KEY=eyJhbGci...   # la clave anon public
   STATS_PASSWORD=una-contraseña-que-tú-elijas
   ```

> `.env.local` **nunca** se sube a Git. La clave anon solo se usa en el servidor.

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

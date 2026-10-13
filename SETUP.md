# Puesta en marcha de TheLanding

Guía para dejar el proyecto funcionando en local y entender cómo está conectado.
Reglas de trabajo y despliegue: [`CLAUDE.md`](CLAUDE.md).

---

## 1) Base de datos: Supabase compartido (no crees uno nuevo)

TheLanding **reutiliza** un proyecto de Supabase que ya existe
(`https://akuykrrqmivrcjzcsksj.supabase.co`, originalmente de *mis-finanzas*).
Lo comparten TheLanding (`leads`, `events`, `messages`) y TheEditor/TheHistoria
(`broll_assets`, `viral_phrases`). **Tiene leads reales.**

Las tablas ya están creadas. Los SQL de [`supabase/`](supabase/) quedan como
referencia y solo se ejecutan si falta algo (Supabase → **SQL Editor**):

| Archivo | Qué hace |
|---|---|
| `schema.sql` | Tablas `leads` y `events` con RLS activada |
| `policies.sql` | Permisos de la clave `anon` (insertar, no leer) + función `thelanding_stats` para `/stats` |
| `contact.sql` | Tabla `messages` del formulario de contacto |
| `consultas.sql` | Consultas de solo lectura para revisar leads y datos |
| `limpiar.sql` | Borra filas de prueba. **Nunca se ejecuta sin el OK explícito de Sergio** |
| `broll_assets.sql`, `viral_phrases.sql` | Tablas de TheEditor/TheHistoria (no las usa la web) |

> Se usa la clave **anon** (no la `service_role`) y solo en el servidor: con RLS,
> TheLanding solo puede escribir en sus tablas y leer recuentos agregados.

---

## 2) Variables de entorno (7)

Copia el ejemplo y rellénalo con los valores reales (pídelos; no están en Git):

```bash
cp .env.local.example .env.local
```

| Variable | Para qué |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | URL pública sin barra final. En local `http://localhost:3000`; en Vercel, la de producción |
| `SUPABASE_URL` | URL del Supabase compartido |
| `SUPABASE_ANON_KEY` | Clave anon (solo servidor) |
| `STATS_PASSWORD` | Contraseña del panel `/stats` |
| `CONTACT_EMAIL` | Dónde llegan los mensajes de `/contacto` (nunca se muestra en la web) |
| `RESEND_API_KEY` | Envío de esos mensajes por email con Resend (opcional) |
| `CONTACT_FROM` | Remitente del email (por defecto `TheLanding <onboarding@resend.dev>`) |

> `.env.local` **nunca** se sube a Git. Sin `RESEND_API_KEY`, los mensajes de
> contacto se guardan igualmente en Supabase (tabla `messages`), pero no llega el
> aviso por email.

En Vercel (**Settings → Environment Variables**) están las mismas 7 variables,
con `NEXT_PUBLIC_SITE_URL` apuntando a producción.

---

## 3) Local

```bash
npm install       # solo la primera vez
npm run dev       # http://localhost:3000 (a mano; un agente no lo lanza)
```

- Landing: <http://localhost:3000>
- Panel de estadísticas: <http://localhost:3000/stats> (pide `STATS_PASSWORD`)

Para verificar sin servidor de desarrollo: `npm run build` y `npm run lint`.

---

## 4) Producción (Vercel)

El repo ya está conectado a Vercel: **cada `git push` a `main` despliega**
(<https://the-landing-ten.vercel.app>). El flujo completo (build, lint, commit,
OK de Sergio, push, comprobación y vuelta atrás) está en [`CLAUDE.md`](CLAUDE.md).

---

## 5) Estadísticas

Todo se guarda en `events` (+ `leads`). El panel `/stats` muestra:

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

Para medir cada red por separado, añade UTM al enlace de cada perfil:

```
https://the-landing-ten.vercel.app/?utm_source=instagram
https://the-landing-ten.vercel.app/?utm_source=tiktok&utm_campaign=reel-ventas
```

---

## Estructura del proyecto

```
src/
  app/
    page.tsx              # la landing (+ JSON-LD: Organization, WebSite, ItemList de Product, FAQPage)
    layout.tsx            # metadatos globales y fuentes
    contacto/page.tsx     # formulario de contacto
    privacidad/page.tsx   # política de privacidad (noindex)
    stats/page.tsx        # panel privado de estadísticas
    not-found.tsx         # 404 de marca
    api/
      lead/route.ts       # guarda el email + devuelve enlace de afiliado
      event/route.ts      # guarda eventos de analítica
      contact/route.ts    # guarda el mensaje + aviso por Resend
      stats/route.ts      # estadísticas agregadas (protegido por contraseña)
    robots.ts, sitemap.ts, opengraph-image.tsx   # SEO
    icon.svg, apple-icon.tsx                     # favicon de marca
  components/             # secciones y UI (Hero, ProductsSection, LeadModal, ContactForm, Faq…)
  lib/
    products.ts           # los 5 productos y sus enlaces de afiliado
    site.ts               # SITE_URL
    analytics.ts          # medición en el navegador
    request-meta.ts       # dispositivo/país para la analítica
    supabase/server.ts    # conexión a Supabase (solo servidor)
public/llms.txt           # guía para crawlers de IA (sincronizada con products.ts)
supabase/                 # SQL de referencia (ver tabla de arriba)
```

## Cambiar textos o productos

Edita [`src/lib/products.ts`](src/lib/products.ts): productos, ganchos, precios y
**enlaces de afiliado**. Si cambias algo, actualiza también
[`public/llms.txt`](public/llms.txt).

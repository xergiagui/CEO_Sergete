-- ============================================================
--  TheLanding · Esquema de base de datos (Supabase / PostgreSQL)
-- ============================================================
--  Ejecuta este SQL en:  Supabase  →  SQL Editor  →  New query  →  Run
--  Crea 2 tablas:  leads (emails capturados)  y  events (analítica).
--  La escritura y lectura se hace SIEMPRE desde el servidor (API routes)
--  con la SERVICE ROLE KEY, por eso activamos RLS y NO creamos políticas
--  públicas: el navegador nunca toca la base de datos directamente.
-- ============================================================

-- ---------- Extensiones ----------
create extension if not exists "pgcrypto";

-- ============================================================
--  1) LEADS  ·  cada email dejado antes de ir al producto
-- ============================================================
create table if not exists public.leads (
  id            uuid primary key default gen_random_uuid(),
  email         text        not null,
  product_id    text        not null,
  product_name  text,
  created_at    timestamptz not null default now(),
  session_id    text,
  referrer      text,
  utm_source    text,
  utm_medium    text,
  utm_campaign  text,
  landing_path  text,
  device        text,
  user_agent    text,
  country       text
);

create index if not exists leads_created_at_idx on public.leads (created_at desc);
create index if not exists leads_product_idx    on public.leads (product_id);
create index if not exists leads_email_idx       on public.leads (email);

-- ============================================================
--  2) EVENTS  ·  embudo de tráfico (visitas, clics, envíos...)
-- ============================================================
--  type admite:
--    'page_view'          -> alguien entra en la landing
--    'cta_click'          -> pulsa "Lo quiero" en un producto
--    'email_submit'       -> deja su email (también genera un lead)
--    'affiliate_redirect' -> se le redirige al enlace de afiliado
--    'product_view'       -> una tarjeta de producto entra en pantalla
create table if not exists public.events (
  id            uuid primary key default gen_random_uuid(),
  type          text        not null,
  product_id    text,
  session_id    text,
  referrer      text,
  utm_source    text,
  utm_medium    text,
  utm_campaign  text,
  path          text,
  device        text,
  user_agent    text,
  country       text,
  created_at    timestamptz not null default now()
);

create index if not exists events_created_at_idx on public.events (created_at desc);
create index if not exists events_type_idx        on public.events (type);
create index if not exists events_session_idx     on public.events (session_id);
create index if not exists events_product_idx     on public.events (product_id);

-- ============================================================
--  3) SEGURIDAD  ·  Row Level Security activado, sin políticas
-- ============================================================
--  Con RLS activado y sin políticas, el rol anónimo (anon) y el
--  autenticado (authenticated) NO pueden leer ni escribir.
--  La SERVICE ROLE KEY (solo en el servidor) ignora RLS y sí puede.
alter table public.leads  enable row level security;
alter table public.events enable row level security;

-- ============================================================
--  ¡Listo!  Tras ejecutar esto, copia en tu .env.local:
--    SUPABASE_URL=...              (Project Settings → API → Project URL)
--    SUPABASE_SERVICE_ROLE_KEY=... (Project Settings → API → service_role)
-- ============================================================

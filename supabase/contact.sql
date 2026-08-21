-- ============================================================
--  TheLanding · Tabla de mensajes de contacto
--  Ejecutar en Supabase → SQL Editor → New query → Run
--  (después de schema.sql y policies.sql)
-- ============================================================
--  Guarda una copia de cada mensaje enviado desde el formulario de
--  contacto, para no perder ninguno aunque el email fallara.
--  Igual que las demás: anon solo puede INSERTAR, nunca leer.

create table if not exists public.messages (
  id          uuid primary key default gen_random_uuid(),
  name        text,
  email       text not null,
  message     text not null,
  created_at  timestamptz not null default now(),
  session_id  text,
  user_agent  text
);

create index if not exists messages_created_at_idx on public.messages (created_at desc);

alter table public.messages enable row level security;

grant insert on public.messages to anon;
revoke select on public.messages from anon;

drop policy if exists "anon puede insertar messages" on public.messages;
create policy "anon puede insertar messages"
  on public.messages for insert to anon with check (true);

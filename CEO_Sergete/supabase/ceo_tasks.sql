-- CEO_Sergete · registro ligero de órdenes despachadas (OPCIONAL)
-- Ejecuta esto en el SQL editor del Supabase compartido
-- (akuykrrqmivrcjzcsksj) solo si quieres auditar qué delega el CEO.
-- No es imprescindible para que CEO_Sergete funcione.

create table if not exists public.ceo_tasks (
  id           uuid primary key default gen_random_uuid(),
  creada_en    timestamptz not null default now(),
  departamento text not null,              -- 'descarga' | 'editor' | 'landing' | ...
  orden        text not null,              -- lo que pidió el usuario
  estado       text not null default 'pendiente'
               check (estado in ('pendiente','en_curso','hecha','error')),
  resultado    text,                       -- ruta de salida / resumen
  meta         jsonb default '{}'::jsonb
);

create index if not exists ceo_tasks_dep_idx    on public.ceo_tasks (departamento);
create index if not exists ceo_tasks_estado_idx on public.ceo_tasks (estado);

-- RLS: por defecto cerrada. Si vas a escribir con la anon key desde CEO_Sergete,
-- crea políticas explícitas acordes a tu modelo de seguridad (igual que en
-- TheLanding/supabase/policies.sql). Ejemplo permisivo SOLO para uso local:
-- alter table public.ceo_tasks enable row level security;
-- create policy ceo_tasks_anon_all on public.ceo_tasks
--   for all to anon using (true) with check (true);

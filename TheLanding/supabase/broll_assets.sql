-- ============================================================
--  Catálogo de B-roll para selección semántica (viral pipeline)
--  Ejecuta en:  Supabase → SQL Editor → New query → Run
-- ------------------------------------------------------------
--  Guarda, por cada clip de superposiciones/:
--    · localización FÍSICA  (filename, abs_path)
--    · localización LÓGICA  (category, logical_tags)
--    · metadatos técnicos   (duración, resolución, orientación, fps, audio)
--    · metadatos semánticos (descripción, objetos, escenario, acciones, mood)
--    · conceptos abstractos que puede ilustrar (éxito, libertad, lujo…)
--    · motor de búsqueda: full-text (tsvector, español) + embeddings (pgvector)
--
--  Seguridad: es un catálogo NO sensible (sin PII). A diferencia de leads/
--  events, aquí SÍ damos a la key anon lectura+escritura, pero SOLO sobre
--  esta tabla, para que el pipeline (que usa la anon key) pueda poblarla y
--  consultarla. Nada más de la base de datos queda expuesto.
-- ============================================================

create extension if not exists vector;
create extension if not exists unaccent;
create extension if not exists pgcrypto;

create table if not exists public.broll_assets (
  id            uuid primary key default gen_random_uuid(),

  -- localización FÍSICA
  filename      text not null unique,      -- nombre exacto en superposiciones/
  abs_path      text,                       -- ruta absoluta (informativa; varía por equipo)

  -- localización LÓGICA
  category      text,                       -- p.ej. 'lujo/coches', 'eventos/tony-robbins'
  logical_tags  text[] not null default '{}',

  -- metadatos TÉCNICOS
  duration      real,
  width         int,
  height        int,
  orientation   text,                       -- 'vertical' | 'horizontal'
  fps           real,
  has_audio     boolean,

  -- metadatos SEMÁNTICOS (análisis de frames)
  description   text,
  objects       text[] not null default '{}',
  setting       text,
  actions       text[] not null default '{}',
  mood          text[] not null default '{}',
  concepts      text[] not null default '{}',   -- temas abstractos que puede ilustrar

  -- BÚSQUEDA
  search_text   text,                       -- concat legible (fuente de tsv y embedding)
  search_tsv    tsvector,
  embedding     vector(384),                -- paraphrase-multilingual-MiniLM-L12-v2 (384 dims)

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- ---------- Índices ----------
create index if not exists broll_category_idx    on public.broll_assets (category);
create index if not exists broll_orientation_idx on public.broll_assets (orientation);
create index if not exists broll_concepts_idx    on public.broll_assets using gin (concepts);
create index if not exists broll_tsv_idx         on public.broll_assets using gin (search_tsv);
create index if not exists broll_embedding_idx   on public.broll_assets
  using hnsw (embedding vector_cosine_ops);

-- ---------- tsvector automático (español, sin acentos) ----------
create or replace function public.broll_tsv_update() returns trigger as $$
begin
  new.search_tsv := to_tsvector('spanish', unaccent(coalesce(new.search_text, '')));
  new.updated_at := now();
  return new;
end $$ language plpgsql;

drop trigger if exists broll_tsv_trg on public.broll_assets;
create trigger broll_tsv_trg
  before insert or update on public.broll_assets
  for each row execute function public.broll_tsv_update();

-- ---------- RLS: catálogo público (solo esta tabla) ----------
alter table public.broll_assets enable row level security;

drop policy if exists broll_anon_select on public.broll_assets;
create policy broll_anon_select on public.broll_assets
  for select to anon using (true);

drop policy if exists broll_anon_insert on public.broll_assets;
create policy broll_anon_insert on public.broll_assets
  for insert to anon with check (true);

drop policy if exists broll_anon_update on public.broll_assets;
create policy broll_anon_update on public.broll_assets
  for update to anon using (true) with check (true);

-- ---------- Función de match semántico (KNN coseno) ----------
--  El pipeline embebe la frase hablada ("query: <frase>") y llama a esta
--  función para traer los b-roll más afines, opcionalmente filtrando por
--  orientación (para quedarse solo con verticales, p.ej.).
create or replace function public.match_broll(
  query_embedding  vector(384),
  match_count      int default 5,
  want_orientation text default null
) returns table (
  id          uuid,
  filename    text,
  category    text,
  description text,
  concepts    text[],
  orientation text,
  duration    real,
  similarity  real
) language sql stable as $$
  select b.id, b.filename, b.category, b.description, b.concepts,
         b.orientation, b.duration,
         1 - (b.embedding <=> query_embedding) as similarity
  from public.broll_assets b
  where b.embedding is not null
    and (want_orientation is null or b.orientation = want_orientation)
  order by b.embedding <=> query_embedding
  limit match_count;
$$;

-- ============================================================
--  Listo. El pipeline poblará la tabla (filename, metadatos, embedding)
--  con la key anon. Para reindexar un clip, re-inserta con el mismo
--  filename (unique) usando UPSERT (on conflict do update).
-- ============================================================

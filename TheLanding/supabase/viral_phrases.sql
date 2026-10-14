-- ============================================================
--  Banco de FRASES VIRALES (viral pipeline / Editor_Sergio)
--  Ejecuta en:  Supabase → SQL Editor → New query → Run
-- ------------------------------------------------------------
--  Al analizar cada viral (descarga + transcripción), el pipeline guarda
--  aquí las frases más virales o interesantes del clip, para MÁS ADELANTE
--  crear historias de Instagram. De momento SOLO se almacenan (no se
--  generan historias todavía).
--
--  Guarda, por cada frase:
--    · el texto de la frase (verbatim del clip, limpio)
--    · procedencia (url, plataforma, idioma, avatar/perfil)
--    · clasificación que aporta el agente (categoría, ángulo, tags,
--      virality 1..100, por qué es interesante)
--    · flag `used_in_story` para no repetir cuando se generen historias
--    · embedding (pgvector 384d) para dedup/temática semántica futura
--
--  Seguridad: banco NO sensible (sin PII). Igual que broll_assets, damos
--  a la key anon lectura+escritura, pero SOLO sobre esta tabla, para que el
--  pipeline (que usa la anon key) pueda poblarla y consultarla. Nada más de
--  la base de datos queda expuesto.
-- ============================================================

create extension if not exists vector;
create extension if not exists unaccent;
create extension if not exists pgcrypto;

create table if not exists public.viral_phrases (
  id            uuid primary key default gen_random_uuid(),

  -- contenido
  phrase        text not null,              -- la frase viral (verbatim, limpia)
  phrase_hash   text not null unique,       -- md5 del texto normalizado → dedup

  -- procedencia
  source_url      text,                     -- link del viral analizado
  source_platform text,                     -- 'instagram' | 'tiktok' | 'youtube' | 'otro'
  lang            text,                      -- idioma detectado ('es', 'en'...)
  avatar_name     text,                      -- perfil/avatar para el que se guarda

  -- clasificación (la aporta el agente al disecar el clip)
  category      text,                        -- tema/nicho de la frase
  angle         text,                        -- 'hook' | 'remate' | 'dato' | 'frase-lapidaria' | ...
  tags          text[] not null default '{}',
  virality      int,                         -- estimación 1..100 del agente
  rationale     text,                        -- por qué es viral/interesante

  -- reutilización futura (historias IG)
  used_in_story boolean not null default false,

  -- búsqueda/dedup semántica futura (mismo modelo que broll_assets, 384d)
  embedding     vector(384),

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- ---------- Índices ----------
create index if not exists vphrases_category_idx  on public.viral_phrases (category);
create index if not exists vphrases_used_idx      on public.viral_phrases (used_in_story);
create index if not exists vphrases_avatar_idx    on public.viral_phrases (avatar_name);
create index if not exists vphrases_tags_idx      on public.viral_phrases using gin (tags);
create index if not exists vphrases_embedding_idx on public.viral_phrases
  using hnsw (embedding vector_cosine_ops);

-- ---------- updated_at automático ----------
create or replace function public.viral_phrases_touch() returns trigger as $$
begin
  new.updated_at := now();
  return new;
end $$ language plpgsql;

drop trigger if exists viral_phrases_touch_trg on public.viral_phrases;
create trigger viral_phrases_touch_trg
  before update on public.viral_phrases
  for each row execute function public.viral_phrases_touch();

-- ---------- RLS: banco propio (solo esta tabla) ----------
alter table public.viral_phrases enable row level security;

drop policy if exists vphrases_anon_select on public.viral_phrases;
create policy vphrases_anon_select on public.viral_phrases
  for select to anon using (true);

drop policy if exists vphrases_anon_insert on public.viral_phrases;
create policy vphrases_anon_insert on public.viral_phrases
  for insert to anon with check (true);

drop policy if exists vphrases_anon_update on public.viral_phrases;
create policy vphrases_anon_update on public.viral_phrases
  for update to anon using (true) with check (true);

-- ============================================================
--  Listo. El pipeline poblará la tabla (upsert por phrase_hash) con la key
--  anon al analizar cada viral. Para revisar lo capturado:
--    select phrase, category, angle, virality, source_platform, created_at
--    from public.viral_phrases
--    where used_in_story = false
--    order by virality desc nulls last, created_at desc;
-- ============================================================

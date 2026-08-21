-- ============================================================
--  TheLanding · Permisos y estadísticas (ejecutar DESPUÉS de schema.sql)
-- ============================================================
--  Pensado para una base de datos COMPARTIDA (p. ej. reutilizada de otro
--  proyecto). Con esto, TheLanding usa solo la clave ANON y queda limitado a:
--    · INSERTAR en leads y events
--    · LEER estadísticas AGREGADAS (recuentos, sin emails)
--  No puede leer filas individuales ni tocar ninguna otra tabla.
--
--  Ejecuta este archivo en:  Supabase → SQL Editor → New query → Run
-- ============================================================

-- ---------- 1) Permitir que anon inserte (y solo inserte) ----------
grant insert on public.leads  to anon;
grant insert on public.events to anon;

-- Defensa en profundidad: anon nunca debe poder leer filas crudas.
-- (Aunque no hubiera SELECT, RLS ya lo bloquea al no existir política de lectura.)
revoke select on public.leads  from anon;
revoke select on public.events from anon;

-- Políticas de inserción (RLS ya está activado por schema.sql)
drop policy if exists "anon puede insertar leads"  on public.leads;
drop policy if exists "anon puede insertar events" on public.events;

create policy "anon puede insertar leads"
  on public.leads for insert to anon with check (true);

create policy "anon puede insertar events"
  on public.events for insert to anon with check (true);

-- ---------- 2) Función de estadísticas agregadas (sin PII) ----------
--  SECURITY DEFINER: se ejecuta con permisos del creador (puede leer las
--  tablas), pero SOLO devuelve recuentos. anon puede llamarla pero no puede
--  leer emails.
create or replace function public.thelanding_stats()
returns jsonb
language sql
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'totals', (
      select jsonb_build_object(
        'views', count(*) filter (where e.type = 'page_view'),
        'unique_visitors', count(distinct e.session_id) filter (where e.type = 'page_view'),
        'clicks', count(*) filter (where e.type = 'cta_click')
      )
      from public.events e
    ) || jsonb_build_object(
        'leads',       (select count(*) from public.leads),
        'leads_today', (select count(*) from public.leads where created_at::date = current_date),
        'leads_7d',    (select count(*) from public.leads where created_at >= now() - interval '7 days')
    ),

    'per_product', (
      select coalesce(
        jsonb_agg(jsonb_build_object('product_id', pid, 'clicks', clicks, 'leads', leads) order by leads desc),
        '[]'::jsonb)
      from (
        select u.pid,
               count(*) filter (where u.src = 'click') as clicks,
               count(*) filter (where u.src = 'lead')  as leads
        from (
          select product_id as pid, 'click'::text as src
            from public.events where type = 'cta_click' and product_id is not null
          union all
          select product_id as pid, 'lead'::text as src
            from public.leads where product_id is not null
        ) u
        group by u.pid
      ) pp
    ),

    'sources', (
      select coalesce(
        jsonb_agg(jsonb_build_object('source', source, 'count', cnt) order by cnt desc),
        '[]'::jsonb)
      from (
        select
          case
            when nullif(utm_source, '') is not null then lower(utm_source)
            when nullif(referrer, '') is null then 'directo'
            else lower(regexp_replace(regexp_replace(referrer, '^https?://(www\.)?', ''), '/.*$', ''))
          end as source,
          count(*) as cnt
        from public.events
        where type = 'page_view'
        group by 1
        order by cnt desc
        limit 8
      ) s
    ),

    'devices', (
      select coalesce(
        jsonb_agg(jsonb_build_object('device', device, 'count', cnt) order by cnt desc),
        '[]'::jsonb)
      from (
        select coalesce(nullif(device, ''), 'unknown') as device, count(*) as cnt
        from public.events
        where type = 'page_view'
        group by 1
      ) d
    ),

    'series', (
      select coalesce(
        jsonb_agg(jsonb_build_object(
          'day', to_char(day, 'YYYY-MM-DD'),
          'views', views, 'clicks', clicks, 'leads', leads) order by day),
        '[]'::jsonb)
      from (
        select g.day::date as day,
          (select count(*) from public.events e where e.type = 'page_view' and e.created_at::date = g.day::date) as views,
          (select count(*) from public.events e where e.type = 'cta_click' and e.created_at::date = g.day::date) as clicks,
          (select count(*) from public.leads  l where l.created_at::date = g.day::date) as leads
        from generate_series(current_date - interval '29 days', current_date, interval '1 day') g(day)
      ) ser
    )
  );
$$;

-- Permitir que la app (rol anon) llame a la función de estadísticas.
grant execute on function public.thelanding_stats() to anon;

-- ============================================================
--  ¡Listo! Ahora TheLanding puede guardar leads/eventos y mostrar
--  estadísticas, usando solo la clave anon, sin exponer datos.
-- ============================================================

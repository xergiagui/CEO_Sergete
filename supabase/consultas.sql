-- ============================================================
--  TheLanding · Consultas útiles para ver tus LEADS y datos
--  Pégalas en Supabase → SQL Editor → Run (una cada vez).
--  El editor SQL se ejecuta como propietario, así que SÍ puede leer
--  (a diferencia de la web, que solo inserta).
-- ============================================================

-- ------------------------------------------------------------
-- 1) ÚLTIMOS LEADS (los más recientes primero)
--    Hora en horario de España para que sea legible.
-- ------------------------------------------------------------
select
  email,
  product_name                                   as producto,
  to_char(created_at at time zone 'Europe/Madrid',
          'DD/MM/YYYY HH24:MI')                  as fecha,
  coalesce(utm_source, 'directo')                as fuente,
  device                                         as dispositivo
from public.leads
order by created_at desc
limit 100;


-- ------------------------------------------------------------
-- 2) LEADS POR PRODUCTO (ranking)
-- ------------------------------------------------------------
select
  product_name        as producto,
  count(*)            as emails
from public.leads
group by product_name
order by emails desc;


-- ------------------------------------------------------------
-- 3) LEADS POR DÍA (últimos 30 días)
-- ------------------------------------------------------------
select
  (created_at at time zone 'Europe/Madrid')::date as dia,
  count(*)                                          as emails
from public.leads
where created_at >= now() - interval '30 days'
group by dia
order by dia desc;


-- ------------------------------------------------------------
-- 4) LEADS POR FUENTE DE TRÁFICO (de qué red vienen)
-- ------------------------------------------------------------
select
  coalesce(nullif(utm_source, ''), 'directo') as fuente,
  count(*)                                     as emails
from public.leads
group by fuente
order by emails desc;


-- ------------------------------------------------------------
-- 5) LISTA DE EMAILS ÚNICOS (para exportar a tu newsletter)
-- ------------------------------------------------------------
select distinct email
from public.leads
order by email;


-- ------------------------------------------------------------
-- 6) EMBUDO GLOBAL (visitas → clics → emails)
-- ------------------------------------------------------------
select
  (select count(*) from public.events where type = 'page_view') as visitas,
  (select count(distinct session_id) from public.events
     where type = 'page_view')                                   as visitantes_unicos,
  (select count(*) from public.events where type = 'cta_click')  as clics,
  (select count(*) from public.leads)                            as emails;


-- ------------------------------------------------------------
-- 7) MENSAJES DE CONTACTO recientes
-- ------------------------------------------------------------
select
  coalesce(name, '(sin nombre)') as nombre,
  email,
  message                        as mensaje,
  to_char(created_at at time zone 'Europe/Madrid',
          'DD/MM/YYYY HH24:MI')  as fecha
from public.messages
order by created_at desc
limit 100;


-- ============================================================
--  BONUS · Vistas guardadas (opcional)
--  Ejecútalas una vez y luego podrás abrir "leads_recientes"
--  directamente en Table editor → Views.
-- ============================================================
create or replace view public.leads_recientes as
select
  email,
  product_name as producto,
  created_at,
  coalesce(utm_source, 'directo') as fuente,
  device
from public.leads
order by created_at desc;

create or replace view public.embudo as
select
  (select count(*) from public.events where type = 'page_view') as visitas,
  (select count(distinct session_id) from public.events where type = 'page_view') as visitantes_unicos,
  (select count(*) from public.events where type = 'cta_click') as clics,
  (select count(*) from public.leads) as emails;

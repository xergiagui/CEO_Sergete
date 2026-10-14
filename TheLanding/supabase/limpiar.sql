-- ============================================================
--  TheLanding · Limpiar datos de prueba
--  ⚠️ BASE COMPARTIDA CON LEADS REALES. Este script NUNCA se ejecuta
--     ni se propone sin el OK explícito de Sergio.
--  Supabase → SQL Editor → pega y Run (solo con ese OK).
--  Borra datos de forma permanente. Revisa antes de ejecutar.
-- ============================================================

-- ------------------------------------------------------------
--  PASO 1 · Ver cuánto hay ahora (solo lectura, para comprobar)
-- ------------------------------------------------------------
select 'leads'    as tabla, count(*) as filas from public.leads
union all
select 'events'   as tabla, count(*)          from public.events
union all
select 'messages' as tabla, count(*)          from public.messages;


-- ============================================================
--  PASO 2 · OPCIÓN POR DEFECTO · Borrar SOLO las filas de prueba
--  Conserva las visitas, leads y mensajes reales.
-- ============================================================
delete from public.leads
  where email ilike '%@test.com'
     or email = 'prueba-e2e@test.com'
     or session_id in ('e2e-1', 'conn-test', 'prod-check', 'test1');

delete from public.events
  where session_id in ('e2e-1', 'conn-test', 'prod-check', 'test1');

delete from public.messages
  where email ilike '%@test.com'
     or name = 'Prueba Sergio';
--  ⚠️ No añadas «or message ilike '%prueba%'» sin revisar antes con un select:
--     un mensaje real puede contener la palabra «prueba».


-- ============================================================
--  OPCIÓN PELIGROSA · Borrar TODO (vacía las 3 tablas)
--  ⛔ Borra también los leads REALES. Queda comentada a propósito.
--  Solo si Sergio lo pide de forma explícita: descomenta las 3 líneas
--  y comenta el PASO 2.
-- ============================================================
-- delete from public.leads;
-- delete from public.events;
-- delete from public.messages;


-- ------------------------------------------------------------
--  PASO 3 · Confirmar el resultado
-- ------------------------------------------------------------
select 'leads'    as tabla, count(*) as filas from public.leads
union all
select 'events'   as tabla, count(*)          from public.events
union all
select 'messages' as tabla, count(*)          from public.messages;

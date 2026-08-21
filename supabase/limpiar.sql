-- ============================================================
--  TheLanding · Limpiar datos de prueba antes de lanzar
--  Supabase → SQL Editor → pega y Run.
--  ⚠️ Borra datos de forma permanente. Revisa antes de ejecutar.
-- ============================================================

-- ------------------------------------------------------------
--  PASO 1 · Ver cuánto hay ahora (opcional, para comprobar)
-- ------------------------------------------------------------
select 'leads'    as tabla, count(*) as filas from public.leads
union all
select 'events'   as tabla, count(*)          from public.events
union all
select 'messages' as tabla, count(*)          from public.messages;


-- ============================================================
--  OPCIÓN A (RECOMENDADA antes de lanzar) · Borrar TODO
--  Deja las 3 tablas vacías para empezar de cero con datos reales.
--  Descomenta las 3 líneas (quita el "-- ") y ejecútalas.
-- ============================================================
delete from public.leads;
delete from public.events;
delete from public.messages;


-- ============================================================
--  OPCIÓN B (alternativa) · Borrar SOLO las filas de prueba
--  Úsala en lugar de la Opción A si ya tienes visitas reales que
--  quieres conservar. (Comenta la Opción A de arriba si usas esta.)
-- ============================================================
-- delete from public.leads
--   where email ilike '%@test.com'
--      or email = 'prueba-e2e@test.com'
--      or session_id in ('e2e-1', 'conn-test', 'prod-check', 'test1');
--
-- delete from public.events
--   where session_id in ('e2e-1', 'conn-test', 'prod-check', 'test1');
--
-- delete from public.messages
--   where email ilike '%@test.com'
--      or message ilike '%prueba%'
--      or name = 'Prueba Sergio';


-- ------------------------------------------------------------
--  PASO 3 · Confirmar que quedó limpio
-- ------------------------------------------------------------
select 'leads'    as tabla, count(*) as filas from public.leads
union all
select 'events'   as tabla, count(*)          from public.events
union all
select 'messages' as tabla, count(*)          from public.messages;

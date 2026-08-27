# Indexación semántica del catálogo de B-roll

Herramientas para poblar la tabla `broll_assets` de Supabase (ver
`TheLanding/supabase/broll_assets.sql`) con los metadatos + embeddings de los
vídeos de `superposiciones/`. El pipeline (Fase C) usa ese catálogo para elegir
el b-roll por SIGNIFICADO (`pipeline_core.broll_match_filename`).

## Flujo (una vez creada la tabla con broll_assets.sql)

1. **`extract_frames.py`** — selecciona los N clips más ligeros de
   `superposiciones/`, extrae 3 frames (20/50/80 %) por clip en un montaje
   horizontal y recoge metadatos técnicos → `frames/` + `broll_tech.json`.
2. **Analizar los montajes** (visión) y escribir un `sem/sem_*.json` por lote con
   los campos semánticos: `orientation, category, logical_tags, description,
   objects, setting, actions, mood, concepts`. Marcar avisos en `logical_tags`
   (`aviso-marca-ajena`, `aviso-persona-identificable`, `aviso-marca-agua`,
   `aviso-baja-calidad`) para que el pipeline los descarte.
3. **`build_records.py`** — fusiona técnico + semántico y construye `search_text`
   → `broll_records.json`.
4. **`embed.py`** — genera embeddings 384d con
   `paraphrase-multilingual-MiniLM-L12-v2` (fastembed) → `broll_final.json`.
   ⚠️ Debe ser el MISMO modelo que usa el pipeline en runtime.
5. **`populate_broll.py`** — upsert (`on_conflict=filename`) a Supabase con la
   key anon de `TheLanding/.env.local`.

## Notas
- Rutas absolutas (SRC, ENV) están fijadas a esta máquina; ajústalas si cambias
  de equipo.
- Para **añadir los 22 clips pesados** omitidos: sube `KEEP` en
  `extract_frames.py` (o filtra por nombre), repite pasos 2-5. El upsert es
  idempotente, no duplica.
- Consola Windows: ejecuta con `PYTHONIOENCODING=utf-8` para evitar errores con
  emojis/acentos en los `print`.

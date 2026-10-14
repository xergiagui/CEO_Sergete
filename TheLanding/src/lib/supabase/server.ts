import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// ============================================================
//  Cliente Supabase de SERVIDOR.
//  Usa la clave ANON (pública) pero SOLO desde el servidor.
//  La seguridad la ponen las reglas RLS de Supabase:
//    - anon puede INSERTAR en leads/events (ver supabase/policies.sql)
//    - anon NO puede LEER filas (los emails nunca se exponen)
//    - las estadísticas se leen vía función agregada (RPC) sin PII
//  Así, aunque la BBDD esté compartida con otro proyecto, TheLanding
//  no tiene acceso de administrador a nada más.
//  Devuelve null si faltan las variables (la app no se rompe).
// ============================================================

let cached: SupabaseClient | null = null;

export function getSupabaseServer(): SupabaseClient | null {
  if (cached) return cached;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_ANON_KEY;

  if (!url || !key || url.includes("TU-PROYECTO") || key.includes("tu_anon")) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        "[TheLanding] Supabase no configurado: define SUPABASE_URL y SUPABASE_ANON_KEY en .env.local"
      );
    }
    return null;
  }

  cached = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}

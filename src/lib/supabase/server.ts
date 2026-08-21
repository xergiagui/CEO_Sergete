import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// ============================================================
//  Cliente Supabase de SERVIDOR (service_role).
//  Solo se importa desde API routes / código de servidor.
//  Devuelve null si faltan las variables de entorno, para que
//  la app funcione en desarrollo sin romperse (sin guardar nada).
// ============================================================

let cached: SupabaseClient | null = null;

export function getSupabaseAdmin(): SupabaseClient | null {
  if (cached) return cached;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key || url.includes("TU-PROYECTO")) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        "[TheLanding] Supabase no configurado: define SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en .env.local"
      );
    }
    return null;
  }

  cached = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}

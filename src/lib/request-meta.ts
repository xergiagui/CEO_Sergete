import type { NextRequest } from "next/server";

// ============================================================
//  Extrae metadatos comunes de una petición para la analítica:
//  device, país (si el hosting lo aporta), user-agent.
// ============================================================

export function deviceFromUA(ua: string | null): string {
  if (!ua) return "unknown";
  const s = ua.toLowerCase();
  if (/tablet|ipad/.test(s)) return "tablet";
  if (/mobi|android|iphone/.test(s)) return "mobile";
  return "desktop";
}

export function requestMeta(req: NextRequest) {
  const ua = req.headers.get("user-agent");
  // Vercel expone el país en esta cabecera; en local será null.
  const country =
    req.headers.get("x-vercel-ip-country") ||
    req.headers.get("cf-ipcountry") ||
    null;
  return {
    user_agent: ua,
    device: deviceFromUA(ua),
    country,
  };
}

import { NextRequest, NextResponse } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { PRODUCTS } from "@/lib/products";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Row = {
  type?: string;
  product_id: string | null;
  session_id: string | null;
  utm_source: string | null;
  referrer: string | null;
  device: string | null;
  created_at: string;
};

function dayKey(iso: string) {
  return iso.slice(0, 10); // YYYY-MM-DD
}

function sourceLabel(r: { utm_source: string | null; referrer: string | null }) {
  if (r.utm_source) return r.utm_source.toLowerCase();
  if (!r.referrer) return "directo";
  try {
    const host = new URL(r.referrer).hostname.replace(/^www\./, "");
    return host || "directo";
  } catch {
    return "directo";
  }
}

export async function GET(req: NextRequest) {
  // ---- Autenticación por contraseña ----
  const pass = req.headers.get("x-stats-password");
  const expected = process.env.STATS_PASSWORD;
  if (!expected) {
    return NextResponse.json(
      { ok: false, error: "STATS_PASSWORD no configurada en el servidor" },
      { status: 500 }
    );
  }
  if (!pass || pass !== expected) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    return NextResponse.json({ ok: false, error: "Supabase no configurado" }, { status: 500 });
  }

  const { data: events, error: evErr } = await supabase
    .from("events")
    .select("type, product_id, session_id, utm_source, referrer, device, created_at")
    .order("created_at", { ascending: false })
    .limit(50000);

  const { data: leads, error: ldErr } = await supabase
    .from("leads")
    .select("product_id, session_id, utm_source, referrer, device, created_at, email")
    .order("created_at", { ascending: false })
    .limit(50000);

  if (evErr || ldErr) {
    return NextResponse.json(
      { ok: false, error: (evErr || ldErr)?.message },
      { status: 500 }
    );
  }

  const ev = (events ?? []) as (Row & { type: string })[];
  const ld = (leads ?? []) as (Row & { email: string })[];

  const views = ev.filter((e) => e.type === "page_view");
  const clicks = ev.filter((e) => e.type === "cta_click");

  const uniqueVisitors = new Set(views.map((e) => e.session_id).filter(Boolean)).size;
  const totalViews = views.length;
  const totalClicks = clicks.length;
  const totalLeads = ld.length;

  const pct = (num: number, den: number) =>
    den > 0 ? Math.round((num / den) * 1000) / 10 : 0;

  // ---- Por producto ----
  const perProduct = PRODUCTS.map((p) => {
    const c = clicks.filter((e) => e.product_id === p.id).length;
    const l = ld.filter((e) => e.product_id === p.id).length;
    return {
      id: p.id,
      name: p.name,
      accent: p.accent,
      clicks: c,
      leads: l,
      cr: pct(l, c), // clic -> lead
    };
  }).sort((a, b) => b.leads - a.leads || b.clicks - a.clicks);

  // ---- Fuentes de tráfico (por visita) ----
  const sourceMap = new Map<string, number>();
  for (const v of views) {
    const key = sourceLabel(v);
    sourceMap.set(key, (sourceMap.get(key) ?? 0) + 1);
  }
  const sources = [...sourceMap.entries()]
    .map(([source, count]) => ({ source, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // ---- Dispositivos ----
  const deviceMap = new Map<string, number>();
  for (const v of views) {
    const key = v.device || "unknown";
    deviceMap.set(key, (deviceMap.get(key) ?? 0) + 1);
  }
  const devices = [...deviceMap.entries()]
    .map(([device, count]) => ({ device, count }))
    .sort((a, b) => b.count - a.count);

  // ---- Serie diaria (últimos 30 días) ----
  const days: string[] = [];
  const base = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(base.getTime() - i * 86400000);
    days.push(d.toISOString().slice(0, 10));
  }
  const seriesMap = new Map<string, { views: number; clicks: number; leads: number }>();
  days.forEach((d) => seriesMap.set(d, { views: 0, clicks: 0, leads: 0 }));
  for (const v of views) {
    const b = seriesMap.get(dayKey(v.created_at));
    if (b) b.views++;
  }
  for (const c of clicks) {
    const b = seriesMap.get(dayKey(c.created_at));
    if (b) b.clicks++;
  }
  for (const l of ld) {
    const b = seriesMap.get(dayKey(l.created_at));
    if (b) b.leads++;
  }
  const series = days.map((d) => ({ day: d.slice(5), ...seriesMap.get(d)! }));

  // ---- Extras ----
  const todayKey = new Date().toISOString().slice(0, 10);
  const leadsToday = ld.filter((l) => dayKey(l.created_at) === todayKey).length;
  const weekAgo = new Date(base.getTime() - 7 * 86400000).toISOString();
  const leads7d = ld.filter((l) => l.created_at >= weekAgo).length;

  return NextResponse.json({
    ok: true,
    generatedAt: new Date().toISOString(),
    totals: {
      views: totalViews,
      uniqueVisitors,
      clicks: totalClicks,
      leads: totalLeads,
      leadsToday,
      leads7d,
    },
    funnel: {
      viewToClick: pct(totalClicks, totalViews),
      clickToLead: pct(totalLeads, totalClicks),
      viewToLead: pct(totalLeads, totalViews),
    },
    perProduct,
    sources,
    devices,
    series,
  });
}

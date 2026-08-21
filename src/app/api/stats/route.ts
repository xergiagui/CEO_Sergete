import { NextRequest, NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";
import { PRODUCTS } from "@/lib/products";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Agg = {
  totals: {
    views: number;
    unique_visitors: number;
    clicks: number;
    leads: number;
    leads_today: number;
    leads_7d: number;
  };
  per_product: { product_id: string; clicks: number; leads: number }[];
  sources: { source: string; count: number }[];
  devices: { device: string; count: number }[];
  series: { day: string; views: number; clicks: number; leads: number }[];
};

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

  const supabase = getSupabaseServer();
  if (!supabase) {
    return NextResponse.json({ ok: false, error: "Supabase no configurado" }, { status: 500 });
  }

  // La función agregada devuelve solo recuentos (sin datos personales).
  const { data, error } = await supabase.rpc("thelanding_stats");
  if (error) {
    return NextResponse.json(
      {
        ok: false,
        error:
          "No se pudo leer las estadísticas. ¿Ejecutaste supabase/policies.sql? Detalle: " +
          error.message,
      },
      { status: 500 }
    );
  }

  const agg = data as Agg;
  const t = agg.totals;
  const pct = (num: number, den: number) =>
    den > 0 ? Math.round((num / den) * 1000) / 10 : 0;

  const perProduct = PRODUCTS.map((p) => {
    const row = agg.per_product.find((r) => r.product_id === p.id);
    const clicks = row?.clicks ?? 0;
    const leads = row?.leads ?? 0;
    return {
      id: p.id,
      name: p.name,
      accent: p.accent,
      clicks,
      leads,
      cr: pct(leads, clicks),
    };
  }).sort((a, b) => b.leads - a.leads || b.clicks - a.clicks);

  return NextResponse.json({
    ok: true,
    generatedAt: new Date().toISOString(),
    totals: {
      views: t.views,
      uniqueVisitors: t.unique_visitors,
      clicks: t.clicks,
      leads: t.leads,
      leadsToday: t.leads_today,
      leads7d: t.leads_7d,
    },
    funnel: {
      viewToClick: pct(t.clicks, t.views),
      clickToLead: pct(t.leads, t.clicks),
      viewToLead: pct(t.leads, t.views),
    },
    perProduct,
    sources: agg.sources ?? [],
    devices: agg.devices ?? [],
    series: (agg.series ?? []).map((s) => ({
      day: s.day.slice(5), // MM-DD
      views: s.views,
      clicks: s.clicks,
      leads: s.leads,
    })),
  });
}

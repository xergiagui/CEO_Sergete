import { NextRequest, NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";
import { requestMeta } from "@/lib/request-meta";

export const runtime = "nodejs";

const VALID = new Set([
  "page_view",
  "product_view",
  "cta_click",
  "email_submit",
  "affiliate_redirect",
]);

export async function POST(req: NextRequest) {
  let data: Record<string, unknown> = {};
  try {
    data = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "bad_json" }, { status: 400 });
  }

  const type = String(data.type ?? "");
  if (!VALID.has(type)) {
    return NextResponse.json({ ok: false, error: "bad_type" }, { status: 400 });
  }

  const supabase = getSupabaseServer();
  // Sin Supabase configurado no rompemos: devolvemos ok para no bloquear la UX.
  if (!supabase) return NextResponse.json({ ok: true, stored: false });

  const meta = requestMeta(req);
  const { error } = await supabase.from("events").insert({
    type,
    product_id: (data.product_id as string) ?? null,
    session_id: (data.session_id as string) ?? null,
    referrer: (data.referrer as string) ?? null,
    utm_source: (data.utm_source as string) ?? null,
    utm_medium: (data.utm_medium as string) ?? null,
    utm_campaign: (data.utm_campaign as string) ?? null,
    path: (data.path as string) ?? null,
    ...meta,
  });

  if (error) {
    console.error("[event] insert error:", error.message);
    return NextResponse.json({ ok: false, error: "db" }, { status: 500 });
  }
  return NextResponse.json({ ok: true, stored: true });
}

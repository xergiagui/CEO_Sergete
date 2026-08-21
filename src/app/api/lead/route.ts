import { NextRequest, NextResponse } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { requestMeta } from "@/lib/request-meta";
import { getProduct } from "@/lib/products";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(req: NextRequest) {
  let data: Record<string, unknown> = {};
  try {
    data = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "bad_json" }, { status: 400 });
  }

  const email = String(data.email ?? "").trim().toLowerCase();
  const productId = String(data.product_id ?? "");
  const product = getProduct(productId);

  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ ok: false, error: "bad_email" }, { status: 400 });
  }
  if (!product) {
    return NextResponse.json({ ok: false, error: "bad_product" }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();
  const meta = requestMeta(req);

  // Si Supabase está configurado, guardamos lead + evento email_submit.
  if (supabase) {
    const common = {
      session_id: (data.session_id as string) ?? null,
      referrer: (data.referrer as string) ?? null,
      utm_source: (data.utm_source as string) ?? null,
      utm_medium: (data.utm_medium as string) ?? null,
      utm_campaign: (data.utm_campaign as string) ?? null,
      ...meta,
    };

    const { error: leadErr } = await supabase.from("leads").insert({
      email,
      product_id: product.id,
      product_name: product.fullName,
      landing_path: (data.path as string) ?? null,
      ...common,
    });
    if (leadErr) {
      console.error("[lead] insert error:", leadErr.message);
      // No bloqueamos la redirección por un fallo de guardado.
    }

    await supabase.from("events").insert({
      type: "email_submit",
      product_id: product.id,
      path: (data.path as string) ?? null,
      ...common,
    });
  }

  // Devolvemos el destino de afiliado para que el cliente redirija.
  return NextResponse.json({ ok: true, redirect: product.href });
}

import { NextRequest, NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";
import { requestMeta } from "@/lib/request-meta";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function esc(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export async function POST(req: NextRequest) {
  let data: Record<string, unknown> = {};
  try {
    data = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "bad_json" }, { status: 400 });
  }

  const name = String(data.name ?? "").trim().slice(0, 120);
  const email = String(data.email ?? "").trim().toLowerCase().slice(0, 200);
  const message = String(data.message ?? "").trim().slice(0, 4000);

  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ ok: false, error: "bad_email" }, { status: 400 });
  }
  if (message.length < 5) {
    return NextResponse.json({ ok: false, error: "short_message" }, { status: 400 });
  }

  const meta = requestMeta(req);
  let stored = false;
  let emailed = false;

  // 1) Guardar copia en Supabase (por si el email fallara)
  const supabase = getSupabaseServer();
  if (supabase) {
    const { error } = await supabase.from("messages").insert({
      name: name || null,
      email,
      message,
      session_id: (data.session_id as string) ?? null,
      user_agent: meta.user_agent,
    });
    if (!error) stored = true;
    else console.error("[contact] insert error:", error.message);
  }

  // 2) Enviar email (destinatario oculto en variable de entorno del servidor)
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.CONTACT_EMAIL;
  const from = process.env.CONTACT_FROM || "TheLanding <onboarding@resend.dev>";

  if (apiKey && to) {
    try {
      const res = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from,
          to: [to],
          reply_to: email,
          subject: `Nuevo mensaje de contacto — ${name || email}`,
          html: `
            <div style="font-family:system-ui,sans-serif;font-size:15px;color:#14171f">
              <h2 style="margin:0 0 12px">Nuevo mensaje desde TheLanding</h2>
              <p><strong>Nombre:</strong> ${esc(name) || "(sin nombre)"}</p>
              <p><strong>Email:</strong> ${esc(email)}</p>
              <p><strong>Mensaje:</strong></p>
              <p style="white-space:pre-wrap;background:#f6f7f9;padding:12px;border-radius:8px">${esc(message)}</p>
            </div>`,
        }),
      });
      if (res.ok) emailed = true;
      else console.error("[contact] resend error:", res.status, await res.text());
    } catch (e) {
      console.error("[contact] resend exception:", e);
    }
  }

  if (stored || emailed) {
    return NextResponse.json({ ok: true, stored, emailed });
  }
  // Ni se guardó ni se envió: avisar (p. ej. falta configurar Resend y Supabase).
  return NextResponse.json(
    { ok: false, error: "not_delivered" },
    { status: 500 }
  );
}

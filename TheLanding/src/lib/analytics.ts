"use client";

// ============================================================
//  Analítica de cliente (ligera, sin cookies de terceros).
//  - Genera un session_id estable por navegador (localStorage).
//  - Captura UTM y referrer de la primera visita.
//  - Envía eventos al backend con navigator.sendBeacon (no bloquea).
// ============================================================

const SESSION_KEY = "tl_sid";
const ATTR_KEY = "tl_attr";

type Attribution = {
  referrer: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
};

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxxyxxxyxxxyxxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = uuid();
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

export function getAttribution(): Attribution {
  if (typeof window === "undefined") {
    return { referrer: null, utm_source: null, utm_medium: null, utm_campaign: null };
  }
  const stored = localStorage.getItem(ATTR_KEY);
  if (stored) {
    try {
      return JSON.parse(stored) as Attribution;
    } catch {
      /* ignore */
    }
  }
  const params = new URLSearchParams(window.location.search);
  const attr: Attribution = {
    referrer: document.referrer || null,
    utm_source: params.get("utm_source"),
    utm_medium: params.get("utm_medium"),
    utm_campaign: params.get("utm_campaign"),
  };
  localStorage.setItem(ATTR_KEY, JSON.stringify(attr));
  return attr;
}

export type EventType =
  | "page_view"
  | "product_view"
  | "cta_click"
  | "email_submit"
  | "affiliate_redirect";

export function track(type: EventType, productId?: string) {
  if (typeof window === "undefined") return;
  const payload = {
    type,
    product_id: productId ?? null,
    session_id: getSessionId(),
    path: window.location.pathname,
    ...getAttribution(),
  };
  const body = JSON.stringify(payload);
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/event", new Blob([body], { type: "application/json" }));
    } else {
      fetch("/api/event", { method: "POST", body, keepalive: true });
    }
  } catch {
    /* la analítica nunca debe romper la experiencia */
  }
}

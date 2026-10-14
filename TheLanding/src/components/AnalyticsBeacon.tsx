"use client";

import { useEffect } from "react";
import { track } from "@/lib/analytics";

// Registra una visita (page_view) al cargar la landing.
export default function AnalyticsBeacon() {
  useEffect(() => {
    track("page_view");
  }, []);
  return null;
}

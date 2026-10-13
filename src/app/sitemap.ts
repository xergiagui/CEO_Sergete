import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    {
      url: `${SITE_URL}/`,
      lastModified,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/contacto`,
      lastModified,
      changeFrequency: "yearly",
      priority: 0.4,
    },
    // Solo rutas indexables. /privacidad es noindex: no va aquí.
  ];
}

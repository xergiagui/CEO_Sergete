import type { Metadata, Viewport } from "next";
import { Geist, Fraunces } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
  axes: ["opsz", "SOFT", "WONK"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

const TITLE =
  "Aprende a vender y ganar dinero online · 4 recursos de Luis Monje Malo";
const DESCRIPTION =
  "Los 4 recursos de Luis Monje Malo para vender más y ganar dinero online: la Escuela de Afiliados, el mejor negocio destripado, el curso de objeciones y la mentoría. Elige el tuyo en 30 segundos.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · TheLanding",
  },
  description: DESCRIPTION,
  applicationName: "TheLanding",
  keywords: [
    "marketing de afiliados",
    "ganar dinero online",
    "vender por internet",
    "Luis Monje Malo",
    "escuela de afiliados",
    "curso de ventas",
    "mentoría de ventas",
    "gestión de objeciones",
    "ingresos pasivos",
  ],
  authors: [{ name: "Sergio Aguilar" }],
  creator: "Sergio Aguilar",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "es_ES",
    url: SITE_URL,
    siteName: "TheLanding",
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  category: "business",
};

export const viewport: Viewport = {
  themeColor: "#070a12",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

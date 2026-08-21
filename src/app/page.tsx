import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import ProofBar from "@/components/ProofBar";
import ProductsSection from "@/components/ProductsSection";
import Faq, { FAQS } from "@/components/Faq";
import FinalCta from "@/components/FinalCta";
import Footer from "@/components/Footer";
import AnalyticsBeacon from "@/components/AnalyticsBeacon";
import { PRODUCTS } from "@/lib/products";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

function StructuredData() {
  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: SITE_URL,
        name: "Selección · Monge Malo",
        description:
          "Los 4 recursos de Luis Monge Malo para aprender a vender y ganar dinero online.",
        inLanguage: "es-ES",
      },
      {
        "@type": "Person",
        "@id": `${SITE_URL}/#luis-monge-malo`,
        name: "Luis Monge Malo",
        description: "Referente en ventas y marketing de afiliación en español.",
      },
      {
        "@type": "ItemList",
        "@id": `${SITE_URL}/#recursos`,
        name: "4 recursos para vender y ganar dinero online",
        numberOfItems: PRODUCTS.length,
        itemListElement: PRODUCTS.map((p, i) => ({
          "@type": "ListItem",
          position: i + 1,
          item: {
            "@type": "Product",
            name: p.fullName,
            description: `${p.hook}. ${p.subhook}`,
            category: p.kind,
            brand: { "@id": `${SITE_URL}/#luis-monge-malo` },
            offers: {
              "@type": "Offer",
              price: p.priceValue,
              priceCurrency: "EUR",
              url: p.href,
              availability: "https://schema.org/InStock",
            },
          },
        })),
      },
      {
        "@type": "FAQPage",
        "@id": `${SITE_URL}/#faq`,
        mainEntity: FAQS.map((f) => ({
          "@type": "Question",
          name: f.q,
          acceptedAnswer: { "@type": "Answer", text: f.a },
        })),
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }}
    />
  );
}

export default function Home() {
  return (
    <>
      <StructuredData />
      <Nav />
      <main className="flex flex-1 flex-col">
        <Hero />
        <ProofBar />
        <ProductsSection products={PRODUCTS} />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
      <AnalyticsBeacon />
    </>
  );
}

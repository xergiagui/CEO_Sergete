import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import ProofBar from "@/components/ProofBar";
import ProductsSection from "@/components/ProductsSection";
import Faq, { FAQS } from "@/components/Faq";
import FinalCta from "@/components/FinalCta";
import Footer from "@/components/Footer";
import AnalyticsBeacon from "@/components/AnalyticsBeacon";
import { PRODUCTS } from "@/lib/products";

import { SITE_URL } from "@/lib/site";

function StructuredData() {
  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}/#org`,
        name: "Selección · Monge Malo",
        url: SITE_URL,
        logo: {
          "@type": "ImageObject",
          url: `${SITE_URL}/apple-icon`,
          width: 180,
          height: 180,
        },
        description:
          "Selección independiente de los 5 recursos de Luis Monge Malo para aprender a vender online.",
      },
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: SITE_URL,
        name: "Selección · Monge Malo",
        description:
          "Los 5 recursos de Luis Monge Malo para aprender a vender online.",
        inLanguage: "es-ES",
        publisher: { "@id": `${SITE_URL}/#org` },
      },
      {
        "@type": "Person",
        "@id": `${SITE_URL}/#luis-monge-malo`,
        name: "Luis Monge Malo",
        description: "Referente en ventas y marketing de afiliación en español.",
        url: "https://mongemalo.com",
        sameAs: ["https://mongemalo.com"],
      },
      {
        "@type": "ItemList",
        "@id": `${SITE_URL}/#recursos`,
        name: "5 recursos para vender online",
        numberOfItems: PRODUCTS.length,
        itemListElement: PRODUCTS.map((p, i) => ({
          "@type": "ListItem",
          position: i + 1,
          url: p.href,
          item: {
            "@type": "Product",
            name: p.fullName,
            description: `${p.hook}. ${p.subhook}`,
            category: p.kind,
            url: p.href,
            image: `${SITE_URL}/opengraph-image`,
            brand: { "@type": "Brand", name: "Luis Monge Malo" },
            offers: {
              "@type": "Offer",
              price: p.priceValue,
              priceCurrency: "EUR",
              url: p.href,
              availability: "https://schema.org/InStock",
              // Web de afiliación: la compra, el envío y las devoluciones
              // los gestiona el vendedor original (producto digital).
              shippingDetails: {
                "@type": "OfferShippingDetails",
                shippingRate: {
                  "@type": "MonetaryAmount",
                  value: 0,
                  currency: "EUR",
                },
                shippingDestination: {
                  "@type": "DefinedRegion",
                  addressCountry: "ES",
                },
                deliveryTime: {
                  "@type": "ShippingDeliveryTime",
                  handlingTime: {
                    "@type": "QuantitativeValue",
                    minValue: 0,
                    maxValue: 0,
                    unitCode: "DAY",
                  },
                  transitTime: {
                    "@type": "QuantitativeValue",
                    minValue: 0,
                    maxValue: 0,
                    unitCode: "DAY",
                  },
                },
              },
              hasMerchantReturnPolicy: {
                "@type": "MerchantReturnPolicy",
                applicableCountry: "ES",
                returnPolicyCategory:
                  "https://schema.org/MerchantReturnNotPermitted",
              },
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

// ============================================================
//  Catálogo de productos de afiliado
//  La landing NO repite la info detallada de las páginas de venta:
//  usa GANCHOS cortos para que el usuario pulse "Lo quiero".
// ============================================================

export type Product = {
  id: string;
  /** Nombre corto para la tarjeta */
  name: string;
  /** Nombre completo real del producto (para JSON-LD / SEO) */
  fullName: string;
  /** Categoría corta que aparece en la píldora superior */
  kind: string;
  /** Gancho principal — una frase que crea deseo, no que explica */
  hook: string;
  /** Subgancho de una línea */
  subhook: string;
  /** 3 bullets breves, orientados a beneficio/curiosidad */
  bullets: string[];
  /** Precio mostrado */
  price: string;
  /** Valor numérico para JSON-LD (aprox, en EUR) */
  priceValue: number;
  /** Texto del badge opcional (p.ej. "Más popular") */
  badge?: string;
  /** Enlace de afiliado final */
  href: string;
  /** Color de acento del producto (hex) */
  accent: string;
  /** Versión más oscura del acento, legible como texto sobre blanco (AA) */
  accentInk: string;
  /** Nombre del acento en CSS custom property */
  accentVar: string;
  /** Para quién es (mini-guía "cuál elijo") */
  bestFor: string;
};

export const PRODUCTS: Product[] = [
  {
    id: "mentoria",
    name: "Mentoría",
    fullName: "Mentoría de Luis Monge Malo",
    kind: "Mentoría",
    hook: "Solo necesitas una habilidad para ser libre",
    subhook: "Formación de venta que se cobra a 10.000 €/día.",
    bullets: [
      "Lecciones semanales de venta avanzada",
      "Grupo Alfa: +1.000 miembros activos",
      "2 cursos de regalo al entrar",
    ],
    price: "desde 200 €",
    priceValue: 200,
    badge: "Premium",
    href: "https://mongemalo.com/mentoria/?via=sergio-aguilar",
    accent: "#E11D48",
    accentInk: "#BE123C",
    accentVar: "--rose",
    bestFor: "Vas en serio y quieres acompañamiento continuo.",
  },
  {
    id: "objeciones",
    name: "Gestión de Objeciones",
    fullName: "Curso de Gestión de Objeciones",
    kind: "Curso",
    hook: "La frase perfecta para cerrar cada venta",
    subhook: "Deja de perder ventas por un 'me lo pienso'.",
    bullets: [
      "Basado en +7.000 conversaciones reales",
      "Desmonta el 'es caro' y el 'ahora no'",
      "3 meses de consultoría incluida",
    ],
    price: "450 €",
    priceValue: 450,
    href: "https://mongemalo.com/curso-objeciones-afiliados/?via=sergio-aguilar",
    accent: "#2563EB",
    accentInk: "#1D4ED8",
    accentVar: "--azure",
    bestFor: "Ya vendes pero se te caen ventas al final.",
  },
  {
    id: "escuela-afiliados",
    name: "Escuela de Afiliados",
    fullName: "Escuela de Afiliados de Luis Monge Malo",
    kind: "Membresía",
    hook: "Gana dinero vendiendo productos de otros",
    subhook: "Sin crear nada tuyo, sin stock y sin soporte al cliente.",
    bullets: [
      "Cero inversión: solo necesitas tu enlace",
      "Formación del nº1 en afiliación en español",
      "Empieza a vender esta misma semana",
    ],
    price: "49 €/mes",
    priceValue: 49,
    badge: "Más popular",
    href: "https://mongemalo.com/afiliados/?via=sergio-aguilar",
    accent: "#059669",
    accentInk: "#047857",
    accentVar: "--emerald",
    bestFor: "Empiezas de cero y quieres tu primer ingreso online.",
  },
  {
    id: "mejor-negocio",
    name: "El mejor negocio, destripado",
    fullName: "El mejor negocio del mundo, destripado",
    kind: "Audio · 3 h",
    hook: "El negocio que da dinero sin sudar sangre",
    subhook: "Casi 3 horas destripando cómo se gana de verdad.",
    bullets: [
      "Capta clientes sin depender del algoritmo",
      "Ideas que ningún gurú te cuenta gratis",
      "Modelo replicable y predecible",
    ],
    price: "120 €",
    priceValue: 120,
    href: "https://mongemalo.com/mejor-negocio-afiliados/?via=sergio-aguilar",
    accent: "#D97706",
    accentInk: "#B45309",
    accentVar: "--gold",
    bestFor: "Quieres entender el modelo antes de meterte de lleno.",
  },
];

export const getProduct = (id: string) => PRODUCTS.find((p) => p.id === id);

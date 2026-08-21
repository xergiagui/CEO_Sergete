import { ImageResponse } from "next/og";

export const alt =
  "Aprende a vender y ganar dinero online · 4 recursos de Luis Monge Malo";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background:
            "radial-gradient(900px 500px at 82% -10%, rgba(245,158,11,0.16), transparent 60%), radial-gradient(700px 500px at 5% 110%, rgba(37,99,235,0.10), transparent 60%), #ffffff",
          color: "#14171f",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 46,
              height: 46,
              borderRadius: 12,
              background: "#f5b841",
              color: "#1a1206",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 26,
              fontWeight: 700,
            }}
          >
            M
          </div>
          <div style={{ fontSize: 24, color: "#545c6e" }}>
            Selección · Monge Malo
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            fontSize: 76,
            fontWeight: 700,
            lineHeight: 1.04,
            letterSpacing: "-0.02em",
          }}
        >
          <div style={{ display: "flex" }}>El dinero no llega por suerte.</div>
          <div style={{ display: "flex" }}>Llega cuando aprendes</div>
          <div style={{ display: "flex", color: "#d97706" }}>a vender.</div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          {["Escuela de Afiliados", "Negocio destripado", "Objeciones", "Mentoría"].map(
            (t) => (
              <div
                key={t}
                style={{
                  fontSize: 22,
                  color: "#545c6e",
                  border: "1px solid #d7dbe4",
                  borderRadius: 999,
                  padding: "10px 20px",
                }}
              >
                {t}
              </div>
            )
          )}
        </div>
      </div>
    ),
    { ...size }
  );
}

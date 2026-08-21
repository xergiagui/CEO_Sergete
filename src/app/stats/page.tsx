"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

type Stats = {
  totals: {
    views: number;
    uniqueVisitors: number;
    clicks: number;
    leads: number;
    leadsToday: number;
    leads7d: number;
  };
  funnel: { viewToClick: number; clickToLead: number; viewToLead: number };
  perProduct: {
    id: string;
    name: string;
    accent: string;
    clicks: number;
    leads: number;
    cr: number;
  }[];
  sources: { source: string; count: number }[];
  devices: { device: string; count: number }[];
  series: { day: string; views: number; clicks: number; leads: number }[];
  generatedAt: string;
};

const PASS_KEY = "tl_stats_pass";

function Kpi({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="card p-5">
      <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
        {label}
      </p>
      <p
        className="mt-2 font-display text-3xl tracking-tight"
        style={{ color: accent || "var(--text)" }}
      >
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-[var(--text-muted)]">{sub}</p>}
    </div>
  );
}

const tooltipStyle = {
  background: "#0f1420",
  border: "1px solid #2a3247",
  borderRadius: 12,
  color: "#eef1f8",
  fontSize: 13,
};

export default function StatsPage() {
  const [pass, setPass] = useState("");
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (password: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/stats", {
        headers: { "x-stats-password": password },
        cache: "no-store",
      });
      if (res.status === 401) {
        setError("Contraseña incorrecta.");
        setAuthed(false);
        sessionStorage.removeItem(PASS_KEY);
        return;
      }
      const json = await res.json();
      if (!json.ok) {
        setError(json.error || "Error al cargar.");
        return;
      }
      setData(json as Stats);
      setAuthed(true);
      sessionStorage.setItem(PASS_KEY, password);
    } catch {
      setError("No se pudo conectar.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const saved = sessionStorage.getItem(PASS_KEY);
    if (saved) {
      setPass(saved);
      load(saved);
    }
  }, [load]);

  if (!authed) {
    return (
      <main className="bg-aura flex min-h-screen items-center justify-center px-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load(pass);
          }}
          className="card w-full max-w-sm p-7"
        >
          <h1 className="font-display text-2xl">Panel de estadísticas</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Acceso privado. Introduce la contraseña.
          </p>
          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            placeholder="Contraseña"
            className="mt-5 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg-2)] px-4 py-3 outline-none focus:border-[var(--gold)]"
            autoFocus
          />
          {error && <p className="mt-2 text-sm text-[var(--rose)]">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary mt-4 w-full">
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center text-[var(--text-muted)]">
        Cargando…
      </main>
    );
  }

  const { totals, funnel, perProduct, sources, devices, series } = data;
  const maxSource = Math.max(1, ...sources.map((s) => s.count));

  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-tight">Estadísticas</h1>
          <p className="text-sm text-[var(--text-faint)]">
            Actualizado: {new Date(data.generatedAt).toLocaleString("es-ES")}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => load(pass)} className="btn-ghost !py-2 !px-4 text-sm">
            Refrescar
          </button>
          <button
            onClick={() => {
              sessionStorage.removeItem(PASS_KEY);
              setAuthed(false);
              setData(null);
            }}
            className="btn-ghost !py-2 !px-4 text-sm"
          >
            Salir
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Kpi label="Visitas" value={totals.views} sub={`${totals.uniqueVisitors} únicos`} />
        <Kpi label="Clics en 'Lo quiero'" value={totals.clicks} accent="var(--azure)" />
        <Kpi label="Emails captados" value={totals.leads} accent="var(--gold)" />
        <Kpi
          label="Conversión total"
          value={`${funnel.viewToLead}%`}
          sub="visita → email"
          accent="var(--emerald)"
        />
      </div>

      {/* Embudo */}
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
            Visita → Clic
          </p>
          <p className="mt-2 font-display text-2xl">{funnel.viewToClick}%</p>
          <div className="mt-3 h-1.5 w-full rounded-full bg-[var(--bg-2)]">
            <div
              className="h-full rounded-full bg-[var(--azure)]"
              style={{ width: `${Math.min(100, funnel.viewToClick)}%` }}
            />
          </div>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
            Clic → Email
          </p>
          <p className="mt-2 font-display text-2xl">{funnel.clickToLead}%</p>
          <div className="mt-3 h-1.5 w-full rounded-full bg-[var(--bg-2)]">
            <div
              className="h-full rounded-full bg-[var(--gold)]"
              style={{ width: `${Math.min(100, funnel.clickToLead)}%` }}
            />
          </div>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
            Emails hoy · 7 días
          </p>
          <p className="mt-2 font-display text-2xl">
            {totals.leadsToday} <span className="text-[var(--text-faint)]">·</span>{" "}
            {totals.leads7d}
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">nuevos suscriptores</p>
        </div>
      </div>

      {/* Serie temporal */}
      <div className="card mt-4 p-5">
        <h2 className="mb-4 font-display text-lg">Últimos 30 días</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={series} margin={{ left: -18, right: 8, top: 4 }}>
            <CartesianGrid stroke="#1e2536" vertical={false} />
            <XAxis dataKey="day" stroke="#5f6982" fontSize={11} tickLine={false} minTickGap={24} />
            <YAxis stroke="#5f6982" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="views" name="Visitas" stroke="#5b9cff" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="clicks" name="Clics" stroke="#f5b841" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="leads" name="Emails" stroke="#34d399" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Por producto */}
        <div className="card p-5">
          <h2 className="mb-4 font-display text-lg">Rendimiento por producto</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={perProduct} margin={{ left: -18, right: 8 }}>
              <CartesianGrid stroke="#1e2536" vertical={false} />
              <XAxis dataKey="name" stroke="#5f6982" fontSize={10} tickLine={false} interval={0} height={50} angle={-12} textAnchor="end" />
              <YAxis stroke="#5f6982" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#141a2860" }} />
              <Bar dataKey="clicks" name="Clics" radius={[4, 4, 0, 0]} fill="#5b9cff" />
              <Bar dataKey="leads" name="Emails" radius={[4, 4, 0, 0]}>
                {perProduct.map((p) => (
                  <Cell key={p.id} fill={p.accent} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-3 flex flex-col gap-1.5 text-sm">
            {perProduct.map((p) => (
              <div key={p.id} className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: p.accent }} />
                  {p.name}
                </span>
                <span className="text-[var(--text-muted)]">
                  {p.leads} emails · {p.cr}% conv.
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Fuentes + dispositivos */}
        <div className="flex flex-col gap-4">
          <div className="card p-5">
            <h2 className="mb-4 font-display text-lg">Fuentes de tráfico</h2>
            {sources.length === 0 && (
              <p className="text-sm text-[var(--text-muted)]">Aún sin datos.</p>
            )}
            <div className="flex flex-col gap-2.5">
              {sources.map((s) => (
                <div key={s.source}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize">{s.source}</span>
                    <span className="text-[var(--text-muted)]">{s.count}</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-[var(--bg-2)]">
                    <div
                      className="h-full rounded-full bg-[var(--azure)]"
                      style={{ width: `${(s.count / maxSource) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-5">
            <h2 className="mb-3 font-display text-lg">Dispositivos</h2>
            <div className="flex flex-wrap gap-2">
              {devices.map((d) => (
                <span
                  key={d.device}
                  className="rounded-full border border-[var(--border-strong)] px-3 py-1.5 text-sm capitalize text-[var(--text-muted)]"
                >
                  {d.device}: <strong className="text-[var(--text)]">{d.count}</strong>
                </span>
              ))}
              {devices.length === 0 && (
                <p className="text-sm text-[var(--text-muted)]">Aún sin datos.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

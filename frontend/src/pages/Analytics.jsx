import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import {
  TrendingUp,
  Bike,
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Truck,
  Package,
} from "lucide-react";

const fmt = (n, cur = "MAD") =>
  `${new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2 }).format(Number(n || 0))} ${
    cur === "EUR" ? "€" : "DH"
  }`;

const Money = ({ value }) => (
  <span className="whitespace-nowrap">
    {value.MAD > 0 && <span className="font-semibold text-slate-800">{fmt(value.MAD, "MAD")}</span>}
    {value.MAD > 0 && value.EUR > 0 && <span className="text-slate-300"> · </span>}
    {value.EUR > 0 && <span className="font-semibold text-slate-800">{fmt(value.EUR, "EUR")}</span>}
    {value.MAD === 0 && value.EUR === 0 && <span className="text-slate-300">—</span>}
  </span>
);

const monthStart = () => new Date().toISOString().slice(0, 8) + "01";
const today = () => new Date().toISOString().slice(0, 10);

export default function Analytics() {
  const [start, setStart] = useState(monthStart());
  const [end, setEnd] = useState(today());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/analytics/profitability", { params: { start, end } });
      setData(data);
    } catch (e) {
      console.error("analytics", e);
    } finally {
      setLoading(false);
    }
  }, [start, end]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const t = data?.totals;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-900">
            <TrendingUp className="h-5 w-5 text-nubo-600" /> Rentabilidad & Auditoría COD
          </h1>
          <p className="text-sm text-slate-500">Ingresos por repartidor y ciudad · control de efectivo recaudado</p>
        </div>
        <div className="flex items-end gap-2">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Desde</label>
            <input
              data-testid="analytics-start"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-nubo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Hasta</label>
            <input
              data-testid="analytics-end"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-nubo-500"
            />
          </div>
        </div>
      </div>

      {/* Totals */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { icon: Package, label: "Pedidos", value: t?.orders ?? 0, cls: "bg-slate-100 text-slate-600" },
          { icon: Truck, label: "Entregados", value: t?.delivered ?? 0, cls: "bg-emerald-100 text-emerald-600" },
          { icon: TrendingUp, label: "Ingresos", money: t?.revenue, cls: "bg-nubo-100 text-nubo-600" },
          { icon: ShieldCheck, label: "COD efectivo", money: t?.cod_cash, cls: "bg-amber-100 text-amber-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className={`mb-2 inline-flex h-9 w-9 items-center justify-center rounded-lg ${s.cls}`}>
              <s.icon className="h-4 w-4" />
            </div>
            <p className="text-xs text-slate-500">{s.label}</p>
            {s.money ? (
              <p className="text-lg font-bold text-slate-900">
                <Money value={s.money || { MAD: 0, EUR: 0 }} />
              </p>
            ) : (
              <p className="text-xl font-bold text-slate-900">{s.value}</p>
            )}
          </div>
        ))}
      </div>

      {/* Cash audit */}
      <section className="mt-6">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <ShieldCheck className="h-4 w-4 text-nubo-500" /> Auditoría de efectivo COD (recaudado vs registrado)
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(data?.cash_audit || []).map((a) => {
            const cfg = {
              ok: { box: "border-emerald-200 bg-emerald-50", text: "text-emerald-700", icon: ShieldCheck, label: "Sin fugas" },
              fuga: { box: "border-rose-200 bg-rose-50", text: "text-rose-700", icon: AlertTriangle, label: "Posible fuga de caja" },
              exceso: { box: "border-amber-200 bg-amber-50", text: "text-amber-700", icon: AlertTriangle, label: "Exceso registrado" },
            }[a.estado];
            const Icon = cfg.icon;
            return (
              <div
                key={a.currency}
                data-testid={`cash-audit-${a.currency}`}
                className={`rounded-2xl border p-5 ${cfg.box}`}
              >
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                    <span className="flex h-7 w-7 items-center justify-center rounded-md bg-white text-xs font-bold">
                      {a.currency === "EUR" ? "€" : "DH"}
                    </span>
                    {a.currency}
                  </span>
                  <span className={`flex items-center gap-1.5 text-xs font-semibold ${cfg.text}`}>
                    <Icon className="h-4 w-4" /> {cfg.label}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <p className="text-xs text-slate-500">Recaudado (COD)</p>
                    <p className="font-semibold text-slate-800">{fmt(a.cod_expected, a.currency)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Registrado (caja)</p>
                    <p className="font-semibold text-slate-800">{fmt(a.cod_registered, a.currency)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Diferencia</p>
                    <p className={`font-bold ${a.estado === "ok" ? "text-emerald-600" : cfg.text}`}>
                      {a.diferencia > 0 ? "+" : ""}
                      {fmt(a.diferencia, a.currency)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* By rider */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
            <Bike className="h-4 w-4 text-nubo-500" />
            <h2 className="text-sm font-semibold text-slate-800">Rentabilidad por repartidor</h2>
          </div>
          <div className="overflow-x-auto">
            <table data-testid="rider-table" className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="px-4 py-3">Repartidor</th>
                  <th className="px-4 py-3 text-center">Entreg.</th>
                  <th className="px-4 py-3 text-center">Tasa</th>
                  <th className="px-4 py-3 text-right">COD efectivo</th>
                </tr>
              </thead>
              <tbody>
                {(data?.by_rider || []).length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-400">Sin datos en el rango.</td></tr>
                )}
                {(data?.by_rider || []).map((r) => (
                  <tr key={r.rider_id} className="border-b border-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{r.rider_name}</div>
                      <div className="text-xs text-slate-400">
                        {r.active} en curso · {r.avg_distance_km ? `${r.avg_distance_km} km prom.` : "—"}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center font-semibold text-slate-700">{r.delivered}/{r.orders}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${r.delivery_rate >= 70 ? "bg-emerald-100 text-emerald-700" : r.delivery_rate >= 40 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"}`}>
                        {r.delivery_rate}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right"><Money value={r.cod_cash} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* By city */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
            <MapPin className="h-4 w-4 text-rose-500" />
            <h2 className="text-sm font-semibold text-slate-800">Rentabilidad por ciudad</h2>
          </div>
          <div className="overflow-x-auto">
            <table data-testid="city-table" className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="px-4 py-3">Ciudad</th>
                  <th className="px-4 py-3 text-center">Entreg.</th>
                  <th className="px-4 py-3 text-right">Ingresos</th>
                  <th className="px-4 py-3 text-right">COD efectivo</th>
                </tr>
              </thead>
              <tbody>
                {(data?.by_city || []).length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-400">Sin datos en el rango.</td></tr>
                )}
                {(data?.by_city || []).map((c) => (
                  <tr key={c.city} className="border-b border-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">{c.city}</td>
                    <td className="px-4 py-3 text-center font-semibold text-slate-700">{c.delivered}/{c.orders}</td>
                    <td className="px-4 py-3 text-right"><Money value={c.revenue} /></td>
                    <td className="px-4 py-3 text-right"><Money value={c.cod_cash} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      {loading && <p className="mt-4 text-center text-xs text-slate-400">Actualizando…</p>}
    </div>
  );
}

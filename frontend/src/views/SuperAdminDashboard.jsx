/**
 * views/SuperAdminDashboard.jsx — Nubo Express
 *
 * Vista principal del Super Admin. Diseñada para ser scannable en segundos:
 *   - Fila de métricas clave (pedidos, couriers, ingresos, caja)
 *   - Panel de alertas activas con severidad
 *   - Tabla de actividad reciente (últimas transacciones)
 *   - Mini-resumen de nóminas pendientes
 *   - Acceso rápido a acciones frecuentes
 *
 * Conectado a useAdminData() para datos reales del backend.
 * Polling automático cada 30 s para métricas y alertas.
 *
 * Props:
 *   onNavigate {Function} — Callback(path) para navegar entre vistas
 */

import { useEffect, useState, useCallback } from "react";
import { useAdminData } from "../hooks/useAdminData";

// ─────────────────────────────────────────────────────────────────
//  ICONOS SVG INLINE
// ─────────────────────────────────────────────────────────────────

const Icon = {
  Orders: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <rect x="2" y="3" width="16" height="14" rx="2" />
      <path d="M6 7h8M6 10h8M6 13h4" />
    </svg>
  ),
  Couriers: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <circle cx="5.5" cy="15.5" r="1.8" /><circle cx="14.5" cy="15.5" r="1.8" />
      <path d="M1 6h8l2.5 6H3.5" /><path d="M12.7 8H17l2 4.5H14" />
    </svg>
  ),
  Revenue: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <path d="M10 2v16M6 5h5.5a2.5 2.5 0 010 5H6m0 0h5a3 3 0 010 6H6" />
    </svg>
  ),
  Cash: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <rect x="1" y="5" width="18" height="10" rx="2" />
      <circle cx="10" cy="10" r="2.5" />
      <path d="M5 10h.01M15 10h.01" />
    </svg>
  ),
  Alert: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M10 2L2 17h16L10 2z" /><path d="M10 8v4M10 14.5h.01" />
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" />
    </svg>
  ),
  Refresh: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M4 4a8 8 0 1 1 0 12" /><path d="M4 8V4H1" />
    </svg>
  ),
  Payroll: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <rect x="2" y="4" width="16" height="13" rx="2" /><path d="M2 8h16M6 12h3M6 15h2" />
      <circle cx="13" cy="13" r="1.5" />
    </svg>
  ),
  Map: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <polygon points="1,4 7,1 13,4 19,1 19,16 13,19 7,16 1,19" />
      <line x1="7" y1="1" x2="7" y2="16" /><line x1="13" y1="4" x2="13" y2="19" />
    </svg>
  ),
  Export: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M4 14v3h12v-3M10 3v9M6 8l4 4 4-4" />
    </svg>
  ),
  Stripe: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <rect x="2" y="4" width="16" height="12" rx="2" />
      <path d="M2 8h16M6 12h4" />
    </svg>
  ),
  TrendUp: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5" aria-hidden="true">
      <polyline points="1,11 5,7 9,9 15,3" /><polyline points="11,3 15,3 15,7" />
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────────
//  DATOS MOCK — se reemplazan automáticamente con datos reales
// ─────────────────────────────────────────────────────────────────

const MOCK_METRICS = {
  active_orders:     24,
  active_couriers:    9,
  daily_revenue_mad: 8_430,
  daily_revenue_eur:   775.6,
  pending_payouts:   3_200,
  cash_balance_mad:  12_150,
  cash_balance_eur:    940,
  alerts: [
    "3 couriers sin actualizar ubicación en más de 30 min.",
    "2 nóminas pendientes de pago con más de 7 días.",
    "1 pedido en tránsito sin actualización en más de 2h.",
  ],
};

const MOCK_TRANSACTIONS = [
  { _id: "1", type: "income",  amount: 350, currency: "MAD", description: "Pedido #4821", created_at: "2025-06-17T09:42:00Z", payment_method: "stripe" },
  { _id: "2", type: "payout",  amount: 120, currency: "MAD", description: "Nómina Ahmed K.", created_at: "2025-06-17T09:30:00Z", payment_method: "cash_mad" },
  { _id: "3", type: "income",  amount: 280, currency: "MAD", description: "Pedido #4820", created_at: "2025-06-17T09:15:00Z", payment_method: "stripe" },
  { _id: "4", type: "refund",  amount: 90,  currency: "MAD", description: "Devolución #4815", created_at: "2025-06-17T08:55:00Z", payment_method: "stripe" },
  { _id: "5", type: "cash_in", amount: 500, currency: "MAD", description: "Ingreso de caja",  created_at: "2025-06-17T08:30:00Z", payment_method: "cash_mad" },
];

const MOCK_PAYROLL = {
  pending: { count: 6, total_mad: 3_200, total_eur: 294.4 },
  paid:    { count: 12, total_mad: 7_800, total_eur: 717.6 },
};

// ─────────────────────────────────────────────────────────────────
//  UTILIDADES
// ─────────────────────────────────────────────────────────────────

function fmt(n, decimals = 0) {
  return new Intl.NumberFormat("es-MA", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

function timeAgo(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60)   return "hace un momento";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  return new Date(isoStr).toLocaleDateString("es-ES", { day: "2-digit", month: "short" });
}

// ─────────────────────────────────────────────────────────────────
//  SUBCOMPONENTES
// ─────────────────────────────────────────────────────────────────

// ── Tarjeta de métrica ──────────────────────────────────────────
function MetricCard({ label, value, sub, icon: IconComp, accentClass, trend }) {
  return (
    <div className={[
      "relative overflow-hidden rounded-xl p-5",
      "bg-slate-800/50 border border-slate-700/50",
      "flex flex-col gap-3",
    ].join(" ")}>
      {/* Icono + etiqueta */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          {label}
        </span>
        <span className={`p-1.5 rounded-lg ${accentClass}`}>
          <IconComp />
        </span>
      </div>

      {/* Valor principal */}
      <div>
        <p className="text-3xl font-bold text-white leading-none tracking-tight">
          {value}
        </p>
        {sub && (
          <p className="text-xs text-slate-500 mt-1.5 leading-snug">{sub}</p>
        )}
      </div>

      {/* Indicador de tendencia */}
      {trend && (
        <div className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
          <Icon.TrendUp />
          <span>{trend}</span>
        </div>
      )}

      {/* Borde izquierdo acento */}
      <span className={`absolute left-0 top-4 bottom-4 w-0.5 rounded-r-full ${accentClass.replace("bg-", "bg-").replace("/10", "")}`}
        style={{ background: "currentColor" }}
        aria-hidden="true"
      />
    </div>
  );
}

// ── Badge de tipo de transacción ────────────────────────────────
const TX_TYPE_CONFIG = {
  income:     { label: "Ingreso",   cls: "bg-emerald-500/15 text-emerald-400" },
  payout:     { label: "Pago",      cls: "bg-amber-500/15 text-amber-400" },
  refund:     { label: "Devolución",cls: "bg-red-500/15 text-red-400" },
  cash_in:    { label: "Caja ↑",    cls: "bg-sky-500/15 text-sky-400" },
  cash_out:   { label: "Caja ↓",    cls: "bg-orange-500/15 text-orange-400" },
  adjustment: { label: "Ajuste",    cls: "bg-slate-500/15 text-slate-400" },
};

function TxTypeBadge({ type }) {
  const cfg = TX_TYPE_CONFIG[type] ?? { label: type, cls: "bg-slate-500/15 text-slate-400" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ── Fila de transacción ─────────────────────────────────────────
function TxRow({ tx }) {
  const isIncome = tx.type === "income" || tx.type === "cash_in";
  return (
    <tr className="border-b border-slate-700/40 last:border-0 hover:bg-slate-800/30 transition-colors">
      <td className="py-3 pl-4 pr-3">
        <TxTypeBadge type={tx.type} />
      </td>
      <td className="py-3 px-3 text-sm text-slate-200 max-w-[180px] truncate">
        {tx.description}
      </td>
      <td className={`py-3 px-3 text-sm font-semibold tabular-nums text-right ${
        isIncome ? "text-emerald-400" : "text-slate-300"
      }`}>
        {isIncome ? "+" : "−"}{fmt(tx.amount)} {tx.currency}
      </td>
      <td className="py-3 pl-3 pr-4 text-xs text-slate-500 text-right whitespace-nowrap">
        {timeAgo(tx.created_at)}
      </td>
    </tr>
  );
}

// ── Alerta ──────────────────────────────────────────────────────
function AlertItem({ text, index }) {
  const severityClass = index === 0
    ? "border-l-red-500 bg-red-500/5"
    : index === 1
    ? "border-l-amber-500 bg-amber-500/5"
    : "border-l-sky-500 bg-sky-500/5";

  const iconColor = index === 0 ? "text-red-400" : index === 1 ? "text-amber-400" : "text-sky-400";

  return (
    <div className={`flex items-start gap-3 px-4 py-3 border-l-2 rounded-r-lg ${severityClass}`}>
      <span className={`flex-shrink-0 mt-0.5 ${iconColor}`}>
        <Icon.Alert />
      </span>
      <p className="text-sm text-slate-300 leading-snug">{text}</p>
    </div>
  );
}

// ── Botón de acción rápida ──────────────────────────────────────
function QuickAction({ label, icon: IconComp, onClick, variant = "default" }) {
  const base = "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400";
  const variants = {
    default: "bg-slate-700/60 text-slate-200 hover:bg-slate-700 border border-slate-600/50",
    primary: "bg-amber-500 text-slate-900 hover:bg-amber-400 font-semibold",
    danger:  "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20",
  };
  return (
    <button onClick={onClick} className={`${base} ${variants[variant]}`}>
      <IconComp />
      {label}
    </button>
  );
}

// ── Skeleton de carga ───────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="rounded-xl p-5 bg-slate-800/50 border border-slate-700/50 animate-pulse">
      <div className="h-3 w-24 bg-slate-700 rounded mb-4" />
      <div className="h-8 w-32 bg-slate-700 rounded mb-2" />
      <div className="h-3 w-20 bg-slate-700/60 rounded" />
    </div>
  );
}

// ── Timestamp del último refresco ───────────────────────────────
function LastRefreshed({ date, onRefresh, loading }) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span>
        Actualizado {date ? timeAgo(date.toISOString()) : "—"}
      </span>
      <button
        onClick={onRefresh}
        disabled={loading}
        aria-label="Refrescar datos"
        className="p-1 rounded hover:text-slate-300 hover:bg-slate-700/50 transition-colors disabled:opacity-40"
      >
        <span className={loading ? "animate-spin inline-block" : ""}>
          <Icon.Refresh />
        </span>
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  VISTA PRINCIPAL
// ─────────────────────────────────────────────────────────────────

export default function SuperAdminDashboard({ onNavigate = () => {} }) {
  const {
    dashboard,
    transactions,
    payrollSummary,
    fetchDashboard,
    fetchTransactions,
    fetchPayrollSummary,
  } = useAdminData();

  const [lastRefresh, setLastRefresh]   = useState(null);
  const [useMock,     setUseMock]       = useState(true);   // true hasta que llegue data real

  // ── Datos efectivos (real o mock) ─────────────────────────────
  const metrics    = useMock ? MOCK_METRICS    : (dashboard.data    ?? MOCK_METRICS);
  const txList     = useMock ? MOCK_TRANSACTIONS : (transactions.data?.data ?? MOCK_TRANSACTIONS);
  const payroll    = useMock ? MOCK_PAYROLL    : (payrollSummary.data ?? MOCK_PAYROLL);
  const alerts     = metrics.alerts ?? [];
  const isLoading  = dashboard.loading;

  // ── Carga inicial ─────────────────────────────────────────────
  const loadAll = useCallback(async () => {
    try {
      await Promise.all([
        fetchDashboard(),
        fetchTransactions({ per_page: 5 }),
        fetchPayrollSummary(),
      ]);
      setUseMock(false);
      setLastRefresh(new Date());
    } catch {
      // Mantiene datos mock si el backend no responde en dev
      setLastRefresh(new Date());
    }
  }, [fetchDashboard, fetchTransactions, fetchPayrollSummary]);

  useEffect(() => {
    loadAll();
    const id = setInterval(loadAll, 30_000); // Polling cada 30 s
    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─────────────────────────────────────────────────────────────
  //  RENDER
  // ─────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* ── Encabezado ──────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {new Date().toLocaleDateString("es-ES", {
                weekday: "long", day: "numeric", month: "long", year: "numeric",
              })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <LastRefreshed date={lastRefresh} onRefresh={loadAll} loading={isLoading} />
            {useMock && (
              <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 text-[11px] font-semibold border border-amber-500/20">
                Vista previa
              </span>
            )}
          </div>
        </div>

        {/* ── Tarjetas de métricas ─────────────────────────────── */}
        <section aria-label="Métricas principales">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {isLoading && !useMock ? (
              Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              <>
                <MetricCard
                  label="Pedidos activos"
                  value={fmt(metrics.active_orders)}
                  sub="En preparación, recogida o tránsito"
                  icon={Icon.Orders}
                  accentClass="bg-sky-500/10 text-sky-400"
                  trend="+3 desde ayer"
                />
                <MetricCard
                  label="Couriers en turno"
                  value={fmt(metrics.active_couriers)}
                  sub="Con GPS activo en los últimos 10 min"
                  icon={Icon.Couriers}
                  accentClass="bg-emerald-500/10 text-emerald-400"
                />
                <MetricCard
                  label="Ingresos del día"
                  value={`${fmt(metrics.daily_revenue_mad)} MAD`}
                  sub={`≈ ${fmt(metrics.daily_revenue_eur, 1)} EUR`}
                  icon={Icon.Revenue}
                  accentClass="bg-amber-500/10 text-amber-400"
                  trend="+12% vs ayer"
                />
                <MetricCard
                  label="Caja efectivo"
                  value={`${fmt(metrics.cash_balance_mad)} MAD`}
                  sub={`${fmt(metrics.cash_balance_eur, 0)} EUR disponibles`}
                  icon={Icon.Cash}
                  accentClass="bg-violet-500/10 text-violet-400"
                />
              </>
            )}
          </div>
        </section>

        {/* ── Grid principal: alertas + transacciones ──────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* ── Columna izquierda: alertas + nóminas ── */}
          <div className="space-y-6">

            {/* Alertas */}
            <section
              aria-label="Alertas activas"
              className="rounded-xl bg-slate-800/40 border border-slate-700/50 overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-700/50">
                <h2 className="text-sm font-semibold text-slate-200">
                  Alertas
                  {alerts.length > 0 && (
                    <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-[10px] font-bold text-white">
                      {alerts.length}
                    </span>
                  )}
                </h2>
                <button
                  onClick={() => onNavigate("/audit")}
                  className="text-xs text-slate-500 hover:text-amber-400 flex items-center gap-1 transition-colors"
                >
                  Ver log <Icon.ArrowRight />
                </button>
              </div>

              <div className="p-4 space-y-2.5">
                {alerts.length === 0 ? (
                  <p className="text-sm text-slate-500 py-4 text-center">
                    Sin alertas activas ✓
                  </p>
                ) : (
                  alerts.map((text, i) => (
                    <AlertItem key={i} text={text} index={i} />
                  ))
                )}
              </div>
            </section>

            {/* Resumen nóminas */}
            <section
              aria-label="Estado de nóminas"
              className="rounded-xl bg-slate-800/40 border border-slate-700/50 overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-700/50">
                <h2 className="text-sm font-semibold text-slate-200">Nóminas</h2>
                <button
                  onClick={() => onNavigate("/payroll")}
                  className="text-xs text-slate-500 hover:text-amber-400 flex items-center gap-1 transition-colors"
                >
                  Gestionar <Icon.ArrowRight />
                </button>
              </div>

              <div className="p-4 space-y-3">
                {/* Pendientes */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-amber-500/8 border border-amber-500/15">
                  <div>
                    <p className="text-xs text-amber-400 font-semibold uppercase tracking-wide">
                      Pendientes
                    </p>
                    <p className="text-lg font-bold text-white mt-0.5">
                      {fmt(payroll.pending.total_mad)} MAD
                    </p>
                    <p className="text-xs text-slate-500">
                      {payroll.pending.count} couriers · ≈ {fmt(payroll.pending.total_eur, 0)} EUR
                    </p>
                  </div>
                  <span className="text-amber-400 opacity-40">
                    <Icon.Payroll />
                  </span>
                </div>

                {/* Pagadas */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30 border border-slate-700/40">
                  <div>
                    <p className="text-xs text-emerald-400 font-semibold uppercase tracking-wide">
                      Pagadas
                    </p>
                    <p className="text-lg font-bold text-white mt-0.5">
                      {fmt(payroll.paid.total_mad)} MAD
                    </p>
                    <p className="text-xs text-slate-500">
                      {payroll.paid.count} couriers este mes
                    </p>
                  </div>
                  <span className="text-emerald-400 opacity-40">
                    <Icon.Payroll />
                  </span>
                </div>
              </div>
            </section>
          </div>

          {/* ── Columna derecha: transacciones recientes ── */}
          <section
            aria-label="Actividad reciente"
            className="lg:col-span-2 rounded-xl bg-slate-800/40 border border-slate-700/50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-700/50">
              <h2 className="text-sm font-semibold text-slate-200">
                Actividad reciente
              </h2>
              <button
                onClick={() => onNavigate("/accounting")}
                className="text-xs text-slate-500 hover:text-amber-400 flex items-center gap-1 transition-colors"
              >
                Ver todo <Icon.ArrowRight />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full" aria-label="Últimas transacciones">
                <thead>
                  <tr className="border-b border-slate-700/40">
                    <th className="py-2.5 pl-4 pr-3 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Tipo
                    </th>
                    <th className="py-2.5 px-3 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Concepto
                    </th>
                    <th className="py-2.5 px-3 text-right text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Importe
                    </th>
                    <th className="py-2.5 pl-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Hora
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {txList.map((tx) => (
                    <TxRow key={tx._id} tx={tx} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Balance del día como footer de la tabla */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/40 bg-slate-800/30">
              <span className="text-xs text-slate-500">
                Balance neto del día
              </span>
              <span className="text-sm font-bold text-emerald-400 tabular-nums">
                +{fmt(
                  metrics.daily_revenue_mad - (payroll.pending?.total_mad ?? 0) * 0.1
                )} MAD
              </span>
            </div>
          </section>
        </div>

        {/* ── Acciones rápidas ─────────────────────────────────── */}
        <section aria-label="Acciones rápidas">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-600 mb-3">
            Acciones rápidas
          </h2>
          <div className="flex flex-wrap gap-2">
            <QuickAction
              label="Mapa en vivo"
              icon={Icon.Map}
              onClick={() => onNavigate("/map")}
              variant="default"
            />
            <QuickAction
              label="Generar nóminas"
              icon={Icon.Payroll}
              onClick={() => onNavigate("/payroll")}
              variant="primary"
            />
            <QuickAction
              label="Exportar transacciones"
              icon={Icon.Export}
              onClick={() => onNavigate("/accounting")}
              variant="default"
            />
            <QuickAction
              label="Balance Stripe"
              icon={Icon.Stripe}
              onClick={() => onNavigate("/accounting")}
              variant="default"
            />
          </div>
        </section>

        {/* ── Nóminas pendientes — alerta crítica si hay ───────── */}
        {payroll.pending.count > 0 && (
          <div
            role="alert"
            className="flex items-center justify-between gap-4 px-5 py-4 rounded-xl border border-amber-500/25 bg-amber-500/5"
          >
            <div className="flex items-center gap-3 text-amber-300">
              <Icon.Alert />
              <p className="text-sm">
                <span className="font-semibold">{payroll.pending.count} couriers</span> tienen
                nóminas pendientes de pago por un total de{" "}
                <span className="font-semibold tabular-nums">
                  {fmt(payroll.pending.total_mad)} MAD
                </span>.
              </p>
            </div>
            <button
              onClick={() => onNavigate("/payroll")}
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 text-slate-900 text-xs font-bold hover:bg-amber-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
            >
              Pagar ahora <Icon.ArrowRight />
            </button>
          </div>
        )}

      </div>
    </div>
  );
}

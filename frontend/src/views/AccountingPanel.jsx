/**
 * views/AccountingPanel.jsx — Nubo Express (adaptado al stack: CRA + AuthContext + axios)
 *
 * Panel completo de Contabilidad. Diseño oscuro premium con acento esmeralda.
 * Sistema 100% INTERNO (sin Stripe externo):
 *   1. Caja MAD/EUR + resumen del periodo (ingresos/gastos/neto)
 *   2. Transacciones — tabla filtrable por tipo, moneda y método
 *   3. Nóminas de Abejas — estado de pago + CTA pagar (interno)
 *   4. Exportación CSV / JSON
 *
 * Conectado a /api/accounting/* mediante AuthContext (API, token).
 */

import { useEffect, useState, useCallback, useContext } from "react";
import axios from "axios";
import { AuthContext } from "@/App";
import { toast } from "sonner";

// ─────────────────────────────────────────────────────────────────
//  ICONOS SVG INLINE
// ─────────────────────────────────────────────────────────────────

const Icon = {
  Cash: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <rect x="1" y="5" width="18" height="10" rx="2" />
      <circle cx="10" cy="10" r="2.5" />
      <path d="M5 10h.01M15 10h.01" />
    </svg>
  ),
  Filter: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M3 5h14M6 10h8M9 15h2" />
    </svg>
  ),
  Download: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M4 14v3h12v-3M10 3v9M6 8l4 4 4-4" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5" aria-hidden="true">
      <polyline points="3,10 8,15 17,5" />
    </svg>
  ),
  Refresh: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M4 4a8 8 0 1 1 0 12" /><path d="M4 8V4H1" />
    </svg>
  ),
  CashIn: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M10 14V6M6 10l4-4 4 4" />
      <rect x="2" y="15" width="16" height="3" rx="1" />
    </svg>
  ),
  CashOut: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M10 6v8M14 10l-4 4-4-4" />
      <rect x="2" y="2" width="16" height="3" rx="1" />
    </svg>
  ),
  Payroll: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <rect x="2" y="4" width="16" height="13" rx="2" />
      <path d="M2 8h16M6 12h3M6 15h2" />
      <circle cx="13" cy="13" r="1.5" />
    </svg>
  ),
  Scale: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
      <path d="M10 3v14M5 17h10M3 7l3-3 3 3M3 7l-1.5 4a3 3 0 0 0 5 0L8 7M17 7l-3-3-3 3M17 7l-1.5 4a3 3 0 0 0 5 0L19 7" />
    </svg>
  ),
  ChevronDown: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5" aria-hidden="true">
      <polyline points="3,5 8,11 13,5" />
    </svg>
  ),
  Spinner: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"
      className="w-4 h-4 animate-spin" aria-hidden="true">
      <circle cx="10" cy="10" r="8" strokeOpacity="0.25" />
      <path d="M10 2a8 8 0 0 1 8 8" />
    </svg>
  ),
  Excel: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <rect x="2" y="2" width="16" height="16" rx="2" />
      <path d="M6 6l8 8M14 6l-8 8" />
    </svg>
  ),
  JSON: () => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
      <path d="M4 7c-1 0-2 .5-2 1.5v3c0 1 1 1.5 2 1.5M16 7c1 0 2 .5 2 1.5v3c0 1-1 1.5-2 1.5M8 6l-2 8M12 6l2 8M9 10h2" />
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────────
//  CONFIGURACIÓN DE TIPOS DE TRANSACCIÓN
// ─────────────────────────────────────────────────────────────────

const TX_CONFIG = {
  income:     { label: "Ingreso",    badgeCls: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20", sign: "+" },
  payout:     { label: "Pago",       badgeCls: "bg-amber-500/15   text-amber-400   ring-1 ring-amber-500/20",   sign: "−" },
  refund:     { label: "Devolución", badgeCls: "bg-red-500/15     text-red-400     ring-1 ring-red-500/20",     sign: "−" },
  cash_in:    { label: "Caja ↑",     badgeCls: "bg-sky-500/15     text-sky-400     ring-1 ring-sky-500/20",     sign: "+" },
  cash_out:   { label: "Caja ↓",     badgeCls: "bg-orange-500/15  text-orange-400  ring-1 ring-orange-500/20",  sign: "−" },
  adjustment: { label: "Ajuste",     badgeCls: "bg-slate-500/15   text-slate-400   ring-1 ring-slate-500/25",   sign: "±" },
};

const METHOD_LABELS = {
  stripe: "Stripe", cash_mad: "Efectivo MAD", cash_eur: "Efectivo EUR",
  bank: "Transferencia", bank_transfer: "Transferencia",
};

// ─────────────────────────────────────────────────────────────────
//  UTILIDADES
// ─────────────────────────────────────────────────────────────────

const fmt = (n, dec = 0) =>
  new Intl.NumberFormat("es-MA", { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(n ?? 0);

const timeAgo = (iso) => {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return "hace un momento";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  return new Date(iso).toLocaleDateString("es-ES", { day: "2-digit", month: "short" });
};

// ─────────────────────────────────────────────────────────────────
//  SUBCOMPONENTES REUTILIZABLES
// ─────────────────────────────────────────────────────────────────

function Card({ title, subtitle, icon: IconComp, accentColor = "emerald", action, children }) {
  const colors = {
    emerald: "bg-emerald-500/10 text-emerald-400",
    amber: "bg-amber-500/10 text-amber-400",
    sky: "bg-sky-500/10 text-sky-400",
    violet: "bg-violet-500/10 text-violet-400",
  };
  return (
    <section className="rounded-2xl bg-slate-800/40 border border-slate-700/50 overflow-hidden">
      <div className="flex items-center justify-between gap-4 px-5 py-4 border-b border-slate-700/50 backdrop-blur-sm bg-slate-800/30">
        <div className="flex items-center gap-3">
          <span className={`p-2 rounded-xl ${colors[accentColor]}`}><IconComp /></span>
          <div>
            <h2 className="text-sm font-semibold text-slate-100 leading-tight">{title}</h2>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function FilterSelect({ value, onChange, options, label, testid }) {
  return (
    <div className="relative">
      <label className="sr-only">{label}</label>
      <select
        data-testid={testid}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-slate-700/60 border border-slate-600/50 text-slate-200 text-xs font-medium rounded-lg pl-3 pr-7 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 cursor-pointer transition-colors hover:bg-slate-700"
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-500"><Icon.ChevronDown /></span>
    </div>
  );
}

function TxBadge({ type }) {
  const cfg = TX_CONFIG[type] ?? TX_CONFIG.adjustment;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold ${cfg.badgeCls}`}>
      {cfg.label}
    </span>
  );
}

function Skeleton({ rows = 4 }) {
  return (
    <div className="p-4 space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="h-4 bg-slate-700 rounded w-20 flex-shrink-0" />
          <div className="h-4 bg-slate-700/70 rounded flex-1" />
          <div className="h-4 bg-slate-700/50 rounded w-24 flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}

function ExportButton({ label, sublabel, icon: IconComp, onClick, loading, success, variant = "default", testid }) {
  const base = "group relative flex items-center gap-3 px-5 py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:opacity-60 disabled:cursor-not-allowed overflow-hidden";
  const variants = {
    default: "bg-slate-700/60 border border-slate-600/50 text-slate-200 hover:bg-slate-700 hover:border-slate-500",
    primary: "bg-emerald-600 border border-emerald-500/50 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-900/30",
    outline: "bg-transparent border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/70",
  };
  return (
    <button data-testid={testid} onClick={onClick} disabled={loading} className={`${base} ${variants[variant]}`} aria-busy={loading}>
      {success && <span className="absolute inset-0 bg-emerald-500/10 rounded-xl pointer-events-none" />}
      <span className={`flex-shrink-0 ${success ? "text-emerald-400" : ""}`}>
        {loading ? <Icon.Spinner /> : success ? <Icon.Check /> : <IconComp />}
      </span>
      <span className="text-left">
        <span className="block leading-tight">{success ? "¡Descargado!" : label}</span>
        {sublabel && <span className="block text-[11px] font-normal opacity-60 mt-0.5">{sublabel}</span>}
      </span>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────
//  SECCIÓN 1: CAJA + RESUMEN DEL PERIODO  (sin Stripe — sistema interno)
// ─────────────────────────────────────────────────────────────────

function CashRow({ cash, summary, onRefresh, loading }) {
  const mad = cash?.cash_mad ?? { balance: 0, last_movement: null };
  const eur = cash?.cash_eur ?? { balance: 0, last_movement: null };
  const inc = summary?.total_income ?? { MAD: 0, EUR: 0 };
  const exp = summary?.total_expenses ?? { MAD: 0, EUR: 0 };
  const net = summary?.net_balance ?? { MAD: 0, EUR: 0 };
  const eurInMad = eur.balance / 0.092;
  const totalMad = mad.balance + eurInMad;
  const madPct = totalMad > 0 ? (mad.balance / totalMad) * 100 : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {/* Caja efectivo */}
      <Card
        title="Caja de efectivo"
        subtitle={`Última actualización ${timeAgo(mad.last_movement)}`}
        icon={Icon.Cash}
        accentColor="emerald"
        action={
          <button data-testid="acct-refresh-cash" onClick={onRefresh} disabled={loading} aria-label="Refrescar balance de caja"
            className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-40">
            <span className={loading ? "animate-spin inline-block" : ""}><Icon.Refresh /></span>
          </button>
        }
      >
        <div className="p-5 grid grid-cols-2 gap-4">
          <div className="rounded-xl bg-slate-900/60 border border-slate-700/40 p-4" data-testid="acct-cash-mad">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">MAD</p>
            <p className="text-2xl font-bold text-white tracking-tight">
              {fmt(mad.balance)}<span className="text-sm font-normal text-slate-500 ml-1.5">MAD</span>
            </p>
            <div className="mt-3 flex gap-2">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-md"><Icon.CashIn /> Ingresos</span>
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded-md"><Icon.CashOut /> Salidas</span>
            </div>
          </div>
          <div className="rounded-xl bg-slate-900/60 border border-slate-700/40 p-4" data-testid="acct-cash-eur">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">EUR</p>
            <p className="text-2xl font-bold text-white tracking-tight">
              {fmt(eur.balance, 0)}<span className="text-sm font-normal text-slate-500 ml-1.5">EUR</span>
            </p>
            <p className="text-xs text-slate-500 mt-3 leading-snug">≈ {fmt(eurInMad, 0)} MAD al tipo actual</p>
          </div>
          <div className="col-span-2">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
              <span>Distribución de caja</span>
              <span>{fmt(totalMad, 0)} MAD total</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden flex">
              <div className="h-full bg-emerald-500 rounded-l-full transition-all duration-700" style={{ width: `${madPct}%` }} />
              <div className="h-full bg-sky-500 flex-1 rounded-r-full" />
            </div>
            <div className="flex gap-4 mt-1.5 text-[11px] text-slate-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />MAD</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-500 inline-block" />EUR</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Resumen del periodo */}
      <Card title="Resumen del periodo" subtitle="Ingresos · Gastos · Balance neto" icon={Icon.Scale} accentColor="sky">
        <div className="p-5 space-y-3" data-testid="acct-summary">
          <div className="rounded-xl bg-slate-900/60 border border-slate-700/40 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">Ingresos</p>
              <p className="text-xl font-bold text-emerald-400 tracking-tight">{fmt(inc.MAD)} <span className="text-sm font-normal text-slate-500">MAD</span></p>
            </div>
            <p className="text-sm text-emerald-400/80">{fmt(inc.EUR, 2)} EUR</p>
          </div>
          <div className="rounded-xl bg-slate-900/60 border border-slate-700/40 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">Gastos</p>
              <p className="text-xl font-bold text-red-400 tracking-tight">{fmt(exp.MAD)} <span className="text-sm font-normal text-slate-500">MAD</span></p>
            </div>
            <p className="text-sm text-red-400/80">{fmt(exp.EUR, 2)} EUR</p>
          </div>
          <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/20 p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400/80 mb-1">Balance neto</p>
              <p className="text-2xl font-bold text-white tracking-tight">{fmt(net.MAD)} <span className="text-sm font-normal text-slate-500">MAD</span></p>
            </div>
            <p className="text-sm font-semibold text-emerald-400">{fmt(net.EUR, 2)} EUR</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
//  SECCIÓN 2: TABLA DE TRANSACCIONES
// ─────────────────────────────────────────────────────────────────

const TX_TYPE_OPTIONS = [
  { value: "", label: "Todos los tipos" },
  { value: "income", label: "Ingresos" },
  { value: "payout", label: "Pagos" },
  { value: "refund", label: "Devoluciones" },
  { value: "cash_in", label: "Caja ↑" },
  { value: "cash_out", label: "Caja ↓" },
  { value: "adjustment", label: "Ajustes" },
];
const TX_METHOD_OPTIONS = [
  { value: "", label: "Todos los métodos" },
  { value: "stripe", label: "Stripe" },
  { value: "cash_mad", label: "Efectivo MAD" },
  { value: "cash_eur", label: "Efectivo EUR" },
  { value: "bank_transfer", label: "Transferencia" },
];
const TX_CURRENCY_OPTIONS = [
  { value: "", label: "MAD + EUR" },
  { value: "MAD", label: "Solo MAD" },
  { value: "EUR", label: "Solo EUR" },
];

function TransactionsTable({ transactions, loading }) {
  const [typeFilter, setTypeFilter] = useState("");
  const [methodFilter, setMethodFilter] = useState("");
  const [currFilter, setCurrFilter] = useState("");
  const [search, setSearch] = useState("");

  const list = (transactions ?? []).filter((tx) => {
    if (typeFilter && tx.type !== typeFilter) return false;
    if (methodFilter && tx.payment_method !== methodFilter) return false;
    if (currFilter && tx.currency !== currFilter) return false;
    if (search && !(tx.description || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const totalIn = list.filter((t) => ["income", "cash_in"].includes(t.type)).reduce((s, t) => s + t.amount, 0);
  const totalOut = list.filter((t) => ["payout", "refund", "cash_out"].includes(t.type)).reduce((s, t) => s + t.amount, 0);

  return (
    <Card
      title="Transacciones"
      subtitle={`${list.length} resultado${list.length !== 1 ? "s" : ""} filtrados`}
      icon={Icon.Filter}
      accentColor="sky"
      action={
        <div className="flex items-center gap-2 flex-wrap">
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar concepto…"
            aria-label="Buscar transacciones" data-testid="acct-search"
            className="bg-slate-700/60 border border-slate-600/50 text-slate-200 placeholder-slate-500 text-xs rounded-lg px-3 py-2 w-36 focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
          <FilterSelect testid="acct-filter-type" value={typeFilter} onChange={setTypeFilter} options={TX_TYPE_OPTIONS} label="Tipo" />
          <FilterSelect testid="acct-filter-method" value={methodFilter} onChange={setMethodFilter} options={TX_METHOD_OPTIONS} label="Método" />
          <FilterSelect testid="acct-filter-currency" value={currFilter} onChange={setCurrFilter} options={TX_CURRENCY_OPTIONS} label="Moneda" />
        </div>
      }
    >
      <div className="flex items-center gap-6 px-5 py-3 border-b border-slate-700/40 bg-slate-900/20">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-slate-400">Entradas</span>
          <span className="text-xs font-bold text-emerald-400 tabular-nums">+{fmt(totalIn)} MAD</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          <span className="text-xs text-slate-400">Salidas</span>
          <span className="text-xs font-bold text-red-400 tabular-nums">−{fmt(totalOut)} MAD</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-slate-500" />
          <span className="text-xs text-slate-400">Neto</span>
          <span className={`text-xs font-bold tabular-nums ${totalIn - totalOut >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {totalIn - totalOut >= 0 ? "+" : "−"}{fmt(Math.abs(totalIn - totalOut))} MAD
          </span>
        </div>
      </div>

      {loading ? <Skeleton rows={5} /> : (
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="Tabla de transacciones">
            <thead>
              <tr className="border-b border-slate-700/40">
                {["Tipo", "Concepto", "Importe", "Método", "Fecha"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-slate-500 whitespace-nowrap first:pl-5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {list.length === 0 ? (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-500">No hay transacciones con los filtros seleccionados.</td></tr>
              ) : (
                list.map((tx) => {
                  const cfg = TX_CONFIG[tx.type] ?? TX_CONFIG.adjustment;
                  const isPos = cfg.sign === "+";
                  return (
                    <tr key={tx._id} data-testid={`acct-txn-${tx._id}`} className="hover:bg-slate-800/30 transition-colors group">
                      <td className="pl-5 pr-3 py-3.5"><TxBadge type={tx.type} /></td>
                      <td className="px-3 py-3.5 text-sm text-slate-300 max-w-[220px]"><span className="truncate block">{tx.description}</span></td>
                      <td className={`px-3 py-3.5 text-sm font-semibold tabular-nums whitespace-nowrap ${isPos ? "text-emerald-400" : "text-slate-300"}`}>{cfg.sign}{fmt(tx.amount, tx.currency === "EUR" ? 2 : 0)} {tx.currency}</td>
                      <td className="px-3 py-3.5 text-xs text-slate-500 whitespace-nowrap">{METHOD_LABELS[tx.payment_method] ?? tx.payment_method}</td>
                      <td className="px-3 py-3.5 text-xs text-slate-500 whitespace-nowrap">{timeAgo(tx.created_at)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────
//  SECCIÓN 3: NÓMINAS
// ─────────────────────────────────────────────────────────────────

function PayrollTable({ payroll, onPay, payingId, loading }) {
  const [paidFilter, setPaidFilter] = useState("");
  const list = (payroll ?? []).filter((p) => {
    if (paidFilter === "paid") return p.is_paid;
    if (paidFilter === "pending") return !p.is_paid;
    return true;
  });
  const totalPending = list.filter((p) => !p.is_paid).reduce((s, p) => s + p.net_amount, 0);
  const totalPaid = list.filter((p) => p.is_paid).reduce((s, p) => s + p.net_amount, 0);

  return (
    <Card
      title="Nóminas de Abejas"
      subtitle="Comisiones por entregas del periodo"
      icon={Icon.Payroll}
      accentColor="amber"
      action={
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-4 mr-2">
            <div className="text-right"><p className="text-[10px] text-slate-500 uppercase tracking-wide">Pendiente</p><p className="text-xs font-bold text-amber-400">{fmt(totalPending)} MAD</p></div>
            <div className="text-right"><p className="text-[10px] text-slate-500 uppercase tracking-wide">Pagado</p><p className="text-xs font-bold text-emerald-400">{fmt(totalPaid)} MAD</p></div>
          </div>
          <FilterSelect testid="acct-payroll-filter" value={paidFilter} onChange={setPaidFilter}
            options={[{ value: "", label: "Todos" }, { value: "pending", label: "Pendientes" }, { value: "paid", label: "Pagados" }]} label="Estado de pago" />
        </div>
      }
    >
      {loading ? <Skeleton rows={4} /> : (
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="Tabla de nóminas">
            <thead>
              <tr className="border-b border-slate-700/40">
                {["Abeja", "Entregas", "Comisión", "Estado", ""].map((h) => (
                  <th key={h} scope="col" className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-slate-500 whitespace-nowrap first:pl-5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {list.length === 0 ? (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-500">No hay nóminas con los filtros seleccionados.</td></tr>
              ) : (
                list.map((p) => (
                  <tr key={p._id} data-testid={`acct-payroll-${p.courier_id}`} className={`hover:bg-slate-800/30 transition-colors ${p.is_paid ? "opacity-70" : ""}`}>
                    <td className="pl-5 pr-3 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300 flex-shrink-0">
                          {(p.courier_name || "?").split(" ").slice(0, 2).map((w) => w[0]).join("")}
                        </div>
                        <span className="text-sm font-medium text-slate-200 whitespace-nowrap">{p.courier_name}</span>
                      </div>
                    </td>
                    <td className="px-3 py-3.5 text-sm font-semibold text-slate-300 tabular-nums">{p.total_deliveries}</td>
                    <td className="px-3 py-3.5 text-sm font-bold text-white tabular-nums whitespace-nowrap">{fmt(p.net_amount)} <span className="text-xs font-normal text-slate-500">{p.currency}</span></td>
                    <td className="px-3 py-3.5">
                      {p.is_paid ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md ring-1 ring-emerald-500/20"><Icon.Check /> Pagado</span>
                      ) : (
                        <span className="inline-flex items-center text-[11px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md ring-1 ring-amber-500/20">Pendiente</span>
                      )}
                    </td>
                    <td className="pl-3 pr-5 py-3.5">
                      {!p.is_paid && (
                        <button data-testid={`acct-pay-${p.courier_id}`} onClick={() => onPay(p.courier_id)} disabled={payingId === p.courier_id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-[11px] font-bold hover:bg-emerald-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 whitespace-nowrap">
                          {payingId === p.courier_id ? <Icon.Spinner /> : <Icon.Check />} Pagar
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {totalPending > 0 && (
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-slate-700/40 bg-amber-500/5">
          <p className="text-xs text-amber-400 font-medium">Total pendiente de pago en este período</p>
          <p className="text-sm font-bold text-amber-400 tabular-nums">{fmt(totalPending)} MAD<span className="text-xs font-normal text-slate-500 ml-1.5">≈ {fmt(totalPending * 0.092, 0)} EUR</span></p>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────
//  SECCIÓN 4: EXPORTACIÓN
// ─────────────────────────────────────────────────────────────────

function ExportSection({ onExportTx, onExportPayroll, onExportReport, mutationState }) {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split("T")[0]);
  const [lastAction, setLastAction] = useState(null);
  const isLoading = mutationState?.loading;
  const run = (fn, action) => { setLastAction(action); fn(); };

  return (
    <Card title="Exportación de datos" subtitle="Descarga registros contables compatibles con tu gestor" icon={Icon.Download} accentColor="emerald">
      <div className="p-5 space-y-5">
        <div className="flex flex-wrap items-end gap-4 p-4 rounded-xl bg-slate-900/50 border border-slate-700/40">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Fecha inicio</label>
            <input type="date" data-testid="acct-export-from" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
              className="bg-slate-700/60 border border-slate-600/50 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Fecha fin</label>
            <input type="date" data-testid="acct-export-to" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
              className="bg-slate-700/60 border border-slate-600/50 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
          </div>
          <p className="text-xs text-slate-500 self-center">Deja vacío para exportar todo el histórico.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <ExportButton testid="acct-export-tx-csv" label="Transacciones CSV" sublabel="Compatible con Excel y Sheets" icon={Icon.Excel} variant="primary"
            loading={isLoading && lastAction === "tx-csv"} success={!isLoading && mutationState?.success && lastAction === "tx-csv"}
            onClick={() => run(() => onExportTx({ format: "csv", date_from: dateFrom, date_to: dateTo }), "tx-csv")} />
          <ExportButton testid="acct-export-tx-json" label="Transacciones JSON" sublabel="Para integraciones internas" icon={Icon.JSON} variant="outline"
            loading={isLoading && lastAction === "tx-json"} success={!isLoading && mutationState?.success && lastAction === "tx-json"}
            onClick={() => run(() => onExportTx({ format: "json", date_from: dateFrom, date_to: dateTo }), "tx-json")} />
          <ExportButton testid="acct-export-pr-csv" label="Nóminas CSV" sublabel="Resumen de comisiones" icon={Icon.Excel} variant="default"
            loading={isLoading && lastAction === "pr-csv"} success={!isLoading && mutationState?.success && lastAction === "pr-csv"}
            onClick={() => run(() => onExportPayroll({ format: "csv", date_from: dateFrom, date_to: dateTo }), "pr-csv")} />
          <ExportButton testid="acct-export-pr-json" label="Nóminas JSON" sublabel="Datos estructurados" icon={Icon.JSON} variant="default"
            loading={isLoading && lastAction === "pr-json"} success={!isLoading && mutationState?.success && lastAction === "pr-json"}
            onClick={() => run(() => onExportPayroll({ format: "json", date_from: dateFrom, date_to: dateTo }), "pr-json")} />
          <ExportButton testid="acct-export-report" label="Reporte completo JSON" sublabel="Balance + nóminas + caja" icon={Icon.Download} variant="outline"
            loading={isLoading && lastAction === "report"} success={!isLoading && mutationState?.success && lastAction === "report"}
            onClick={() => run(() => onExportReport({ date_from: dateFrom, date_to: dateTo }), "report")} />
        </div>

        {mutationState?.error && (
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            <svg className="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M10 2L2 17h16L10 2z" /><path d="M10 8v4M10 14.5h.01" /></svg>
            <span>{mutationState.error}</span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────
//  VISTA PRINCIPAL
// ─────────────────────────────────────────────────────────────────

export default function AccountingPanel() {
  const { API, token } = useContext(AuthContext);
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [cash, setCash] = useState(null);
  const [summary, setSummary] = useState(null);
  const [txns, setTxns] = useState(null);
  const [payroll, setPayroll] = useState(null);
  const [loading, setLoading] = useState(true);
  const [payingId, setPayingId] = useState(null);
  const [exportState, setExportState] = useState({ loading: false, success: false, error: null });

  const fetchCash = useCallback(async () => {
    const r = await axios.get(`${API}/accounting/cash/balance`, auth);
    setCash(r.data);
  }, [API, token]); // eslint-disable-line

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s, t, p] = await Promise.all([
        axios.get(`${API}/accounting/cash/balance`, auth),
        axios.get(`${API}/accounting/transactions/summary`, auth),
        axios.get(`${API}/accounting/transactions`, { params: { per_page: 100 }, ...auth }),
        axios.get(`${API}/accounting/payroll`, auth),
      ]);
      setCash(c.data);
      setSummary(s.data);
      setTxns((t.data.data || []).map((x) => ({ ...x, _id: x.id })));
      setPayroll((p.data.entries || []).map((e) => ({
        _id: e.courier_id, courier_id: e.courier_id, courier_name: e.courier_name,
        total_deliveries: e.total_deliveries, net_amount: e.net_amount_mad,
        net_amount_eur: e.net_amount_eur, currency: "MAD", is_paid: e.is_paid,
      })));
    } catch (e) {
      toast.error("No se pudieron cargar los datos de contabilidad");
    } finally {
      setLoading(false);
    }
  }, [API, token]); // eslint-disable-line

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handlePay = useCallback(async (courierId) => {
    setPayingId(courierId);
    try {
      await axios.post(`${API}/accounting/payroll/pay`, { courier_id: courierId }, auth);
      toast.success("Nómina marcada como pagada");
      await fetchAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "No se pudo pagar la nómina");
    } finally {
      setPayingId(null);
    }
  }, [API, token, fetchAll]); // eslint-disable-line

  const download = (content, filename, type) => {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const runExport = async (fn) => {
    setExportState({ loading: true, success: false, error: null });
    try {
      await fn();
      setExportState({ loading: false, success: true, error: null });
      setTimeout(() => setExportState((s) => ({ ...s, success: false })), 2500);
    } catch (e) {
      setExportState({ loading: false, success: false, error: e?.response?.data?.detail || "Error al exportar" });
    }
  };

  const exportTx = ({ format, date_from, date_to }) => runExport(async () => {
    if (format === "csv") {
      const r = await axios.get(`${API}/accounting/export/transactions`, { params: { date_from: date_from || undefined, date_to: date_to || undefined }, ...auth, responseType: "blob" });
      download(r.data, "transacciones.csv", "text/csv");
    } else {
      const r = await axios.get(`${API}/accounting/transactions`, { params: { per_page: 1000, date_from: date_from || undefined, date_to: date_to || undefined }, ...auth });
      download(JSON.stringify(r.data.data, null, 2), "transacciones.json", "application/json");
    }
  });

  const exportPayroll = ({ format, date_from, date_to }) => runExport(async () => {
    const r = await axios.get(`${API}/accounting/payroll`, { params: { start_date: date_from || undefined, end_date: date_to || undefined }, ...auth });
    if (format === "csv") {
      const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      const rows = [["courier", "entregas", "comision_eur", "comision_mad", "estado"]];
      (r.data.entries || []).forEach((e) => rows.push([e.courier_name, e.total_deliveries, e.net_amount_eur, e.net_amount_mad, e.is_paid ? "Pagado" : "Pendiente"]));
      download(rows.map((row) => row.map(esc).join(",")).join("\n"), "nominas.csv", "text/csv");
    } else {
      download(JSON.stringify(r.data, null, 2), "nominas.json", "application/json");
    }
  });

  const exportReport = ({ date_from, date_to }) => runExport(async () => {
    const [s, p, c] = await Promise.all([
      axios.get(`${API}/accounting/transactions/summary`, { params: { date_from: date_from || undefined, date_to: date_to || undefined }, ...auth }),
      axios.get(`${API}/accounting/payroll`, { params: { start_date: date_from || undefined, end_date: date_to || undefined }, ...auth }),
      axios.get(`${API}/accounting/cash/balance`, auth),
    ]);
    download(JSON.stringify({ generated_at: new Date().toISOString(), cash: c.data, summary: s.data, payroll: p.data }, null, 2), "reporte_contable.json", "application/json");
  });

  return (
    <div className="rounded-2xl bg-slate-950 text-white p-4 sm:p-6" data-testid="accounting-panel">
      <div className="space-y-7">
        <CashRow cash={cash} summary={summary} onRefresh={fetchCash} loading={loading} />
        <TransactionsTable transactions={txns} loading={loading} />
        <PayrollTable payroll={payroll} onPay={handlePay} payingId={payingId} loading={loading} />
        <ExportSection onExportTx={exportTx} onExportPayroll={exportPayroll} onExportReport={exportReport} mutationState={exportState} />
      </div>
    </div>
  );
}

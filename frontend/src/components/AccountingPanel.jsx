import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import {
  Wallet,
  ArrowDownCircle,
  ArrowUpCircle,
  Scale,
  FileText,
  FileSpreadsheet,
  RefreshCw,
  Plus,
  Trash2,
  Sparkles,
  Calendar,
  Coins,
  CheckCircle2,
  AlertTriangle,
  Eraser,
  History,
  Eye,
  TrendingUp,
  TrendingDown,
  Scale as ScaleIcon,
} from "lucide-react";
import { ACCOUNTING } from "@/constants/testIds";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DENOMINATIONS = {
  MAD: [200, 100, 50, 20, 10, 5, 2, 1, 0.5],
  EUR: [500, 200, 100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05],
};
const SYMBOLS = { MAD: "DH", EUR: "€" };
const CURRENCIES = ["MAD", "EUR"];

const todayStr = () => new Date().toISOString().slice(0, 10);

const fmt = (n, currency = "MAD") => {
  const num = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(n || 0));
  return `${num} ${SYMBOLS[currency] || currency}`;
};

const SummaryCard = ({ icon: Icon, label, value, accent, testId, delay, currency }) => (
  <motion.div
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.45, delay }}
    className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
  >
    <div className={`absolute right-0 top-0 h-24 w-24 -translate-y-8 translate-x-8 rounded-full opacity-10 ${accent.bg}`} />
    <div className={`mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl ${accent.bg} ${accent.text}`}>
      <Icon className="h-5 w-5" />
    </div>
    <p className="text-sm font-medium text-slate-500">{label}</p>
    <p data-testid={testId} className={`mt-1 text-2xl font-bold tracking-tight ${accent.value}`}>
      {fmt(value, currency)}
    </p>
  </motion.div>
);

export default function AccountingPanel() {
  const [date, setDate] = useState(todayStr());
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState("");
  const [mov, setMov] = useState({ concept: "", amount: "", type: "entrada", method: "efectivo" });
  const [counts, setCounts] = useState({});
  const [currency, setCurrency] = useState("MAD");
  const [history, setHistory] = useState([]);
  const [month, setMonth] = useState(todayStr().slice(0, 7));
  const [monthly, setMonthly] = useState([]);

  const fetchMonthly = useCallback(async (m) => {
    try {
      const res = await axios.get(`${API}/accounting/monthly-summary`, { params: { month: m } });
      setMonthly(res.data.summary || []);
    } catch (e) {
      console.error("Error al cargar resumen mensual", e);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/accounting/history`);
      setHistory(res.data.history || []);
    } catch (e) {
      console.error("Error al cargar historial", e);
    }
  }, []);

  const fetchSummary = useCallback(async (d) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/accounting/cash-closing`, { params: { date: d } });
      setSummary(res.data);
      setCurrency(res.data?.currency || "MAD");
      const saved = res.data?.reconciliation?.counts;
      setCounts(saved ? { ...saved } : {});
    } catch (e) {
      console.error("Error al cargar el arqueo", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary(date);
    fetchHistory();
  }, [date, fetchSummary, fetchHistory]);

  useEffect(() => {
    fetchMonthly(month);
  }, [month, fetchMonthly, history]);

  const download = async (format) => {
    try {
      const res = await axios.get(`${API}/accounting/cash-closing/export`, {
        params: { date, format },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `cierre-caja-${date}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Error al descargar", e);
    }
  };

  const saveOpening = async () => {
    if (opening === "") return;
    await axios.post(`${API}/accounting/opening`, {
      date,
      saldo_inicial: parseFloat(opening),
    });
    setOpening("");
    fetchSummary(date);
    fetchHistory();
  };

  const addMovement = async () => {
    if (!mov.concept || !mov.amount) return;
    await axios.post(`${API}/accounting/movements`, {
      date,
      type: mov.type,
      concept: mov.concept,
      amount: parseFloat(mov.amount),
      method: mov.method,
    });
    setMov({ concept: "", amount: "", type: "entrada", method: "efectivo" });
    fetchSummary(date);
    fetchHistory();
  };

  const deleteMovement = async (id) => {
    await axios.delete(`${API}/accounting/movements/${id}`);
    fetchSummary(date);
    fetchHistory();
  };

  const seed = async () => {
    await axios.post(`${API}/accounting/seed`, null, { params: { date } });
    fetchSummary(date);
    fetchHistory();
  };

  const denoms = DENOMINATIONS[currency];

  const changeCurrency = (cur) => {
    setCurrency(cur);
    setCounts({});
  };

  const setCountQty = (denom, val) => {
    const qty = val === "" ? "" : Math.max(0, parseInt(val, 10) || 0);
    setCounts((p) => ({ ...p, [String(denom)]: qty }));
  };

  const totalContado = denoms.reduce(
    (acc, d) => acc + d * (parseInt(counts[String(d)], 10) || 0),
    0
  );
  const efectivoEsperado = summary?.efectivo_esperado || 0;
  const diferencia = Math.round((totalContado - efectivoEsperado) * 100) / 100;
  const estado =
    Math.abs(diferencia) < 0.005 ? "cuadra" : diferencia < 0 ? "faltante" : "sobrante";

  const saveCount = async () => {
    const clean = {};
    denoms.forEach((d) => {
      clean[String(d)] = parseInt(counts[String(d)], 10) || 0;
    });
    await axios.post(`${API}/accounting/cash-count`, { date, currency, counts: clean });
    fetchSummary(date);
    fetchHistory();
  };

  const clearCount = () => setCounts({});

  const movimientos = summary?.movimientos || [];

  return (
    <div data-testid={ACCOUNTING.panel} className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-6 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
                <Wallet className="h-5 w-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">MoboExpress</h1>
            </div>
            <p className="mt-1 text-sm text-slate-500">Cierre de caja diario · Arqueo</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
              {CURRENCIES.map((cur) => (
                <button
                  key={cur}
                  data-testid={`accounting-currency-${cur}`}
                  onClick={() => changeCurrency(cur)}
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold transition-colors ${
                    currency === cur
                      ? "bg-indigo-600 text-white"
                      : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {cur} {SYMBOLS[cur]}
                </button>
              ))}
            </div>
            <div className="relative">
              <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                data-testid={ACCOUNTING.datePicker}
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
            <button
              data-testid={ACCOUNTING.refreshBtn}
              onClick={() => fetchSummary(date)}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {/* Summary cards */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            icon={Wallet}
            label="Saldo inicial"
            value={summary?.saldo_inicial}
            accent={{ bg: "bg-slate-100", text: "text-slate-600", value: "text-slate-900" }}
            testId={ACCOUNTING.saldoInicial}
            delay={0.02}
            currency={currency}
          />
          <SummaryCard
            icon={ArrowUpCircle}
            label="Entradas"
            value={summary?.total_entradas}
            accent={{ bg: "bg-emerald-100", text: "text-emerald-600", value: "text-emerald-600" }}
            testId={ACCOUNTING.totalEntradas}
            delay={0.08}
            currency={currency}
          />
          <SummaryCard
            icon={ArrowDownCircle}
            label="Salidas"
            value={summary?.total_salidas}
            accent={{ bg: "bg-rose-100", text: "text-rose-600", value: "text-rose-600" }}
            testId={ACCOUNTING.totalSalidas}
            delay={0.14}
            currency={currency}
          />
          <SummaryCard
            icon={Scale}
            label="Saldo final esperado"
            value={summary?.saldo_final_esperado}
            accent={{ bg: "bg-indigo-100", text: "text-indigo-600", value: "text-indigo-700" }}
            testId={ACCOUNTING.saldoFinal}
            delay={0.2}
            currency={currency}
          />
        </section>

        {/* Download actions */}
        <section className="mt-6 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mr-auto">
            <p className="text-sm font-semibold text-slate-800">Descargar arqueo del {date}</p>
            <p className="text-xs text-slate-500">Genera el reporte de cierre en un clic.</p>
          </div>
          <button
            data-testid={ACCOUNTING.downloadCsv}
            onClick={() => download("csv")}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Descargar CSV
          </button>
          <button
            data-testid={ACCOUNTING.downloadPdf}
            onClick={() => download("pdf")}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            <FileText className="h-4 w-4" />
            Descargar PDF
          </button>
        </section>

        {/* Cash count / reconciliation */}
        <section
          data-testid={ACCOUNTING.cashCountSection}
          className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white"
        >
          <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
            <Coins className="h-5 w-5 text-amber-500" />
            <h2 className="text-sm font-semibold text-slate-800">
              Conteo de efectivo físico (arqueo) · {currency}
            </h2>
            <span className="ml-auto text-xs text-slate-500">
              Efectivo esperado en caja:{" "}
              <span data-testid={ACCOUNTING.efectivoEsperado} className="font-semibold text-slate-800">
                {fmt(efectivoEsperado, currency)}
              </span>
            </span>
          </div>

          <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-3">
            {/* Denominations */}
            <div className="lg:col-span-2">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                Captura la cantidad de billetes y monedas ({currency})
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {denoms.map((d) => {
                  const qty = counts[String(d)] === "" || counts[String(d)] == null ? "" : counts[String(d)];
                  const subtotal = d * (parseInt(qty, 10) || 0);
                  const isBill = currency === "EUR" ? d >= 5 : d >= 20;
                  return (
                    <div key={d} className="rounded-xl border border-slate-200 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-700">{fmt(d, currency)}</span>
                        <span className="text-xs text-slate-400">{isBill ? "billete" : "moneda"}</span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs text-slate-400">×</span>
                        <input
                          data-testid={`${ACCOUNTING.cashCountQty}-${d}`}
                          type="number"
                          min="0"
                          value={qty}
                          onChange={(e) => setCountQty(d, e.target.value)}
                          placeholder="0"
                          className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                        />
                      </div>
                      <p className="mt-1.5 text-right text-xs font-medium text-slate-500">{fmt(subtotal, currency)}</p>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  data-testid={ACCOUNTING.cashCountSaveBtn}
                  onClick={saveCount}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Guardar conteo
                </button>
                <button
                  data-testid={ACCOUNTING.cashCountClearBtn}
                  onClick={clearCount}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <Eraser className="h-4 w-4" />
                  Limpiar
                </button>
              </div>
            </div>

            {/* Reconciliation result */}
            <div className="flex flex-col gap-4">
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Total contado</span>
                  <span data-testid={ACCOUNTING.cashCountTotal} className="font-semibold text-slate-900">
                    {fmt(totalContado, currency)}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="text-slate-500">Efectivo esperado</span>
                  <span className="font-semibold text-slate-900">{fmt(efectivoEsperado, currency)}</span>
                </div>
              </div>

              {(() => {
                const cfg = {
                  cuadra: {
                    box: "border-emerald-200 bg-emerald-50 text-emerald-700",
                    icon: CheckCircle2,
                    label: "La caja cuadra",
                  },
                  faltante: {
                    box: "border-rose-200 bg-rose-50 text-rose-700",
                    icon: AlertTriangle,
                    label: "Faltante de caja",
                  },
                  sobrante: {
                    box: "border-amber-200 bg-amber-50 text-amber-700",
                    icon: AlertTriangle,
                    label: "Sobrante de caja",
                  },
                }[estado];
                const Icon = cfg.icon;
                return (
                  <motion.div
                    key={estado}
                    initial={{ opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    data-testid={ACCOUNTING.reconciliationBanner}
                    className={`flex flex-col items-center justify-center rounded-xl border p-5 text-center ${cfg.box}`}
                  >
                    <Icon className="h-8 w-8" />
                    <p className="mt-2 text-sm font-semibold">{cfg.label}</p>
                    <p
                      data-testid={ACCOUNTING.reconciliationDiff}
                      className="mt-1 text-2xl font-bold tracking-tight"
                    >
                      {diferencia > 0 ? "+" : ""}
                      {fmt(diferencia, currency)}
                    </p>
                    <p className="mt-1 text-xs opacity-80">
                      {estado === "cuadra"
                        ? "El conteo coincide con lo esperado"
                        : "Diferencia entre lo contado y lo esperado"}
                    </p>
                  </motion.div>
                );
              })()}
            </div>
          </div>
        </section>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Movements table */}
          <section className="lg:col-span-2 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-800">Movimientos del día</h2>
              <button
                data-testid={ACCOUNTING.seedBtn}
                onClick={seed}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Cargar demo
              </button>
            </div>
            <div className="overflow-x-auto">
              <table data-testid={ACCOUNTING.movementsTable} className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-5 py-3 font-medium">Hora</th>
                    <th className="px-5 py-3 font-medium">Concepto</th>
                    <th className="px-5 py-3 font-medium">Método</th>
                    <th className="px-5 py-3 text-right font-medium">Monto</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {movimientos.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-slate-400">
                        Sin movimientos registrados para esta fecha.
                      </td>
                    </tr>
                  )}
                  {movimientos.map((m) => (
                    <tr key={m.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                      <td className="px-5 py-3 text-slate-500">
                        {m.created_at ? m.created_at.slice(11, 16) : "--:--"}
                      </td>
                      <td className="px-5 py-3 font-medium text-slate-800">{m.concept}</td>
                      <td className="px-5 py-3 capitalize text-slate-500">{m.method}</td>
                      <td
                        className={`px-5 py-3 text-right font-semibold ${
                          m.type === "entrada" ? "text-emerald-600" : "text-rose-600"
                        }`}
                      >
                        {m.type === "entrada" ? "+" : "−"}
                        {fmt(m.amount, currency)}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => deleteMovement(m.id)}
                          className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                          aria-label="Eliminar movimiento"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Side forms */}
          <section className="space-y-6">
            {/* Opening */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-slate-800">Saldo inicial</h3>
              <p className="mt-1 text-xs text-slate-500">Fondo de caja con el que abre el día.</p>
              <div className="mt-3 flex gap-2">
                <input
                  data-testid={ACCOUNTING.openingInput}
                  type="number"
                  value={opening}
                  onChange={(e) => setOpening(e.target.value)}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
                <button
                  data-testid={ACCOUNTING.openingSaveBtn}
                  onClick={saveOpening}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
                >
                  Guardar
                </button>
              </div>
            </div>

            {/* Add movement */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-slate-800">Registrar movimiento</h3>
              <div className="mt-3 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setMov((p) => ({ ...p, type: "entrada" }))}
                    data-testid={ACCOUNTING.movType}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      mov.type === "entrada"
                        ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                        : "border-slate-300 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    Entrada
                  </button>
                  <button
                    onClick={() => setMov((p) => ({ ...p, type: "salida" }))}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      mov.type === "salida"
                        ? "border-rose-500 bg-rose-50 text-rose-700"
                        : "border-slate-300 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    Salida
                  </button>
                </div>
                <input
                  data-testid={ACCOUNTING.movConcept}
                  value={mov.concept}
                  onChange={(e) => setMov((p) => ({ ...p, concept: e.target.value }))}
                  placeholder="Concepto (ej. Venta iPhone)"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    data-testid={ACCOUNTING.movAmount}
                    type="number"
                    value={mov.amount}
                    onChange={(e) => setMov((p) => ({ ...p, amount: e.target.value }))}
                    placeholder="Monto"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  />
                  <select
                    data-testid={ACCOUNTING.movMethod}
                    value={mov.method}
                    onChange={(e) => setMov((p) => ({ ...p, method: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="efectivo">Efectivo</option>
                    <option value="tarjeta">Tarjeta</option>
                    <option value="transferencia">Transferencia</option>
                  </select>
                </div>
                <button
                  data-testid={ACCOUNTING.movAddBtn}
                  onClick={addMovement}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
                >
                  <Plus className="h-4 w-4" />
                  Agregar movimiento
                </button>
              </div>
            </div>
          </section>
        </div>

        {/* Monthly summary */}
        <section data-testid={ACCOUNTING.monthlySection} className="mt-6">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <ScaleIcon className="h-5 w-5 text-indigo-500" />
              <h2 className="text-sm font-semibold text-slate-800">Resumen mensual por moneda</h2>
            </div>
            <input
              data-testid={ACCOUNTING.monthlyPicker}
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="ml-auto rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>

          {monthly.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
              Sin datos para {month}. Registra cierres para ver el resumen.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {monthly.map((m) => {
                const neta = m.diferencia_neta;
                const netaCfg =
                  Math.abs(neta) < 0.005
                    ? { c: "text-emerald-600", t: "Cuadrada" }
                    : neta < 0
                    ? { c: "text-rose-600", t: "Faltante neto" }
                    : { c: "text-amber-600", t: "Sobrante neto" };
                return (
                  <div
                    key={m.currency}
                    data-testid={`${ACCOUNTING.monthlyCard}-${m.currency}`}
                    className="overflow-hidden rounded-2xl border border-slate-200 bg-white"
                  >
                    <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
                      <div className="flex items-center gap-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white">
                          {SYMBOLS[m.currency]}
                        </span>
                        <span className="text-sm font-semibold text-slate-800">{m.currency}</span>
                      </div>
                      <span className="text-xs text-slate-400">
                        {m.cierres} cierre(s) · {m.cierres_cuadran} cuadran / {m.cierres_descuadran} descuadran
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-px bg-slate-100">
                      <div className="bg-white p-4">
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <TrendingUp className="h-3.5 w-3.5 text-emerald-500" /> Entradas del mes
                        </div>
                        <p className="mt-1 text-lg font-bold text-emerald-600">
                          {fmt(m.total_entradas, m.currency)}
                        </p>
                      </div>
                      <div className="bg-white p-4">
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <TrendingDown className="h-3.5 w-3.5 text-rose-500" /> Salidas del mes
                        </div>
                        <p className="mt-1 text-lg font-bold text-rose-600">
                          {fmt(m.total_salidas, m.currency)}
                        </p>
                      </div>
                      <div className="bg-white p-4">
                        <div className="text-xs text-slate-500">Acum. faltantes</div>
                        <p className="mt-1 text-lg font-bold text-rose-600">
                          −{fmt(m.total_faltante, m.currency)}
                        </p>
                      </div>
                      <div className="bg-white p-4">
                        <div className="text-xs text-slate-500">Acum. sobrantes</div>
                        <p className="mt-1 text-lg font-bold text-amber-600">
                          +{fmt(m.total_sobrante, m.currency)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3">
                      <span className="text-xs font-medium text-slate-500">
                        Descuadre neto del mes · {netaCfg.t}
                      </span>
                      <span className={`text-base font-bold ${netaCfg.c}`}>
                        {neta > 0 ? "+" : ""}
                        {fmt(neta, m.currency)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* History of past closings */}
        <section
          data-testid={ACCOUNTING.historySection}
          className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white"
        >
          <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
            <History className="h-5 w-5 text-indigo-500" />
            <h2 className="text-sm font-semibold text-slate-800">Historial de cierres anteriores</h2>
            <span className="ml-auto text-xs text-slate-500">{history.length} registro(s)</span>
          </div>
          <div className="overflow-x-auto">
            <table data-testid={ACCOUNTING.historyTable} className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-3 font-medium">Fecha</th>
                  <th className="px-5 py-3 font-medium">Moneda</th>
                  <th className="px-5 py-3 text-right font-medium">Saldo inicial</th>
                  <th className="px-5 py-3 text-right font-medium">Entradas</th>
                  <th className="px-5 py-3 text-right font-medium">Salidas</th>
                  <th className="px-5 py-3 text-right font-medium">Saldo final</th>
                  <th className="px-5 py-3 text-right font-medium">Contado</th>
                  <th className="px-5 py-3 text-right font-medium">Diferencia</th>
                  <th className="px-5 py-3 text-center font-medium">Estado</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 && (
                  <tr>
                    <td colSpan={10} className="px-5 py-10 text-center text-slate-400">
                      Aún no hay cierres registrados.
                    </td>
                  </tr>
                )}
                {history.map((h) => {
                  const badge = {
                    cuadra: "bg-emerald-100 text-emerald-700",
                    faltante: "bg-rose-100 text-rose-700",
                    sobrante: "bg-amber-100 text-amber-700",
                    pendiente: "bg-slate-100 text-slate-500",
                  }[h.estado];
                  return (
                    <tr
                      key={h.date}
                      data-testid={`${ACCOUNTING.historyRow}-${h.date}`}
                      className={`border-b border-slate-50 transition-colors hover:bg-slate-50/60 ${
                        h.date === date ? "bg-indigo-50/40" : ""
                      }`}
                    >
                      <td className="px-5 py-3 font-medium text-slate-800">{h.date}</td>
                      <td className="px-5 py-3 text-slate-500">{h.currency}</td>
                      <td className="px-5 py-3 text-right text-slate-600">{fmt(h.saldo_inicial, h.currency)}</td>
                      <td className="px-5 py-3 text-right text-emerald-600">{fmt(h.total_entradas, h.currency)}</td>
                      <td className="px-5 py-3 text-right text-rose-600">{fmt(h.total_salidas, h.currency)}</td>
                      <td className="px-5 py-3 text-right font-semibold text-slate-900">{fmt(h.saldo_final_esperado, h.currency)}</td>
                      <td className="px-5 py-3 text-right text-slate-600">
                        {h.total_contado == null ? "—" : fmt(h.total_contado, h.currency)}
                      </td>
                      <td
                        className={`px-5 py-3 text-right font-semibold ${
                          h.diferencia == null
                            ? "text-slate-400"
                            : Math.abs(h.diferencia) < 0.005
                            ? "text-emerald-600"
                            : h.diferencia < 0
                            ? "text-rose-600"
                            : "text-amber-600"
                        }`}
                      >
                        {h.diferencia == null
                          ? "—"
                          : `${h.diferencia > 0 ? "+" : ""}${fmt(h.diferencia, h.currency)}`}
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium capitalize ${badge}`}>
                          {h.estado}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right">
                        <button
                          data-testid={`${ACCOUNTING.historyViewBtn}-${h.date}`}
                          onClick={() => setDate(h.date)}
                          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-50"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Ver
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

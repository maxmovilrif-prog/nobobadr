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
} from "lucide-react";
import { ACCOUNTING } from "@/constants/testIds";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const todayStr = () => new Date().toISOString().slice(0, 10);

const fmt = (n) =>
  new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(Number(n || 0));

const SummaryCard = ({ icon: Icon, label, value, accent, testId, delay }) => (
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
      {fmt(value)}
    </p>
  </motion.div>
);

export default function AccountingPanel() {
  const [date, setDate] = useState(todayStr());
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState("");
  const [mov, setMov] = useState({ concept: "", amount: "", type: "entrada", method: "efectivo" });

  const fetchSummary = useCallback(async (d) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/accounting/cash-closing`, { params: { date: d } });
      setSummary(res.data);
    } catch (e) {
      console.error("Error al cargar el arqueo", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary(date);
  }, [date, fetchSummary]);

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
  };

  const deleteMovement = async (id) => {
    await axios.delete(`${API}/accounting/movements/${id}`);
    fetchSummary(date);
  };

  const seed = async () => {
    await axios.post(`${API}/accounting/seed`, null, { params: { date } });
    fetchSummary(date);
  };

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
          />
          <SummaryCard
            icon={ArrowUpCircle}
            label="Entradas"
            value={summary?.total_entradas}
            accent={{ bg: "bg-emerald-100", text: "text-emerald-600", value: "text-emerald-600" }}
            testId={ACCOUNTING.totalEntradas}
            delay={0.08}
          />
          <SummaryCard
            icon={ArrowDownCircle}
            label="Salidas"
            value={summary?.total_salidas}
            accent={{ bg: "bg-rose-100", text: "text-rose-600", value: "text-rose-600" }}
            testId={ACCOUNTING.totalSalidas}
            delay={0.14}
          />
          <SummaryCard
            icon={Scale}
            label="Saldo final esperado"
            value={summary?.saldo_final_esperado}
            accent={{ bg: "bg-indigo-100", text: "text-indigo-600", value: "text-indigo-700" }}
            testId={ACCOUNTING.saldoFinal}
            delay={0.2}
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
                        {fmt(m.amount)}
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
      </main>
    </div>
  );
}

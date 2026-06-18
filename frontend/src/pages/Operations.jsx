import { useEffect, useState, useCallback, useRef } from "react";
import api, { WS_URL, TOKEN_KEY } from "@/lib/api";
import LiveMap from "@/components/LiveMap";
import {
  Package,
  Bike,
  Plus,
  Truck,
  CircleDollarSign,
  Radio,
  CheckCircle2,
} from "lucide-react";

const STATUS_META = {
  pending: { label: "Pendiente", cls: "bg-slate-100 text-slate-600" },
  assigned: { label: "Asignado", cls: "bg-blue-100 text-blue-700" },
  picked_up: { label: "Recogido", cls: "bg-violet-100 text-violet-700" },
  in_transit: { label: "En camino", cls: "bg-amber-100 text-amber-700" },
  delivered: { label: "Entregado", cls: "bg-emerald-100 text-emerald-700" },
  cancelled: { label: "Cancelado", cls: "bg-rose-100 text-rose-700" },
};
const FLOW = ["pending", "assigned", "picked_up", "in_transit", "delivered"];

const fmt = (n, cur = "MAD") =>
  `${new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2 }).format(Number(n || 0))} ${
    cur === "EUR" ? "€" : "DH"
  }`;

const emptyForm = {
  customer_name: "",
  customer_phone: "",
  address: "",
  city: "Tanger",
  country: "Morocco",
  amount: "",
  payment_method: "cod_cash",
};

export default function Operations() {
  const [orders, setOrders] = useState([]);
  const [riders, setRiders] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [wsOnline, setWsOnline] = useState(false);
  const wsRef = useRef(null);

  const fetchAll = useCallback(async () => {
    try {
      const [o, r] = await Promise.all([api.get("/orders"), api.get("/riders")]);
      setOrders(o.data.orders || []);
      setRiders(r.data.riders || []);
    } catch (e) {
      console.error("fetch ops", e);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Realtime WebSocket
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    wsRef.current = ws;
    ws.onopen = () => setWsOnline(true);
    ws.onclose = () => setWsOnline(false);
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (
          ["order_created", "order_status", "order_assigned", "assignment_update",
           "rider_location", "cash_entry_created"].includes(msg.type)
        ) {
          fetchAll();
        }
      } catch (_) {}
    };
    return () => ws.close();
  }, [fetchAll]);

  const createOrder = async (e) => {
    e.preventDefault();
    if (!form.customer_name || !form.address || !form.amount) return;
    setCreating(true);
    try {
      await api.post("/orders", { ...form, amount: parseFloat(form.amount) });
      setForm(emptyForm);
      fetchAll();
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const assign = async (orderId, riderId) => {
    if (!riderId) return;
    await api.post("/assignments", { order_id: orderId, rider_id: riderId });
    fetchAll();
  };

  const setStatus = async (orderId, status) => {
    await api.patch(`/orders/${orderId}/status`, { status });
    fetchAll();
  };

  const stats = {
    pending: orders.filter((o) => o.status === "pending").length,
    active: orders.filter((o) => ["assigned", "picked_up", "in_transit"].includes(o.status)).length,
    delivered: orders.filter((o) => o.status === "delivered").length,
    cod: orders
      .filter((o) => o.status === "delivered" && o.payment_method === "cod_cash")
      .reduce((acc, o) => acc + o.amount, 0),
  };

  const nextStatus = (s) => {
    const i = FLOW.indexOf(s);
    return i >= 0 && i < FLOW.length - 1 ? FLOW[i + 1] : null;
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Operaciones de reparto</h1>
          <p className="text-sm text-slate-500">Pedidos, asignaciones y seguimiento en tiempo real</p>
        </div>
        <span
          data-testid="ws-status"
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
            wsOnline ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
          }`}
        >
          <Radio className="h-3.5 w-3.5" /> {wsOnline ? "Tiempo real activo" : "Desconectado"}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { icon: Package, label: "Pendientes", value: stats.pending, cls: "text-slate-600 bg-slate-100" },
          { icon: Truck, label: "En curso", value: stats.active, cls: "text-amber-600 bg-amber-100" },
          { icon: CheckCircle2, label: "Entregados", value: stats.delivered, cls: "text-emerald-600 bg-emerald-100" },
          { icon: CircleDollarSign, label: "COD efectivo", value: fmt(stats.cod), cls: "text-indigo-600 bg-indigo-100" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className={`mb-2 inline-flex h-9 w-9 items-center justify-center rounded-lg ${s.cls}`}>
              <s.icon className="h-4 w-4" />
            </div>
            <p className="text-xs text-slate-500">{s.label}</p>
            <p className="text-xl font-bold text-slate-900">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Orders */}
        <section className="lg:col-span-2 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-800">Pedidos</h2>
          </div>
          <div className="overflow-x-auto">
            <table data-testid="orders-table" className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="px-4 py-3">Pedido</th>
                  <th className="px-4 py-3">Cliente / Ciudad</th>
                  <th className="px-4 py-3 text-right">Monto</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3">Repartidor / Acción</th>
                </tr>
              </thead>
              <tbody>
                {orders.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                      Sin pedidos. Crea el primero a la derecha.
                    </td>
                  </tr>
                )}
                {orders.map((o) => {
                  const meta = STATUS_META[o.status] || STATUS_META.pending;
                  const next = nextStatus(o.status);
                  return (
                    <tr key={o.id} data-testid={`order-row-${o.code}`} className="border-b border-slate-50">
                      <td className="px-4 py-3">
                        <span className="font-semibold text-slate-800">{o.code}</span>
                        <div className="text-xs text-slate-400">
                          {o.payment_method === "cod_cash" ? "COD efectivo" : o.payment_method}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-700">{o.customer_name}</div>
                        <div className="text-xs text-slate-400">{o.city || "—"}</div>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-900">
                        {fmt(o.amount, o.currency)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${meta.cls}`}>
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {o.status === "pending" ? (
                          <select
                            data-testid={`assign-select-${o.code}`}
                            defaultValue=""
                            onChange={(e) => assign(o.id, e.target.value)}
                            className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs outline-none focus:border-indigo-500"
                          >
                            <option value="" disabled>
                              Asignar a…
                            </option>
                            {riders.map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.name}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">
                              {riders.find((r) => r.id === o.assigned_rider_id)?.name || "—"}
                            </span>
                            {next && (
                              <button
                                data-testid={`advance-${o.code}`}
                                onClick={() => setStatus(o.id, next)}
                                className="rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700"
                              >
                                → {STATUS_META[next].label}
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* New order */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Plus className="h-4 w-4" /> Nuevo pedido
          </h2>
          <form onSubmit={createOrder} className="space-y-3">
            <input
              data-testid="order-customer"
              placeholder="Nombre del cliente"
              value={form.customer_name}
              onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <input
              placeholder="Teléfono"
              value={form.customer_phone}
              onChange={(e) => setForm({ ...form, customer_phone: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <input
              data-testid="order-address"
              placeholder="Dirección de entrega"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                data-testid="order-city"
                placeholder="Ciudad"
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
              <select
                data-testid="order-country"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="Morocco">Marruecos (MAD)</option>
                <option value="Spain">España (EUR)</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                data-testid="order-amount"
                type="number"
                step="0.01"
                placeholder="Monto"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
              <select
                data-testid="order-payment"
                value={form.payment_method}
                onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="cod_cash">COD efectivo</option>
                <option value="card">Tarjeta</option>
                <option value="prepaid">Prepagado</option>
              </select>
            </div>
            <button
              data-testid="order-submit"
              type="submit"
              disabled={creating}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              <Plus className="h-4 w-4" /> Crear pedido
            </button>
            <p className="text-center text-xs text-slate-400">
              COD efectivo + entregado → entrada automática en el arqueo
            </p>
          </form>
        </section>
      </div>

      {/* Live tracking */}
      <section className="mt-6">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Bike className="h-4 w-4 text-indigo-500" /> Seguimiento en vivo de repartidores
        </h2>
        <LiveMap riders={riders} orders={orders} />
      </section>
    </div>
  );
}

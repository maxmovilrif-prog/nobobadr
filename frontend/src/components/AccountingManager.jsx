import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import {
  Wallet, TrendingUp, TrendingDown, Banknote, Download, Loader2, ArrowDownCircle,
  ArrowUpCircle, Receipt, Users, FileText, RefreshCw,
} from 'lucide-react';

const eur = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0);
const mad = (n) => `${new Intl.NumberFormat('ar-MA', { maximumFractionDigits: 2 }).format(n || 0)} MAD`;
const TXN_LABEL = {
  income: 'Ingreso', payout: 'Nómina', refund: 'Devolución',
  adjustment: 'Ajuste', cash_in: 'Entrada caja', cash_out: 'Salida caja',
};
const TXN_CLASS = {
  income: 'bg-emerald-100 text-emerald-700', cash_in: 'bg-emerald-100 text-emerald-700',
  payout: 'bg-rose-100 text-rose-700', refund: 'bg-amber-100 text-amber-700',
  cash_out: 'bg-rose-100 text-rose-700', adjustment: 'bg-gray-100 text-gray-600',
};

export const AccountingManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [summary, setSummary] = useState(null);
  const [cash, setCash] = useState(null);
  const [payroll, setPayroll] = useState({ entries: [], total_net_eur: 0, pending_net_eur: 0 });
  const [txns, setTxns] = useState({ data: [], total: 0 });
  const [cashForm, setCashForm] = useState({ amount: '', currency: 'EUR', description: '' });
  const [busy, setBusy] = useState(false);
  const [payingId, setPayingId] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [s, c, p, t] = await Promise.all([
        axios.get(`${API}/accounting/transactions/summary`, auth),
        axios.get(`${API}/accounting/cash/balance`, auth),
        axios.get(`${API}/accounting/payroll`, auth),
        axios.get(`${API}/accounting/transactions?per_page=12`, auth),
      ]);
      setSummary(s.data); setCash(c.data); setPayroll(p.data); setTxns(t.data);
    } catch (e) { /* noop */ }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const submitCash = async (direction) => {
    const amount = parseFloat(cashForm.amount);
    if (!amount || amount <= 0 || cashForm.description.trim().length < 2) {
      toast.error('Indica importe y un concepto (mín. 2 caracteres)'); return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/accounting/cash/${direction}`,
        { amount, currency: cashForm.currency, description: cashForm.description.trim() }, auth);
      toast.success(direction === 'in' ? 'Entrada de caja registrada' : 'Salida de caja registrada');
      setCashForm({ amount: '', currency: cashForm.currency, description: '' });
      fetchAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo registrar el movimiento');
    } finally { setBusy(false); }
  };

  const payPayroll = async (courierId) => {
    setPayingId(courierId);
    try {
      const res = await axios.post(`${API}/accounting/payroll/pay`, { courier_id: courierId }, auth);
      toast.success(`Nómina pagada: ${eur(res.data.amount_eur)}`);
      fetchAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo pagar la nómina');
    } finally { setPayingId(null); }
  };

  const download = async (url, filename) => {
    try {
      const res = await axios.get(url, { ...auth, responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = blobUrl; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (e) { toast.error('No se pudo exportar'); }
  };

  return (
    <div className="mt-8 space-y-6" data-testid="accounting-manager">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Wallet className="w-6 h-6 text-emerald-600" />
          <h2 className="text-xl font-bold text-gray-900">Contabilidad y Finanzas</h2>
        </div>
        <Button data-testid="acct-refresh" size="sm" variant="outline" onClick={fetchAll}>
          <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
        </Button>
      </div>

      {/* Resumen financiero */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-0 shadow-lg" data-testid="acct-income-card">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><TrendingUp className="w-3 h-3 text-emerald-600" /> Ingresos (EUR)</p>
            <p className="text-2xl font-bold text-emerald-700">{eur(summary?.total_income?.EUR)}</p>
            <p className="text-xs text-gray-500">{mad(summary?.total_income?.MAD)}</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-lg" data-testid="acct-expense-card">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><TrendingDown className="w-3 h-3 text-rose-600" /> Gastos (EUR)</p>
            <p className="text-2xl font-bold text-rose-700">{eur(summary?.total_expenses?.EUR)}</p>
            <p className="text-xs text-gray-500">{mad(summary?.total_expenses?.MAD)}</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-lg" data-testid="acct-net-card">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><Receipt className="w-3 h-3 text-teal-600" /> Balance neto</p>
            <p className="text-2xl font-bold text-teal-700">{eur(summary?.net_balance?.EUR)}</p>
            <p className="text-xs text-gray-500">{mad(summary?.net_balance?.MAD)}</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-lg" data-testid="acct-pending-payroll-card">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><Users className="w-3 h-3 text-amber-600" /> Nóminas pendientes</p>
            <p className="text-2xl font-bold text-amber-700">{eur(payroll?.pending_net_eur)}</p>
            <p className="text-xs text-gray-500">{payroll?.entries?.length || 0} Abejas</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Caja en efectivo */}
        <Card className="border-0 shadow-lg" data-testid="acct-cash-card">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2"><Banknote className="w-5 h-5 text-emerald-600" /> Control de caja</span>
              <div className="flex gap-2">
                <Button data-testid="acct-closing-csv" size="sm" variant="outline"
                  onClick={() => download(`${API}/accounting/cash/closing/export?format=csv`, 'arqueo.csv')}>
                  <Download className="w-4 h-4 mr-1" /> Arqueo CSV
                </Button>
                <Button data-testid="acct-closing-pdf" size="sm" className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => download(`${API}/accounting/cash/closing/export?format=pdf`, 'arqueo.pdf')}>
                  <FileText className="w-4 h-4 mr-1" /> PDF
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-emerald-50" data-testid="acct-cash-eur">
                <p className="text-xs text-gray-500">Caja EUR</p>
                <p className="text-xl font-bold text-emerald-700">{eur(cash?.cash_eur?.balance)}</p>
              </div>
              <div className="p-3 rounded-lg bg-teal-50" data-testid="acct-cash-mad">
                <p className="text-xs text-gray-500">Caja MAD</p>
                <p className="text-xl font-bold text-teal-700">{mad(cash?.cash_mad?.balance)}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
              <div>
                <label className="text-xs text-gray-500">Importe</label>
                <Input data-testid="acct-cash-amount" type="number" min="0" step="0.01" value={cashForm.amount}
                  onChange={(e) => setCashForm({ ...cashForm, amount: e.target.value })} className="h-9" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Moneda</label>
                <select data-testid="acct-cash-currency" value={cashForm.currency}
                  onChange={(e) => setCashForm({ ...cashForm, currency: e.target.value })}
                  className="w-full h-9 text-sm border rounded-md px-2 bg-white">
                  <option value="EUR">EUR</option><option value="MAD">MAD</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-gray-500">Concepto</label>
                <Input data-testid="acct-cash-desc" value={cashForm.description}
                  onChange={(e) => setCashForm({ ...cashForm, description: e.target.value })} className="h-9" placeholder="Ej. cobro en efectivo" />
              </div>
            </div>
            <div className="flex gap-2">
              <Button data-testid="acct-cash-in-btn" disabled={busy} onClick={() => submitCash('in')}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                <ArrowDownCircle className="w-4 h-4 mr-1" /> Entrada
              </Button>
              <Button data-testid="acct-cash-out-btn" disabled={busy} onClick={() => submitCash('out')}
                variant="outline" className="flex-1 border-rose-200 text-rose-700 hover:bg-rose-50">
                <ArrowUpCircle className="w-4 h-4 mr-1" /> Salida
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Nóminas de Abejas */}
        <Card className="border-0 shadow-lg" data-testid="acct-payroll-card">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2"><Users className="w-5 h-5 text-emerald-600" /> Nóminas de Abejas</span>
              <Button data-testid="acct-payroll-export" size="sm" variant="outline"
                onClick={() => download(`${API}/admin/finances/export`, 'pagos_repartidores.csv')}>
                <Download className="w-4 h-4 mr-1" /> CSV
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-[320px] overflow-y-auto">
            {(!payroll.entries || payroll.entries.length === 0) ? (
              <p className="text-sm text-gray-500 text-center py-8">No hay comisiones en el periodo (aún no hay entregas).</p>
            ) : (
              <table className="w-full text-sm" data-testid="acct-payroll-table">
                <thead><tr className="text-left text-xs text-gray-400 border-b">
                  <th className="py-2 pr-2">Abeja</th><th className="py-2 pr-2">Entregas</th>
                  <th className="py-2 pr-2">Comisión</th><th className="py-2 pr-2 text-right">Acción</th>
                </tr></thead>
                <tbody>
                  {payroll.entries.map((e) => (
                    <tr key={e.courier_id} className="border-b last:border-0">
                      <td className="py-2 pr-2 truncate max-w-[120px]">{e.courier_name}</td>
                      <td className="py-2 pr-2">{e.total_deliveries}</td>
                      <td className="py-2 pr-2 font-semibold text-emerald-700">{eur(e.net_amount_eur)}</td>
                      <td className="py-2 pr-2 text-right">
                        {e.is_paid ? (
                          <Badge className="bg-emerald-100 text-emerald-700">Pagada</Badge>
                        ) : (
                          <Button data-testid={`acct-pay-btn-${e.courier_id}`} size="sm" className="bg-emerald-600 hover:bg-emerald-700"
                            disabled={payingId === e.courier_id} onClick={() => payPayroll(e.courier_id)}>
                            {payingId === e.courier_id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Pagar'}
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Libro de transacciones */}
      <Card className="border-0 shadow-lg" data-testid="acct-txns-card">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2"><Receipt className="w-5 h-5 text-emerald-600" /> Libro de transacciones ({txns.total})</span>
            <Button data-testid="acct-txns-export" size="sm" className="bg-teal-600 hover:bg-teal-700"
              onClick={() => download(`${API}/accounting/export/transactions`, 'transacciones.csv')}>
              <Download className="w-4 h-4 mr-1" /> CSV
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(!txns.data || txns.data.length === 0) ? (
            <p className="text-sm text-gray-500 text-center py-8">Sin transacciones todavía.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="acct-txns-table">
                <thead><tr className="text-left text-xs text-gray-400 border-b">
                  <th className="py-2 pr-3">Fecha</th><th className="py-2 pr-3">Tipo</th>
                  <th className="py-2 pr-3">Importe</th><th className="py-2 pr-3">Método</th>
                  <th className="py-2 pr-3">Concepto</th>
                </tr></thead>
                <tbody>
                  {txns.data.map((t) => (
                    <tr key={t.id} className="border-b last:border-0">
                      <td className="py-2 pr-3 text-xs text-gray-500 whitespace-nowrap">{new Date(t.created_at).toLocaleString('es-ES')}</td>
                      <td className="py-2 pr-3"><Badge className={TXN_CLASS[t.type] || 'bg-gray-100'}>{TXN_LABEL[t.type] || t.type}</Badge></td>
                      <td className="py-2 pr-3 font-semibold">{t.currency === 'MAD' ? mad(t.amount) : eur(t.amount)}</td>
                      <td className="py-2 pr-3 text-xs text-gray-500">{t.payment_method}</td>
                      <td className="py-2 pr-3 truncate max-w-[220px]">{t.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AccountingManager;

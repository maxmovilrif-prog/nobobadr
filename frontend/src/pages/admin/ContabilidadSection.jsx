import React, { useState, useEffect, useContext, useCallback } from 'react';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import {
  Wallet, Banknote, ArrowDownCircle, ArrowUpCircle, TrendingUp, TrendingDown,
  Plus, Download, Loader2, Receipt, Users,
} from 'lucide-react';

/** Sección "Contabilidad" del Panel Admin — caja MAD/EUR, transacciones, nóminas y export. */

const TYPE_LABELS = {
  income: 'Ingreso', payout: 'Pago', refund: 'Devolución',
  adjustment: 'Ajuste', cash_in: 'Entrada caja', cash_out: 'Salida caja',
};
const TYPE_STYLES = {
  income: 'bg-emerald-100 text-emerald-700', cash_in: 'bg-emerald-100 text-emerald-700',
  payout: 'bg-rose-100 text-rose-700', refund: 'bg-amber-100 text-amber-700',
  cash_out: 'bg-rose-100 text-rose-700', adjustment: 'bg-slate-100 text-slate-700',
};
const METHOD_LABELS = {
  stripe: 'Stripe', cash_mad: 'Efectivo MAD', cash_eur: 'Efectivo EUR', bank_transfer: 'Transferencia',
};

const BalanceCard = ({ icon: Icon, label, amount, currency, sub, accent }) => (
  <Card className="border-0 shadow-sm">
    <CardContent className="p-5">
      <div className="flex items-center gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="text-2xl font-bold text-slate-900">
            {amount} <span className="text-base font-medium text-slate-400">{currency}</span>
          </p>
        </div>
      </div>
      {sub && <p className="mt-2 text-xs text-slate-400">{sub}</p>}
    </CardContent>
  </Card>
);

export const ContabilidadSection = () => {
  const { API, token } = useContext(AuthContext);
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [balance, setBalance] = useState(null);
  const [summary, setSummary] = useState(null);
  const [txns, setTxns] = useState([]);
  const [payroll, setPayroll] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');

  // Diálogos de caja
  const [cashDialog, setCashDialog] = useState(null); // 'in' | 'out' | null
  const [cashForm, setCashForm] = useState({ amount: '', currency: 'MAD', description: '' });
  const [saving, setSaving] = useState(false);

  const fetchAll = useCallback(async (type = '') => {
    setLoading(true);
    try {
      const [b, s, t, p] = await Promise.all([
        axios.get(`${API}/accounting/cash/balance`, auth),
        axios.get(`${API}/accounting/transactions/summary`, auth),
        axios.get(`${API}/accounting/transactions`, { params: { per_page: 50, type: type || undefined }, ...auth }),
        axios.get(`${API}/accounting/payroll`, auth),
      ]);
      setBalance(b.data); setSummary(s.data); setTxns(t.data.data || []); setPayroll(p.data);
    } catch (e) {
      toast.error('No se pudieron cargar los datos de contabilidad');
    } finally {
      setLoading(false);
    }
  }, [API, token]); // eslint-disable-line

  useEffect(() => { fetchAll(filterType); }, [fetchAll, filterType]);

  const submitCash = async () => {
    const amt = parseFloat(cashForm.amount);
    if (!amt || amt <= 0 || cashForm.description.trim().length < 2) {
      toast.error('Indica un importe válido y un concepto'); return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/accounting/cash/${cashDialog}`, {
        amount: amt, currency: cashForm.currency, description: cashForm.description.trim(),
      }, auth);
      toast.success(cashDialog === 'in' ? 'Entrada de caja registrada' : 'Salida de caja registrada');
      setCashDialog(null);
      setCashForm({ amount: '', currency: 'MAD', description: '' });
      fetchAll(filterType);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Error al registrar el movimiento');
    } finally {
      setSaving(false);
    }
  };

  const exportCsv = () => {
    window.open(`${API}/accounting/export/transactions?token=${token}`, '_blank');
    // Fallback con fetch+blob para respetar el header Authorization
    axios.get(`${API}/accounting/export/transactions`, { ...auth, responseType: 'blob' })
      .then((res) => {
        const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
        const a = document.createElement('a');
        a.href = url; a.download = 'transacciones.csv'; a.click();
        URL.revokeObjectURL(url);
      }).catch(() => {});
  };

  const fmtDate = (d) => d ? new Date(d).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';

  return (
    <div className="space-y-6" data-testid="contabilidad-section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500">Caja, transacciones y nóminas en MAD / EUR.</p>
        <div className="flex gap-2">
          <Button data-testid="cash-in-btn" size="sm" className="gap-2 bg-emerald-600 hover:bg-emerald-700"
            onClick={() => setCashDialog('in')}>
            <ArrowDownCircle className="h-4 w-4" /> Entrada caja
          </Button>
          <Button data-testid="cash-out-btn" size="sm" variant="outline" className="gap-2"
            onClick={() => setCashDialog('out')}>
            <ArrowUpCircle className="h-4 w-4" /> Salida caja
          </Button>
          <Button data-testid="export-txns-btn" size="sm" variant="outline" className="gap-2" onClick={exportCsv}>
            <Download className="h-4 w-4" /> CSV
          </Button>
        </div>
      </div>

      {/* Caja + resumen */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <BalanceCard icon={Banknote} label="Caja efectivo MAD"
          amount={balance ? balance.cash_mad.balance : '—'} currency="MAD"
          sub={balance?.cash_mad?.last_movement ? `Últ. mov: ${fmtDate(balance.cash_mad.last_movement)}` : 'Sin movimientos'}
          accent="bg-emerald-100 text-emerald-600" />
        <BalanceCard icon={Wallet} label="Caja efectivo EUR"
          amount={balance ? balance.cash_eur.balance : '—'} currency="EUR"
          sub={balance?.cash_eur?.last_movement ? `Últ. mov: ${fmtDate(balance.cash_eur.last_movement)}` : 'Sin movimientos'}
          accent="bg-teal-100 text-teal-600" />
        <BalanceCard icon={TrendingUp} label="Ingresos netos (EUR)"
          amount={summary ? summary.net_balance.EUR : '—'} currency="EUR"
          sub={summary ? `Ingresos: ${summary.total_income.EUR} · Gastos: ${summary.total_expenses.EUR}` : ''}
          accent="bg-indigo-100 text-indigo-600" />
        <BalanceCard icon={TrendingDown} label="Balance neto (MAD)"
          amount={summary ? summary.net_balance.MAD : '—'} currency="MAD"
          sub={summary ? `Ingresos: ${summary.total_income.MAD} · Gastos: ${summary.total_expenses.MAD}` : ''}
          accent="bg-amber-100 text-amber-600" />
      </div>

      {/* Transacciones */}
      <Card className="border-0 shadow-sm" data-testid="transactions-card">
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-6 py-4">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <Receipt className="h-5 w-5 text-slate-400" /> Transacciones
            </h2>
            <select data-testid="txn-filter-type" value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm">
              <option value="">Todos los tipos</option>
              {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Fecha</th>
                  <th className="px-6 py-3 font-medium">Tipo</th>
                  <th className="px-6 py-3 font-medium">Método</th>
                  <th className="px-6 py-3 font-medium">Concepto</th>
                  <th className="px-6 py-3 text-right font-medium">Importe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-400"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></td></tr>
                ) : txns.length === 0 ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-500">No hay transacciones.</td></tr>
                ) : (
                  txns.map((t) => (
                    <tr key={t.id} data-testid={`txn-row-${t.id}`} className="transition-colors hover:bg-slate-50">
                      <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-400">{fmtDate(t.created_at)}</td>
                      <td className="px-6 py-3"><Badge className={TYPE_STYLES[t.type] || 'bg-slate-100 text-slate-700'}>{TYPE_LABELS[t.type] || t.type}</Badge></td>
                      <td className="px-6 py-3 text-slate-600">{METHOD_LABELS[t.payment_method] || t.payment_method}</td>
                      <td className="px-6 py-3 text-slate-900">{t.description}</td>
                      <td className={`px-6 py-3 text-right font-semibold ${ACCT_SIGN(t.type)}`}>
                        {ACCT_SIGN_TXT(t.type)}{t.amount} {t.currency}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Nóminas */}
      <Card className="border-0 shadow-sm" data-testid="payroll-card">
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <Users className="h-5 w-5 text-slate-400" /> Nóminas de Abejas
            </h2>
            {payroll && (
              <span className="text-sm font-medium text-slate-500">
                Total: {payroll.total_net_eur} € · {payroll.total_net_mad} MAD
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Abeja</th>
                  <th className="px-6 py-3 text-center font-medium">Entregas</th>
                  <th className="px-6 py-3 text-right font-medium">Comisión EUR</th>
                  <th className="px-6 py-3 text-right font-medium">Comisión MAD</th>
                  <th className="px-6 py-3 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-400"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></td></tr>
                ) : !payroll || payroll.entries.length === 0 ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-500">No hay nóminas en el periodo.</td></tr>
                ) : (
                  payroll.entries.map((e) => (
                    <tr key={e.courier_id} data-testid={`payroll-row-${e.courier_id}`} className="transition-colors hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-900">{e.courier_name}</td>
                      <td className="px-6 py-3 text-center text-slate-600">{e.total_deliveries}</td>
                      <td className="px-6 py-3 text-right font-semibold text-slate-900">{e.net_amount_eur} €</td>
                      <td className="px-6 py-3 text-right text-slate-600">{e.net_amount_mad} MAD</td>
                      <td className="px-6 py-3">
                        <Badge className={e.is_paid ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
                          {e.is_paid ? 'Pagado' : 'Pendiente'}
                        </Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Diálogo entrada/salida de caja */}
      <Dialog open={!!cashDialog} onOpenChange={(o) => { if (!o) setCashDialog(null); }}>
        <DialogContent data-testid="cash-dialog">
          <DialogHeader>
            <DialogTitle>{cashDialog === 'in' ? 'Entrada de caja' : 'Salida de caja'}</DialogTitle>
            <DialogDescription>Registra un movimiento de efectivo en MAD o EUR.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Importe</Label>
                <Input data-testid="cash-amount" type="number" step="any" value={cashForm.amount}
                  onChange={(e) => setCashForm({ ...cashForm, amount: e.target.value })} placeholder="0.00" />
              </div>
              <div>
                <Label className="text-xs">Moneda</Label>
                <select data-testid="cash-currency" value={cashForm.currency}
                  onChange={(e) => setCashForm({ ...cashForm, currency: e.target.value })}
                  className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm">
                  <option value="MAD">MAD</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Concepto</Label>
              <Input data-testid="cash-description" value={cashForm.description}
                onChange={(e) => setCashForm({ ...cashForm, description: e.target.value })}
                placeholder="Ej. Apertura de caja" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCashDialog(null)}>Cancelar</Button>
            <Button data-testid="cash-submit" onClick={submitCash} disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-700">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Registrar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Signo visual según tipo de movimiento
function ACCT_SIGN(type) {
  return ['payout', 'refund', 'cash_out'].includes(type) ? 'text-rose-600' : 'text-emerald-600';
}
function ACCT_SIGN_TXT(type) {
  return ['payout', 'refund', 'cash_out'].includes(type) ? '− ' : '+ ';
}

export default ContabilidadSection;

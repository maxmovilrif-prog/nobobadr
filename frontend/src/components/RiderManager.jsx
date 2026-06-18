import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Bike, Car, Truck, Zap, Plus, QrCode, Loader2, RefreshCw, UserCheck, UserX, Users } from 'lucide-react';

const EMPTY = { name: '', phone: '', vehicle_type: 'motorcycle', dni: '', license_plate: '' };
const VICON = { bicycle: Bike, motorcycle: Zap, car: Car, truck: Truck };
const VLABEL = { bicycle: 'Bici', motorcycle: 'Moto', car: 'Coche', truck: 'Camión' };

export const RiderManager = ({ API, token }) => {
  const [riders, setRiders] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [qrModal, setQrModal] = useState(null); // {name, code, qr}
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const fetchRiders = async () => {
    try {
      const res = await axios.get(`${API}/admin/riders`, auth);
      setRiders(res.data.riders || []);
    } catch (e) { /* noop */ }
  };

  useEffect(() => { fetchRiders(); /* eslint-disable-next-line */ }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.phone.trim()) { toast.error('Nombre y teléfono obligatorios'); return; }
    setCreating(true);
    try {
      const res = await axios.post(`${API}/admin/riders`, { ...form, name: form.name.trim(), phone: form.phone.trim() }, auth);
      toast.success('Rider dado de alta');
      setQrModal({ name: res.data.name, code: res.data.activation_code, qr: res.data.qr_data_url });
      setForm(EMPTY);
      fetchRiders();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo crear el rider');
    } finally {
      setCreating(false);
    }
  };

  const toggleContract = async (rider) => {
    const next = rider.contract_status === 'suspended' ? 'active' : 'suspended';
    try {
      await axios.patch(`${API}/admin/riders/${rider.id}`, { contract_status: next }, auth);
      toast.success(next === 'suspended' ? 'Rider suspendido' : 'Rider reactivado');
      fetchRiders();
    } catch (e) { toast.error('No se pudo actualizar'); }
  };

  const showQr = async (rider) => {
    try {
      const res = await axios.get(`${API}/admin/riders/${rider.id}/qr`, auth);
      setQrModal({ name: rider.name, code: res.data.activation_code, qr: res.data.qr_data_url });
    } catch (e) { toast.error('No se pudo cargar el QR'); }
  };

  const regenerate = async (rider) => {
    try {
      const res = await axios.post(`${API}/admin/riders/${rider.id}/regenerate-code`, {}, auth);
      toast.success('Código regenerado');
      setQrModal({ name: rider.name, code: res.data.activation_code, qr: res.data.qr_data_url });
      fetchRiders();
    } catch (e) { toast.error('No se pudo regenerar'); }
  };

  const printQr = () => {
    if (!qrModal) return;
    const w = window.open('', '_blank');
    w.document.write(`<html><head><title>${qrModal.name} - ${qrModal.code}</title></head>
      <body style="text-align:center;font-family:sans-serif;padding:40px">
      <h2>🐝 Nubo Rider</h2><h3>${qrModal.name}</h3>
      <img src="${qrModal.qr}" style="width:280px"/>
      <p style="font-size:28px;letter-spacing:4px;font-weight:bold">${qrModal.code}</p>
      </body></html>`);
    w.document.close();
    w.focus();
    w.print();
  };

  return (
    <Card className="border-0 shadow-xl mt-8" data-testid="rider-manager-card">
      <CardContent className="p-0">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-600" /> Conductores (Riders) y códigos QR
          </h2>
          <span data-testid="rider-count" className="text-sm font-medium text-gray-500">{riders.length} riders</span>
        </div>

        <form onSubmit={handleCreate} className="px-6 py-4 border-b bg-gray-50 grid grid-cols-1 sm:grid-cols-6 gap-3 items-end" data-testid="rider-add-form">
          <div className="sm:col-span-2">
            <Label className="text-xs">Nombre</Label>
            <Input data-testid="rider-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Karim El..." />
          </div>
          <div>
            <Label className="text-xs">Teléfono</Label>
            <Input data-testid="rider-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+212..." />
          </div>
          <div>
            <Label className="text-xs">Vehículo</Label>
            <select data-testid="rider-vehicle-select" value={form.vehicle_type} onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}
              className="w-full h-10 rounded-md border border-gray-200 bg-white px-2 text-sm">
              <option value="bicycle">Bici</option>
              <option value="motorcycle">Moto</option>
              <option value="car">Coche</option>
              <option value="truck">Camión</option>
            </select>
          </div>
          <div>
            <Label className="text-xs">DNI/ID</Label>
            <Input data-testid="rider-dni-input" value={form.dni} onChange={(e) => setForm({ ...form, dni: e.target.value })} placeholder="X1234" />
          </div>
          <div>
            <Label className="text-xs">Matrícula</Label>
            <Input data-testid="rider-plate-input" value={form.license_plate} onChange={(e) => setForm({ ...form, license_plate: e.target.value })} placeholder="1234-ABC" />
          </div>
          <div className="sm:col-span-6">
            <Button data-testid="rider-add-btn" type="submit" disabled={creating} className="bg-emerald-600 hover:bg-emerald-700 gap-2">
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Dar de alta y generar QR
            </Button>
          </div>
        </form>

        <div className="overflow-x-auto max-h-[420px] overflow-y-auto" data-testid="rider-table">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left sticky top-0">
              <tr>
                <th className="px-4 py-3 font-medium">Rider</th>
                <th className="px-4 py-3 font-medium">Vehículo</th>
                <th className="px-4 py-3 font-medium">Código</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {riders.length === 0 ? (
                <tr><td colSpan="5" className="px-6 py-10 text-center text-gray-500">No hay riders. Da de alta el primero.</td></tr>
              ) : (
                riders.map((r) => {
                  const Icon = VICON[r.vehicle_type] || Zap;
                  return (
                    <tr key={r.id} data-testid={`rider-row-${r.id}`}>
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-900">{r.name}</p>
                        <p className="text-xs text-gray-500">{r.phone}</p>
                      </td>
                      <td className="px-4 py-3 text-gray-700"><span className="inline-flex items-center gap-1"><Icon className="w-4 h-4" /> {VLABEL[r.vehicle_type]}</span></td>
                      <td className="px-4 py-3 font-mono text-gray-700">{r.activation_code}</td>
                      <td className="px-4 py-3">
                        {r.contract_status === 'suspended'
                          ? <Badge className="bg-red-100 text-red-700">Suspendido</Badge>
                          : r.activated
                            ? <Badge className="bg-emerald-100 text-emerald-700">Activo</Badge>
                            : <Badge className="bg-amber-100 text-amber-700">Pendiente</Badge>}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <Button data-testid={`rider-qr-${r.id}`} variant="ghost" size="sm" onClick={() => showQr(r)} title="Ver QR"><QrCode className="w-4 h-4 text-gray-600" /></Button>
                        <Button data-testid={`rider-regen-${r.id}`} variant="ghost" size="sm" onClick={() => regenerate(r)} title="Regenerar código"><RefreshCw className="w-4 h-4 text-gray-500" /></Button>
                        <Button data-testid={`rider-toggle-${r.id}`} variant="ghost" size="sm" onClick={() => toggleContract(r)} title={r.contract_status === 'suspended' ? 'Reactivar' : 'Suspender'}>
                          {r.contract_status === 'suspended' ? <UserCheck className="w-4 h-4 text-emerald-600" /> : <UserX className="w-4 h-4 text-red-500" />}
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </CardContent>

      <Dialog open={!!qrModal} onOpenChange={(o) => { if (!o) setQrModal(null); }}>
        <DialogContent data-testid="rider-qr-dialog" className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><QrCode className="w-5 h-5 text-emerald-600" /> Código de activación</DialogTitle>
            <DialogDescription>El conductor escanea este QR o escribe el código en su app Nubo Riders.</DialogDescription>
          </DialogHeader>
          {qrModal && (
            <div className="text-center space-y-3">
              <p className="font-medium text-gray-900">{qrModal.name}</p>
              <img src={qrModal.qr} alt="QR" className="w-48 h-48 mx-auto rounded-lg border" data-testid="rider-qr-image" />
              <p className="text-2xl font-mono font-bold tracking-widest text-emerald-700" data-testid="rider-qr-code">{qrModal.code}</p>
              <Button onClick={printQr} variant="outline" className="w-full" data-testid="rider-qr-print">Imprimir ficha</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default RiderManager;

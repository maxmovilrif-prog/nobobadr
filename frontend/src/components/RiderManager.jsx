import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { QRCodeCanvas } from 'qrcode.react';
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
  const downloadQrRef = useRef(null);
  const APP_DOWNLOAD_URL = `${window.location.origin}/rider`;
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const fetchRiders = async () => {
    try {
      const res = await axios.get(`${API}/admin/riders`, auth);
      setRiders(res.data.riders || []);
    } catch (e) { console.error('Error cargando riders', e); }
  };

  useEffect(() => { fetchRiders(); /* eslint-disable-next-line */ }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.phone.trim()) { toast.error('Nombre y teléfono obligatorios'); return; }
    setCreating(true);
    try {
      const res = await axios.post(`${API}/admin/riders`, { ...form, name: form.name.trim(), phone: form.phone.trim() }, auth);
      toast.success('Rider dado de alta');
      setQrModal({
        name: res.data.name, code: res.data.activation_code, qr: res.data.qr_data_url,
        vehicle_type: res.data.vehicle_type, phone: res.data.phone, dni: res.data.dni, license_plate: res.data.license_plate,
      });
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
      setQrModal({
        name: rider.name, code: res.data.activation_code, qr: res.data.qr_data_url,
        vehicle_type: rider.vehicle_type, phone: rider.phone, dni: rider.dni, license_plate: rider.license_plate,
      });
    } catch (e) { toast.error('No se pudo cargar el QR'); }
  };

  const regenerate = async (rider) => {
    try {
      const res = await axios.post(`${API}/admin/riders/${rider.id}/regenerate-code`, {}, auth);
      toast.success('Código regenerado');
      setQrModal({
        name: rider.name, code: res.data.activation_code, qr: res.data.qr_data_url,
        vehicle_type: rider.vehicle_type, phone: rider.phone, dni: rider.dni, license_plate: rider.license_plate,
      });
      fetchRiders();
    } catch (e) { toast.error('No se pudo regenerar'); }
  };

  const printQr = () => {
    if (!qrModal) return;
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
    const vlabelRaw = VLABEL[qrModal.vehicle_type] || qrModal.vehicle_type || '—';
    const vlabel = esc(vlabelRaw);
    const name = esc(qrModal.name);
    const code = esc(qrModal.code);
    let downloadQr = '';
    try { downloadQr = downloadQrRef.current?.toDataURL('image/png') || ''; } catch (e) { console.warn('No se pudo generar el QR de descarga', e); }
    const row = (label, value) => value
      ? `<tr><td style="padding:6px 14px;color:#6b7280;font-size:13px">${label}</td><td style="padding:6px 14px;font-weight:600;color:#111827">${esc(value)}</td></tr>`
      : '';
    const html = `<html><head><title>Ficha de activación · ${name} · ${code}</title>
      <meta charset="utf-8"/>
      <style>
        @page { margin: 16mm; }
        body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; color:#111827; margin:0; }
        .sheet { max-width: 660px; margin: 0 auto; border:1px solid #e5e7eb; border-radius:16px; overflow:hidden; }
        .head { background:#047857; color:#fff; padding:22px 28px; display:flex; align-items:center; gap:12px; }
        .head h1 { font-size:22px; margin:0; letter-spacing:.5px; }
        .head p { margin:2px 0 0; font-size:13px; opacity:.85; }
        .body { padding:24px 28px; display:flex; gap:24px; align-items:flex-start; }
        .info { flex:1; }
        table { border-collapse:collapse; width:100%; }
        .name { font-size:20px; font-weight:800; margin:0 0 4px; }
        .badge { display:inline-block; background:#ecfdf5; color:#047857; border-radius:999px; padding:4px 12px; font-size:13px; font-weight:700; margin-bottom:12px; }
        .qrs { display:flex; gap:18px; padding:0 28px 8px; }
        .qrcard { flex:1; text-align:center; border:1px solid #e5e7eb; border-radius:12px; padding:14px; }
        .qrcard h4 { margin:0 0 8px; font-size:13px; color:#047857; }
        .qrcard img { width:170px; height:170px; }
        .qrcard .num { margin-top:8px; font-size:13px; color:#6b7280; }
        .code { font-size:22px; font-weight:800; letter-spacing:5px; color:#047857; font-family:monospace; }
        .steps { margin:18px 28px 24px; background:#f9fafb; border-radius:12px; padding:16px 22px; }
        .steps h3 { margin:0 0 8px; font-size:14px; color:#047857; }
        .steps ol { margin:0; padding-left:20px; color:#374151; font-size:13px; line-height:1.7; }
        .foot { text-align:center; color:#9ca3af; font-size:11px; padding:0 28px 22px; }
      </style></head>
      <body>
        <div class="sheet">
          <div class="head">
            <div style="font-size:30px">🐝</div>
            <div><h1>Nubo Express</h1><p>Hoja de activación de conductor (Abeja)</p></div>
          </div>
          <div class="body">
            <div class="info">
              <p class="name">${name}</p>
              <span class="badge">${vlabel}</span>
              <table>
                ${row('ID único', qrModal.code)}
                ${row('Vehículo', vlabelRaw)}
                ${row('Teléfono', qrModal.phone)}
                ${row('DNI/ID', qrModal.dni)}
                ${row('Matrícula', qrModal.license_plate)}
              </table>
            </div>
          </div>
          <div class="qrs">
            <div class="qrcard">
              <h4>1 · Descarga la app</h4>
              ${downloadQr ? `<img src="${downloadQr}" alt="Descargar app"/>` : ''}
              <div class="num">Abre Nubo Riders</div>
            </div>
            <div class="qrcard">
              <h4>2 · Activa tu cuenta</h4>
              <img src="${qrModal.qr}" alt="Activación"/>
              <div class="code">${code}</div>
            </div>
          </div>
          <div class="steps">
            <h3>Cómo empezar (2 escaneos)</h3>
            <ol>
              <li>Escanea el <b>QR 1</b> para abrir e instalar la app <b>Nubo Riders</b> en tu móvil.</li>
              <li>Dentro de la app, pulsa <b>"Escanear QR"</b> y apunta al <b>QR 2</b>.</li>
              <li>La app se configurará con tu nombre, perfil y vehículo automáticamente.</li>
              <li>Si no puedes escanear, escribe el código <b>${code}</b> manualmente.</li>
            </ol>
          </div>
          <div class="foot">Documento generado por Nubo Express · Conserva esta hoja. El código es personal e intransferible.</div>
        </div>
        <script>window.onload = function(){ window.focus(); window.print(); }</script>
      </body></html>`;
    const w = window.open('', '_blank');
    if (!w) { toast.error('Permite las ventanas emergentes para imprimir la ficha'); return; }
    const blob = new Blob([html], { type: 'text/html' });
    w.location.href = URL.createObjectURL(blob);
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
              {qrModal.vehicle_type && (
                <Badge className="bg-emerald-100 text-emerald-700" data-testid="rider-qr-vehicle">{VLABEL[qrModal.vehicle_type] || qrModal.vehicle_type}</Badge>
              )}
              <div className="flex items-start justify-center gap-4">
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-1">1 · Descargar app</p>
                  <div className="p-2 bg-white border rounded-lg inline-block" data-testid="rider-download-qr">
                    <QRCodeCanvas ref={downloadQrRef} value={APP_DOWNLOAD_URL} size={120} fgColor="#047857" level="M" includeMargin={false} />
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-1">2 · Activar cuenta</p>
                  <img src={qrModal.qr} alt="QR activación" className="w-[136px] h-[136px] mx-auto rounded-lg border" data-testid="rider-qr-image" />
                </div>
              </div>
              <p className="text-2xl font-mono font-bold tracking-widest text-emerald-700" data-testid="rider-qr-code">{qrModal.code}</p>
              <Button onClick={printQr} variant="outline" className="w-full" data-testid="rider-qr-print">Imprimir ficha de activación</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default RiderManager;

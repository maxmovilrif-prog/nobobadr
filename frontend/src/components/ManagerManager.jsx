import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { ShieldCheck, UserPlus, Trash2, Loader2, Mail } from 'lucide-react';

export const ManagerManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [managers, setManagers] = useState([]);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchManagers = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/managers`, auth);
      setManagers(res.data.managers || []);
    } catch (e) { /* noop */ }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchManagers(); }, [fetchManagers]);

  const createManager = async () => {
    if (form.name.trim().length < 2 || !form.email.trim() || form.password.length < 6) {
      toast.error('Nombre, email válido y contraseña (mín. 6 caracteres)'); return;
    }
    setCreating(true);
    try {
      await axios.post(`${API}/admin/managers`, {
        name: form.name.trim(), email: form.email.trim().toLowerCase(), password: form.password,
      }, auth);
      toast.success('Cuenta de Gestor creada');
      setForm({ name: '', email: '', password: '' });
      fetchManagers();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo crear el Gestor');
    } finally { setCreating(false); }
  };

  const removeManager = async (id) => {
    setDeletingId(id);
    try {
      await axios.delete(`${API}/admin/managers/${id}`, auth);
      toast.success('Gestor eliminado');
      fetchManagers();
    } catch (e) { toast.error('No se pudo eliminar'); }
    finally { setDeletingId(null); }
  };

  return (
    <Card className="mt-8 border-0 shadow-lg" data-testid="manager-manager-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-600" /> Equipo de Gestión (Administración)</span>
          <Badge className="bg-emerald-100 text-emerald-700" data-testid="manager-count">{managers.length} gestores</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-gray-500">
          Los Gestores acceden <b>solo a Operaciones</b> (ver pedidos, tarifas por distancia y despachar). No ven KPIs ni Contabilidad.
        </p>
        <div className="grid sm:grid-cols-4 gap-2 items-end">
          <div>
            <label className="text-xs text-gray-500">Nombre</label>
            <Input data-testid="manager-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-9" placeholder="Ej. María Gestora" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Email</label>
            <Input data-testid="manager-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="h-9" placeholder="gestor@nubo.com" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Contraseña</label>
            <Input data-testid="manager-password-input" type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="h-9" placeholder="mín. 6 caracteres" />
          </div>
          <Button data-testid="manager-add-btn" onClick={createManager} disabled={creating} className="bg-emerald-600 hover:bg-emerald-700">
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4 mr-1" />}
            {creating ? '' : 'Crear Gestor'}
          </Button>
        </div>

        {managers.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">Aún no hay gestores. Crea la primera cuenta de tu equipo.</p>
        ) : (
          <div className="space-y-2">
            {managers.map((m) => (
              <div key={m.id} data-testid={`manager-row-${m.id}`} className="flex items-center gap-3 p-3 rounded-lg border bg-white">
                <div className="w-9 h-9 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-semibold">
                  {(m.name || '?').charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{m.name}</p>
                  <p className="text-xs text-gray-500 flex items-center gap-1 truncate"><Mail className="w-3 h-3" /> {m.email}</p>
                </div>
                <Badge className="bg-blue-100 text-blue-700">Gestor</Badge>
                <Button data-testid={`manager-delete-${m.id}`} onClick={() => removeManager(m.id)} disabled={deletingId === m.id}
                  size="icon" variant="ghost" className="text-rose-500 hover:bg-rose-50">
                  {deletingId === m.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ManagerManager;

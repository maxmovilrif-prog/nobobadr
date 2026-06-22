import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Building2, Plus, Trash2, Loader2, MapPin } from 'lucide-react';

export const RegionManager = ({ API, token }) => {
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const [regions, setRegions] = useState([]);
  const [cities, setCities] = useState([]);
  const [name, setName] = useState('');
  const [selected, setSelected] = useState([]);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [rRes, cRes] = await Promise.all([
        axios.get(`${API}/admin/regions`, auth),
        axios.get(`${API}/public/cities`),
      ]);
      setRegions(rRes.data.regions || []);
      const c = cRes.data;
      setCities(Array.isArray(c) ? c : (c.cities || []));
    } catch (e) { console.error('Error cargando regiones/ciudades', e); }
    // eslint-disable-next-line
  }, [API, token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const toggleCity = (id) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const createRegion = async () => {
    if (name.trim().length < 2) { toast.error('Nombre de delegación (mín. 2 caracteres)'); return; }
    if (selected.length === 0) { toast.error('Selecciona al menos una ciudad'); return; }
    setCreating(true);
    try {
      await axios.post(`${API}/admin/regions`, { name: name.trim(), city_ids: selected }, auth);
      toast.success('Delegación creada');
      setName(''); setSelected([]);
      fetchAll();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo crear la delegación');
    } finally { setCreating(false); }
  };

  const removeRegion = async (id) => {
    setDeletingId(id);
    try {
      await axios.delete(`${API}/admin/regions/${id}`, auth);
      toast.success('Delegación eliminada');
      fetchAll();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo eliminar');
    } finally { setDeletingId(null); }
  };

  return (
    <Card className="mt-8 border-0 shadow-lg" data-testid="region-manager-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2"><Building2 className="w-5 h-5 text-emerald-600" /> Delegaciones (Administraciones Regionales)</span>
          <Badge className="bg-emerald-100 text-emerald-700" data-testid="region-count">{regions.length} delegaciones</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-gray-500">
          Cada delegación agrupa varias ciudades y aísla por completo sus datos (pedidos, riders, despacho). Asigna gestores a cada una.
        </p>

        <div className="rounded-lg border p-3 bg-gray-50 space-y-3">
          <div className="grid sm:grid-cols-3 gap-2 items-end">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500">Nombre de la delegación</label>
              <Input data-testid="region-name-input" value={name} onChange={(e) => setName(e.target.value)} className="h-9 bg-white" placeholder="Ej. Zona Sur (Algeciras)" />
            </div>
            <Button data-testid="region-add-btn" onClick={createRegion} disabled={creating} className="bg-emerald-600 hover:bg-emerald-700">
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4 mr-1" />}
              {creating ? '' : 'Crear delegación'}
            </Button>
          </div>
          <div>
            <label className="text-xs text-gray-500">Ciudades que controla ({selected.length} seleccionadas)</label>
            <div className="flex flex-wrap gap-2 mt-1" data-testid="region-cities-picker">
              {cities.map((c) => (
                <button key={c.id} type="button" data-testid={`region-city-${c.id}`} onClick={() => toggleCity(c.id)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${selected.includes(c.id) ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200 hover:border-emerald-400'}`}>
                  {c.name} <span className="opacity-60">{c.country}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {regions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">Aún no hay delegaciones. Crea la primera para organizar tu red regional.</p>
        ) : (
          <div className="space-y-2">
            {regions.map((r) => (
              <div key={r.id} data-testid={`region-row-${r.id}`} className="flex items-start gap-3 p-3 rounded-lg border bg-white">
                <div className="w-9 h-9 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Building2 className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">{r.name}</p>
                  <p className="text-xs text-gray-500 flex items-center gap-1 flex-wrap mt-0.5">
                    <MapPin className="w-3 h-3" /> {(r.cities || []).map((c) => c.name).join(' · ') || 'Sin ciudades'}
                  </p>
                  <div className="flex gap-2 mt-1">
                    <Badge className="bg-blue-50 text-blue-600 text-[10px]">{r.managers_count || 0} gestores</Badge>
                    <Badge className="bg-amber-50 text-amber-600 text-[10px]">{r.riders_count || 0} riders</Badge>
                  </div>
                </div>
                <Button data-testid={`region-delete-${r.id}`} onClick={() => removeRegion(r.id)} disabled={deletingId === r.id}
                  size="icon" variant="ghost" className="text-rose-500 hover:bg-rose-50">
                  {deletingId === r.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RegionManager;

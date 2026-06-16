import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { MapPin, Plus, Pencil, Trash2, Loader2 } from 'lucide-react';

const EMPTY = { name: '', country: 'ES', lat: '', lng: '' };

export const CityManager = ({ API, token, onChanged }) => {
  const [cities, setCities] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [editCity, setEditCity] = useState(null); // city being edited (dialog)
  const [saving, setSaving] = useState(false);
  const [deleteCity, setDeleteCity] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const fetchCities = async () => {
    try {
      const res = await axios.get(`${API}/cities`, auth);
      setCities(res.data.cities || []);
    } catch (e) { /* noop */ }
  };

  useEffect(() => { fetchCities(); /* eslint-disable-next-line */ }, []);

  const refresh = () => { fetchCities(); if (onChanged) onChanged(); };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || form.lat === '' || form.lng === '') {
      toast.error('Completa nombre, latitud y longitud');
      return;
    }
    setCreating(true);
    try {
      await axios.post(`${API}/admin/cities`, {
        name: form.name.trim(), country: form.country,
        lat: parseFloat(form.lat), lng: parseFloat(form.lng),
      }, auth);
      toast.success('Ciudad añadida');
      setForm(EMPTY);
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo crear la ciudad');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdate = async () => {
    if (!editCity) return;
    setSaving(true);
    try {
      await axios.patch(`${API}/admin/cities/${editCity.id}`, {
        name: editCity.name.trim(), country: editCity.country,
        lat: parseFloat(editCity.lat), lng: parseFloat(editCity.lng),
      }, auth);
      toast.success('Ciudad actualizada');
      setEditCity(null);
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo actualizar');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteCity) return;
    setDeleting(true);
    try {
      await axios.delete(`${API}/admin/cities/${deleteCity.id}`, auth);
      toast.success('Ciudad eliminada');
      setDeleteCity(null);
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo eliminar');
    } finally {
      setDeleting(false);
    }
  };

  const flag = (c) => (c === 'MA' ? '🇲🇦' : '🇪🇸');

  return (
    <Card className="border-0 shadow-xl mt-8" data-testid="city-manager-card">
      <CardContent className="p-0">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-emerald-600" /> Zonas operativas (ciudades)
          </h2>
          <span data-testid="city-count" className="text-sm font-medium text-gray-500">{cities.length} ciudades</span>
        </div>

        {/* Formulario de alta */}
        <form onSubmit={handleCreate} className="px-6 py-4 border-b bg-gray-50 grid grid-cols-1 sm:grid-cols-5 gap-3 items-end" data-testid="city-add-form">
          <div className="sm:col-span-2">
            <Label className="text-xs">Nombre</Label>
            <Input data-testid="city-name-input" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej. Tetuán" />
          </div>
          <div>
            <Label className="text-xs">País</Label>
            <select data-testid="city-country-select" value={form.country}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
              className="w-full h-10 rounded-md border border-gray-200 bg-white px-3 text-sm">
              <option value="ES">🇪🇸 España</option>
              <option value="MA">🇲🇦 Marruecos</option>
            </select>
          </div>
          <div>
            <Label className="text-xs">Latitud</Label>
            <Input data-testid="city-lat-input" type="number" step="any" value={form.lat}
              onChange={(e) => setForm({ ...form, lat: e.target.value })} placeholder="35.57" />
          </div>
          <div>
            <Label className="text-xs">Longitud</Label>
            <Input data-testid="city-lng-input" type="number" step="any" value={form.lng}
              onChange={(e) => setForm({ ...form, lng: e.target.value })} placeholder="-5.36" />
          </div>
          <div className="sm:col-span-5">
            <Button data-testid="city-add-btn" type="submit" disabled={creating}
              className="bg-emerald-600 hover:bg-emerald-700 gap-2">
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Añadir ciudad
            </Button>
          </div>
        </form>

        {/* Tabla */}
        <div className="overflow-x-auto max-h-[420px] overflow-y-auto" data-testid="city-table">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left sticky top-0">
              <tr>
                <th className="px-4 py-3 font-medium">Ciudad</th>
                <th className="px-4 py-3 font-medium">País</th>
                <th className="px-4 py-3 font-medium">Lat</th>
                <th className="px-4 py-3 font-medium">Lng</th>
                <th className="px-4 py-3 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {cities.length === 0 ? (
                <tr><td colSpan="5" className="px-6 py-10 text-center text-gray-500">No hay ciudades.</td></tr>
              ) : (
                cities.map((c) => (
                  <tr key={c.id} data-testid={`city-row-${c.id}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                    <td className="px-4 py-3 text-gray-700">{flag(c.country)} {c.country || 'ES'}</td>
                    <td className="px-4 py-3 text-gray-600">{c.lat}</td>
                    <td className="px-4 py-3 text-gray-600">{c.lng}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button data-testid={`city-edit-${c.id}`} variant="ghost" size="sm"
                        onClick={() => setEditCity({ ...c, country: c.country || 'ES' })}>
                        <Pencil className="w-4 h-4 text-gray-500" />
                      </Button>
                      <Button data-testid={`city-delete-${c.id}`} variant="ghost" size="sm"
                        onClick={() => setDeleteCity(c)}>
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>

      {/* Dialogo de edición */}
      <Dialog open={!!editCity} onOpenChange={(o) => { if (!o) setEditCity(null); }}>
        <DialogContent data-testid="city-edit-dialog">
          <DialogHeader>
            <DialogTitle>Editar ciudad</DialogTitle>
            <DialogDescription>Actualiza el nombre, país y coordenadas de la zona operativa.</DialogDescription>
          </DialogHeader>
          {editCity && (
            <div className="space-y-3">
              <div>
                <Label className="text-xs">Nombre</Label>
                <Input data-testid="city-edit-name" value={editCity.name}
                  onChange={(e) => setEditCity({ ...editCity, name: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">País</Label>
                <select data-testid="city-edit-country" value={editCity.country}
                  onChange={(e) => setEditCity({ ...editCity, country: e.target.value })}
                  className="w-full h-10 rounded-md border border-gray-200 bg-white px-3 text-sm">
                  <option value="ES">🇪🇸 España</option>
                  <option value="MA">🇲🇦 Marruecos</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Latitud</Label>
                  <Input data-testid="city-edit-lat" type="number" step="any" value={editCity.lat}
                    onChange={(e) => setEditCity({ ...editCity, lat: e.target.value })} />
                </div>
                <div>
                  <Label className="text-xs">Longitud</Label>
                  <Input data-testid="city-edit-lng" type="number" step="any" value={editCity.lng}
                    onChange={(e) => setEditCity({ ...editCity, lng: e.target.value })} />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditCity(null)}>Cancelar</Button>
            <Button data-testid="city-edit-save" onClick={handleUpdate} disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-700">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmación de borrado */}
      <AlertDialog open={!!deleteCity} onOpenChange={(o) => { if (!o) setDeleteCity(null); }}>
        <AlertDialogContent data-testid="city-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar ciudad</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteCity ? `¿Seguro que quieres eliminar "${deleteCity.name}"? Esta acción no se puede deshacer.` : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction data-testid="city-delete-confirm" onClick={handleDelete} disabled={deleting}
              className="bg-red-600 hover:bg-red-500">
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
};

export default CityManager;

import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, Plane, Ship, Hotel, Save, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

export default function AffiliateSettings() {
  const navigate = useNavigate();
  const { user, token, API } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    flights_url: '',
    flights_provider: 'Skyscanner',
    ferries_url: '',
    ferries_provider: 'Direct Ferries',
    hotels_url: '',
    hotels_provider: 'Booking.com'
  });

  useEffect(() => {
    if (user && user.role === 'business') {
      fetchAffiliateLinks();
    }
  }, [user]);

  const fetchAffiliateLinks = async () => {
    try {
      const response = await axios.get(`${API}/affiliate-links`);
      setFormData({
        flights_url: response.data.flights_url || '',
        flights_provider: response.data.flights_provider || 'Skyscanner',
        ferries_url: response.data.ferries_url || '',
        ferries_provider: response.data.ferries_provider || 'Direct Ferries',
        hotels_url: response.data.hotels_url || '',
        hotels_provider: response.data.hotels_provider || 'Booking.com'
      });
    } catch (error) {
      console.error('Error fetching affiliate links:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await axios.put(`${API}/affiliate-links`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Enlaces de afiliado actualizados correctamente');
    } catch (error) {
      console.error('Error saving affiliate links:', error);
      toast.error('Error al guardar los enlaces');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!user || user.role !== 'business') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Acceso solo para cuentas de negocio</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      {/* Header */}
      <header className="glass sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Button onClick={() => navigate('/dashboard')} variant="ghost">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver al Dashboard
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Configuración de Afiliados</h1>
          <div className="w-32"></div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Info Banner */}
        <Card className="mb-8 border-emerald-200 bg-emerald-50">
          <CardContent className="p-6">
            <h3 className="text-lg font-bold text-emerald-900 mb-2">ℹ️ Cómo obtener tus enlaces de afiliado</h3>
            <div className="space-y-2 text-sm text-emerald-800">
              <p>1. <strong>Regístrate</strong> en los programas de afiliados de cada proveedor</p>
              <p>2. <strong>Obtén tu enlace único</strong> con tu ID de afiliado</p>
              <p>3. <strong>Pega los enlaces aquí</strong> y guarda los cambios</p>
              <p>4. Los clientes verán estos enlaces en la sección de Viajes</p>
              <p className="mt-3 text-emerald-900 font-semibold">💰 Ganarás comisión automáticamente cuando los clientes reserven a través de tus enlaces</p>
            </div>
          </CardContent>
        </Card>

        <form onSubmit={handleSave} className="space-y-6">
          {/* Flights */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plane className="w-5 h-5 text-blue-600" />
                Vuelos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="flights_provider">Proveedor</Label>
                <Input
                  id="flights_provider"
                  value={formData.flights_provider}
                  onChange={(e) => handleChange('flights_provider', e.target.value)}
                  placeholder="ej: Skyscanner, Kiwi.com, Amadeus"
                />
              </div>
              <div>
                <Label htmlFor="flights_url">URL de Afiliado</Label>
                <Input
                  id="flights_url"
                  type="url"
                  value={formData.flights_url}
                  onChange={(e) => handleChange('flights_url', e.target.value)}
                  placeholder="https://www.skyscanner.com/?associateid=TU_ID"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Ejemplo: Skyscanner Affiliate Program, Kiwi.com Partners
                </p>
              </div>
              {formData.flights_url && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(formData.flights_url, '_blank')}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Probar enlace
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Ferries */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Ship className="w-5 h-5 text-teal-600" />
                Ferries
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="ferries_provider">Proveedor</Label>
                <Input
                  id="ferries_provider"
                  value={formData.ferries_provider}
                  onChange={(e) => handleChange('ferries_provider', e.target.value)}
                  placeholder="ej: Direct Ferries, FerryHopper"
                />
              </div>
              <div>
                <Label htmlFor="ferries_url">URL de Afiliado</Label>
                <Input
                  id="ferries_url"
                  type="url"
                  value={formData.ferries_url}
                  onChange={(e) => handleChange('ferries_url', e.target.value)}
                  placeholder="https://www.directferries.com/?affiliate=TU_ID"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Ejemplo: Direct Ferries Affiliate Program
                </p>
              </div>
              {formData.ferries_url && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(formData.ferries_url, '_blank')}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Probar enlace
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Hotels */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Hotel className="w-5 h-5 text-purple-600" />
                Hoteles
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="hotels_provider">Proveedor</Label>
                <Input
                  id="hotels_provider"
                  value={formData.hotels_provider}
                  onChange={(e) => handleChange('hotels_provider', e.target.value)}
                  placeholder="ej: Booking.com, Expedia, Hotels.com"
                />
              </div>
              <div>
                <Label htmlFor="hotels_url">URL de Afiliado</Label>
                <Input
                  id="hotels_url"
                  type="url"
                  value={formData.hotels_url}
                  onChange={(e) => handleChange('hotels_url', e.target.value)}
                  placeholder="https://www.booking.com/?aid=TU_ID"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Ejemplo: Booking.com Affiliate Partner Program, Expedia Affiliate Network
                </p>
              </div>
              {formData.hotels_url && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(formData.hotels_url, '_blank')}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Probar enlace
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Save Button */}
          <Button
            type="submit"
            disabled={saving}
            className="w-full bg-emerald-600 hover:bg-emerald-700 py-6 text-lg"
          >
            {saving ? 'Guardando...' : (
              <>
                <Save className="w-5 h-5 mr-2" />
                Guardar Configuración
              </>
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}

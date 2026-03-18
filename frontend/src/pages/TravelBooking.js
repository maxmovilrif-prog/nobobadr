import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Plane, Ship, Hotel, ExternalLink, Globe } from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';
import { toast } from 'sonner';

export default function TravelBooking() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { API } = useContext(AuthContext);
  const [affiliateLinks, setAffiliateLinks] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAffiliateLinks();
  }, []);

  const fetchAffiliateLinks = async () => {
    try {
      const response = await axios.get(`${API}/affiliate-links`);
      setAffiliateLinks(response.data);
    } catch (error) {
      console.error('Error fetching affiliate links:', error);
      toast.error('Error al cargar enlaces de reserva');
    } finally {
      setLoading(false);
    }
  };

  const handleBooking = (url, type) => {
    if (!url) {
      toast.error(`Enlaces de ${type} no configurados aún`);
      return;
    }
    window.open(url, '_blank');
  };

  const services = [
    {
      id: 'flights',
      icon: <Plane className="w-16 h-16 text-blue-600" />,
      title: 'Vuelos',
      titleEn: 'Flights',
      description: 'Encuentra los mejores vuelos para tu destino en España',
      descriptionEn: 'Find the best flights to your destination in Spain',
      gradient: 'from-blue-400 to-cyan-500',
      provider: affiliateLinks?.flights_provider,
      url: affiliateLinks?.flights_url,
      benefits: ['Comparamos precios', 'Mejores aerolíneas', 'Vuelos directos y con escalas']
    },
    {
      id: 'ferries',
      icon: <Ship className="w-16 h-16 text-teal-600" />,
      title: 'Ferries',
      titleEn: 'Ferries',
      description: 'Reserva ferries en España',
      descriptionEn: 'Book ferries in Spain',
      gradient: 'from-teal-400 to-emerald-500',
      provider: affiliateLinks?.ferries_provider,
      url: affiliateLinks?.ferries_url,
      benefits: ['Rutas directas', 'Precio garantizado', 'Vehículos permitidos']
    },
    {
      id: 'hotels',
      icon: <Hotel className="w-16 h-16 text-purple-600" />,
      title: 'Hoteles',
      titleEn: 'Hotels',
      description: 'Reserva hoteles en España al mejor precio',
      descriptionEn: 'Book hotels in Spain at the best price',
      gradient: 'from-purple-400 to-pink-500',
      provider: affiliateLinks?.hotels_provider,
      url: affiliateLinks?.hotels_url,
      benefits: ['Miles de hoteles', 'Cancelación gratis', 'Mejor precio garantizado']
    }
  ];

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
          <div className="flex items-center gap-3">
            <Button onClick={() => navigate(-1)} variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Volver
            </Button>
            <div className="flex items-center gap-2">
              <Globe className="w-6 h-6 text-emerald-600" />
              <h1 className="text-2xl font-bold text-gray-900">Reservas de Viaje</h1>
            </div>
          </div>
          <LanguageSelector variant="outline" />
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Viaja por <span className="bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">Europa y África</span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Encuentra las mejores ofertas en vuelos, ferries y hoteles. Reserva de forma segura con nuestros socios de confianza.
          </p>
        </div>

        {/* Services Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {services.map((service) => (
            <Card key={service.id} className="hover-lift border-0 shadow-xl overflow-hidden">
              <div className={`h-32 bg-gradient-to-br ${service.gradient} flex items-center justify-center`}>
                {service.icon}
              </div>
              <CardHeader>
                <CardTitle className="text-2xl">{service.title}</CardTitle>
                {service.provider && (
                  <p className="text-sm text-gray-500">Powered by {service.provider}</p>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-gray-600">{service.description}</p>
                
                <ul className="space-y-2">
                  {service.benefits.map((benefit, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm text-gray-600">
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                      {benefit}
                    </li>
                  ))}
                </ul>

                <Button
                  onClick={() => handleBooking(service.url, service.title)}
                  className={`w-full bg-gradient-to-r ${service.gradient} hover:opacity-90 text-white`}
                  disabled={!service.url}
                >
                  {service.url ? (
                    <>
                      Buscar {service.title}
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </>
                  ) : (
                    'Próximamente'
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Info Banner */}
        <Card className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white border-0">
          <CardContent className="p-8">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                <Globe className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">¿Cómo funciona?</h3>
                <p className="text-white/90 mb-4">
                  Al hacer clic en cualquier servicio, serás redirigido a nuestro socio de confianza donde podrás completar tu reserva de forma segura. 
                  Trabajamos con las mejores plataformas de viajes para ofrecerte los mejores precios y servicio.
                </p>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                  <div className="bg-white/10 rounded-lg p-3">
                    <p className="font-semibold mb-1">1. Selecciona</p>
                    <p className="text-white/80">Elige vuelo, ferry u hotel</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-3">
                    <p className="font-semibold mb-1">2. Busca</p>
                    <p className="text-white/80">Encuentra tu opción ideal</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-3">
                    <p className="font-semibold mb-1">3. Reserva</p>
                    <p className="text-white/80">Completa tu reserva segura</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Package, Truck, Store, Clock, Shield, MapPin } from 'lucide-react';
import Footer from '@/components/Footer';

export default function Landing() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Store className="w-8 h-8 text-emerald-600" />,
      title: 'Restaurantes y Tiendas',
      description: 'Pide de tus negocios favoritos en España, Europa y Marruecos'
    },
    {
      icon: <Package className="w-8 h-8 text-emerald-600" />,
      title: 'Entregas Express',
      description: 'Envía paquetes y documentos de forma rápida y segura'
    },
    {
      icon: <Clock className="w-8 h-8 text-emerald-600" />,
      title: 'Seguimiento en Tiempo Real',
      description: 'Sigue tu pedido desde que sale hasta que llega'
    },
    {
      icon: <Shield className="w-8 h-8 text-emerald-600" />,
      title: 'Pagos Seguros',
      description: 'Paga de forma segura con tarjeta o efectivo'
    },
    {
      icon: <Truck className="w-8 h-8 text-emerald-600" />,
      title: 'Repartidores Verificados',
      description: 'Todos nuestros repartidores están verificados'
    },
    {
      icon: <MapPin className="w-8 h-8 text-emerald-600" />,
      title: 'Cobertura Total',
      description: 'Servicio en España, Europa y Marruecos'
    }
  ];

  const categories = [
    { name: 'Restaurantes', emoji: '🍔', color: 'from-orange-400 to-red-500' },
    { name: 'Supermercados', emoji: '🛒', color: 'from-blue-400 to-cyan-500' },
    { name: 'Paquetería', emoji: '📦', color: 'from-purple-400 to-pink-500' }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
        {/* Decorative elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-emerald-200 rounded-full opacity-20 blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-cyan-200 rounded-full opacity-20 blur-3xl"></div>
        </div>

        {/* Navbar */}
        <nav className="relative z-10 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                <Truck className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900">Nubo</span>
            </div>
            <Button 
              data-testid="nav-login-btn"
              onClick={() => navigate('/auth')}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-6"
            >
              Iniciar Sesión
            </Button>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 py-20 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="animate-slide-up">
              <h1 className="text-5xl lg:text-7xl font-bold text-gray-900 mb-6 leading-tight">
                Todo lo que necesitas,
                <span className="bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent"> a tu puerta</span>
              </h1>
              <p className="text-lg lg:text-xl text-gray-600 mb-8">
                Pide comida, haz la compra o envía lo que necesites. En España, Europa y Marruecos, lo tienes todo al alcance de un click.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button 
                  data-testid="hero-cta-btn"
                  size="lg" 
                  onClick={() => navigate('/auth')}
                  className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white px-8 py-6 text-lg rounded-2xl shadow-lg hover:shadow-xl"
                >
                  Empezar Ahora
                </Button>
                <Button 
                  data-testid="partner-cta-btn"
                  size="lg" 
                  variant="outline"
                  onClick={() => navigate('/auth?role=business')}
                  className="border-2 border-emerald-600 text-emerald-700 hover:bg-emerald-50 px-8 py-6 text-lg rounded-2xl"
                >
                  Soy un Negocio
                </Button>
              </div>
            </div>
            <div className="animate-fade-in hidden lg:block">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-3xl blur-2xl opacity-20"></div>
                <div className="relative bg-white rounded-3xl p-8 shadow-2xl">
                  <div className="grid grid-cols-3 gap-4">
                    {categories.map((cat, idx) => (
                      <div key={idx} className="text-center hover-lift cursor-pointer">
                        <div className={`w-20 h-20 mx-auto mb-3 bg-gradient-to-br ${cat.color} rounded-2xl flex items-center justify-center text-3xl shadow-lg`}>
                          {cat.emoji}
                        </div>
                        <p className="text-sm font-medium text-gray-700">{cat.name}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">¿Por qué elegirnos?</h2>
            <p className="text-lg text-gray-600">Servicio rápido, seguro y confiable en España, Europa y Marruecos</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, idx) => (
              <Card key={idx} data-testid={`feature-card-${idx}`} className="hover-lift glass border-0 shadow-lg">
                <CardContent className="p-6">
                  <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
                  <p className="text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20 px-6 bg-gradient-to-br from-emerald-600 to-teal-700">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl lg:text-5xl font-bold text-white mb-6">¿Listo para empezar?</h2>
          <p className="text-xl text-emerald-50 mb-8">Únete a miles de usuarios en Algeciras</p>
          <Button 
            data-testid="footer-cta-btn"
            size="lg" 
            onClick={() => navigate('/auth')}
            className="bg-white text-emerald-700 hover:bg-gray-100 px-8 py-6 text-lg rounded-2xl shadow-xl"
          >
            Crear Cuenta Gratis
          </Button>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
}
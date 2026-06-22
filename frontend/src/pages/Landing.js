import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Package, Truck, Store, Clock, Shield, MapPin, User } from 'lucide-react';
import Footer from '@/components/Footer';
import LanguageSelector from '@/components/LanguageSelector';

export default function Landing() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const features = [
    {
      icon: <Store className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.restaurants.title'),
      description: t('landing.features.restaurants.description')
    },
    {
      icon: <Package className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.express.title'),
      description: t('landing.features.express.description')
    },
    {
      icon: <Clock className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.tracking.title'),
      description: t('landing.features.tracking.description')
    },
    {
      icon: <Shield className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.payments.title'),
      description: t('landing.features.payments.description')
    },
    {
      icon: <Truck className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.verified.title'),
      description: t('landing.features.verified.description')
    },
    {
      icon: <MapPin className="w-8 h-8 text-emerald-600" />,
      title: t('landing.features.coverage.title'),
      description: t('landing.features.coverage.description')
    }
  ];

  const categories = [
    { name: t('landing.services.restaurants'), emoji: '🍔', color: 'from-orange-400 to-red-500', path: '/auth' },
    { name: t('landing.services.supermarkets'), emoji: '🛒', color: 'from-blue-400 to-cyan-500', path: '/auth' },
    { name: t('landing.services.courier'), emoji: '📦', color: 'from-purple-400 to-pink-500', path: '/presupuesto' },
    { name: 'Nubo Car', emoji: '🚗', color: 'from-slate-800 to-slate-900', path: '/ride', img: 'https://static.prod-images.emergentagent.com/jobs/b2114274-550f-4f93-8612-a95098ea48da/images/6171a4cb06401b700892f39b880ec54b1e5d9ec3ebbe57e460b62c7400cad0c4.png' }  ];

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
              <span className="text-2xl font-bold text-gray-900">{t('landing.brand')}</span>
            </div>
            <div className="flex items-center gap-3">
              <LanguageSelector variant="outline" />
              <Button
                data-testid="nav-client-login-btn"
                variant="ghost"
                onClick={() => navigate('/auth')}
                className="text-gray-600 hover:text-emerald-700 hover:bg-emerald-50 px-3"
              >
                <User className="w-4 h-4 mr-1.5" />
                {t('landing.nav.customer_area')}
              </Button>
              <Button
                data-testid="nav-track-btn"
                variant="outline"
                onClick={() => navigate('/track')}
                className="border-emerald-600 text-emerald-700 hover:bg-emerald-50 px-5"
              >
                {t('landing.nav.track_order')}
              </Button>
              <Button
                data-testid="nav-quote-btn"
                onClick={() => navigate('/presupuesto')}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-6"
              >
                {t('landing.nav.calculate_price')}
              </Button>
            </div>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 py-20 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="animate-slide-up">
              <h1 className="text-5xl lg:text-7xl font-bold text-gray-900 mb-6 leading-tight">
                {t('landing.hero_title')}
                <span className="bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent"> {t('landing.hero_subtitle')}</span>
              </h1>
              <p className="text-lg lg:text-xl text-gray-600 mb-8">
                {t('landing.hero_description')}
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button 
                  data-testid="hero-cta-btn"
                  size="lg" 
                  onClick={() => navigate('/presupuesto')}
                  className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white px-8 py-6 text-lg rounded-2xl shadow-lg hover:shadow-xl"
                >
                  {t('landing.hero_cta_quote')}
                </Button>
                <Button 
                  data-testid="hero-track-btn"
                  size="lg" 
                  variant="outline"
                  onClick={() => navigate('/track')}
                  className="border-2 border-emerald-600 text-emerald-700 hover:bg-emerald-50 px-8 py-6 text-lg rounded-2xl"
                >
                  {t('landing.hero_cta_track')}
                </Button>
              </div>
            </div>
            <div className="animate-fade-in hidden lg:block">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-3xl blur-2xl opacity-20"></div>
                <div className="relative bg-white rounded-3xl p-8 shadow-2xl">
                  <div className="grid grid-cols-2 gap-4">
                    {categories.map((cat, idx) => (
                      <div
                        key={idx}
                        data-testid={`landing-service-${idx}`}
                        onClick={() => navigate(cat.path)}
                        className="text-center hover-lift cursor-pointer"
                      >
                        {cat.img ? (
                          <div className="w-20 h-20 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center overflow-hidden shadow-lg ring-1 ring-black/5">
                            <img src={cat.img} alt={cat.name} className="w-full h-full object-contain p-1.5" />
                          </div>
                        ) : (
                          <div className={`w-20 h-20 mx-auto mb-3 bg-gradient-to-br ${cat.color} rounded-2xl flex items-center justify-center text-3xl shadow-lg`}>
                            {cat.emoji}
                          </div>
                        )}
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
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">{t('landing.why_title')}</h2>
            <p className="text-lg text-gray-600">{t('landing.why_subtitle')}</p>
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
          <h2 className="text-4xl lg:text-5xl font-bold text-white mb-6">{t('landing.cta_ready_title')}</h2>
          <p className="text-xl text-emerald-50 mb-8">{t('landing.cta_ready_subtitle')}</p>
          <Button 
            data-testid="footer-cta-btn"
            size="lg" 
            onClick={() => navigate('/presupuesto')}
            className="bg-white text-emerald-700 hover:bg-gray-100 px-8 py-6 text-lg rounded-2xl shadow-xl"
          >
            {t('landing.hero_cta_quote')}
          </Button>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
}
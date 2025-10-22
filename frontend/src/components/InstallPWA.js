import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, X } from 'lucide-react';

export default function InstallPWA() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handler);

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setShowInstallPrompt(false);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) {
      return;
    }

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('✅ PWA instalada');
    }
    
    setDeferredPrompt(null);
    setShowInstallPrompt(false);
  };

  const handleDismiss = () => {
    setShowInstallPrompt(false);
  };

  if (!showInstallPrompt) {
    return null;
  }

  return (
    <div 
      data-testid="install-pwa-banner"
      className="fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-white border-2 border-emerald-500 rounded-2xl shadow-2xl p-4 z-50 animate-slide-up"
    >
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
        data-testid="dismiss-install-btn"
      >
        <X className="w-5 h-5" />
      </button>
      
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <Download className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-gray-900 mb-1">Instalar Nubo</h3>
          <p className="text-sm text-gray-600 mb-3">
            Instala la app en tu dispositivo para acceso rápido
          </p>
          <Button
            data-testid="install-pwa-btn"
            onClick={handleInstallClick}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
            size="sm"
          >
            <Download className="w-4 h-4 mr-2" />
            Instalar Ahora
          </Button>
        </div>
      </div>
    </div>
  );
}

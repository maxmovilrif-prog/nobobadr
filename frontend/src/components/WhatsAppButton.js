import React from 'react';
import { MessageCircle } from 'lucide-react';

export default function WhatsAppButton({ phoneNumber = '+34654243848' }) {
  const handleClick = () => {
    // Format phone number for WhatsApp (remove spaces and special characters)
    const formattedNumber = phoneNumber.replace(/\s+/g, '').replace(/[^0-9+]/g, '');
    const message = encodeURIComponent('Hola, necesito ayuda con Nubo');
    const whatsappUrl = `https://wa.me/${formattedNumber}?text=${message}`;
    window.open(whatsappUrl, '_blank');
  };

  return (
    <button
      onClick={handleClick}
      data-testid="whatsapp-button"
      className="fixed bottom-6 right-6 z-50 bg-green-500 hover:bg-green-600 text-white rounded-full p-4 shadow-2xl hover:scale-110 transition-all duration-300 flex items-center gap-3 group"
      aria-label="Contactar por WhatsApp"
    >
      <MessageCircle className="w-6 h-6" />
      <span className="hidden group-hover:inline-block font-medium pr-2 animate-fade-in">
        ¡Chatea con nosotros!
      </span>
      
      {/* Ping animation */}
      <span className="absolute top-0 right-0 -mt-1 -mr-1 flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
      </span>
    </button>
  );
}

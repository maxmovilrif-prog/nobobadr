import React from 'react';
import { Phone, Mail, MapPin, MessageCircle, Facebook, Instagram, Twitter } from 'lucide-react';

export default function Footer() {
  const phoneNumber = '+34 729 34 251';
  const email = 'contacto@nubo.com';
  const address = 'España, Europa y Marruecos';

  const handleWhatsApp = () => {
    const formattedNumber = phoneNumber.replace(/\s+/g, '');
    const message = encodeURIComponent('Hola, necesito información sobre Nubo');
    window.open(`https://wa.me/${formattedNumber}?text=${message}`, '_blank');
  };

  const handleCall = () => {
    window.location.href = `tel:${phoneNumber}`;
  };

  return (
    <footer className="bg-gradient-to-br from-gray-900 to-gray-800 text-white mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8">
          {/* About */}
          <div>
            <h3 className="text-xl font-bold mb-4 text-emerald-400">Nubo</h3>
            <p className="text-gray-300 text-sm">
              Tu marketplace en España, Europa y Marruecos. Comida, compras, paquetería, coches y electrónica.
            </p>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold mb-4 text-emerald-400">Contacto</h4>
            <div className="space-y-3">
              <button
                onClick={handleCall}
                className="flex items-center gap-2 text-sm text-gray-300 hover:text-emerald-400 transition-colors"
              >
                <Phone className="w-4 h-4" />
                {phoneNumber}
              </button>
              <a
                href={`mailto:${email}`}
                className="flex items-center gap-2 text-sm text-gray-300 hover:text-emerald-400 transition-colors"
              >
                <Mail className="w-4 h-4" />
                {email}
              </a>
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <MapPin className="w-4 h-4" />
                {address}
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold mb-4 text-emerald-400">Enlaces</h4>
            <ul className="space-y-2 text-sm text-gray-300">
              <li><a href="/" className="hover:text-emerald-400 transition-colors">Inicio</a></li>
              <li><a href="/auth" className="hover:text-emerald-400 transition-colors">Iniciar Sesión</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition-colors">Ayuda</a></li>
              <li><a href="#" className="hover:text-emerald-400 transition-colors">Términos y Condiciones</a></li>
            </ul>
          </div>

          {/* Social & WhatsApp */}
          <div>
            <h4 className="font-semibold mb-4 text-emerald-400">Síguenos</h4>
            <div className="flex gap-3 mb-4">
              <a href="#" className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center hover:bg-emerald-500 transition-colors">
                <Facebook className="w-5 h-5" />
              </a>
              <a href="#" className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center hover:bg-emerald-500 transition-colors">
                <Instagram className="w-5 h-5" />
              </a>
              <a href="#" className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center hover:bg-emerald-500 transition-colors">
                <Twitter className="w-5 h-5" />
              </a>
            </div>
            
            <button
              onClick={handleWhatsApp}
              className="w-full bg-green-500 hover:bg-green-600 text-white px-4 py-3 rounded-lg flex items-center justify-center gap-2 transition-colors font-medium"
            >
              <MessageCircle className="w-5 h-5" />
              Chatea con nosotros
            </button>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-700 mt-8 pt-6 text-center text-sm text-gray-400">
          <p>© 2025 Nubo Algeciras. Todos los derechos reservados.</p>
          <p className="mt-2">
            <span className="text-emerald-400">📱 WhatsApp:</span> {phoneNumber}
          </p>
        </div>
      </div>
    </footer>
  );
}

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Phone, Mail, MapPin, MessageCircle, Facebook, Instagram, Twitter, CreditCard } from 'lucide-react';
import LanguageSelector from './LanguageSelector';

export default function Footer() {
  const { t } = useTranslation();
  const phoneNumber = '+34 654 24 20 92';
  const email = 'exprenobo@hotmail.com';
  const address = t('landing.coverage');

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
        <div className="grid md:grid-cols-5 gap-8">
          {/* About */}
          <div className="md:col-span-2">
            <h3 className="text-xl font-bold mb-4 text-emerald-400">{t('footer.about')}</h3>
            <p className="text-gray-300 text-sm mb-4">
              {t('footer.about_text')}
            </p>
            {/* Payment Methods */}
            <div className="mt-4">
              <p className="text-xs text-gray-400 mb-2">{t('footer.payment_methods')}</p>
              <div className="flex gap-3 items-center">
                <div className="bg-white px-3 py-2 rounded">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/4/41/Visa_Logo.png" alt="Visa" className="h-5" />
                </div>
                <div className="bg-white px-3 py-2 rounded">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Mastercard-logo.svg" alt="Mastercard" className="h-5" />
                </div>
                <div className="flex items-center gap-1 bg-gray-700 px-3 py-2 rounded text-xs">
                  <CreditCard className="w-4 h-4" />
                  <span>+más</span>
                </div>
              </div>
            </div>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold mb-4 text-emerald-400">{t('footer.contact')}</h4>
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
            <h4 className="font-semibold mb-4 text-emerald-400">{t('footer.links')}</h4>
            <ul className="space-y-2 text-sm text-gray-300">
              <li><a href="/" className="hover:text-emerald-400 transition-colors">{t('footer.home')}</a></li>
              <li><a href="/auth" className="hover:text-emerald-400 transition-colors">{t('common.login')}</a></li>
              <li><a href="/privacy" className="hover:text-emerald-400 transition-colors">Privacidad</a></li>
              <li><a href="/terms" className="hover:text-emerald-400 transition-colors">{t('footer.terms')}</a></li>
            </ul>
          </div>

          {/* Social & Language */}
          <div>
            <h4 className="font-semibold mb-4 text-emerald-400">{t('footer.follow')}</h4>
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
              className="w-full bg-green-500 hover:bg-green-600 text-white px-4 py-3 rounded-lg flex items-center justify-center gap-2 transition-colors font-medium mb-4"
            >
              <MessageCircle className="w-5 h-5" />
              {t('footer.chat')}
            </button>

            {/* Language Selector */}
            <div className="w-full">
              <LanguageSelector variant="outline" />
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-700 mt-8 pt-6 text-center text-sm text-gray-400">
          <p>© 2025 {t('footer.about')} - {t('landing.coverage')}. {t('footer.rights')}.</p>
          <p className="mt-2">
            <span className="text-emerald-400">📱 {t('footer.whatsapp')}:</span> {phoneNumber}
          </p>
        </div>
      </div>
    </footer>
  );
}

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import translationES from './locales/es/translation.json';
import translationEN from './locales/en/translation.json';
import translationFR from './locales/fr/translation.json';
import translationNL from './locales/nl/translation.json';
import translationDE from './locales/de/translation.json';
import translationAR from './locales/ar/translation.json';
import translationPT from './locales/pt/translation.json';

const resources = {
  es: { translation: translationES },
  en: { translation: translationEN },
  fr: { translation: translationFR },
  nl: { translation: translationNL },
  de: { translation: translationDE },
  ar: { translation: translationAR },
  pt: { translation: translationPT }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'es',
    debug: false,
    interpolation: {
      escapeValue: false
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

// Aplica dirección RTL/LTR según el idioma (al cargar y al cambiar)
const RTL_LANGS = ['ar'];
const applyDir = (lng) => {
  const code = (lng || 'es').split('-')[0];
  document.documentElement.dir = RTL_LANGS.includes(code) ? 'rtl' : 'ltr';
  document.documentElement.lang = code;
};
applyDir(i18n.language);
i18n.on('languageChanged', applyDir);

export default i18n;

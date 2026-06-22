// Centraliza la detección de la clave de Google Maps.
// Si no hay clave válida (vacía o placeholder), los componentes muestran un fallback limpio
// en vez del error de Google "Esta página no cargó correctamente Google Maps".
export const MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || '';
export const MAPS_ENABLED = !!MAPS_API_KEY && MAPS_API_KEY !== 'YOUR_API_KEY_HERE';

// Referencia estable para evitar recargas del script (react-google-maps lo exige).
export const MAPS_LIBRARIES = ['places'];

// Config única y compartida del loader de Google Maps.
// region='MA' fuerza la vista geopolítica de Marruecos (mapa unificado, sin frontera
// discontinua ni etiqueta "Western Sahara"). language='es' para etiquetas en español.
export const MAPS_LOADER_OPTIONS = {
  id: 'google-map-script',
  googleMapsApiKey: MAPS_ENABLED ? MAPS_API_KEY : 'YOUR_API_KEY_HERE',
  region: 'MA',
  language: 'es',
  libraries: MAPS_LIBRARIES,
};

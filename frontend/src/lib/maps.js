// Centraliza la detección de la clave de Google Maps.
// Si no hay clave válida (vacía o placeholder), los componentes muestran un fallback limpio
// en vez del error de Google "Esta página no cargó correctamente Google Maps".
export const MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || '';
export const MAPS_ENABLED = !!MAPS_API_KEY && MAPS_API_KEY !== 'YOUR_API_KEY_HERE';

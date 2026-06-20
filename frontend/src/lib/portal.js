// Detecta el "portal" según el subdominio del host.
// - director.noboexpress.com   -> Panel del Fundador / Director General
// - delegacion.noboexpress.com -> Panel de Delegaciones (Gestores Regionales)
// - cualquier otro (noboexpress.com, preview, localhost) -> App de Clientes (web pública)
export function getPortal() {
  const host = (typeof window !== 'undefined' ? window.location.hostname : '').toLowerCase();
  if (host.startsWith('director.')) return 'founder';
  if (host.startsWith('delegacion.')) return 'delegacion';
  return 'client';
}

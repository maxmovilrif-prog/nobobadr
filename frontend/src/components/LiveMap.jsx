import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";
import { MapPin, Bike } from "lucide-react";

const DEFAULT_CENTER = { lat: 35.7595, lng: -5.834 }; // Tánger
const apiKey = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

export default function LiveMap({ riders = [], orders = [] }) {
  const located = riders.filter((r) => r.location && r.location.lat != null);

  if (!apiKey) {
    return (
      <div
        data-testid="livemap-fallback"
        className="flex h-[420px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 text-center"
      >
        <MapPin className="h-8 w-8 text-slate-400" />
        <p className="mt-2 text-sm font-medium text-slate-600">Mapa en vivo (modo desarrollo)</p>
        <p className="mt-1 max-w-xs text-xs text-slate-400">
          Añade <code className="rounded bg-slate-200 px-1">REACT_APP_GOOGLE_MAPS_API_KEY</code> en el
          .env del frontend para activar Google Maps.
        </p>
        <div className="mt-4 w-full max-w-sm space-y-1.5 px-6">
          {located.length === 0 && (
            <p className="text-xs text-slate-400">Sin ubicaciones de repartidores aún.</p>
          )}
          {located.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-xs shadow-sm"
            >
              <span className="flex items-center gap-1.5 font-medium text-slate-700">
                <Bike className="h-3.5 w-3.5 text-indigo-500" /> {r.name}
              </span>
              <span className="text-slate-400">
                {r.location.lat.toFixed(4)}, {r.location.lng.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const center = located[0]
    ? { lat: located[0].location.lat, lng: located[0].location.lng }
    : DEFAULT_CENTER;

  return (
    <div className="h-[420px] overflow-hidden rounded-2xl border border-slate-200">
      <APIProvider apiKey={apiKey}>
        <Map
          style={{ width: "100%", height: "100%" }}
          defaultCenter={center}
          defaultZoom={12}
          mapId="nuboexpress-map"
          gestureHandling="greedy"
          disableDefaultUI={false}
          mapTypeControl={false}
          streetViewControl={false}
          fullscreenControl={false}
        >
          {located.map((r) => (
            <AdvancedMarker key={r.id} position={{ lat: r.location.lat, lng: r.location.lng }}>
              <div className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-indigo-600 shadow-lg">
                <Bike className="h-4 w-4 text-white" />
              </div>
            </AdvancedMarker>
          ))}
          {orders
            .filter((o) => o.dropoff && o.dropoff.lat != null && o.status !== "delivered")
            .map((o) => (
              <AdvancedMarker key={o.id} position={{ lat: o.dropoff.lat, lng: o.dropoff.lng }}>
                <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-rose-500 shadow-lg">
                  <MapPin className="h-3.5 w-3.5 text-white" />
                </div>
              </AdvancedMarker>
            ))}
        </Map>
      </APIProvider>
    </div>
  );
}

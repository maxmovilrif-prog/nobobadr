import React from 'react';
import { GoogleMap, Marker, useJsApiLoader, DirectionsRenderer } from '@react-google-maps/api';
import { MAPS_ENABLED, MAPS_API_KEY } from '@/lib/maps';

const containerStyle = {
  width: '100%',
  height: '400px',
  borderRadius: '12px'
};

const defaultCenter = {
  lat: 36.1408, // Algeciras coordinates
  lng: -5.4534
};

const Fallback = () => (
  <div className="w-full h-[400px] bg-gradient-to-br from-slate-50 to-emerald-50 rounded-xl flex items-center justify-center">
    <div className="text-center p-6">
      <p className="text-gray-700 font-semibold mb-1">Mapa en vivo próximamente</p>
      <p className="text-sm text-gray-500">El mapa estará disponible al activar la clave de Google Maps. Los datos sí se muestran.</p>
    </div>
  </div>
);

export default function MapComponent(props) {
  // Si no hay clave válida, ni siquiera montamos el loader de Google (evita el warning InvalidKey)
  if (!MAPS_ENABLED) return <Fallback />;
  return <MapInner {...props} />;
}

function MapInner({ 
  markers = [], 
  showDirections = false, 
  origin = null, 
  destination = null,
  center = defaultCenter,
  zoom = 13
}) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: MAPS_API_KEY
  });

  const [map, setMap] = React.useState(null);
  const [directions, setDirections] = React.useState(null);

  const onLoad = React.useCallback(function callback(map) {
    setMap(map);
  }, []);

  const onUnmount = React.useCallback(function callback(map) {
    setMap(null);
  }, []);

  // Get directions when origin and destination are provided
  React.useEffect(() => {
    if (showDirections && origin && destination && isLoaded) {
      const directionsService = new window.google.maps.DirectionsService();
      
      directionsService.route(
        {
          origin: origin,
          destination: destination,
          travelMode: window.google.maps.TravelMode.DRIVING,
        },
        (result, status) => {
          if (status === 'OK') {
            setDirections(result);
          } else {
            console.error('Error fetching directions:', status);
          }
        }
      );
    }
  }, [showDirections, origin, destination, isLoaded]);

  if (loadError) {
    return <Fallback />;
  }

  if (!isLoaded) {
    return (
      <div className="w-full h-[400px] bg-gray-100 rounded-xl flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={zoom}
      onLoad={onLoad}
      onUnmount={onUnmount}
      options={{
        zoomControl: true,
        streetViewControl: false,
        mapTypeControl: false,
        fullscreenControl: true,
      }}
    >
      {/* Display markers */}
      {markers.map((marker, index) => (
        <Marker
          key={index}
          position={{ lat: marker.lat, lng: marker.lng }}
          title={marker.title}
          icon={marker.icon}
        />
      ))}

      {/* Display directions */}
      {directions && <DirectionsRenderer directions={directions} />}
    </GoogleMap>
  );
}
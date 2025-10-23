import React from 'react';
import { GoogleMap, Marker, useJsApiLoader, DirectionsRenderer } from '@react-google-maps/api';

const containerStyle = {
  width: '100%',
  height: '400px',
  borderRadius: '12px'
};

const defaultCenter = {
  lat: 36.1408, // Algeciras coordinates
  lng: -5.4534
};

export default function MapComponent({ 
  markers = [], 
  showDirections = false, 
  origin = null, 
  destination = null,
  center = defaultCenter,
  zoom = 13
}) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE'
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
    return (
      <div className="w-full h-[400px] bg-gray-100 rounded-xl flex items-center justify-center">
        <div className="text-center p-6">
          <p className="text-red-600 font-semibold mb-2">Error al cargar el mapa</p>
          <p className="text-sm text-gray-600">Por favor, verifica tu conexión a internet</p>
        </div>
      </div>
    );
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
import React, { useState, useEffect } from 'react';
import { GoogleMap, DirectionsRenderer, Marker, useJsApiLoader } from '@react-google-maps/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { MapPin, Navigation, Clock, TrendingUp } from 'lucide-react';

const containerStyle = {
  width: '100%',
  height: '400px',
  borderRadius: '12px'
};

const defaultCenter = {
  lat: 36.1408, // Algeciras
  lng: -5.4534
};

export default function RouteSelector({ 
  onRouteCalculated, 
  origin: initialOrigin,
  destination: initialDestination,
  servicePrice = 1.5 // Precio por km
}) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE',
    libraries: ['places']
  });

  const [origin, setOrigin] = useState(initialOrigin || '');
  const [destination, setDestination] = useState(initialDestination || '');
  const [directions, setDirections] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [map, setMap] = useState(null);
  const [calculating, setCalculating] = useState(false);

  useEffect(() => {
    if (initialOrigin) setOrigin(initialOrigin);
    if (initialDestination) setDestination(initialDestination);
  }, [initialOrigin, initialDestination]);

  const calculateRoute = async () => {
    if (!origin || !destination || !isLoaded) {
      return;
    }

    setCalculating(true);
    
    try {
      const directionsService = new window.google.maps.DirectionsService();
      
      const result = await directionsService.route({
        origin: origin,
        destination: destination,
        travelMode: window.google.maps.TravelMode.DRIVING,
      });

      if (result.status === 'OK') {
        setDirections(result);
        
        const route = result.routes[0];
        const leg = route.legs[0];
        
        const info = {
          distance: leg.distance.text,
          distanceValue: leg.distance.value / 1000, // km
          duration: leg.duration.text,
          durationValue: leg.duration.value, // seconds
          startAddress: leg.start_address,
          endAddress: leg.end_address,
          estimatedCost: ((leg.distance.value / 1000) * servicePrice).toFixed(2)
        };
        
        setRouteInfo(info);
        
        if (onRouteCalculated) {
          onRouteCalculated(info);
        }
      }
    } catch (error) {
      console.error('Error calculating route:', error);
    } finally {
      setCalculating(false);
    }
  };

  const onLoad = React.useCallback(function callback(map) {
    setMap(map);
  }, []);

  if (!isLoaded) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando mapa...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="route-selector" className="border-0 shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Navigation className="w-5 h-5 text-emerald-600" />
          Selecciona tu Ruta
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Origin and Destination Inputs */}
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="origin" className="flex items-center gap-2 mb-2">
              <MapPin className="w-4 h-4 text-blue-600" />
              Origen
            </Label>
            <Input
              id="origin"
              data-testid="origin-input"
              placeholder="Dirección de origen"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && calculateRoute()}
            />
          </div>
          <div>
            <Label htmlFor="destination" className="flex items-center gap-2 mb-2">
              <MapPin className="w-4 h-4 text-red-600" />
              Destino
            </Label>
            <Input
              id="destination"
              data-testid="destination-input"
              placeholder="Dirección de destino"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && calculateRoute()}
            />
          </div>
        </div>

        <Button
          data-testid="calculate-route-btn"
          onClick={calculateRoute}
          disabled={!origin || !destination || calculating}
          className="w-full bg-emerald-600 hover:bg-emerald-700"
        >
          {calculating ? 'Calculando...' : (
            <>
              <Navigation className="w-4 h-4 mr-2" />
              Calcular Ruta
            </>
          )}
        </Button>

        {/* Map */}
        <div className="relative">
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={defaultCenter}
            zoom={13}
            onLoad={onLoad}
            options={{
              zoomControl: true,
              streetViewControl: false,
              mapTypeControl: false,
              fullscreenControl: true,
            }}
          >
            {directions && <DirectionsRenderer directions={directions} />}
          </GoogleMap>
        </div>

        {/* Route Information */}
        {routeInfo && (
          <div className="grid md:grid-cols-3 gap-4 mt-4">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <TrendingUp className="w-6 h-6 text-blue-600 mx-auto mb-2" />
              <p className="text-sm text-gray-600 mb-1">Distancia</p>
              <p className="text-2xl font-bold text-blue-900">{routeInfo.distance}</p>
            </div>
            
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <Clock className="w-6 h-6 text-purple-600 mx-auto mb-2" />
              <p className="text-sm text-gray-600 mb-1">Tiempo estimado</p>
              <p className="text-2xl font-bold text-purple-900">{routeInfo.duration}</p>
            </div>
            
            <div className="bg-emerald-50 rounded-lg p-4 text-center">
              <span className="text-3xl mb-2 block">💰</span>
              <p className="text-sm text-gray-600 mb-1">Precio estimado</p>
              <p className="text-2xl font-bold text-emerald-900">€{routeInfo.estimatedCost}</p>
            </div>
          </div>
        )}

        {routeInfo && (
          <div className="bg-gray-50 rounded-lg p-4 text-sm">
            <p className="mb-2">
              <span className="font-semibold text-blue-600">📍 Origen:</span> {routeInfo.startAddress}
            </p>
            <p>
              <span className="font-semibold text-red-600">🎯 Destino:</span> {routeInfo.endAddress}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

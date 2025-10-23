import React, { useState, useEffect } from 'react';
import MapComponent from './MapComponent';
import { MapPin, Navigation } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ALGECIRAS_CENTER = { lat: 36.1408, lng: -5.4534 };

export default function DeliveryMap({ order, deliveryAddress, businessAddress }) {
  const [markers, setMarkers] = useState([]);
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [showDirections, setShowDirections] = useState(false);

  useEffect(() => {
    // Parse addresses to coordinates (mock implementation)
    // In production, you would use Google Geocoding API
    const businessCoords = businessAddress || ALGECIRAS_CENTER;
    const deliveryCoords = deliveryAddress ? 
      { lat: ALGECIRAS_CENTER.lat + 0.01, lng: ALGECIRAS_CENTER.lng + 0.01 } : 
      ALGECIRAS_CENTER;

    setMarkers([
      {
        lat: businessCoords.lat || ALGECIRAS_CENTER.lat,
        lng: businessCoords.lng || ALGECIRAS_CENTER.lng,
        title: 'Punto de recogida',
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png'
        }
      },
      {
        lat: deliveryCoords.lat,
        lng: deliveryCoords.lng,
        title: 'Destino',
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'
        }
      }
    ]);

    // Set origin and destination for directions
    if (order && (order.status === 'in_transit' || order.status === 'accepted')) {
      setOrigin(businessCoords);
      setDestination(deliveryCoords);
      setShowDirections(true);
    }
  }, [order, deliveryAddress, businessAddress]);

  return (
    <Card data-testid="delivery-map" className="border-0 shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-emerald-600" />
          Mapa de Entrega
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MapComponent
          markers={markers}
          showDirections={showDirections}
          origin={origin}
          destination={destination}
          center={ALGECIRAS_CENTER}
          zoom={14}
        />
        
        {order && order.status === 'in_transit' && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg flex items-center gap-3">
            <Navigation className="w-5 h-5 text-blue-600 animate-pulse" />
            <div>
              <p className="font-semibold text-blue-900">En camino</p>
              <p className="text-sm text-blue-700">El repartidor está de camino a tu ubicación</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
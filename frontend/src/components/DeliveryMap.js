import React, { useState, useEffect, useRef } from 'react';
import MapComponent from './MapComponent';
import { MapPin, Navigation } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const SPAIN_CENTER = { lat: 40.4168, lng: -3.7038 }; // Madrid

export default function DeliveryMap({ order, deliveryAddress, businessAddress, driverLocation }) {
  const [markers, setMarkers] = useState([]);
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [showDirections, setShowDirections] = useState(false);
  const beeMarkerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    // Parse addresses to coordinates
    const businessCoords = businessAddress || SPAIN_CENTER;
    const deliveryCoords = deliveryAddress ? 
      { lat: SPAIN_CENTER.lat + 0.01, lng: SPAIN_CENTER.lng + 0.01 } : 
      SPAIN_CENTER;

    const baseMarkers = [
      {
        lat: businessCoords.lat || SPAIN_CENTER.lat,
        lng: businessCoords.lng || SPAIN_CENTER.lng,
        title: '🏪 Punto de recogida',
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png'
        }
      },
      {
        lat: deliveryCoords.lat,
        lng: deliveryCoords.lng,
        title: '🏠 Destino',
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'
        }
      }
    ];

    // Add driver location marker (the Bee 🐝)
    if (driverLocation && driverLocation.lat && driverLocation.lng) {
      baseMarkers.push({
        lat: driverLocation.lat,
        lng: driverLocation.lng,
        title: `🐝 ${driverLocation.driver_name || 'Conductor'}`,
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
          scaledSize: { width: 40, height: 40 }
        },
        animation: 'DROP'
      });
    }

    setMarkers(baseMarkers);

    // Set origin and destination for directions
    if (order && (order.status === 'in_transit' || order.status === 'accepted')) {
      setOrigin(businessCoords);
      setDestination(deliveryCoords);
      setShowDirections(true);
    }
  }, [order, deliveryAddress, businessAddress, driverLocation]);

  // Smooth animation for bee marker movement
  useEffect(() => {
    if (driverLocation && beeMarkerRef.current) {
      animateBeeMovement(beeMarkerRef.current, driverLocation);
    }
  }, [driverLocation]);

  const animateBeeMovement = (marker, newLocation) => {
    // Smooth transition using Google Maps animation
    if (window.google && window.google.maps) {
      const newPos = new window.google.maps.LatLng(newLocation.lat, newLocation.lng);
      marker.setPosition(newPos);
      marker.setAnimation(window.google.maps.Animation.BOUNCE);
      setTimeout(() => {
        marker.setAnimation(null);
      }, 1000);
    }
  };

  // Expose updateBeeLocation to window for external WebSocket calls
  useEffect(() => {
    window.updateBeeLocation = (lat, lng) => {
      console.log("🐝 Actualizando ubicación de la Abeja:", lat, lng);
      
      // Update markers with new bee position
      setMarkers(prevMarkers => {
        const updatedMarkers = prevMarkers.filter(m => m.title !== '🐝 Conductor');
        updatedMarkers.push({
          lat: lat,
          lng: lng,
          title: '🐝 Conductor',
          icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
            scaledSize: { width: 40, height: 40 }
          },
          animation: 'BOUNCE'
        });
        return updatedMarkers;
      });
    };

    return () => {
      delete window.updateBeeLocation;
    };
  }, []);

  return (
    <Card data-testid="delivery-map" className="border-0 shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-emerald-600" />
          Mapa de Entrega en Tiempo Real
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MapComponent
          markers={markers}
          showDirections={showDirections}
          origin={origin}
          destination={destination}
          center={driverLocation || SPAIN_CENTER}
          zoom={14}
          onMapLoad={(map) => { mapRef.current = map; }}
        />
        
        {order && order.status === 'in_transit' && (
          <div className="mt-4 space-y-2">
            {driverLocation ? (
              <div className="p-4 bg-emerald-50 rounded-lg flex items-center gap-3 border border-emerald-200">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <div className="flex-1">
                  <p className="font-semibold text-emerald-900 flex items-center gap-2">
                    🐝 Abeja en movimiento
                  </p>
                  <p className="text-sm text-emerald-700">
                    {driverLocation.driver_name || 'El conductor'} está de camino
                  </p>
                </div>
                <Navigation className="w-5 h-5 text-emerald-600" />
              </div>
            ) : (
              <div className="p-4 bg-blue-50 rounded-lg flex items-center gap-3">
                <Navigation className="w-5 h-5 text-blue-600 animate-pulse" />
                <div>
                  <p className="font-semibold text-blue-900">En camino</p>
                  <p className="text-sm text-blue-700">El repartidor está de camino a tu ubicación</p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Legend */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-xs font-semibold text-gray-600 mb-2">Leyenda:</p>
          <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span>Recogida</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <span>🐝 Conductor</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span>Destino</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

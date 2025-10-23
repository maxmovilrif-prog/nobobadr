import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Car, Fuel, Gauge, Calendar, MapPin } from 'lucide-react';

export default function VehicleCard({ vehicle, business, onViewDetails }) {
  // Parse vehicle details from description
  const details = vehicle.description.split('|').map(d => d.trim());
  
  return (
    <Card 
      data-testid={`vehicle-card-${vehicle.id}`}
      className="hover-lift cursor-pointer border-0 shadow-lg overflow-hidden"
      onClick={onViewDetails}
    >
      {/* Image */}
      <div className="aspect-video bg-gradient-to-br from-slate-800 to-slate-900 relative overflow-hidden">
        <img 
          src={vehicle.image_url} 
          alt={vehicle.name}
          className="w-full h-full object-cover hover:scale-110 transition-transform duration-500"
        />
        <div className="absolute top-3 right-3">
          <Badge className="bg-emerald-500 text-white font-bold px-3 py-1">
            {vehicle.category}
          </Badge>
        </div>
      </div>

      <CardContent className="p-5">
        {/* Vehicle Name */}
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          {vehicle.name}
        </h3>

        {/* Business Name */}
        <div className="flex items-center text-sm text-gray-600 mb-3">
          <MapPin className="w-4 h-4 mr-1" />
          {business?.name || 'Concesionario'}
        </div>

        {/* Vehicle Details */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {details.slice(0, 4).map((detail, idx) => (
            <div key={idx} className="flex items-center text-sm text-gray-700">
              {idx === 0 && <Fuel className="w-4 h-4 mr-1 text-emerald-600" />}
              {idx === 1 && <Gauge className="w-4 h-4 mr-1 text-emerald-600" />}
              {idx === 2 && <Car className="w-4 h-4 mr-1 text-emerald-600" />}
              {idx === 3 && <Calendar className="w-4 h-4 mr-1 text-emerald-600" />}
              <span className="truncate">{detail}</span>
            </div>
          ))}
        </div>

        {/* Price */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div>
            <p className="text-3xl font-bold text-emerald-600">
              €{vehicle.price.toLocaleString('es-ES')}
            </p>
            <p className="text-xs text-gray-500">Precio final</p>
          </div>
          <Button 
            data-testid={`view-vehicle-${vehicle.id}`}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            Ver detalles
          </Button>
        </div>

        {/* Financing hint */}
        <div className="mt-3 text-center">
          <p className="text-xs text-gray-500">
            Desde €{Math.round(vehicle.price / 60)}/mes con financiación
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

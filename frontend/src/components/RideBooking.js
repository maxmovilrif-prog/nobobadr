import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import RouteSelector from './RouteSelector';
import { Car, Users, Zap, Crown } from 'lucide-react';

export default function RideBooking({ 
  isOpen, 
  onClose, 
  services = [],
  businessName = '',
  onBookRide
}) {
  const [selectedService, setSelectedService] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [step, setStep] = useState(1); // 1: select service, 2: select route, 3: confirm

  const handleServiceSelect = (service) => {
    setSelectedService(service);
    setStep(2);
  };

  const handleRouteCalculated = (info) => {
    setRouteInfo(info);
  };

  const handleBooking = () => {
    if (onBookRide && selectedService && routeInfo) {
      onBookRide({
        service: selectedService,
        route: routeInfo,
        totalPrice: routeInfo.estimatedCost
      });
    }
    handleClose();
  };

  const handleClose = () => {
    setStep(1);
    setSelectedService(null);
    setRouteInfo(null);
    onClose();
  };

  const getServiceIcon = (category) => {
    if (category.includes('XL') || category.includes('Van')) return <Users className="w-5 h-5" />;
    if (category.includes('Lujo') || category.includes('Executive')) return <Crown className="w-5 h-5" />;
    if (category.includes('Moto')) return <Zap className="w-5 h-5" />;
    return <Car className="w-5 h-5" />;
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">
            {step === 1 && `${businessName} - Selecciona tu servicio`}
            {step === 2 && 'Indica tu ruta'}
            {step === 3 && 'Confirma tu viaje'}
          </DialogTitle>
        </DialogHeader>

        {/* Step 1: Service Selection */}
        {step === 1 && (
          <div className="grid md:grid-cols-2 gap-4">
            {services.map((service) => (
              <Card 
                key={service.id}
                data-testid={`service-${service.id}`}
                className="cursor-pointer hover-lift border-2 hover:border-emerald-500 transition-all"
                onClick={() => handleServiceSelect(service)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600">
                      {getServiceIcon(service.category)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-bold text-lg">{service.name}</h3>
                        <Badge className="bg-emerald-100 text-emerald-700">
                          {service.category}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{service.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-2xl font-bold text-emerald-600">
                          €{service.price.toFixed(2)}/km
                        </span>
                        <Button size="sm" className="bg-emerald-600">
                          Seleccionar
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Step 2: Route Selection */}
        {step === 2 && selectedService && (
          <div className="space-y-4">
            <div className="bg-emerald-50 rounded-lg p-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Servicio seleccionado:</p>
                <p className="font-bold text-lg">{selectedService.name}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">Precio base:</p>
                <p className="text-2xl font-bold text-emerald-600">€{selectedService.price}/km</p>
              </div>
            </div>

            <RouteSelector 
              onRouteCalculated={handleRouteCalculated}
              servicePrice={selectedService.price}
            />

            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={() => setStep(1)}
                className="flex-1"
              >
                Cambiar servicio
              </Button>
              {routeInfo && (
                <Button 
                  data-testid="confirm-booking-btn"
                  onClick={handleBooking}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  Confirmar y Pagar €{routeInfo.estimatedCost}
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

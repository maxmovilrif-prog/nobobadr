import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, SlidersHorizontal, X, Car } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

export default function VehicleFilters({ onFilterChange, onSearchChange }) {
  const [isOpen, setIsOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [priceRange, setPriceRange] = useState([0, 50000]);
  const [selectedBrand, setSelectedBrand] = useState('all');
  const [selectedFuel, setSelectedFuel] = useState('all');
  const [selectedType, setSelectedType] = useState('all');
  const [sortBy, setSortBy] = useState('name');

  const brands = ['Toyota', 'Seat', 'Volkswagen', 'BMW', 'Peugeot', 'Mercedes-Benz', 'Nissan', 'Jeep'];
  const fuelTypes = ['Híbrido', 'Gasolina', 'Diesel', 'Eléctrico'];
  const vehicleTypes = ['Deportivo', 'SUV', 'Urbano', 'Premium', '4x4'];

  const handleSearchChange = (value) => {
    setSearchTerm(value);
    onSearchChange(value);
  };

  const applyFilters = () => {
    const filters = {
      priceRange,
      brand: selectedBrand,
      fuel: selectedFuel,
      type: selectedType,
      sortBy
    };
    onFilterChange(filters);
  };

  const resetFilters = () => {
    setSearchTerm('');
    setPriceRange([0, 50000]);
    setSelectedBrand('all');
    setSelectedFuel('all');
    setSelectedType('all');
    setSortBy('name');
    onSearchChange('');
    onFilterChange({
      priceRange: [0, 50000],
      brand: 'all',
      fuel: 'all',
      type: 'all',
      sortBy: 'name'
    });
  };

  const activeFiltersCount = 
    (selectedBrand !== 'all' ? 1 : 0) +
    (selectedFuel !== 'all' ? 1 : 0) +
    (selectedType !== 'all' ? 1 : 0) +
    (priceRange[0] !== 0 || priceRange[1] !== 50000 ? 1 : 0);

  return (
    <div className="space-y-4 mb-6">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <Input
          data-testid="vehicle-search-input"
          type="text"
          placeholder="Buscar por marca, modelo..."
          value={searchTerm}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="pl-10 pr-4 py-6 text-lg border-2 focus:border-emerald-500"
        />
      </div>

      {/* Advanced Filters */}
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <Card className="border-2 border-emerald-100">
          <CardHeader>
            <CollapsibleTrigger asChild>
              <div className="flex items-center justify-between cursor-pointer">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <SlidersHorizontal className="w-5 h-5 text-emerald-600" />
                  Filtros Avanzados
                  {activeFiltersCount > 0 && (
                    <Badge className="bg-emerald-500">{activeFiltersCount}</Badge>
                  )}
                </CardTitle>
                <Button variant="ghost" size="sm">
                  {isOpen ? '−' : '+'}
                </Button>
              </div>
            </CollapsibleTrigger>
          </CardHeader>

          <CollapsibleContent>
            <CardContent className="space-y-6">
              {/* Price Range */}
              <div>
                <Label className="text-base font-semibold mb-3 block">
                  Rango de Precio
                </Label>
                <div className="px-2">
                  <Slider
                    data-testid="price-range-slider"
                    min={0}
                    max={50000}
                    step={1000}
                    value={priceRange}
                    onValueChange={setPriceRange}
                    className="mb-3"
                  />
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>€{priceRange[0].toLocaleString('es-ES')}</span>
                    <span>€{priceRange[1].toLocaleString('es-ES')}</span>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                {/* Brand Filter */}
                <div>
                  <Label htmlFor="brand-filter" className="text-base font-semibold mb-2 block">
                    Marca
                  </Label>
                  <Select value={selectedBrand} onValueChange={setSelectedBrand}>
                    <SelectTrigger data-testid="brand-filter">
                      <SelectValue placeholder="Todas las marcas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas las marcas</SelectItem>
                      {brands.map(brand => (
                        <SelectItem key={brand} value={brand}>{brand}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Fuel Type Filter */}
                <div>
                  <Label htmlFor="fuel-filter" className="text-base font-semibold mb-2 block">
                    Combustible
                  </Label>
                  <Select value={selectedFuel} onValueChange={setSelectedFuel}>
                    <SelectTrigger data-testid="fuel-filter">
                      <SelectValue placeholder="Todos" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {fuelTypes.map(fuel => (
                        <SelectItem key={fuel} value={fuel}>{fuel}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Vehicle Type Filter */}
                <div>
                  <Label htmlFor="type-filter" className="text-base font-semibold mb-2 block">
                    Tipo de Vehículo
                  </Label>
                  <Select value={selectedType} onValueChange={setSelectedType}>
                    <SelectTrigger data-testid="type-filter">
                      <SelectValue placeholder="Todos" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {vehicleTypes.map(type => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Sort By */}
                <div>
                  <Label htmlFor="sort-filter" className="text-base font-semibold mb-2 block">
                    Ordenar por
                  </Label>
                  <Select value={sortBy} onValueChange={setSortBy}>
                    <SelectTrigger data-testid="sort-filter">
                      <SelectValue placeholder="Ordenar" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="name">Nombre (A-Z)</SelectItem>
                      <SelectItem value="price-asc">Precio (Menor a Mayor)</SelectItem>
                      <SelectItem value="price-desc">Precio (Mayor a Menor)</SelectItem>
                      <SelectItem value="newest">Más Recientes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Active Filters */}
              {activeFiltersCount > 0 && (
                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  <span className="text-sm font-medium text-gray-600">Filtros activos:</span>
                  {selectedBrand !== 'all' && (
                    <Badge variant="secondary" className="cursor-pointer" onClick={() => setSelectedBrand('all')}>
                      {selectedBrand} <X className="w-3 h-3 ml-1" />
                    </Badge>
                  )}
                  {selectedFuel !== 'all' && (
                    <Badge variant="secondary" className="cursor-pointer" onClick={() => setSelectedFuel('all')}>
                      {selectedFuel} <X className="w-3 h-3 ml-1" />
                    </Badge>
                  )}
                  {selectedType !== 'all' && (
                    <Badge variant="secondary" className="cursor-pointer" onClick={() => setSelectedType('all')}>
                      {selectedType} <X className="w-3 h-3 ml-1" />
                    </Badge>
                  )}
                  {(priceRange[0] !== 0 || priceRange[1] !== 50000) && (
                    <Badge variant="secondary" className="cursor-pointer" onClick={() => setPriceRange([0, 50000])}>
                      €{priceRange[0].toLocaleString()} - €{priceRange[1].toLocaleString()} <X className="w-3 h-3 ml-1" />
                    </Badge>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3">
                <Button
                  data-testid="apply-filters-btn"
                  onClick={applyFilters}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  <Car className="w-4 h-4 mr-2" />
                  Aplicar Filtros
                </Button>
                <Button
                  data-testid="reset-filters-btn"
                  onClick={resetFilters}
                  variant="outline"
                >
                  <X className="w-4 h-4 mr-2" />
                  Limpiar
                </Button>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  );
}

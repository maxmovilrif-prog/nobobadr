import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, FileText, CreditCard, XCircle, Package } from 'lucide-react';
import Footer from '@/components/Footer';

export default function Terms() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      {/* Header */}
      <header className="glass sticky top-0 z-50 shadow-md bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Button onClick={() => navigate('/')} variant="ghost">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver al inicio
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Términos y Condiciones</h1>
          <div className="w-32"></div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-10 h-10 text-emerald-600" />
          </div>
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Términos y Condiciones
          </h2>
          <p className="text-lg text-gray-600">
            NUBO EXPRESS - Condiciones de Uso del Servicio
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Última actualización: {new Date().toLocaleDateString('es-ES')}
          </p>
        </div>

        {/* Content Cards */}
        <div className="space-y-6">
          {/* Section 1 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <Package className="w-5 h-5" />
                1. El Servicio
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                <strong>Nubo Express</strong> es una plataforma intermediaria que conecta:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Comercios:</strong> Restaurantes, supermercados, tiendas de electrónica, concesionarios y más</li>
                <li><strong>Repartidores independientes:</strong> Conductores autónomos que realizan las entregas</li>
                <li><strong>Clientes finales:</strong> Usuarios que realizan pedidos a través de la plataforma</li>
              </ul>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-blue-900">
                  <strong>Importante:</strong> Nubo Express actúa únicamente como intermediario. Los comercios son responsables de la calidad de sus productos y los repartidores de la entrega en buen estado.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 2 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <CreditCard className="w-5 h-5" />
                2. Pagos
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                Los pagos se realizan de forma segura a través de:
              </p>
              <div className="grid md:grid-cols-2 gap-4 mt-4">
                <div className="bg-gray-100 rounded-lg p-4">
                  <h4 className="font-semibold mb-2">💳 Pago Online</h4>
                  <ul className="text-sm space-y-1">
                    <li>• Tarjeta de crédito/débito</li>
                    <li>• Visa, Mastercard, AmEx</li>
                    <li>• Procesado por Stripe (seguro)</li>
                    <li>• Disponible en toda España</li>
                  </ul>
                </div>
                <div className="bg-gray-100 rounded-lg p-4">
                  <h4 className="font-semibold mb-2">💵 Pago en Efectivo</h4>
                  <ul className="text-sm space-y-1">
                    <li>• En el momento de la entrega</li>
                    <li>• Según disponibilidad en tu zona</li>
                    <li>• Verifica antes de pedir</li>
                    <li>• Prepara el importe exacto</li>
                  </ul>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-4">
                <strong>Nota:</strong> El pago incluye el precio del producto, gastos de envío y comisión de servicio. Todo está claramente desglosado antes de confirmar tu pedido.
              </p>
            </CardContent>
          </Card>

          {/* Section 3 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <XCircle className="w-5 h-5" />
                3. Cancelaciones y Devoluciones
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-emerald-800 mb-2">✅ Puedes cancelar:</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4 text-sm">
                    <li>Antes de que el comercio acepte tu pedido</li>
                    <li>Reembolso completo e inmediato</li>
                    <li>Sin penalizaciones</li>
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-red-800 mb-2">❌ No se admiten cancelaciones:</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4 text-sm">
                    <li>Una vez que el comercio está preparando tu pedido</li>
                    <li>Cuando el repartidor ya ha recogido el pedido</li>
                    <li>Para productos perecederos (comida, productos frescos)</li>
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-orange-800 mb-2">⚠️ Devoluciones especiales:</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4 text-sm">
                    <li>Productos defectuosos: Contacta al comercio en 24h</li>
                    <li>Error en el pedido: Reporta inmediatamente</li>
                    <li>Productos electrónicos: Aplica garantía del fabricante</li>
                    <li>Vehículos: Según condiciones del concesionario</li>
                  </ul>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-yellow-900">
                  <strong>📞 Soporte:</strong> Si tienes un problema con tu pedido, contáctanos inmediatamente en +34 654 23 25 73 o exprenobo@hotmail.com
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 4 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <FileText className="w-5 h-5" />
                4. Responsabilidades
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <div className="space-y-3">
                <div>
                  <p className="font-semibold mb-1">🏪 Comercios:</p>
                  <p className="text-sm">Responsables de la calidad, preparación y empaquetado de los productos.</p>
                </div>
                <div>
                  <p className="font-semibold mb-1">🚗 Repartidores:</p>
                  <p className="text-sm">Responsables de la entrega en tiempo y forma, manteniendo los productos en buen estado.</p>
                </div>
                <div>
                  <p className="font-semibold mb-1">📱 Nubo Express:</p>
                  <p className="text-sm">Responsable de la plataforma tecnológica, procesamiento de pagos y soporte al cliente.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 5 */}
          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6">
              <h3 className="font-bold text-emerald-900 mb-3">5. Uso Aceptable</h3>
              <p className="text-sm text-emerald-800 mb-2">
                Al usar Nubo Express, te comprometes a:
              </p>
              <ul className="text-sm text-emerald-800 list-disc list-inside space-y-1 ml-2">
                <li>Proporcionar información verídica</li>
                <li>No abusar del servicio de cancelaciones</li>
                <li>Tratar con respeto a repartidores y comercios</li>
                <li>No usar la plataforma para actividades ilegales</li>
                <li>Cumplir con las leyes locales aplicables</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6">
              <h3 className="font-bold text-emerald-900 mb-3">6. Modificaciones</h3>
              <p className="text-sm text-emerald-800">
                Nos reservamos el derecho de modificar estos términos en cualquier momento. Los cambios significativos serán notificados con 30 días de antelación.
              </p>
            </CardContent>
          </Card>

          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6">
              <h3 className="font-bold text-emerald-900 mb-3">7. Jurisdicción</h3>
              <p className="text-sm text-emerald-800">
                Estos términos se rigen por la legislación española. Cualquier disputa será resuelta en los tribunales de España.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <Button
            onClick={() => navigate('/')}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-6 text-lg"
          >
            Volver al Inicio
          </Button>
        </div>
      </div>

      <Footer />
    </div>
  );
}

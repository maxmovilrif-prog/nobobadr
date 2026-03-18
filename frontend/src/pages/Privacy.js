import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Shield, Lock, Eye, Mail } from 'lucide-react';
import Footer from '@/components/Footer';

export default function Privacy() {
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
          <h1 className="text-2xl font-bold text-gray-900">Política de Privacidad</h1>
          <div className="w-32"></div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-10 h-10 text-emerald-600" />
          </div>
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Política de Privacidad
          </h2>
          <p className="text-lg text-gray-600">
            NUBO EXPRESS - Tu privacidad es nuestra prioridad
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
                <Eye className="w-5 h-5" />
                1. Información que recopilamos
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                Recopilamos la siguiente información para facilitar nuestro servicio de reparto:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Datos personales:</strong> Nombre completo, número de teléfono y correo electrónico</li>
                <li><strong>Dirección de entrega:</strong> Para completar sus pedidos correctamente</li>
                <li><strong>Datos de ubicación en tiempo real:</strong> Para mostrar comercios cercanos y tracking de pedidos</li>
                <li><strong>Información de pago:</strong> Procesada de forma segura a través de Stripe</li>
                <li><strong>Historial de pedidos:</strong> Para mejorar su experiencia</li>
              </ul>
            </CardContent>
          </Card>

          {/* Section 2 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <Lock className="w-5 h-5" />
                2. Uso de la ubicación (GPS)
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                <strong>Nubo Express</strong> utiliza su ubicación para:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Mostrarle los <strong>comercios más cercanos</strong> a su ubicación actual</li>
                <li>Permitir el <strong>seguimiento en tiempo real</strong> de su pedido (la "Abeja" 🐝)</li>
                <li>Calcular tiempos de entrega estimados</li>
                <li>Optimizar rutas de reparto</li>
              </ul>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mt-4">
                <p className="text-sm font-semibold text-emerald-900">
                  ℹ️ Importante: Sus datos de ubicación solo se activan cuando la aplicación está en uso y nunca son compartidos con terceros con fines publicitarios.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 3 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <Shield className="w-5 h-5" />
                3. Seguridad de Datos
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                Sus datos están protegidos bajo la normativa europea <strong>GDPR</strong> (Reglamento General de Protección de Datos).
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Usamos <strong>encriptación SSL/TLS</strong> para todas las comunicaciones</li>
                <li>Las contraseñas se almacenan con <strong>hashing bcrypt</strong></li>
                <li>Los pagos son procesados por <strong>Stripe</strong> (PCI-DSS compliant)</li>
                <li><strong>No compartimos</strong> su información personal con terceros, excepto:</li>
                <ul className="list-disc list-inside ml-8 mt-2">
                  <li>Con repartidores para completar la entrega</li>
                  <li>Con comercios para preparar su pedido</li>
                  <li>Con procesadores de pago (Stripe)</li>
                </ul>
              </ul>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-blue-900">
                  <strong>Sus derechos GDPR:</strong> Acceso, rectificación, supresión, portabilidad y oposición al tratamiento de sus datos personales.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 4 */}
          <Card className="border-emerald-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-700">
                <Mail className="w-5 h-5" />
                4. Contacto y Derechos
              </CardTitle>
            </CardHeader>
            <CardContent className="text-gray-700 space-y-3">
              <p>
                Para ejercer sus derechos de privacidad o realizar cualquier consulta sobre el tratamiento de sus datos, puede contactarnos en:
              </p>
              <div className="bg-gray-100 rounded-lg p-4 mt-4">
                <p className="font-semibold text-gray-900 mb-2">Datos de contacto:</p>
                <p className="text-sm">📧 Email: <a href="mailto:exprenobo@hotmail.com" className="text-emerald-600 hover:underline">exprenobo@hotmail.com</a></p>
                <p className="text-sm">📱 Teléfono: +34 654 24 20 92</p>
                <p className="text-sm">📍 Servicio: España</p>
              </div>
              <p className="text-sm text-gray-600 mt-4">
                Nos comprometemos a responder a todas las solicitudes en un plazo máximo de 30 días.
              </p>
            </CardContent>
          </Card>

          {/* Additional Info */}
          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6">
              <h3 className="font-bold text-emerald-900 mb-3">5. Cookies y Tecnologías Similares</h3>
              <p className="text-sm text-emerald-800 mb-2">
                Utilizamos cookies esenciales para el funcionamiento de la plataforma y para mejorar su experiencia de usuario.
              </p>
              <ul className="text-sm text-emerald-800 list-disc list-inside space-y-1 ml-2">
                <li>Cookies de sesión (obligatorias)</li>
                <li>Cookies de preferencias (idioma, etc.)</li>
                <li>No usamos cookies de publicidad de terceros</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6">
              <h3 className="font-bold text-emerald-900 mb-3">6. Cambios en la Política</h3>
              <p className="text-sm text-emerald-800">
                Nos reservamos el derecho de actualizar esta política de privacidad. Los cambios serán notificados a través de la aplicación o por email.
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

import React, { useState, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { AuthContext } from '@/App';
import { Truck, ArrowLeft } from 'lucide-react';

export default function Auth() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, API } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    role: 'customer',
    vehicle_type: ''
  });

  // Extrae un mensaje de error claro y en español a partir de la respuesta del backend
  const getErrorMessage = (error, fallback) => {
    if (!error.response) {
      return 'No se pudo conectar con el servidor. Revisa tu conexión a internet.';
    }
    const detail = error.response.data?.detail;
    if (Array.isArray(detail)) {
      // Errores de validación de FastAPI (422)
      const first = detail[0];
      const field = first?.loc?.slice(-1)[0];
      if (field === 'email') return 'El email no es válido.';
      if (field === 'password') return 'La contraseña no cumple los requisitos.';
      return first?.msg || fallback;
    }
    if (typeof detail === 'string') {
      const map = {
        'Email already registered': 'Este email ya está registrado. Inicia sesión o usa otro email.',
        'Invalid credentials': 'Email o contraseña incorrectos.',
      };
      return map[detail] || detail;
    }
    return fallback;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, loginData);
      login(response.data.token, response.data.user);
      toast.success('¡Bienvenido!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Error al iniciar sesión'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/auth/register`, registerData);
      toast.success('Cuenta creada exitosamente');
      // Auto login
      const loginResponse = await axios.post(`${API}/auth/login`, {
        email: registerData.email,
        password: registerData.password
      });
      login(loginResponse.data.token, loginResponse.data.user);
      navigate('/dashboard');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Error al registrarse'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 py-12 px-4">
      <div className="max-w-md mx-auto">
        <Button
          data-testid="back-to-home-btn"
          variant="ghost"
          onClick={() => navigate('/')}
          className="mb-6"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver
        </Button>

        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
            <Truck className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Nubo</h1>
        </div>

        <Card className="shadow-2xl border-0">
          <CardHeader>
            <CardTitle className="text-2xl">Accede a tu cuenta</CardTitle>
            <CardDescription>Inicia sesión o crea una cuenta nueva</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger data-testid="login-tab" value="login">Iniciar Sesión</TabsTrigger>
                <TabsTrigger data-testid="register-tab" value="register">Registrarse</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form data-testid="login-form" onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email-input"
                      type="email"
                      placeholder="tu@email.com"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="login-password">Contraseña</Label>
                    <Input
                      id="login-password"
                      data-testid="login-password-input"
                      type="password"
                      placeholder="••••••••"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      required
                    />
                  </div>
                  <Button
                    data-testid="login-submit-btn"
                    type="submit"
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    disabled={loading}
                  >
                    {loading ? 'Cargando...' : 'Iniciar Sesión'}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form data-testid="register-form" onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <Label htmlFor="register-name">Nombre Completo</Label>
                    <Input
                      id="register-name"
                      data-testid="register-name-input"
                      placeholder="Juan Pérez"
                      value={registerData.name}
                      onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-email">Email</Label>
                    <Input
                      id="register-email"
                      data-testid="register-email-input"
                      type="email"
                      placeholder="tu@email.com"
                      value={registerData.email}
                      onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-phone">Teléfono</Label>
                    <Input
                      id="register-phone"
                      data-testid="register-phone-input"
                      placeholder="+34 600 123 456"
                      value={registerData.phone}
                      onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-password">Contraseña</Label>
                    <Input
                      id="register-password"
                      data-testid="register-password-input"
                      type="password"
                      placeholder="••••••••"
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-role">Tipo de Usuario</Label>
                    <Select
                      value={registerData.role}
                      onValueChange={(value) => setRegisterData({ ...registerData, role: value })}
                    >
                      <SelectTrigger data-testid="register-role-select">
                        <SelectValue placeholder="Selecciona tu rol" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem data-testid="role-customer" value="customer">Cliente</SelectItem>
                        <SelectItem data-testid="role-driver" value="driver">Repartidor</SelectItem>
                        <SelectItem data-testid="role-business" value="business">Negocio</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {registerData.role === 'driver' && (
                    <div>
                      <Label htmlFor="vehicle-type">Tipo de Vehículo</Label>
                      <Select
                        value={registerData.vehicle_type}
                        onValueChange={(value) => setRegisterData({ ...registerData, vehicle_type: value })}
                      >
                        <SelectTrigger data-testid="vehicle-type-select">
                          <SelectValue placeholder="Selecciona vehículo" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="bike">Bicicleta</SelectItem>
                          <SelectItem value="motorcycle">Moto</SelectItem>
                          <SelectItem value="car">Coche</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  <Button
                    data-testid="register-submit-btn"
                    type="submit"
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    disabled={loading}
                  >
                    {loading ? 'Creando cuenta...' : 'Crear Cuenta'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
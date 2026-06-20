import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'sonner';
import { AdminAuthContext } from '@/App';
import { ShieldCheck, Lock } from 'lucide-react';

export default function AdminLogin() {
  const navigate = useNavigate();
  const { adminLogin, API } = useContext(AdminAuthContext);
  const [loading, setLoading] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [data, setData] = useState({ email: '', password: '' });

  const handleForgot = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/auth/forgot-password`, { email: forgotEmail.trim().toLowerCase() });
      toast.success('Si el email pertenece a una cuenta de gestión, recibirás un enlace de recuperación.');
      setForgotMode(false);
    } catch (error) {
      toast.error('No se pudo procesar la solicitud');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, data);
      const role = response.data?.user?.role;
      if (role !== 'admin' && role !== 'manager') {
        toast.error('Acceso no autorizado');
        setLoading(false);
        return;
      }
      adminLogin(response.data.token, response.data.user);
      toast.success('Acceso concedido');
      navigate('/nubo-control');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Credenciales no válidas');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'radial-gradient(circle at 30% 20%, #0f2027, #18302b 60%, #0b1411)' }}
      data-testid="admin-login-page"
    >
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center mb-4">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Nubo Control</h1>
          <p className="text-sm text-emerald-300/70 mt-1">Acceso restringido · Panel de gestión</p>
        </div>

        <Card className="border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl">
          {forgotMode ? (
            <>
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2 text-lg">
                  <Lock className="w-4 h-4 text-emerald-400" /> Recuperar contraseña
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Te enviaremos un enlace de recuperación a tu email de gestión.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form data-testid="admin-forgot-form" onSubmit={handleForgot} className="space-y-4">
                  <div>
                    <Label htmlFor="forgot-email" className="text-gray-300">Email registrado</Label>
                    <Input
                      id="forgot-email"
                      data-testid="admin-forgot-email"
                      type="email"
                      placeholder="tu@email.com"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                      required
                    />
                  </div>
                  <Button data-testid="admin-forgot-submit" type="submit" disabled={loading}
                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white">
                    {loading ? 'Enviando...' : 'Enviar enlace de recuperación'}
                  </Button>
                  <button type="button" data-testid="admin-forgot-back" onClick={() => setForgotMode(false)}
                    className="w-full text-center text-sm text-gray-400 hover:text-emerald-400">
                    ← Volver a iniciar sesión
                  </button>
                </form>
              </CardContent>
            </>
          ) : (
            <>
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2 text-lg">
                  <Lock className="w-4 h-4 text-emerald-400" /> Iniciar sesión
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Introduce tus credenciales de administración.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form data-testid="admin-login-form" onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="admin-email" className="text-gray-300">Email</Label>
                    <Input
                      id="admin-email"
                      data-testid="admin-login-email"
                      type="email"
                      autoComplete="username"
                      placeholder="tu@email.com"
                      value={data.email}
                      onChange={(e) => setData({ ...data, email: e.target.value })}
                      className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="admin-password" className="text-gray-300">Contraseña</Label>
                    <Input
                      id="admin-password"
                      data-testid="admin-login-password"
                      type="password"
                      autoComplete="current-password"
                      placeholder="••••••••"
                      value={data.password}
                      onChange={(e) => setData({ ...data, password: e.target.value })}
                      className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                      required
                    />
                  </div>
                  <Button
                    data-testid="admin-login-submit"
                    type="submit"
                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                    disabled={loading}
                  >
                    {loading ? 'Verificando...' : 'Acceder'}
                  </Button>
                  <button type="button" data-testid="admin-forgot-link" onClick={() => setForgotMode(true)}
                    className="w-full text-center text-sm text-emerald-300/70 hover:text-emerald-400">
                    ¿Olvidaste tu contraseña?
                  </button>
                </form>
              </CardContent>
            </>
          )}
        </Card>

        <p className="text-center text-xs text-gray-600 mt-6">
          Zona privada de Nubo Express. El acceso queda registrado.
        </p>
      </div>
    </div>
  );
}

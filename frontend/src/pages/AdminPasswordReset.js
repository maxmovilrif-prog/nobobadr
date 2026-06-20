import React, { useState, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'sonner';
import { AdminAuthContext } from '@/App';
import { KeyRound, CheckCircle2, ArrowRight, Eye, EyeOff, AlertTriangle } from 'lucide-react';

export default function AdminPasswordReset() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const { API } = useContext(AdminAuthContext);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [data, setData] = useState({ new_password: '', confirm: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (data.new_password.length < 8) { toast.error('Mínimo 8 caracteres'); return; }
    if (data.new_password !== data.confirm) { toast.error('Las contraseñas no coinciden'); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/auth/reset-password`, { token, new_password: data.new_password });
      setDone(true);
      toast.success('Contraseña actualizada');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo restablecer la contraseña');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'radial-gradient(circle at 30% 20%, #0f2027, #18302b 60%, #0b1411)' }}
      data-testid="admin-pwreset-page"
    >
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center mb-4">
            <KeyRound className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Nueva contraseña</h1>
          <p className="text-sm text-emerald-300/70 mt-1">Recuperación de acceso · Nubo Control</p>
        </div>

        {!token ? (
          <Card className="border border-amber-400/20 bg-white/5 backdrop-blur-xl shadow-2xl">
            <CardContent className="p-6 text-center text-amber-200">
              <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-amber-400" />
              Enlace no válido. Solicita uno nuevo desde "¿Olvidaste tu contraseña?".
            </CardContent>
          </Card>
        ) : done ? (
          <Card className="border border-emerald-400/20 bg-white/5 backdrop-blur-xl shadow-2xl" data-testid="admin-pwreset-success">
            <CardContent className="p-6 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
              <p className="text-white font-semibold mb-6">Contraseña actualizada con éxito</p>
              <Button data-testid="pwreset-go-login" onClick={() => navigate('/nubo-control')} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white">
                Ir a iniciar sesión <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl">
            <CardHeader>
              <CardTitle className="text-white text-lg">Define tu nueva contraseña</CardTitle>
              <CardDescription className="text-gray-400">El enlace caduca en 1 hora.</CardDescription>
            </CardHeader>
            <CardContent>
              <form data-testid="admin-pwreset-form" onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="np" className="text-gray-300">Nueva contraseña</Label>
                  <div className="relative">
                    <Input id="np" data-testid="pwreset-password" type={showPass ? 'text' : 'password'} placeholder="Mínimo 8 caracteres"
                      value={data.new_password} onChange={(e) => setData({ ...data, new_password: e.target.value })}
                      className="bg-white/10 border-white/15 text-white placeholder:text-gray-500 pr-10" required />
                    <button type="button" data-testid="pwreset-toggle" onClick={() => setShowPass(!showPass)} tabIndex={-1}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-emerald-400">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <Label htmlFor="cf" className="text-gray-300">Repite la contraseña</Label>
                  <Input id="cf" data-testid="pwreset-confirm" type={showPass ? 'text' : 'password'} placeholder="••••••••"
                    value={data.confirm} onChange={(e) => setData({ ...data, confirm: e.target.value })}
                    className="bg-white/10 border-white/15 text-white placeholder:text-gray-500" required />
                </div>
                <Button data-testid="pwreset-submit" type="submit" disabled={loading} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white">
                  {loading ? 'Guardando...' : 'Restablecer contraseña'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

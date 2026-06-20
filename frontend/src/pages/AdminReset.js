import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'sonner';
import { AuthContext } from '@/App';
import { KeyRound, ShieldCheck, CheckCircle2, ArrowRight } from 'lucide-react';

export default function AdminReset() {
  const navigate = useNavigate();
  const { API } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(null);
  const [data, setData] = useState({ email: 'badarbox1756@gmail.com', new_password: '', confirm: '', secret: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (data.new_password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    if (data.new_password !== data.confirm) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    setLoading(true);
    try {
      const r = await axios.post(`${API}/admin/reset-password`, {
        email: data.email.trim().toLowerCase(),
        new_password: data.new_password,
        secret: data.secret,
      });
      setDone(r.data);
      toast.success(r.data.created ? 'Cuenta de Fundador creada' : 'Contraseña actualizada');
    } catch (error) {
      const code = error.response?.status;
      if (code === 403) toast.error('Secreto inválido (ADMIN_RESET_SECRET no coincide)');
      else if (code === 404) toast.error('Función desactivada: falta ADMIN_RESET_SECRET o redeploy');
      else toast.error(error.response?.data?.detail || 'No se pudo completar la operación');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'radial-gradient(circle at 30% 20%, #0f2027, #18302b 60%, #0b1411)' }}
      data-testid="admin-reset-page"
    >
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center mb-4">
            <KeyRound className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Provisionar Fundador</h1>
          <p className="text-sm text-emerald-300/70 mt-1">Crear o resetear acceso · Zona privada</p>
        </div>

        {done ? (
          <Card className="border border-emerald-400/20 bg-white/5 backdrop-blur-xl shadow-2xl" data-testid="admin-reset-success">
            <CardContent className="p-6 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
              <p className="text-white font-semibold mb-1">
                {done.created ? 'Cuenta de Fundador creada' : 'Contraseña actualizada'}
              </p>
              <p className="text-gray-400 text-sm mb-6">{done.email} · rol {done.role}</p>
              <Button
                data-testid="admin-reset-go-login"
                onClick={() => navigate('/nubo-control')}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
              >
                Ir a iniciar sesión <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <p className="text-xs text-amber-300/80 mt-4 flex items-start gap-1 text-left">
                <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
                Por seguridad, borra ahora la variable ADMIN_RESET_SECRET en producción y vuelve a desplegar.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl">
            <CardHeader>
              <CardTitle className="text-white text-lg">Datos de acceso</CardTitle>
              <CardDescription className="text-gray-400">
                Crea la cuenta de Fundador o resetea su contraseña.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form data-testid="admin-reset-form" onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="reset-email" className="text-gray-300">Email del Fundador</Label>
                  <Input
                    id="reset-email"
                    data-testid="admin-reset-email"
                    type="email"
                    value={data.email}
                    onChange={(e) => setData({ ...data, email: e.target.value })}
                    className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="reset-pass" className="text-gray-300">Nueva contraseña</Label>
                  <Input
                    id="reset-pass"
                    data-testid="admin-reset-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Mínimo 8 caracteres"
                    value={data.new_password}
                    onChange={(e) => setData({ ...data, new_password: e.target.value })}
                    className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="reset-confirm" className="text-gray-300">Repite la contraseña</Label>
                  <Input
                    id="reset-confirm"
                    data-testid="admin-reset-confirm"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={data.confirm}
                    onChange={(e) => setData({ ...data, confirm: e.target.value })}
                    className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="reset-secret" className="text-gray-300">Secreto de seguridad</Label>
                  <Input
                    id="reset-secret"
                    data-testid="admin-reset-secret"
                    type="password"
                    placeholder="ADMIN_RESET_SECRET"
                    value={data.secret}
                    onChange={(e) => setData({ ...data, secret: e.target.value })}
                    className="bg-white/10 border-white/15 text-white placeholder:text-gray-500"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">El mismo valor que definiste en los Secrets de producción.</p>
                </div>
                <Button
                  data-testid="admin-reset-submit"
                  type="submit"
                  className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                  disabled={loading}
                >
                  {loading ? 'Procesando...' : 'Crear / Resetear Fundador'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        <p className="text-center text-xs text-gray-600 mt-6">
          Zona privada de Nubo Express. El acceso queda registrado.
        </p>
      </div>
    </div>
  );
}

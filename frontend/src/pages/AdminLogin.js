import React, { useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { ShieldCheck, Loader2, KeyRound, Lock } from 'lucide-react';

// Adds a noindex/nofollow meta tag while this private page is mounted
function useNoIndex() {
  useEffect(() => {
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow, noarchive';
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);
}

export default function AdminLogin() {
  const navigate = useNavigate();
  const { login, API } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', secret_code: '' });
  useNoIndex();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post(`${API}/admin-auth/login`, {
        email: form.email.trim().toLowerCase(),
        password: form.password,
        secret_code: form.secret_code.trim(),
      });
      login(res.data.token, res.data.user);
      toast.success('Acceso concedido');
      navigate('/nubo-private-control-badr/panel');
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      if (status === 429) {
        toast.error(typeof detail === 'string' ? detail : 'Cuenta bloqueada temporalmente.');
      } else if (!error.response) {
        toast.error('No se pudo conectar con el servidor.');
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Acceso denegado.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0b0f14] px-4" data-testid="admin-login-page">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(16,185,129,0.10),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(16,185,129,0.08),transparent_40%)]" />
      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Centro de Control · Nubo</h1>
          <p className="text-sm text-gray-500 mt-1">Acceso restringido a administradores</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 bg-[#11161d] border border-white/5 rounded-2xl p-6 shadow-2xl" data-testid="admin-login-form">
          <div>
            <Label htmlFor="admin-email" className="text-gray-400 text-xs uppercase tracking-wider">Email</Label>
            <Input
              id="admin-email"
              data-testid="admin-email-input"
              type="email"
              autoComplete="off"
              placeholder="email@admin"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
              className="mt-1 bg-[#0b0f14] border-white/10 text-white placeholder:text-gray-600 focus-visible:ring-emerald-500/40"
            />
          </div>

          <div>
            <Label htmlFor="admin-password" className="text-gray-400 text-xs uppercase tracking-wider flex items-center gap-1">
              <Lock className="w-3 h-3" /> Contraseña
            </Label>
            <Input
              id="admin-password"
              data-testid="admin-password-input"
              type="password"
              autoComplete="off"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              className="mt-1 bg-[#0b0f14] border-white/10 text-white placeholder:text-gray-600 focus-visible:ring-emerald-500/40"
            />
          </div>

          <div>
            <Label htmlFor="admin-secret" className="text-gray-400 text-xs uppercase tracking-wider flex items-center gap-1">
              <KeyRound className="w-3 h-3" /> Código secreto
            </Label>
            <Input
              id="admin-secret"
              data-testid="admin-secret-input"
              type="password"
              autoComplete="off"
              placeholder="NUBO-XXXX-XXXX-XXXX"
              value={form.secret_code}
              onChange={(e) => setForm({ ...form, secret_code: e.target.value })}
              required
              className="mt-1 bg-[#0b0f14] border-white/10 text-white placeholder:text-gray-600 focus-visible:ring-emerald-500/40 font-mono"
            />
          </div>

          <Button
            type="submit"
            data-testid="admin-login-submit"
            disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4 mr-2" />}
            {loading ? '' : 'Acceder'}
          </Button>

          <p className="text-[11px] text-gray-600 text-center pt-2">
            Las sesiones se registran. El acceso no autorizado está prohibido.
          </p>
        </form>
      </div>
    </div>
  );
}

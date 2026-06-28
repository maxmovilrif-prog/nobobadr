import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import '@/App.css';
import Landing from '@/pages/Landing';
import Auth from '@/pages/Auth';
import CustomerDashboard from '@/pages/CustomerDashboard';
import DriverDashboard from '@/pages/DriverDashboard';
import BusinessDashboard from '@/pages/BusinessDashboard';
import AdminDashboard from '@/pages/AdminDashboard';
import AdminLogin from '@/pages/AdminLogin';
import AdminReset from '@/pages/AdminReset';
import AdminPasswordReset from '@/pages/AdminPasswordReset';
import CustomerPasswordReset from '@/pages/CustomerPasswordReset';
import { getPortal } from '@/lib/portal';
import DeliveryQuote from '@/pages/DeliveryQuote';
import NuboRide from '@/pages/NuboRide';
import QuoteConfirm from '@/pages/QuoteConfirm';
import RiderApp from '@/rider/RiderApp';
import PublicTracking from '@/pages/PublicTracking';
import OrderTracking from '@/pages/OrderTracking';
import OrderSuccess from '@/pages/OrderSuccess';
import DropshippingPanel from '@/pages/DropshippingPanel';
import TravelBooking from '@/pages/TravelBooking';
import FerrySearch from '@/pages/FerrySearch';
import AffiliateSettings from '@/pages/AffiliateSettings';
import Privacy from '@/pages/Privacy';
import Terms from '@/pages/Terms';
import InstallPWA from '@/components/InstallPWA';
import WhatsAppButton from '@/components/WhatsAppButton';
import { Toaster } from '@/components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext();
export const AdminAuthContext = React.createContext();

function App() {
  // --- Sesión de clientes / público (token compartido) ---
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // --- Sesión de administración (AISLADA, token propio) ---
  const [adminUser, setAdminUser] = useState(null);
  const [loadingAdmin, setLoadingAdmin] = useState(true);
  const [adminToken, setAdminToken] = useState(localStorage.getItem('nubo_admin_token'));

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoadingUser(false);
    }
  }, [token]);

  useEffect(() => {
    if (adminToken) {
      fetchAdmin();
    } else {
      setLoadingAdmin(false);
    }
  }, [adminToken]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      setToken(null);
    } finally {
      setLoadingUser(false);
    }
  };

  const fetchAdmin = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${adminToken}` }
      });
      const role = response.data?.role;
      if (role === 'admin' || role === 'manager') {
        setAdminUser(response.data);
      } else {
        localStorage.removeItem('nubo_admin_token');
        setAdminToken(null);
      }
    } catch (error) {
      localStorage.removeItem('nubo_admin_token');
      setAdminToken(null);
    } finally {
      setLoadingAdmin(false);
    }
  };

  const login = (newToken, userData) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const adminLogin = (newToken, userData) => {
    localStorage.setItem('nubo_admin_token', newToken);
    setAdminToken(newToken);
    setAdminUser(userData);
  };

  const adminLogout = () => {
    localStorage.removeItem('nubo_admin_token');
    setAdminToken(null);
    setAdminUser(null);
  };

  if (loadingUser || loadingAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  // Enrutado por subdominio: cada portal muestra solo su app.
  const portal = getPortal();
  const adminAllowed = adminUser && (adminUser.role === 'admin' || adminUser.role === 'manager');
  const rootElement = portal === 'client'
    ? <Landing />
    : (adminAllowed ? <AdminDashboard /> : <AdminLogin portal={portal} />);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, API }}>
    <AdminAuthContext.Provider value={{ adminUser, adminToken, adminLogin, adminLogout, API }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={rootElement} />
          <Route path="/auth" element={!user ? <Auth /> : <Navigate to="/dashboard" />} />
          <Route path="/recuperar" element={<CustomerPasswordReset />} />
          <Route path="/dashboard" element={
            user ? (
              user.role === 'customer' ? <CustomerDashboard /> :
              user.role === 'driver' ? <DriverDashboard /> :
              (user.role === 'admin' || user.role === 'manager') ? <Navigate to="/nubo-control" /> :
              <BusinessDashboard />
            ) : <Navigate to="/auth" />
          } />
          <Route path="/nubo-control" element={
            adminAllowed ? <AdminDashboard /> : <AdminLogin portal={portal} />
          } />
          <Route path="/nubo-control/reset" element={<AdminReset />} />
          <Route path="/nubo-control/recuperar" element={<AdminPasswordReset />} />
          <Route path="/admin" element={<Navigate to="/nubo-control" replace />} />
          <Route path="/presupuesto" element={<DeliveryQuote />} />
          <Route path="/confirmar-cotizacion/:orderId" element={<QuoteConfirm />} />
          <Route path="/ride" element={user && user.role === 'customer' ? <NuboRide /> : <Navigate to="/auth" />} />
          <Route path="/rider" element={<RiderApp />} />
          <Route path="/track" element={<PublicTracking />} />
          <Route path="/orders" element={user ? <CustomerDashboard /> : <Navigate to="/auth" />} />
          <Route path="/order-tracking/:orderId" element={user ? <OrderTracking /> : <Navigate to="/auth" />} />
          <Route path="/order-success" element={user ? <OrderSuccess /> : <Navigate to="/auth" />} />
          <Route path="/dropshipping-panel" element={user && user.role === 'business' ? <DropshippingPanel /> : <Navigate to="/auth" />} />
          <Route path="/travel" element={<TravelBooking />} />
          <Route path="/ferries" element={<FerrySearch />} />
          <Route path="/affiliate-settings" element={user && user.role === 'business' ? <AffiliateSettings /> : <Navigate to="/auth" />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/manager" element={<Navigate to="/nubo-control" replace />} />
          <Route path="/admin-panel" element={<Navigate to="/nubo-control" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <InstallPWA />
        <WhatsAppButton phoneNumber="+34612284215" />
        <Toaster position="top-right" />
      </BrowserRouter>
    </AdminAuthContext.Provider>
    </AuthContext.Provider>
  );
}

export default App;
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
import OrderTracking from '@/pages/OrderTracking';
import OrderSuccess from '@/pages/OrderSuccess';
import DropshippingPanel from '@/pages/DropshippingPanel';
import TravelBooking from '@/pages/TravelBooking';
import AffiliateSettings from '@/pages/AffiliateSettings';
import Privacy from '@/pages/Privacy';
import Terms from '@/pages/Terms';
import InstallPWA from '@/components/InstallPWA';
import WhatsAppButton from '@/components/WhatsAppButton';
import { Toaster } from '@/components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('token');
      setToken(null);
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, API }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={!user ? <Landing /> : <Navigate to={user.role === 'admin' ? '/nubo-private-control-badr/panel' : '/dashboard'} />} />
          <Route path="/auth" element={!user ? <Auth /> : <Navigate to={user.role === 'admin' ? '/nubo-private-control-badr/panel' : '/dashboard'} />} />
          <Route path="/dashboard" element={
            user ? (
              user.role === 'customer' ? <CustomerDashboard /> :
              user.role === 'driver' ? <DriverDashboard /> :
              user.role === 'admin' ? <Navigate to="/nubo-private-control-badr/panel" /> :
              <BusinessDashboard />
            ) : <Navigate to="/auth" />
          } />
          {/* Hidden, decoupled admin portal — secret URL */}
          <Route path="/nubo-private-control-badr" element={
            !user ? <AdminLogin /> :
            user.role === 'admin' ? <Navigate to="/nubo-private-control-badr/panel" /> :
            <Navigate to="/dashboard" />
          } />
          <Route path="/nubo-private-control-badr/panel" element={
            user && user.role === 'admin' ? <AdminDashboard /> :
            user ? <Navigate to="/dashboard" /> :
            <Navigate to="/nubo-private-control-badr" />
          } />
          {/* Old/guessable admin paths are hidden -> redirected to the public site */}
          <Route path="/admin" element={<Navigate to="/" />} />
          <Route path="/admin-nubo" element={<Navigate to="/" />} />
          <Route path="/admin-nubo/panel" element={<Navigate to="/" />} />
          <Route path="/orders" element={user ? <CustomerDashboard /> : <Navigate to="/auth" />} />
          <Route path="/order-tracking/:orderId" element={user ? <OrderTracking /> : <Navigate to="/auth" />} />
          <Route path="/order-success" element={user ? <OrderSuccess /> : <Navigate to="/auth" />} />
          <Route path="/dropshipping-panel" element={user && user.role === 'business' ? <DropshippingPanel /> : <Navigate to="/auth" />} />
          <Route path="/travel" element={<TravelBooking />} />
          <Route path="/affiliate-settings" element={user && user.role === 'business' ? <AffiliateSettings /> : <Navigate to="/auth" />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
        </Routes>
        <InstallPWA />
        <WhatsAppButton phoneNumber="+34654242092" />
        <Toaster position="top-right" />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
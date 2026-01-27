import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import InvestigationsPage from './pages/InvestigationsPage';
import InvestigationWorkspace from './pages/InvestigationWorkspace';
import EntitiesPage from './pages/EntitiesPage';
import GraphsPage from './pages/GraphsPage';
import type { User } from './types';
import apiService from './services/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Verificar si el usuario ya está autenticado al cargar la app
    const checkAuth = async () => {
      if (apiService.isAuthenticated()) {
        const storedUser = apiService.getStoredUser();
        if (storedUser) {
          setUser(storedUser);
          setIsAuthenticated(true);
        } else {
          // Verificar con el servidor si el token es válido
          try {
            const response = await apiService.getCurrentUser();
            if (response.success && response.data) {
              setUser(response.data);
              setIsAuthenticated(true);
            } else {
              // Token inválido, limpiar
              apiService.logout();
            }
          } catch {
            // Error de conexión, mantener datos locales si existen
            if (storedUser) {
              setUser(storedUser);
              setIsAuthenticated(true);
            }
          }
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const handleLoginSuccess = () => {
    const storedUser = apiService.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
      setIsAuthenticated(true);
    }
  };

  const handleLogout = () => {
    apiService.logout();
    setUser(null);
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="app-shell d-flex align-items-center justify-content-center">
        <div className="text-center text-light">
          <div className="spinner-border text-primary mb-3" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
          <h5>Cargando OSINT Platform...</h5>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        {isAuthenticated && user ? (
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard user={user} onLogout={handleLogout} />} />
            <Route path="/investigations" element={<InvestigationsPage user={user} onLogout={handleLogout} />} />
            <Route path="/investigations/workspace/:id" element={<InvestigationWorkspace />} />
            <Route path="/entities" element={<EntitiesPage user={user} onLogout={handleLogout} />} />
            <Route path="/graphs" element={<GraphsPage user={user} onLogout={handleLogout} />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        ) : (
          <Login onLoginSuccess={handleLoginSuccess} />
        )}
      </div>
    </Router>
  );
}

export default App;

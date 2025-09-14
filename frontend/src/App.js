import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import keycloak from './utils/keycloak';
import { AuthProvider, useAuth } from './utils/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import CreateNote from './components/CreateNote';
import './index.css';

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Public Route component (redirect to dashboard if logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  return !isAuthenticated ? children : <Navigate to="/dashboard" />;
};

function AppRoutes() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/login" 
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/create" 
            element={
              <ProtectedRoute>
                <CreateNote />
              </ProtectedRoute>
            } 
          />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  const keycloakProviderInitOptions = {
    onLoad: 'check-sso',
    checkLoginIframe: false,
    pkceMethod: 'S256'
  };

  const handleKeycloakEvent = (event, error) => {
    console.log('Keycloak event:', event, error);
  };

  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={keycloakProviderInitOptions}
      onEvent={handleKeycloakEvent}
      LoadingComponent={<div>Loading authentication...</div>}
    >
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ReactKeycloakProvider>
  );
}

export default App;

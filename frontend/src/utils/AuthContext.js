import React, { createContext, useContext } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const { keycloak, initialized } = useKeycloak();

  const login = async (redirectUri = window.location.origin) => {
    try {
      await keycloak.login({ 
        redirectUri,
        prompt: 'login' 
      });
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: 'Login failed' 
      };
    }
  };

  const register = async (redirectUri = window.location.origin) => {
    try {
      await keycloak.register({
        redirectUri
      });
      return { success: true };
    } catch (error) {
      console.error('Registration error:', error);
      return { 
        success: false, 
        error: 'Registration failed' 
      };
    }
  };

  const logout = async () => {
    try {
      await keycloak.logout({
        redirectUri: window.location.origin
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const getUser = () => {
    if (!keycloak.authenticated || !keycloak.tokenParsed) {
      return null;
    }

    return {
      id: keycloak.tokenParsed.sub,
      username: keycloak.tokenParsed.preferred_username,
      email: keycloak.tokenParsed.email,
      name: keycloak.tokenParsed.name,
      firstName: keycloak.tokenParsed.given_name,
      lastName: keycloak.tokenParsed.family_name,
      roles: keycloak.tokenParsed.realm_access?.roles || []
    };
  };

  const getToken = () => {
    return keycloak.token;
  };

  const isAuthenticated = () => {
    return keycloak.authenticated;
  };

  const value = {
    user: getUser(),
    login,
    register,
    logout,
    loading: !initialized,
    isAuthenticated: isAuthenticated(),
    getToken,
    keycloak // Expose keycloak instance for advanced usage
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

import React from 'react';
import { useAuth } from '../utils/AuthContext';

const Login = () => {
  const { login, register } = useAuth();

  const handleLogin = () => {
    login();
  };

  const handleRegister = () => {
    register();
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      backgroundColor: '#f5f5f5'
    }}>
      <div className="card" style={{ width: '100%', maxWidth: '400px' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '30px' }}>
          Welcome to SharedNotes
        </h2>
        
        <p style={{ textAlign: 'center', marginBottom: '30px', color: '#666' }}>
          Please choose an option to continue:
        </p>

        <button 
          onClick={handleLogin}
          className="btn" 
          style={{ width: '100%', marginBottom: '15px' }}
        >
          Login
        </button>

        <button 
          onClick={handleRegister}
          className="btn" 
          style={{ 
            width: '100%', 
            backgroundColor: '#28a745',
            borderColor: '#28a745'
          }}
        >
          Register New Account
        </button>

        <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#e9ecef', borderRadius: '4px' }}>
          <p style={{ margin: '0 0 15px 0', fontWeight: 'bold', fontSize: '14px' }}>Test Users (for login):</p>
          <p style={{ margin: '5px 0', fontSize: '12px' }}>👤 pippo / pippo123</p>
          <p style={{ margin: '5px 0', fontSize: '12px' }}>👤 pluto / pluto123</p>
          <p style={{ margin: '5px 0', fontSize: '12px' }}>👤 paperino / paperino123</p>
        </div>

        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#d4edda', borderRadius: '4px' }}>
          <p style={{ margin: '0', fontSize: '12px', color: '#155724' }}>
            ✅ <strong>Secure Authentication:</strong> Powered by Keycloak with OAuth2/OpenID Connect
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;

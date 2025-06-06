import React, { useState } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { Lock, User, LogIn, AlertCircle } from 'lucide-react';
import { ragService } from '../services/ragService';

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
`;

const LoginCard = styled(motion.div)`
  background: rgba(255, 255, 255, 0.95);
  padding: 2rem;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  width: 100%;
  max-width: 400px;
`;

const Logo = styled.div`
  text-align: center;
  margin-bottom: 2rem;
`;

const LogoText = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  color: #333;
  margin: 0;
`;

const LogoSubtext = styled.p`
  color: #666;
  font-size: 0.875rem;
  margin: 0.5rem 0 0 0;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const InputGroup = styled.div`
  position: relative;
`;

const InputLabel = styled.label`
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
`;

const InputWrapper = styled.div`
  position: relative;
  display: flex;
  align-items: center;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.75rem 0.75rem 0.75rem 2.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.2s ease;
  background: white;

  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  &::placeholder {
    color: #9ca3af;
  }
`;

const InputIcon = styled.div`
  position: absolute;
  left: 0.75rem;
  color: #9ca3af;
  z-index: 1;
`;

const LoginButton = styled(motion.button)`
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
`;

const ErrorMessage = styled(motion.div)`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 0.875rem;
`;

const DemoCredentials = styled.div`
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f3f4f6;
  border-radius: 8px;
  border-left: 4px solid #667eea;
`;

const DemoTitle = styled.h4`
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
`;

const DemoText = styled.p`
  margin: 0;
  font-size: 0.75rem;
  color: #6b7280;
  line-height: 1.4;
`;

function LoginForm({ onLoginSuccess }) {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!credentials.username || !credentials.password) {
      setError('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await ragService.login(credentials.username, credentials.password);
      console.log('Login successful:', response);
      onLoginSuccess?.(response);
    } catch (err) {
      console.error('Login failed:', err);
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };
  const handleDemoLogin = () => {
    setCredentials({
      username: 'admin',
      password: 'admin123'
    });
  };

  return (
    <LoginContainer>
      <LoginCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Logo>
          <LogoText>RAGdoll Enterprise</LogoText>
          <LogoSubtext>Secure Knowledge Management</LogoSubtext>
        </Logo>

        <Form onSubmit={handleSubmit}>
          <InputGroup>
            <InputLabel htmlFor="username">Username</InputLabel>
            <InputWrapper>
              <InputIcon>
                <User size={18} />
              </InputIcon>
              <Input
                id="username"
                name="username"
                type="text"
                placeholder="Enter your username"
                value={credentials.username}
                onChange={handleInputChange}
                autoComplete="username"
              />
            </InputWrapper>
          </InputGroup>

          <InputGroup>
            <InputLabel htmlFor="password">Password</InputLabel>
            <InputWrapper>
              <InputIcon>
                <Lock size={18} />
              </InputIcon>
              <Input
                id="password"
                name="password"
                type="password"
                placeholder="Enter your password"
                value={credentials.password}
                onChange={handleInputChange}
                autoComplete="current-password"
              />
            </InputWrapper>
          </InputGroup>

          {error && (
            <ErrorMessage
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <AlertCircle size={16} />
              {error}
            </ErrorMessage>
          )}

          <LoginButton
            type="submit"
            disabled={isLoading}
            whileTap={{ scale: 0.98 }}
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                Logging in...
              </>
            ) : (
              <>
                <LogIn size={18} />
                Sign In
              </>
            )}
          </LoginButton>
        </Form>

        <DemoCredentials>
          <DemoTitle>Demo Credentials</DemoTitle>          <DemoText>
            For testing purposes, try:<br />
            Username: <strong>admin</strong><br />
            Password: <strong>admin123</strong>
          </DemoText>
          <motion.button
            onClick={handleDemoLogin}
            style={{
              marginTop: '0.5rem',
              padding: '0.25rem 0.5rem',
              background: 'none',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              color: '#6b7280'
            }}
            whileHover={{ backgroundColor: '#f3f4f6' }}
          >
            Use Demo Credentials
          </motion.button>
        </DemoCredentials>
      </LoginCard>
    </LoginContainer>
  );
}

export default LoginForm;

import React, { useState, useEffect } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import Chat from './components/Chat';
import DocumentManager from './components/DocumentManager';
import NamespaceManager from './components/NamespaceManager';
import Dashboard from './components/Dashboard';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LoginForm from './components/LoginForm';
import { ragService } from './services/ragService';

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #333;
  }

  #root {
    min-height: 100vh;
  }
`;

const AppContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
`;

const MainContent = styled.main`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const ContentArea = styled.div`
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
`;

const ErrorBoundary = styled(motion.div)`
  padding: 2rem;
  text-align: center;
  color: #ff6b6b;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  margin: 2rem;
`;

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [selectedNamespace, setSelectedNamespace] = useState('default');
  const [systemStatus, setSystemStatus] = useState({ status: 'checking', message: 'Checking system...' });
  const [error, setError] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    try {
      setIsCheckingAuth(true);
      const authenticated = ragService.isAuthenticated();
      if (authenticated) {
        // Verify token is still valid by making a test request
        await ragService.getHealth();
        setIsAuthenticated(true);
        checkSystemHealth();
      } else {
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.error('Authentication check failed:', err);
      setIsAuthenticated(false);
      ragService.clearToken();
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    checkSystemHealth();
  };

  const handleLogout = () => {
    ragService.clearToken();
    setIsAuthenticated(false);
    setSystemStatus({ status: 'checking', message: 'Checking system...' });
    setError(null);
  };

  const checkSystemHealth = async () => {
    try {
      const health = await ragService.getHealth();
      setSystemStatus({ 
        status: 'healthy', 
        message: `System operational - ${health.message || 'All services running'}` 
      });
      setError(null);
    } catch (err) {
      console.error('System health check failed:', err);
      setSystemStatus({ 
        status: 'error', 
        message: 'System connection failed' 
      });
      setError('Unable to connect to RAGdoll system. Please ensure the backend is running.');
    }
  };

  const handleNamespaceChange = (namespace) => {
    setSelectedNamespace(namespace);
  };

  const renderContent = () => {
    if (error) {
      return (
        <ErrorBoundary
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <h2>Connection Error</h2>
          <p>{error}</p>
          <button 
            onClick={checkSystemHealth}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Retry Connection
          </button>
        </ErrorBoundary>
      );
    }

    switch (activeTab) {
      case 'chat':
        return <Chat namespace={selectedNamespace} />;
      case 'documents':
        return <DocumentManager namespace={selectedNamespace} />;
      case 'namespaces':
        return <NamespaceManager onNamespaceChange={handleNamespaceChange} />;
      case 'dashboard':
        return <Dashboard />;
      default:
        return <Chat namespace={selectedNamespace} />;
    }
  };
  return (
    <>
      <GlobalStyle />
      {isCheckingAuth ? (
        <AppContainer>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: '100vh',
            color: 'white',
            fontSize: '1.2rem'
          }}>
            Checking authentication...
          </div>
        </AppContainer>
      ) : !isAuthenticated ? (
        <LoginForm onLoginSuccess={handleLoginSuccess} />
      ) : (
        <AppContainer>
          <Sidebar 
            activeTab={activeTab} 
            onTabChange={setActiveTab}
            systemStatus={systemStatus}
            onLogout={handleLogout}
          />
          <MainContent>
            <Header 
              selectedNamespace={selectedNamespace}
              onNamespaceChange={handleNamespaceChange}
              systemStatus={systemStatus}
            />
            <ContentArea>
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  {renderContent()}
                </motion.div>
              </AnimatePresence>
            </ContentArea>
          </MainContent>
        </AppContainer>
      )}
    </>
  );
}

export default App;

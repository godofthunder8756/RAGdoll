import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';

const HeaderContainer = styled.header`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h1`
  color: #667eea;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
`;

const StatusIndicator = styled(motion.div)`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 500;
  background: ${props => {
    switch (props.status) {
      case 'healthy': return 'rgba(34, 197, 94, 0.1)';
      case 'error': return 'rgba(239, 68, 68, 0.1)';
      default: return 'rgba(156, 163, 175, 0.1)';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'healthy': return '#22c55e';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  }};
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
`;

const NamespaceSelector = styled.select`
  padding: 0.5rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(5px);
  color: #333;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;

  &:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const Header = ({ selectedNamespace, onNamespaceChange, systemStatus }) => {
  const namespaces = ['default', 'engineering', 'hr', 'legal', 'marketing'];

  return (
    <HeaderContainer>
      <Title>TParty RAG Interface</Title>
      
      <RightSection>
        <div>
          <label htmlFor="namespace-select" style={{ marginRight: '0.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
            Namespace:
          </label>
          <NamespaceSelector
            id="namespace-select"
            value={selectedNamespace}
            onChange={(e) => onNamespaceChange(e.target.value)}
          >
            {namespaces.map(ns => (
              <option key={ns} value={ns}>
                {ns.charAt(0).toUpperCase() + ns.slice(1)}
              </option>
            ))}
          </NamespaceSelector>
        </div>

        <StatusIndicator
          status={systemStatus.status}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          <StatusDot />
          {systemStatus.message}
        </StatusIndicator>
      </RightSection>
    </HeaderContainer>
  );
};

export default Header;

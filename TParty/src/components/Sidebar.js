import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { 
  MessageCircle, 
  FileText, 
  Database, 
  BarChart3, 
  Zap,
  LogOut 
} from 'lucide-react';

const SidebarContainer = styled.aside`
  width: 250px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  padding: 2rem 0;
`;

const Logo = styled.div`
  padding: 0 2rem 2rem 2rem;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 2rem;
`;

const LogoIcon = styled(motion.div)`
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.5rem;
  color: white;
  font-size: 1.5rem;
  font-weight: bold;
`;

const LogoText = styled.h2`
  color: white;
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
`;

const LogoSubtext = styled.p`
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  margin: 0.25rem 0 0 0;
`;

const NavList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
`;

const NavItem = styled(motion.li)`
  margin: 0.25rem 1rem;
`;

const NavButton = styled.button`
  width: 100%;
  padding: 0.75rem 1rem;
  background: ${props => props.active ? 'rgba(255, 255, 255, 0.2)' : 'transparent'};
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateX(4px);
  }

  &:active {
    transform: translateX(2px);
  }
`;

const StatusSection = styled.div`
  padding: 1rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
`;

const StatusTitle = styled.h3`
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
`;

const StatusText = styled.p`
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  margin: 0;
`;

const LogoutButton = styled(motion.button)`
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(239, 68, 68, 0.3);
    border-color: rgba(239, 68, 68, 0.5);
  }

  &:active {
    transform: scale(0.98);
  }
`;

const Sidebar = ({ activeTab, onTabChange, systemStatus, onLogout }) => {
  const navItems = [
    { id: 'chat', label: 'AI Chat', icon: MessageCircle },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'namespaces', label: 'Namespaces', icon: Database },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  ];

  return (
    <SidebarContainer>
      <Logo>
        <LogoIcon
          whileHover={{ scale: 1.05, rotate: 5 }}
          whileTap={{ scale: 0.95 }}
        >
          <Zap size={24} />
        </LogoIcon>
        <LogoText>TParty</LogoText>
        <LogoSubtext>RAGdoll Enterprise</LogoSubtext>
      </Logo>

      <NavList>
        {navItems.map((item) => (
          <NavItem
            key={item.id}
            whileHover={{ x: 4 }}
            whileTap={{ x: 2 }}
          >
            <NavButton
              active={activeTab === item.id}
              onClick={() => onTabChange(item.id)}
            >
              <item.icon size={18} />
              {item.label}
            </NavButton>
          </NavItem>
        ))}
      </NavList>      <StatusSection>
        <StatusTitle>System Status</StatusTitle>
        <StatusText>
          {systemStatus.status === 'healthy' ? '🟢' : 
           systemStatus.status === 'error' ? '🔴' : '🟡'} {systemStatus.message}
        </StatusText>
        
        {onLogout && (
          <LogoutButton
            onClick={onLogout}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <LogOut size={16} />
            Logout
          </LogoutButton>
        )}
      </StatusSection>
    </SidebarContainer>
  );
};

export default Sidebar;

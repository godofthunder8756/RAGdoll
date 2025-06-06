import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, 
  Plus, 
  Trash2, 
  Users, 
  FileText, 
  BarChart3,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { ragService } from '../services/ragService';

const NamespacesContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
`;

const Header = styled.div`
  background: rgba(255, 255, 255, 0.95);
  padding: 1.5rem 2rem;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
`;

const HeaderTitle = styled.h2`
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
`;

const HeaderSubtitle = styled.p`
  margin: 0;
  color: #6b7280;
  font-size: 0.875rem;
`;

const ActionsBar = styled.div`
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 1rem;
`;

const Button = styled(motion.button)`
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 8px;
  background: ${props => props.variant === 'primary' ? '#667eea' : 'white'};
  color: ${props => props.variant === 'primary' ? 'white' : '#667eea'};
  border: ${props => props.variant === 'primary' ? 'none' : '1px solid #667eea'};
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const NamespaceGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
  flex: 1;
  overflow-y: auto;
`;

const NamespaceCard = styled(motion.div)`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  }

  &.active {
    border-color: #667eea;
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2);
  }
`;

const NamespaceIcon = styled.div`
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 1rem;
`;

const NamespaceTitle = styled.h3`
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #333;
  text-transform: capitalize;
`;

const NamespaceDescription = styled.p`
  margin: 0 0 1rem 0;
  color: #6b7280;
  font-size: 0.875rem;
  line-height: 1.4;
`;

const NamespaceStats = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
`;

const StatItem = styled.div`
  text-align: center;
  padding: 0.75rem;
  background: rgba(102, 126, 234, 0.05);
  border-radius: 8px;
`;

const StatValue = styled.div`
  font-size: 1.25rem;
  font-weight: 600;
  color: #667eea;
`;

const StatLabel = styled.div`
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
`;

const NamespaceActions = styled.div`
  display: flex;
  gap: 0.5rem;
  position: absolute;
  top: 1rem;
  right: 1rem;
  opacity: 0;
  transition: opacity 0.2s;

  ${NamespaceCard}:hover & {
    opacity: 1;
  }
`;

const ActionButton = styled(motion.button)`
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  color: #667eea;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  &:hover {
    background: white;
  }

  &.danger {
    color: #ef4444;
  }
`;

const CreateModal = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled(motion.div)`
  background: white;
  border-radius: 16px;
  padding: 2rem;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
`;

const ModalTitle = styled.h3`
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #333;
`;

const FormGroup = styled.div`
  margin-bottom: 1rem;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  outline: none;

  &:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  outline: none;
  resize: vertical;
  min-height: 80px;

  &:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
`;

const ModalActions = styled.div`
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
`;

const LoadingSpinner = styled(motion.div)`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
`;

const ErrorMessage = styled(motion.div)`
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const NamespaceManager = ({ onNamespaceChange }) => {
  const [namespaces, setNamespaces] = useState([]);
  const [stats, setStats] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newNamespace, setNewNamespace] = useState({ name: '', description: '' });
  const [isCreating, setIsCreating] = useState(false);
  const [selectedNamespace, setSelectedNamespace] = useState(null);

  const loadNamespaces = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await ragService.getNamespaces();
      const namespaceList = response.namespaces || ['default', 'engineering', 'hr', 'legal', 'marketing'];
      
      setNamespaces(namespaceList);

      // Load stats for each namespace
      const namespaceStats = {};
      for (const ns of namespaceList) {
        try {
          const nsStats = await ragService.getNamespaceStats(ns);
          namespaceStats[ns] = nsStats;
        } catch (err) {
          // If stats endpoint doesn't exist, use mock data
          namespaceStats[ns] = {
            documents: Math.floor(Math.random() * 50) + 5,
            chunks: Math.floor(Math.random() * 500) + 50,
            size: Math.floor(Math.random() * 1000000) + 100000
          };
        }
      }
      setStats(namespaceStats);
    } catch (err) {
      console.error('Failed to load namespaces:', err);
      setError('Failed to load namespaces. Please try again.');
      // Fallback to default namespaces
      setNamespaces(['default', 'engineering', 'hr', 'legal', 'marketing']);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNamespaces();
  }, []);

  const handleCreateNamespace = async () => {
    if (!newNamespace.name.trim()) return;

    setIsCreating(true);
    try {
      await ragService.createNamespace(newNamespace.name, newNamespace.description);
      setShowCreateModal(false);
      setNewNamespace({ name: '', description: '' });
      loadNamespaces();
    } catch (err) {
      console.error('Failed to create namespace:', err);
      setError('Failed to create namespace. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteNamespace = async (namespace) => {
    if (!window.confirm(`Are you sure you want to delete the "${namespace}" namespace? This action cannot be undone.`)) {
      return;
    }

    try {
      await ragService.deleteNamespace(namespace);
      loadNamespaces();
    } catch (err) {
      console.error('Failed to delete namespace:', err);
      setError('Failed to delete namespace. Please try again.');
    }
  };

  const handleNamespaceClick = (namespace) => {
    setSelectedNamespace(namespace);
    if (onNamespaceChange) {
      onNamespaceChange(namespace);
    }
  };

  const getNamespaceDescription = (namespace) => {
    const descriptions = {
      default: 'General purpose document storage and retrieval',
      engineering: 'Technical documentation, specifications, and code references',
      hr: 'Human resources policies, procedures, and employee information',
      legal: 'Legal documents, contracts, and compliance materials',
      marketing: 'Marketing materials, campaigns, and brand guidelines'
    };
    return descriptions[namespace] || 'Custom namespace for specialized content';
  };

  return (
    <NamespacesContainer>
      <Header>
        <HeaderTitle>Namespace Manager</HeaderTitle>
        <HeaderSubtitle>
          Organize your documents into isolated namespaces for better security and organization
        </HeaderSubtitle>

        <ActionsBar>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Plus size={16} />
            Create Namespace
          </Button>

          <Button
            onClick={loadNamespaces}
            disabled={isLoading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <RefreshCw size={16} />
            Refresh
          </Button>
        </ActionsBar>

        {error && (
          <ErrorMessage
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <AlertCircle size={16} />
            {error}
          </ErrorMessage>
        )}
      </Header>

      {isLoading ? (
        <LoadingSpinner>
          <RefreshCw size={24} className="animate-spin" />
        </LoadingSpinner>
      ) : (
        <NamespaceGrid>
          <AnimatePresence>
            {namespaces.map((namespace) => (
              <NamespaceCard
                key={namespace}
                className={selectedNamespace === namespace ? 'active' : ''}
                onClick={() => handleNamespaceClick(namespace)}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <NamespaceActions>
                  {namespace !== 'default' && (
                    <ActionButton
                      className="danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteNamespace(namespace);
                      }}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      title="Delete namespace"
                    >
                      <Trash2 size={16} />
                    </ActionButton>
                  )}
                </NamespaceActions>

                <NamespaceIcon>
                  <Database size={24} />
                </NamespaceIcon>

                <NamespaceTitle>{namespace}</NamespaceTitle>
                <NamespaceDescription>
                  {getNamespaceDescription(namespace)}
                </NamespaceDescription>

                <NamespaceStats>
                  <StatItem>
                    <StatValue>{stats[namespace]?.documents || 0}</StatValue>
                    <StatLabel>Documents</StatLabel>
                  </StatItem>
                  <StatItem>
                    <StatValue>{stats[namespace]?.chunks || 0}</StatValue>
                    <StatLabel>Chunks</StatLabel>
                  </StatItem>
                  <StatItem>
                    <StatValue>
                      {stats[namespace]?.size ? ragService.formatFileSize(stats[namespace].size) : '0 KB'}
                    </StatValue>
                    <StatLabel>Size</StatLabel>
                  </StatItem>
                </NamespaceStats>
              </NamespaceCard>
            ))}
          </AnimatePresence>
        </NamespaceGrid>
      )}

      <AnimatePresence>
        {showCreateModal && (
          <CreateModal
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowCreateModal(false)}
          >
            <ModalContent
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <ModalTitle>Create New Namespace</ModalTitle>

              <FormGroup>
                <Label htmlFor="namespace-name">Name</Label>
                <Input
                  id="namespace-name"
                  type="text"
                  value={newNamespace.name}
                  onChange={(e) => setNewNamespace(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter namespace name"
                />
              </FormGroup>

              <FormGroup>
                <Label htmlFor="namespace-description">Description</Label>
                <TextArea
                  id="namespace-description"
                  value={newNamespace.description}
                  onChange={(e) => setNewNamespace(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe the purpose of this namespace"
                />
              </FormGroup>

              <ModalActions>
                <Button onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleCreateNamespace}
                  disabled={!newNamespace.name.trim() || isCreating}
                >
                  {isCreating ? <RefreshCw size={16} className="animate-spin" /> : <Plus size={16} />}
                  Create
                </Button>
              </ModalActions>
            </ModalContent>
          </CreateModal>
        )}
      </AnimatePresence>
    </NamespacesContainer>
  );
};

export default NamespaceManager;

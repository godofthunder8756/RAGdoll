import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  FileText, 
  Trash2, 
  Download, 
  Search,
  Filter,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { ragService } from '../services/ragService';

const DocumentsContainer = styled.div`
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
  flex-wrap: wrap;
  margin-top: 1rem;
`;

const SearchInput = styled.input`
  flex: 1;
  min-width: 200px;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  background: white;
  font-size: 0.875rem;
  outline: none;

  &:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
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

const FileInput = styled.input`
  display: none;
`;

const DocumentGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  flex: 1;
  overflow-y: auto;
`;

const DocumentCard = styled(motion.div)`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  }
`;

const DocumentIcon = styled.div`
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

const DocumentTitle = styled.h3`
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  word-break: break-word;
`;

const DocumentMeta = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
`;

const MetaItem = styled.span`
  font-size: 0.75rem;
  color: #6b7280;
`;

const DocumentActions = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
`;

const ActionButton = styled(motion.button)`
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: rgba(102, 126, 234, 0.2);
  }

  &.danger {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;

    &:hover {
      background: rgba(239, 68, 68, 0.2);
    }
  }
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
`;

const EmptyIcon = styled.div`
  width: 64px;
  height: 64px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
  margin-bottom: 1rem;
`;

const EmptyTitle = styled.h3`
  color: #333;
  margin: 0 0 0.5rem 0;
`;

const EmptyDescription = styled.p`
  color: #6b7280;
  margin: 0;
  font-size: 0.875rem;
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

const UploadProgress = styled(motion.div)`
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid rgba(34, 197, 94, 0.2);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const DocumentManager = ({ namespace }) => {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [uploadProgress, setUploadProgress] = useState(null);
  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Get available namespaces first
      const namespaces = await ragService.getNamespaces();
      
      // For now, we'll show namespace information instead of individual documents
      // since the backend doesn't have a direct documents endpoint
      if (Array.isArray(namespaces)) {
        // Transform namespaces into document-like objects for display
        const namespaceItems = namespaces.map(ns => ({
          id: ns,
          name: ns,
          type: 'namespace',
          size: 'N/A',
          modified: new Date().toISOString(),
          namespace: ns
        }));
        setDocuments(namespaceItems);
      } else {
        setDocuments([]);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
      setError('Failed to load documents. Please check your connection and try again.');
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }, [namespace]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(`Uploading ${files.length} file(s)...`);

    try {
      for (const file of files) {
        await ragService.uploadDocument(namespace, file, {
          title: file.name,
          description: `Uploaded to ${namespace} namespace`
        });
      }

      setUploadProgress('Upload completed successfully!');
      setTimeout(() => setUploadProgress(null), 3000);
      
      // Reload documents
      loadDocuments();
    } catch (err) {
      console.error('Upload failed:', err);
      setError('Upload failed. Please try again.');
      setUploadProgress(null);
    } finally {
      setIsUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleDeleteDocument = async (documentId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await ragService.deleteDocument(namespace, documentId);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    } catch (err) {
      console.error('Delete failed:', err);
      setError('Failed to delete document. Please try again.');
    }
  };

  const filteredDocuments = documents.filter(doc =>
    doc.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.content?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown size';
    return ragService.formatFileSize(bytes);
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown date';
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <DocumentsContainer>
      <Header>
        <HeaderTitle>Document Manager</HeaderTitle>
        <HeaderSubtitle>
          Manage documents in the "{namespace}" namespace
        </HeaderSubtitle>

        <ActionsBar>
          <SearchInput
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />

          <Button
            variant="primary"
            onClick={() => document.getElementById('file-upload').click()}
            disabled={isUploading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Upload size={16} />
            Upload
          </Button>

          <Button
            onClick={loadDocuments}
            disabled={isLoading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <RefreshCw size={16} />
            Refresh
          </Button>

          <FileInput
            id="file-upload"
            type="file"
            multiple
            accept=".txt,.pdf,.doc,.docx,.md"
            onChange={handleFileUpload}
          />
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

        {uploadProgress && (
          <UploadProgress
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Upload size={16} />
            {uploadProgress}
          </UploadProgress>
        )}
      </Header>

      {isLoading ? (
        <LoadingSpinner>
          <RefreshCw size={24} className="animate-spin" />
        </LoadingSpinner>
      ) : filteredDocuments.length === 0 ? (
        <EmptyState>
          <EmptyIcon>
            <FileText size={32} />
          </EmptyIcon>
          <EmptyTitle>
            {documents.length === 0 ? 'No documents yet' : 'No matching documents'}
          </EmptyTitle>
          <EmptyDescription>
            {documents.length === 0 
              ? `Upload your first document to the "${namespace}" namespace`
              : 'Try adjusting your search terms'
            }
          </EmptyDescription>
        </EmptyState>
      ) : (
        <DocumentGrid>
          <AnimatePresence>
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
              >
                <DocumentIcon>
                  <FileText size={24} />
                </DocumentIcon>

                <DocumentTitle>
                  {doc.title || doc.filename || 'Untitled Document'}
                </DocumentTitle>

                <DocumentMeta>
                  <MetaItem>Size: {formatFileSize(doc.size)}</MetaItem>
                  <MetaItem>Added: {formatDate(doc.created_at)}</MetaItem>
                  {doc.chunks && (
                    <MetaItem>Chunks: {doc.chunks}</MetaItem>
                  )}
                </DocumentMeta>

                <DocumentActions>
                  <ActionButton
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    title="Download"
                  >
                    <Download size={16} />
                  </ActionButton>

                  <ActionButton
                    className="danger"
                    onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </ActionButton>
                </DocumentActions>
              </DocumentCard>
            ))}
          </AnimatePresence>
        </DocumentGrid>
      )}
    </DocumentsContainer>
  );
};

export default DocumentManager;

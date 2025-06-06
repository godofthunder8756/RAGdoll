import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, Loader, AlertCircle, Copy, ThumbsUp, ThumbsDown } from 'lucide-react';
import { ragService } from '../services/ragService';

const ChatContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  overflow: hidden;
`;

const ChatHeader = styled.div`
  padding: 1.5rem 2rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
`;

const ChatTitle = styled.h2`
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
`;

const ChatSubtitle = styled.p`
  margin: 0.25rem 0 0 0;
  opacity: 0.9;
  font-size: 0.875rem;
`;

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const MessageBubble = styled(motion.div)`
  display: flex;
  gap: 0.75rem;
  max-width: 80%;
  align-self: ${props => props.isUser ? 'flex-end' : 'flex-start'};
  flex-direction: ${props => props.isUser ? 'row-reverse' : 'row'};
`;

const Avatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${props => props.isUser ? '#667eea' : '#22c55e'};
  color: white;
  flex-shrink: 0;
`;

const MessageContent = styled.div`
  background: ${props => props.isUser ? '#667eea' : 'white'};
  color: ${props => props.isUser ? 'white' : '#333'};
  padding: 0.75rem 1rem;
  border-radius: 16px;
  border: ${props => props.isUser ? 'none' : '1px solid rgba(0, 0, 0, 0.1)'};
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: relative;
`;

const MessageText = styled.p`
  margin: 0;
  line-height: 1.5;
  white-space: pre-wrap;
`;

const MessageActions = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  opacity: 0.7;
`;

const ActionButton = styled.button`
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  opacity: 0.6;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
`;

const SourcesContainer = styled.div`
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
`;

const SourcesTitle = styled.h4`
  margin: 0 0 0.5rem 0;
  font-size: 0.75rem;
  text-transform: uppercase;
  opacity: 0.7;
  font-weight: 600;
`;

const Source = styled.div`
  background: rgba(0, 0, 0, 0.05);
  padding: 0.5rem;
  border-radius: 6px;
  margin-bottom: 0.25rem;
  font-size: 0.75rem;
`;

const InputContainer = styled.div`
  padding: 1.5rem 2rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.5);
`;

const InputWrapper = styled.div`
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
`;

const TextArea = styled.textarea`
  flex: 1;
  min-height: 44px;
  max-height: 120px;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  background: white;
  font-family: inherit;
  font-size: 0.875rem;
  resize: none;
  outline: none;

  &:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  &::placeholder {
    color: #9ca3af;
  }
`;

const SendButton = styled(motion.button)`
  padding: 0.75rem;
  background: ${props => props.disabled ? '#9ca3af' : '#667eea'};
  border: none;
  border-radius: 12px;
  color: white;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  display: flex;
  align-items: center;
  justify-content: center;
`;

const LoadingIndicator = styled(motion.div)`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 12px;
  color: #667eea;
  font-size: 0.875rem;
`;

const ErrorMessage = styled(motion.div)`
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const Chat = ({ namespace }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const textAreaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  useEffect(() => {
    // Reset chat when namespace changes
    setMessages([]);
    setError(null);
  }, [namespace]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      text: inputValue.trim(),
      isUser: true,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);
    setStreamingMessage('');

    try {
      let fullResponse = '';
      let sources = [];

      await ragService.streamChatWithGPT(
        userMessage.text,
        namespace,
        {
          temperature: 0.7,
          maxTokens: 1000,
          includeSources: true
        },
        (chunk) => {
          if (chunk.type === 'content') {
            fullResponse += chunk.content;
            setStreamingMessage(fullResponse);
          } else if (chunk.type === 'sources') {
            sources = chunk.sources;
          }
        }
      );

      const botMessage = {
        id: Date.now() + 1,
        text: fullResponse,
        isUser: false,
        timestamp: new Date().toISOString(),
        sources: sources
      };

      setMessages(prev => [...prev, botMessage]);
      setStreamingMessage('');
    } catch (err) {
      console.error('Chat error:', err);
      
      // Fallback to non-streaming chat
      try {
        const response = await ragService.chatWithGPT(userMessage.text, namespace);
        const botMessage = {
          id: Date.now() + 1,
          text: response.response || response.answer || 'I received your message but had trouble generating a response.',
          isUser: false,
          timestamp: new Date().toISOString(),
          sources: response.sources || []
        };
        setMessages(prev => [...prev, botMessage]);
      } catch (fallbackErr) {
        setError('Failed to get response. Please check your connection and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <ChatContainer>
      <ChatHeader>
        <ChatTitle>AI Assistant</ChatTitle>
        <ChatSubtitle>
          Ask questions about your documents in the "{namespace}" namespace
        </ChatSubtitle>
      </ChatHeader>

      <MessagesContainer>
        <AnimatePresence>
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              isUser={message.isUser}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Avatar isUser={message.isUser}>
                {message.isUser ? <User size={18} /> : <Bot size={18} />}
              </Avatar>
              <MessageContent isUser={message.isUser}>
                <MessageText>{message.text}</MessageText>
                
                {!message.isUser && (
                  <MessageActions>
                    <ActionButton onClick={() => copyToClipboard(message.text)}>
                      <Copy size={14} />
                    </ActionButton>
                    <ActionButton>
                      <ThumbsUp size={14} />
                    </ActionButton>
                    <ActionButton>
                      <ThumbsDown size={14} />
                    </ActionButton>
                  </MessageActions>
                )}

                {message.sources && message.sources.length > 0 && (
                  <SourcesContainer>
                    <SourcesTitle>Sources</SourcesTitle>
                    {message.sources.map((source, index) => (
                      <Source key={index}>
                        {source.metadata?.filename || `Document ${index + 1}`}
                        {source.score && ` (${Math.round(source.score * 100)}% match)`}
                      </Source>
                    ))}
                  </SourcesContainer>
                )}
              </MessageContent>
            </MessageBubble>
          ))}

          {streamingMessage && (
            <MessageBubble
              isUser={false}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Avatar isUser={false}>
                <Bot size={18} />
              </Avatar>
              <MessageContent isUser={false}>
                <MessageText>{streamingMessage}</MessageText>
              </MessageContent>
            </MessageBubble>
          )}

          {isLoading && !streamingMessage && (
            <LoadingIndicator
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Loader size={16} className="animate-spin" />
              Thinking...
            </LoadingIndicator>
          )}

          {error && (
            <ErrorMessage
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <AlertCircle size={16} />
              {error}
            </ErrorMessage>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </MessagesContainer>

      <InputContainer>
        <form onSubmit={handleSubmit}>
          <InputWrapper>
            <TextArea
              ref={textAreaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              disabled={isLoading}
              rows={1}
            />
            <SendButton
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {isLoading ? (
                <Loader size={18} className="animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </SendButton>
          </InputWrapper>
        </form>
      </InputContainer>
    </ChatContainer>
  );
};

export default Chat;

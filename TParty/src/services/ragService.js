import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class RAGService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests if available
    this.api.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Response Error:', error.response?.data || error.message);
        
        if (error.response?.status === 401) {
          this.clearToken();
        }
        
        return Promise.reject(error);
      }
    );
  }

  // Authentication methods
  getToken() {
    return localStorage.getItem('ragdoll_token');
  }

  setToken(token) {
    localStorage.setItem('ragdoll_token', token);
  }

  clearToken() {
    localStorage.removeItem('ragdoll_token');
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async login(username, password) {
    try {
      const response = await this.api.post('/auth/login', {
        username,
        password
      });
      
      const { access_token } = response.data;
      this.setToken(access_token);
      return response.data;
    } catch (error) {
      throw new Error('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  }

  async logout() {
    this.clearToken();
  }

  async getProfile() {
    const response = await this.api.get('/auth/profile');
    return response.data;
  }

  // Health check
  async getHealth() {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error('Health check failed');
    }
  }

  // Document operations
  async getDocuments(namespace = 'default') {
    const response = await this.api.get('/namespaces');
    return response.data;
  }

  // Query operations
  async query(query, namespace = 'default', options = {}) {
    const payload = {
      query,
      top_k: options.topK || 5,
      score_threshold: options.scoreThreshold || 0.0,
      ...options
    };

    const response = await this.api.post(`/query/${namespace}`, payload);
    return response.data;
  }

  // GPT-4 integration
  async chatWithGPT(query, namespace = 'default', options = {}) {
    const payload = {
      query,
      namespace,
      max_tokens: options.maxTokens || 1000,
      temperature: options.temperature || 0.7,
      include_sources: options.includeSources !== false,
      ...options
    };

    const response = await this.api.post('/api/v1/openai/chat/gpt4', payload);    return response.data;
  }

  // Chat methods
  async chatWithGPT(query, namespace = 'default', options = {}) {
    const request = {
      query,
      namespace,
      temperature: options.temperature || 0.7,
      max_tokens: options.max_tokens || 1000,
      top_k: options.top_k || 5,
      include_sources: options.include_sources !== false
    };

    try {
      const response = await this.api.post('/api/v1/openai/chat/gpt4', request);
      return response.data;
    } catch (error) {
      console.error('Chat error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get chat response');
    }
  }

  async streamChatWithGPT(query, namespace = 'default', options = {}, onData) {
    const request = {
      query,
      namespace,
      stream: true,
      temperature: options.temperature || 0.7,
      max_tokens: options.max_tokens || 1000,
      top_k: options.top_k || 5,
      include_sources: options.include_sources !== false
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/openai/chat/gpt4/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getToken()}`
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (onData) {
                onData(parsed);
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', data);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream chat error:', error);
      throw new Error(error.message || 'Failed to stream chat response');
    }
  }

  // Namespace operations
  async getNamespaces() {
    const response = await this.api.get('/namespaces');
    return response.data;
  }
}

export const ragService = new RAGService();
export default RAGService;

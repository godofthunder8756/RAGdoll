# RAGdoll Enterprise
## Multi-Service RAG (Retrieval-Augmented Generation) System

A containerized enterprise-grade RAG system featuring namespaced document retrieval, GPT-4o integration, and a modern React frontend.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key (optional, for GPT-4o integration)

### Setup
1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd RAGdoll
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

2. **Build and run**:
   ```bash
   docker-compose -f docker-compose.fast.yml up --build
   ```

3. **Access the application**:
   - Frontend (TParty): http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - Default login: `admin` / `admin123`

## 🏗️ Architecture

### Services
- **RAGdoll API** (Port 8000): FastAPI backend with JWT authentication
- **TParty Frontend** (Port 3000): React.js chat interface
- **Redis** (Port 6379): Caching layer

### Features
- ✅ **Namespaced Document Storage**: Organize documents by department/domain
- ✅ **BGE-M3 Embeddings**: High-quality semantic search (offline-capable)
- ✅ **FAISS Vector Search**: Sub-second document retrieval
- ✅ **JWT Authentication**: Secure API access
- ✅ **Redis Caching**: Performance optimization
- ✅ **Docker Containerization**: Easy deployment
- 🔧 **GPT-4o Integration**: (SSL configuration required in corporate environments)

## 📁 Project Structure

```
RAGdoll/
├── app/                    # FastAPI backend
│   ├── api_new.py         # Main API routes
│   ├── auth.py            # JWT authentication
│   ├── openai_api.py      # GPT-4o integration
│   ├── query_namespaced.py # RAG retrieval logic
│   └── ...
├── TParty/                # React frontend
│   ├── src/components/    # React components
│   ├── src/services/      # API service layer
│   └── ...
├── data/                  # Sample documents
├── docker-compose.fast.yml # Fast development setup
└── bge-m3_repo/          # Local BGE-M3 model
```

## 🔧 Development

### Fast Build Mode
Uses pre-built layers for rapid iteration:
```bash
docker-compose -f docker-compose.fast.yml up --build
```

### Document Ingestion
Add documents to namespaces via API:
```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Authorization: Bearer <token>" \
  -F "files=@document.pdf" \
  -F "namespace=engineering"
```

### Namespace Management
- `default`: General documents
- `engineering`: Technical documentation  
- `legal`: Legal and compliance docs
- `hr`: Human resources materials
- `marketing`: Marketing and brand content

## 🔍 Usage

### Chat Interface (TParty)
1. Login with admin credentials
2. Select a namespace
3. Ask questions about documents in that namespace
4. Get AI-powered responses with source citations

### API Endpoints
- `POST /auth/login` - Authentication
- `POST /query/{namespace}` - Document search
- `POST /api/v1/openai/chat/gpt4` - GPT-4o chat
- `GET /namespaces` - List available namespaces

## 🛠️ Configuration

### Environment Variables
```bash
OPENAI_API_KEY=sk-...           # OpenAI API key
OFFLINE_MODE=true               # Use local BGE-M3 model
REDIS_URL=redis://redis:6379/0  # Redis connection
ENABLE_CACHE=true               # Enable response caching
```

### Known Issues
- **SSL Certificate Issues**: Corporate firewalls may block OpenAI API calls
- **Solution**: Configure proxy settings or use offline mode for document retrieval only

## 📊 Performance
- **Document Retrieval**: Sub-second response times
- **Memory Usage**: ~2GB for BGE-M3 model + application
- **Scalability**: Horizontal scaling via Docker Swarm/Kubernetes

## 🤝 Contributing
1. Use the fast build mode for development
2. Follow the existing code structure
3. Test with sample documents in `data/` directory
4. Update documentation for new features

## 📄 License
[Add your license here]

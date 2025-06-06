```mermaid
graph TD
  %% ────────── Client/UI ──────────
  subgraph Client_Tier
    Browser[React UI (Port 3000)]
  end

  %% ────────── API & Cache ──────────
  subgraph API_Tier
    API[ragdoll-api (Port 8000)]
    Redis[Redis Cache (Port 6379)]
    GPT[GPT-4o (OpenAI)]
  end

  %% ────────── Retrieval Layer ──────────
  subgraph Retrieval_Layer
    BM25[BM25 Search]
    FAISS[FAISS Vector Index]
    Emb[BGE-M3 Embeddings]
  end

  %% ────────── Ingestion ──────────
  subgraph Ingestion_Service
    Ingest[ragdoll-enterprise]
    Data[data/ folder]
  end

  %% ────────── Connections ──────────
  Browser -->|POST /query| API
  API -->|get/set| Redis
  Redis -->|cached result| API

  API -->|embed Q| Emb
  API -->|keyword search| BM25
  API -->|vector search| FAISS
  API -->|prompt + context| GPT
  GPT -->|completion| API
  API -->|response| Browser

  Ingest -->|watch folder| Data
  Ingest -->|embed chunks| Emb
  Ingest -->|index vectors| FAISS
  Ingest -->|index metadata| BM25
```
#!/usr/bin/env python3
"""
RAG Query Interface - handles query processing and retrieval
"""

import numpy as np
from typing import List, Dict, Any, Optional
from .embedder import embed_text
from .vector_store import VectorStore


class RAGRetriever:
    """
    RAG (Retrieval-Augmented Generation) system for querying documents
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Initialize the RAG retriever
        
        Args:
            vector_store: VectorStore instance, creates new one if None
        """
        self.vector_store = vector_store or VectorStore()
    
    def query(self, query_text: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Query the RAG system for relevant documents
        
        Args:
            query_text: The query string
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
              Returns:
            List of dictionaries containing text, metadata, and scores
        """
        # Generate embedding for the query
        print(f"🔍 Processing query: {query_text}")
        query_embeddings = embed_text([query_text])  # embed_text expects a list
        
        if query_embeddings is None or len(query_embeddings) == 0:
            print("❌ Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]  # Get the first (and only) embedding
          # Search the vector store
        indices, distances, metadata_list = self.vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by score threshold and format results
        filtered_results = []
        for i, (idx, distance, metadata) in enumerate(zip(indices, distances, metadata_list)):
            # Convert distance to similarity score (FAISS uses L2 distance)
            score = max(0, 1 - distance / 2)  # Simple conversion from L2 distance to similarity
            
            if score >= score_threshold:
                # Get the text from metadata
                text = metadata.get('text', f'Document {idx}')
                
                filtered_results.append({
                    'text': text,
                    'metadata': metadata,
                    'score': score
                })
        
        print(f"✅ Found {len(filtered_results)} relevant documents")
        return filtered_results
    
    def get_context(self, query_text: str, top_k: int = 3, max_context_length: int = 2000) -> str:
        """
        Get formatted context for RAG generation
        
        Args:
            query_text: The query string
            top_k: Number of top documents to include
            max_context_length: Maximum character length of context
            
        Returns:
            Formatted context string
        """
        results = self.query(query_text, top_k=top_k)
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            text = result['text']
            metadata = result['metadata']
            score = result['score']
            
            # Format context piece
            source_info = f"[Source: {metadata.get('filename', 'Unknown')}]"
            context_piece = f"Document {i} {source_info}:\n{text}\n"
            
            # Check if adding this would exceed max length
            if total_length + len(context_piece) > max_context_length and context_parts:
                break
                
            context_parts.append(context_piece)
            total_length += len(context_piece)
        
        return "\n".join(context_parts)
    
    def interactive_query(self):
        """
        Interactive query interface for testing
        """
        print("\n🤖 RAGdoll Interactive Query Interface")
        print("Type 'quit' to exit, 'stats' for vector store info")
        print("-" * 50)
        
        while True:
            try:
                query = input("\n💬 Enter your query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                if query.lower() == 'stats':
                    stats = self.vector_store.get_stats()
                    print(f"\n📊 Vector Store Stats:")
                    print(f"   Documents: {stats['num_documents']}")
                    print(f"   Dimension: {stats['dimension']}")
                    print(f"   Index file: {stats['index_file']}")
                    continue
                
                if not query:
                    continue
                
                # Get and display results
                results = self.query(query, top_k=5)
                
                if not results:
                    print("❌ No relevant documents found")
                    continue
                
                print(f"\n📋 Found {len(results)} relevant documents:")
                print("-" * 50)
                
                for i, result in enumerate(results, 1):
                    text = result['text']
                    metadata = result['metadata']
                    score = result['score']
                    
                    # Truncate long text for display
                    display_text = text[:200] + "..." if len(text) > 200 else text
                    
                    print(f"\n{i}. Score: {score:.4f}")
                    print(f"   Source: {metadata.get('filename', 'Unknown')}")
                    print(f"   Chunk: {metadata.get('chunk_id', 'N/A')}")
                    print(f"   Text: {display_text}")
                
                # Show formatted context
                context = self.get_context(query, top_k=3)
                print(f"\n📄 Formatted Context for RAG:")
                print("-" * 30)
                print(context[:500] + "..." if len(context) > 500 else context)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main function for standalone execution"""
    retriever = RAGRetriever()
    retriever.interactive_query()


if __name__ == "__main__":
    main()
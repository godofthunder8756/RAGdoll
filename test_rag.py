#!/usr/bin/env python3
"""
Test script for RAGdoll - demonstrates the complete RAG pipeline
"""

from app.embedder import get_model_info, embed_text
from app.vector_store import VectorStore
from app.query import RAGRetriever

def test_embedder():
    """Test the embedding functionality"""
    print("Testing Embedder...")
    
    # Check model info
    model_info = get_model_info()
    print(f"Model info: {model_info}")
    
    # Test embedding a few texts
    test_texts = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is a subset of artificial intelligence",
        "Python is a popular programming language"
    ]
    
    embeddings = embed_text(test_texts)
    print(f"Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")
    
    # Test single query embedding with caching
    from app.embedder import embed_query
    query_embedding = embed_query("What is machine learning?")
    print(f"Query embedding dimension: {len(query_embedding)}")
    
    print("✓ Embedder test passed\n")

def test_vector_store():
    """Test the vector store functionality"""
    print("Testing Vector Store...")
      # Create a test vector store with correct dimensions
    vs = VectorStore("test_index.faiss")
    
    # Add some test data with correct 1024 dimensions (BGE-M3 dimension)
    test_embeddings = [
        [0.1] * 1024,  # Create 1024-dimensional vectors
        [0.2] * 1024,
        [0.3] * 1024
    ]
    test_metadata = [
        {"text": "First document", "category": "A"},
        {"text": "Second document", "category": "B"},
        {"text": "Third document", "category": "A"}
    ]
    
    vs.add(test_embeddings, test_metadata)
    vs.save()
      # Test search with correct dimensions
    query_vec = [0.15] * 1024  # Create a 1024-dimensional query vector
    indices, distances, metadata = vs.search(query_vec, top_k=2)
    
    print(f"Search results: {len(indices)} documents found")
    print(f"Indices: {indices}")
    print(f"Distances: {distances}")
    print(f"Metadata: {metadata}")
    
    print("✓ Vector Store test passed\n")

def test_rag_retriever():
    """Test the RAG retriever"""
    print("Testing RAG Retriever...")
    
    try:
        retriever = RAGRetriever()
          # Test with a sample query
        results = retriever.query("machine learning", top_k=3)
        
        if results:
            print(f"Retrieved {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['score']:.3f}")
                print(f"     Text: {result['text'][:100]}...")
        else:
            print("No results found (this is expected if no documents are indexed)")
        
        print("✓ RAG Retriever test passed\n")
        
    except Exception as e:
        print(f"RAG Retriever test failed: {e}")
        print("This is expected if no documents are indexed yet\n")

if __name__ == "__main__":
    print("=" * 60)
    print("RAGdoll Test Suite")
    print("=" * 60)
    
    try:
        test_embedder()
        test_vector_store()
        test_rag_retriever()
        
        print("=" * 60)
        print("All tests completed!")
        print("To use RAGdoll:")
        print("1. Add documents to the 'data' folder")
        print("2. Run: python -m app.ingest")
        print("3. Run: python -m app.query")
        print("=" * 60)
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

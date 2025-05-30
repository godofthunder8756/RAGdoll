#!/usr/bin/env python3
"""
Test the current RAG system
"""

from app.query import RAGRetriever

def test_rag_system():
    print("🔧 Testing RAG system...")
    
    try:
        # Initialize retriever
        retriever = RAGRetriever()
        print("✅ RAG retriever initialized successfully")
        
        # Get vector store stats
        stats = retriever.vector_store.get_stats()
        print(f"📊 Vector Store Stats:")
        print(f"   Documents: {stats['num_documents']}")
        print(f"   Dimension: {stats['dimension']}")
        print(f"   Index file: {stats['index_file']}")
        
        # Test query
        print("\n🔍 Testing query: 'machine learning'")
        results = retriever.query('machine learning', top_k=3)
        print(f"✅ Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            score = result['score']
            text = result['text'][:100]
            filename = result['metadata'].get('filename', 'Unknown')
            print(f"{i}. Score: {score:.4f} | File: {filename}")
            print(f"   Text: {text}...")
            print()
        
        # Test context generation
        print("📄 Testing context generation...")
        context = retriever.get_context('machine learning', top_k=2)
        print(f"✅ Generated context (length: {len(context)} chars)")
        print("First 200 chars:", context[:200])
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_system()

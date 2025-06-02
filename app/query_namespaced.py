"""
Namespaced RAG Query Interface
Supports querying specific namespaces or across multiple namespaces
Perfect for enterprise knowledge silos
"""

import argparse
from typing import List, Dict, Any, Optional
from app.embedder import embed_text
from app.namespaced_vector_store import NamespacedVectorStore, MultiNamespaceVectorStore
from app.config import DEFAULT_NAMESPACE


class NamespacedRAGRetriever:
    """
    Namespaced RAG retriever that can query specific knowledge silos
    """
    
    def __init__(self, namespace: str = DEFAULT_NAMESPACE):
        """
        Initialize the namespaced RAG retriever
        
        Args:
            namespace: Target namespace for queries
        """
        self.namespace = namespace
        self.vector_store = NamespacedVectorStore(namespace)
    
    def query(self, query_text: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Query the RAG system within the current namespace
        
        Args:
            query_text: The query string
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
        
        Returns:
            List of dictionaries containing text, metadata, and scores
        """
        # Generate embedding for the query
        print(f"🔍 [{self.namespace}] Processing query: {query_text}")
        query_embeddings = embed_text([query_text])
        
        if query_embeddings is None or len(query_embeddings) == 0:
            print("❌ Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]
        
        # Search the namespace-specific vector store
        indices, distances, metadata_list = self.vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by score threshold and format results
        filtered_results = []
        for i, (idx, distance, metadata) in enumerate(zip(indices, distances, metadata_list)):
            # Convert distance to similarity score (FAISS uses L2 distance)
            score = max(0, 1 - distance / 2)
            
            if score >= score_threshold:
                text = metadata.get('text', f'Document {idx}')
                
                filtered_results.append({
                    'text': text,
                    'metadata': metadata,
                    'score': score,
                    'namespace': self.namespace
                })
        
        print(f"✅ [{self.namespace}] Found {len(filtered_results)} relevant documents")
        return filtered_results
    
    def get_context(self, query_text: str, top_k: int = 3, max_context_length: int = 2000) -> str:
        """Get formatted context for RAG generation from the current namespace"""
        results = self.query(query_text, top_k=top_k)
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            text = result['text']
            metadata = result['metadata']
            score = result['score']
            
            # Format context piece with namespace info
            source_info = f"[Namespace: {self.namespace}, Source: {metadata.get('filename', 'Unknown')}]"
            context_piece = f"Document {i} {source_info}:\n{text}\n"
            
            # Check if adding this would exceed max length
            if total_length + len(context_piece) > max_context_length and context_parts:
                break
                
            context_parts.append(context_piece)
            total_length += len(context_piece)
        
        return "\n".join(context_parts)


class MultiNamespaceRAGRetriever:
    """
    Multi-namespace RAG retriever for cross-silo queries
    """
    
    def __init__(self):
        """Initialize the multi-namespace RAG retriever"""
        self.multi_store = MultiNamespaceVectorStore()
    
    def query_namespace(self, query_text: str, namespace: str, top_k: int = 5, 
                       score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Query a specific namespace"""
        retriever = NamespacedRAGRetriever(namespace)
        return retriever.query(query_text, top_k, score_threshold)
    
    def query_all_namespaces(self, query_text: str, top_k: int = 5, 
                           score_threshold: float = 0.0, 
                           namespace_filter: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query across multiple namespaces
        
        Returns:
            Dictionary mapping namespace names to their query results
        """
        print(f"🔍 [Multi-namespace] Processing query: {query_text}")
        query_embeddings = embed_text([query_text])
        
        if query_embeddings is None or len(query_embeddings) == 0:
            print("❌ Failed to generate query embedding")
            return {}
        
        query_embedding = query_embeddings[0]
        
        # Search across namespaces
        raw_results = self.multi_store.search_all_namespaces(
            query_embedding, top_k, namespace_filter
        )
        
        # Format results for each namespace
        formatted_results = {}
        total_docs = 0
        
        for namespace, (indices, distances, metadata_list) in raw_results.items():
            namespace_results = []
            
            for idx, distance, metadata in zip(indices, distances, metadata_list):
                score = max(0, 1 - distance / 2)
                
                if score >= score_threshold:
                    text = metadata.get('text', f'Document {idx}')
                    namespace_results.append({
                        'text': text,
                        'metadata': metadata,
                        'score': score,
                        'namespace': namespace
                    })
            
            if namespace_results:
                formatted_results[namespace] = namespace_results
                total_docs += len(namespace_results)
        
        print(f"✅ [Multi-namespace] Found {total_docs} relevant documents across {len(formatted_results)} namespaces")
        return formatted_results
    
    def query_best_across_namespaces(self, query_text: str, top_k: int = 5,
                                   score_threshold: float = 0.0,
                                   namespace_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Query across namespaces and return the globally best results
        """
        print(f"🔍 [Cross-namespace] Processing query: {query_text}")
        query_embeddings = embed_text([query_text])
        
        if query_embeddings is None or len(query_embeddings) == 0:
            print("❌ Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]
        
        # Get best results across all namespaces
        indices, distances, metadata_list = self.multi_store.search_best_across_namespaces(
            query_embedding, top_k, namespace_filter
        )
        
        # Format results
        filtered_results = []
        for idx, distance, metadata in zip(indices, distances, metadata_list):
            score = max(0, 1 - distance / 2)
            
            if score >= score_threshold:
                text = metadata.get('text', f'Document {idx}')
                namespace = metadata.get('namespace', 'unknown')
                
                filtered_results.append({
                    'text': text,
                    'metadata': metadata,
                    'score': score,
                    'namespace': namespace
                })
        
        print(f"✅ [Cross-namespace] Found {len(filtered_results)} best results across namespaces")
        return filtered_results
    
    def get_cross_namespace_context(self, query_text: str, top_k: int = 3, 
                                  max_context_length: int = 2000,
                                  namespace_filter: Optional[List[str]] = None) -> str:
        """Get formatted context from the best results across namespaces"""
        results = self.query_best_across_namespaces(query_text, top_k, namespace_filter=namespace_filter)
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            text = result['text']
            metadata = result['metadata']
            score = result['score']
            namespace = result['namespace']
            
            # Format context piece with namespace info
            source_info = f"[Namespace: {namespace}, Source: {metadata.get('filename', 'Unknown')}]"
            context_piece = f"Document {i} {source_info}:\n{text}\n"
            
            # Check if adding this would exceed max length
            if total_length + len(context_piece) > max_context_length and context_parts:
                break
                
            context_parts.append(context_piece)
            total_length += len(context_piece)
        
        return "\n".join(context_parts)
    
    def interactive_query(self):
        """Interactive query interface with namespace support"""
        print("\n🤖 RAGdoll Namespaced Interactive Query Interface")
        print("Commands:")
        print("  - Type a query to search all namespaces")
        print("  - 'ns <namespace>' to switch to a specific namespace")
        print("  - 'list' to show available namespaces")
        print("  - 'stats' to show namespace statistics")
        print("  - 'quit' to exit")
        print("-" * 70)
        
        current_namespace = None
        single_retriever = None
        
        while True:
            try:
                if current_namespace:
                    prompt = f"\n💬 [{current_namespace}] Enter your query: "
                else:
                    prompt = "\n💬 [Multi-namespace] Enter your query: "
                
                user_input = input(prompt).strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'list':
                    namespaces = self.multi_store.list_namespaces()
                    print(f"\n📋 Available namespaces: {', '.join(namespaces)}")
                    continue
                
                if user_input.lower() == 'stats':
                    self._show_stats()
                    continue
                
                if user_input.lower().startswith('ns '):
                    target_namespace = user_input[3:].strip()
                    available_namespaces = self.multi_store.list_namespaces()
                    
                    if target_namespace in available_namespaces:
                        current_namespace = target_namespace
                        single_retriever = NamespacedRAGRetriever(current_namespace)
                        print(f"🏢 Switched to namespace: {current_namespace}")
                    else:
                        print(f"❌ Namespace '{target_namespace}' not found. Available: {', '.join(available_namespaces)}")
                    continue
                
                if user_input.lower() == 'multi':
                    current_namespace = None
                    single_retriever = None
                    print("🌐 Switched to multi-namespace mode")
                    continue
                
                if not user_input:
                    continue
                
                # Process query
                if current_namespace and single_retriever:
                    # Single namespace query
                    results = single_retriever.query(user_input, top_k=5)
                    self._display_results(results, f"Results from namespace '{current_namespace}':")
                else:
                    # Multi-namespace query
                    results = self.query_all_namespaces(user_input, top_k=3)
                    self._display_multi_namespace_results(results)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _show_stats(self):
        """Show namespace statistics"""
        stats = self.multi_store.get_all_stats()
        
        print("\n📊 Namespace Statistics:")
        print("=" * 60)
        
        for namespace, stat in stats.items():
            ns_info = stat.get('namespace_info', {})
            print(f"\n🏢 {namespace}")
            print(f"   Description: {ns_info.get('description', 'No description')}")
            print(f"   Documents: {ns_info.get('document_count', 0)}")
            print(f"   Chunks: {stat.get('metadata_entries', 0)}")
            print(f"   Vector Count: {stat.get('num_documents', 0)}")
    
    def _display_results(self, results: List[Dict], title: str):
        """Display query results"""
        if not results:
            print("❌ No relevant documents found.")
            return
        
        print(f"\n{title}")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            score = result['score']
            text = result['text']
            
            print(f"\n{i}. Score: {score:.3f}")
            print(f"   Source: {metadata.get('filename', 'Unknown')}")
            print(f"   Chunk: {metadata.get('chunk_index', 'N/A')}")
            print(f"   Text: {text[:200]}{'...' if len(text) > 200 else ''}")
    
    def _display_multi_namespace_results(self, results: Dict[str, List[Dict]]):
        """Display multi-namespace query results"""
        if not results:
            print("❌ No relevant documents found in any namespace.")
            return
        
        print(f"\n📋 Results from {len(results)} namespaces:")
        print("=" * 60)
        
        for namespace, namespace_results in results.items():
            print(f"\n🏢 Namespace: {namespace} ({len(namespace_results)} results)")
            print("-" * 40)
            
            for i, result in enumerate(namespace_results, 1):
                metadata = result['metadata']
                score = result['score']
                text = result['text']
                
                print(f"\n  {i}. Score: {score:.3f}")
                print(f"     Source: {metadata.get('filename', 'Unknown')}")
                print(f"     Text: {text[:150]}{'...' if len(text) > 150 else ''}")


def main():
    """Main CLI interface for namespaced queries"""
    parser = argparse.ArgumentParser(description="RAGdoll Namespaced Query Interface")
    parser.add_argument("--namespace", help="Target namespace for query")
    parser.add_argument("--query", help="Query text")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--score-threshold", type=float, default=0.0, help="Minimum similarity score")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--list-namespaces", action="store_true", help="List available namespaces")
    parser.add_argument("--stats", action="store_true", help="Show namespace statistics")
    parser.add_argument("--cross-namespace", action="store_true", help="Search across all namespaces")
    
    args = parser.parse_args()
    
    multi_retriever = MultiNamespaceRAGRetriever()
    
    if args.list_namespaces:
        namespaces = multi_retriever.multi_store.list_namespaces()
        print(f"Available namespaces: {', '.join(namespaces)}")
        return
    
    if args.stats:
        multi_retriever._show_stats()
        return
    
    if args.interactive:
        multi_retriever.interactive_query()
        return
    
    if args.query:
        if args.cross_namespace:
            results = multi_retriever.query_best_across_namespaces(args.query, args.top_k, args.score_threshold)
            multi_retriever._display_results(results, "Best results across all namespaces:")
        elif args.namespace:
            retriever = NamespacedRAGRetriever(args.namespace)
            results = retriever.query(args.query, args.top_k, args.score_threshold)
            multi_retriever._display_results(results, f"Results from namespace '{args.namespace}':")
        else:
            results = multi_retriever.query_all_namespaces(args.query, args.top_k, args.score_threshold)
            multi_retriever._display_multi_namespace_results(results)
    else:
        # Default to interactive mode
        multi_retriever.interactive_query()


if __name__ == "__main__":
    main()

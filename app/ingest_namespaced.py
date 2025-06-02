"""
Namespaced Document Ingestion for RAGdoll
Supports ingesting documents into specific namespaces for enterprise knowledge silos
"""

import os
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from app.embedder import embed_text
from app.vector_store import VectorStore
from app.namespaced_vector_store import NamespacedVectorStore, MultiNamespaceVectorStore
from app.config import DATA_DIR, DEFAULT_NAMESPACE


def load_texts_from_folder(folder: str, namespace_hint: Optional[str] = None) -> List[Dict]:
    """Load texts and return with metadata, optionally inferring namespace from folder structure"""
    documents = []
    folder_path = Path(folder)
    
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            try:
                # Infer namespace from folder structure if not explicitly provided
                inferred_namespace = namespace_hint
                if not inferred_namespace:
                    # Use parent directory name as namespace hint
                    relative_path = file_path.relative_to(folder_path)
                    if len(relative_path.parts) > 1:
                        inferred_namespace = relative_path.parts[0].lower()
                    else:
                        inferred_namespace = DEFAULT_NAMESPACE
                
                if file_path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        documents.append({
                            'content': content,
                            'filename': file_path.name,
                            'filepath': str(file_path),
                            'file_type': 'txt',
                            'inferred_namespace': inferred_namespace
                        })
                
                elif file_path.suffix.lower() == '.pdf':
                    try:
                        import PyPDF2
                        with open(file_path, 'rb') as f:
                            pdf = PyPDF2.PdfReader(f)
                            content = " ".join([page.extract_text() for page in pdf.pages])
                            documents.append({
                                'content': content,
                                'filename': file_path.name,
                                'filepath': str(file_path),
                                'file_type': 'pdf',
                                'inferred_namespace': inferred_namespace
                            })
                    except ImportError:
                        print(f"PyPDF2 not installed, skipping {file_path}")
                    except Exception as e:
                        print(f"Error processing PDF {file_path}: {e}")
                        
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
    
    return documents


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i:i + chunk_size]
        if len(chunk) > 0:  # Only add non-empty chunks
            chunks.append(" ".join(chunk))
    
    return chunks


def create_chunks_with_metadata(documents: List[Dict], target_namespace: Optional[str] = None) -> tuple[List[str], List[Dict]]:
    """Create text chunks and corresponding metadata with namespace information"""
    all_chunks = []
    all_metadata = []
    
    for doc in documents:
        chunks = chunk_text(doc['content'])
        # Use target namespace if provided, otherwise use inferred namespace
        namespace = target_namespace or doc.get('inferred_namespace', DEFAULT_NAMESPACE)
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                'text': chunk,  # Store the full chunk text
                'filename': doc['filename'],
                'filepath': doc['filepath'],
                'file_type': doc['file_type'],
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_text_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk,
                'namespace': namespace,
                'inferred_namespace': doc.get('inferred_namespace')
            })
    
    return all_chunks, all_metadata


def ingest_to_namespace(data_dir: str, namespace: str, description: str = ""):
    """Ingest documents into a specific namespace"""
    print(f"[RAGdoll] Ingesting documents into namespace: {namespace}")
    
    # Create namespace if it doesn't exist
    multi_store = MultiNamespaceVectorStore()
    if namespace not in multi_store.list_namespaces():
        multi_store.create_namespace(namespace, description)
    
    # Load documents
    print("[RAGdoll] Loading documents...")
    documents = load_texts_from_folder(data_dir, namespace_hint=namespace)
    print(f"[RAGdoll] Found {len(documents)} documents")
    
    if not documents:
        print("[RAGdoll] No documents found. Make sure to add .txt or .pdf files to the data directory.")
        return False
    
    # Create chunks
    print("[RAGdoll] Creating chunks...")
    chunks, metadata = create_chunks_with_metadata(documents, target_namespace=namespace)
    print(f"[RAGdoll] Created {len(chunks)} chunks")
    
    # Generate embeddings
    print("[RAGdoll] Generating embeddings...")
    embeddings = embed_text(chunks)
    
    # Store in namespace-specific vector store
    print(f"[RAGdoll] Storing in namespace '{namespace}' vector database...")
    vector_store = NamespacedVectorStore(namespace)
    vector_store.add(embeddings, metadata)
    vector_store.save()
    
    print(f"[RAGdoll] Successfully indexed {len(chunks)} chunks from {len(documents)} documents into namespace '{namespace}'")
    return True


def ingest_auto_namespace(data_dir: str):
    """Automatically ingest documents into namespaces based on folder structure"""
    print("[RAGdoll] Auto-ingesting documents with namespace detection...")
    
    # Load documents and group by inferred namespace
    documents = load_texts_from_folder(data_dir)
    if not documents:
        print("[RAGdoll] No documents found.")
        return False
    
    # Group documents by namespace
    namespace_docs = {}
    for doc in documents:
        ns = doc.get('inferred_namespace', DEFAULT_NAMESPACE)
        if ns not in namespace_docs:
            namespace_docs[ns] = []
        namespace_docs[ns].append(doc)
    
    print(f"[RAGdoll] Found documents for {len(namespace_docs)} namespaces: {list(namespace_docs.keys())}")
    
    # Process each namespace
    multi_store = MultiNamespaceVectorStore()
    for namespace, docs in namespace_docs.items():
        print(f"\n[RAGdoll] Processing namespace: {namespace}")
        
        # Create namespace if it doesn't exist
        if namespace not in multi_store.list_namespaces():
            description = f"Auto-created namespace from folder structure: {namespace}"
            multi_store.create_namespace(namespace, description)
        
        # Create chunks
        chunks, metadata = create_chunks_with_metadata(docs, target_namespace=namespace)
        print(f"[RAGdoll] Created {len(chunks)} chunks for namespace '{namespace}'")
        
        # Generate embeddings
        print("[RAGdoll] Generating embeddings...")
        embeddings = embed_text(chunks)
        
        # Store in namespace-specific vector store
        vector_store = NamespacedVectorStore(namespace)
        vector_store.add(embeddings, metadata)
        vector_store.save()
        
        print(f"[RAGdoll] Successfully indexed {len(chunks)} chunks from {len(docs)} documents into namespace '{namespace}'")
    
    return True


def show_namespace_stats():
    """Show statistics for all namespaces"""
    multi_store = MultiNamespaceVectorStore()
    namespaces = multi_store.list_namespaces()
    
    if not namespaces:
        print("No namespaces found.")
        return
    
    print("\n📊 Namespace Statistics:")
    print("=" * 60)
    
    for namespace in namespaces:
        stats = multi_store.get_store(namespace).get_stats()
        ns_info = stats.get('namespace_info', {})
        
        print(f"\n🏢 Namespace: {namespace}")
        print(f"   Description: {ns_info.get('description', 'No description')}")
        print(f"   Documents: {ns_info.get('document_count', 0)}")
        print(f"   Chunks: {stats.get('metadata_entries', 0)}")
        print(f"   Vector Count: {stats.get('num_documents', 0)}")
        print(f"   Created: {ns_info.get('created', 'Unknown')}")
        if 'last_updated' in ns_info:
            print(f"   Last Updated: {ns_info['last_updated']}")
        print(f"   Tags: {', '.join(ns_info.get('tags', []))}")


def main():
    """Main CLI interface for namespaced ingestion"""
    parser = argparse.ArgumentParser(description="RAGdoll Namespaced Document Ingestion")
    parser.add_argument("--data-dir", default=DATA_DIR, help="Directory containing documents")
    parser.add_argument("--namespace", help="Target namespace for ingestion")
    parser.add_argument("--description", default="", help="Description for the namespace")
    parser.add_argument("--auto", action="store_true", help="Auto-detect namespaces from folder structure")
    parser.add_argument("--stats", action="store_true", help="Show namespace statistics")
    parser.add_argument("--create-namespace", help="Create a new empty namespace")
    parser.add_argument("--delete-namespace", help="Delete a namespace (WARNING: destructive)")
    parser.add_argument("--force", action="store_true", help="Force operation (for deletions)")
    
    args = parser.parse_args()
    
    if args.stats:
        show_namespace_stats()
        return
    
    if args.create_namespace:
        multi_store = MultiNamespaceVectorStore()
        if multi_store.create_namespace(args.create_namespace, args.description):
            print(f"Created namespace: {args.create_namespace}")
        return
    
    if args.delete_namespace:
        multi_store = MultiNamespaceVectorStore()
        if multi_store.delete_namespace(args.delete_namespace, args.force):
            print(f"Deleted namespace: {args.delete_namespace}")
        return
    
    if args.auto:
        ingest_auto_namespace(args.data_dir)
    elif args.namespace:
        ingest_to_namespace(args.data_dir, args.namespace, args.description)
    else:
        # Default behavior: ingest to default namespace (backward compatibility)
        print("[RAGdoll] No namespace specified, using default namespace")
        ingest_to_namespace(args.data_dir, DEFAULT_NAMESPACE, "Default namespace for general documents")


if __name__ == "__main__":
    main()

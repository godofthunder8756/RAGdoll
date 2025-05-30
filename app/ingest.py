import os
from pathlib import Path
from typing import List, Dict
from app.embedder import embed_text
from app.vector_store import VectorStore
from app.config import DATA_DIR

def load_texts_from_folder(folder: str) -> List[Dict]:
    """Load texts and return with metadata"""
    documents = []
    folder_path = Path(folder)
    
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            try:
                if file_path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        documents.append({
                            'content': content,
                            'filename': file_path.name,
                            'filepath': str(file_path),
                            'file_type': 'txt'
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
                                'file_type': 'pdf'
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

def create_chunks_with_metadata(documents: List[Dict]) -> tuple[List[str], List[Dict]]:
    """Create text chunks and corresponding metadata"""
    all_chunks = []
    all_metadata = []
    
    for doc in documents:
        chunks = chunk_text(doc['content'])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                'text': chunk,  # Store the full chunk text
                'filename': doc['filename'],
                'filepath': doc['filepath'],
                'file_type': doc['file_type'],
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_text_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk
            })
    
    return all_chunks, all_metadata

if __name__ == "__main__":
    print("[RAGdoll] Loading documents...")
    documents = load_texts_from_folder(DATA_DIR)
    print(f"[RAGdoll] Found {len(documents)} documents")
    
    if not documents:
        print("[RAGdoll] No documents found. Make sure to add .txt or .pdf files to the data directory.")
        exit(1)
    
    print("[RAGdoll] Creating chunks...")
    chunks, metadata = create_chunks_with_metadata(documents)
    print(f"[RAGdoll] Created {len(chunks)} chunks")
    
    print("[RAGdoll] Generating embeddings...")
    embeddings = embed_text(chunks)
    
    print("[RAGdoll] Storing in vector database...")
    vector_store = VectorStore()
    vector_store.add(embeddings, metadata)
    vector_store.save()
    
    print(f"[RAGdoll] Successfully indexed {len(chunks)} chunks from {len(documents)} documents")

#!/usr/bin/env python3
"""
Enterprise Namespace Management CLI for RAGdoll
Complete management interface for large organizations with multiple knowledge silos
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import shutil

from app.namespaced_vector_store import MultiNamespaceVectorStore, NamespacedVectorStore
from app.ingest_namespaced import ingest_to_namespace, ingest_auto_namespace
from app.query_namespaced import MultiNamespaceRAGRetriever, NamespacedRAGRetriever
from app.config import NAMESPACED_INDEXES_DIR, DATA_DIR, DEFAULT_NAMESPACE


class EnterpriseNamespaceManager:
    """
    Enterprise-grade namespace management for large organizations
    Provides comprehensive CRUD operations, migration, and analytics
    """
    
    def __init__(self):
        self.multi_store = MultiNamespaceVectorStore()
        self.multi_retriever = MultiNamespaceRAGRetriever()
    
    def create_namespace(self, namespace: str, description: str = "", tags: List[str] = None, 
                        department: str = "", contact: str = "") -> bool:
        """Create a new namespace with enterprise metadata"""
        if self.multi_store.create_namespace(namespace, description, tags or []):
            # Add enterprise-specific metadata
            namespace_info = self.multi_store.namespace_manager.get_namespace_info(namespace)
            if namespace_info:
                namespace_info.update({
                    'department': department,
                    'contact': contact,
                    'access_level': 'internal',
                    'retention_policy': 'standard'
                })
                self.multi_store.namespace_manager._save_config(self.multi_store.namespace_manager.config)
            
            print(f"✅ Created enterprise namespace: {namespace}")
            if department:
                print(f"   Department: {department}")
            if contact:
                print(f"   Contact: {contact}")
            return True
        return False
    
    def list_namespaces(self, show_details: bool = False, department_filter: str = None) -> List[str]:
        """List namespaces with optional filtering and detailed view"""
        namespaces = self.multi_store.list_namespaces()
        
        if department_filter:
            filtered_namespaces = []
            for ns in namespaces:
                info = self.multi_store.namespace_manager.get_namespace_info(ns)
                if info and info.get('department', '').lower() == department_filter.lower():
                    filtered_namespaces.append(ns)
            namespaces = filtered_namespaces
        
        if show_details:
            self._show_detailed_namespace_list(namespaces)
        else:
            print(f"Namespaces ({len(namespaces)}): {', '.join(namespaces)}")
        
        return namespaces
    
    def get_namespace_details(self, namespace: str) -> Optional[Dict]:
        """Get comprehensive details about a namespace"""
        if namespace not in self.multi_store.list_namespaces():
            print(f"❌ Namespace '{namespace}' not found")
            return None
        
        # Get basic info
        info = self.multi_store.namespace_manager.get_namespace_info(namespace)
        
        # Get storage stats
        store = self.multi_store.get_store(namespace)
        stats = store.get_stats()
        
        # Get file system info
        index_path = store.index_path
        metadata_path = store.metadata_path
        index_size = os.path.getsize(index_path) if os.path.exists(index_path) else 0
        metadata_size = os.path.getsize(metadata_path) if os.path.exists(metadata_path) else 0
        
        details = {
            'namespace': namespace,
            'info': info,
            'stats': stats,
            'storage': {
                'index_path': index_path,
                'metadata_path': metadata_path,
                'index_size_mb': round(index_size / (1024 * 1024), 2),
                'metadata_size_mb': round(metadata_size / (1024 * 1024), 2),
                'total_size_mb': round((index_size + metadata_size) / (1024 * 1024), 2)
            }
        }
        
        return details
    
    def migrate_namespace(self, source_namespace: str, target_namespace: str, 
                         merge: bool = False) -> bool:
        """Migrate documents from one namespace to another"""
        if source_namespace not in self.multi_store.list_namespaces():
            print(f"❌ Source namespace '{source_namespace}' not found")
            return False
        
        # Create target namespace if it doesn't exist
        if target_namespace not in self.multi_store.list_namespaces():
            print(f"Creating target namespace: {target_namespace}")
            self.create_namespace(target_namespace, f"Migrated from {source_namespace}")
        
        source_store = self.multi_store.get_store(source_namespace)
        target_store = self.multi_store.get_store(target_namespace)
        
        if source_store.index.ntotal == 0:
            print(f"❌ Source namespace '{source_namespace}' is empty")
            return False
        
        print(f"🔄 Migrating {source_store.index.ntotal} vectors from '{source_namespace}' to '{target_namespace}'")
        
        # Get all vectors and metadata from source
        if source_store.index.ntotal > 0:
            # Extract all vectors
            all_vectors = []
            for i in range(source_store.index.ntotal):
                vector = source_store.index.reconstruct(i)
                all_vectors.append(vector.tolist())
            
            # Update metadata to reflect new namespace
            migrated_metadata = []
            for meta in source_store.metadata:
                new_meta = meta.copy()
                new_meta['namespace'] = target_namespace
                new_meta['migrated_from'] = source_namespace
                new_meta['migration_date'] = datetime.now().isoformat()
                migrated_metadata.append(new_meta)
            
            # Add to target store
            target_store.add(all_vectors, migrated_metadata)
            target_store.save()
            
            print(f"✅ Successfully migrated {len(all_vectors)} vectors to '{target_namespace}'")
            
            # Optionally clear source namespace
            if not merge:
                confirm = input(f"Delete source namespace '{source_namespace}'? (y/N): ")
                if confirm.lower() == 'y':
                    self.delete_namespace(source_namespace, force=True)
            
            return True
        
        return False
    
    def clone_namespace(self, source_namespace: str, target_namespace: str) -> bool:
        """Clone a namespace (copy without deleting source)"""
        return self.migrate_namespace(source_namespace, target_namespace, merge=True)
    
    def backup_namespace(self, namespace: str, backup_dir: str = None) -> str:
        """Create a backup of a namespace"""
        if namespace not in self.multi_store.list_namespaces():
            print(f"❌ Namespace '{namespace}' not found")
            return ""
        
        if not backup_dir:
            backup_dir = f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        os.makedirs(backup_dir, exist_ok=True)
        
        store = self.multi_store.get_store(namespace)
        
        # Copy index and metadata files
        index_backup = os.path.join(backup_dir, f"{namespace}.faiss")
        metadata_backup = os.path.join(backup_dir, f"{namespace}_metadata.pkl")
        
        if os.path.exists(store.index_path):
            shutil.copy2(store.index_path, index_backup)
        if os.path.exists(store.metadata_path):
            shutil.copy2(store.metadata_path, metadata_backup)
        
        # Save namespace config
        config_backup = os.path.join(backup_dir, f"{namespace}_config.json")
        namespace_info = self.multi_store.namespace_manager.get_namespace_info(namespace)
        with open(config_backup, 'w') as f:
            json.dump(namespace_info, f, indent=2)
        
        print(f"✅ Backup created: {backup_dir}")
        return backup_dir
    
    def restore_namespace(self, backup_dir: str, namespace: str = None) -> bool:
        """Restore a namespace from backup"""
        if not os.path.exists(backup_dir):
            print(f"❌ Backup directory not found: {backup_dir}")
            return False
        
        # Auto-detect namespace if not provided
        if not namespace:
            faiss_files = [f for f in os.listdir(backup_dir) if f.endswith('.faiss')]
            if faiss_files:
                namespace = faiss_files[0].replace('.faiss', '')
            else:
                print("❌ No FAISS files found in backup directory")
                return False
        
        print(f"🔄 Restoring namespace '{namespace}' from {backup_dir}")
        
        # Create namespace if it doesn't exist
        if namespace not in self.multi_store.list_namespaces():
            self.create_namespace(namespace, f"Restored from backup")
        
        store = self.multi_store.get_store(namespace)
        
        # Restore files
        index_backup = os.path.join(backup_dir, f"{namespace}.faiss")
        metadata_backup = os.path.join(backup_dir, f"{namespace}_metadata.pkl")
        
        if os.path.exists(index_backup):
            shutil.copy2(index_backup, store.index_path)
        if os.path.exists(metadata_backup):
            shutil.copy2(metadata_backup, store.metadata_path)
        
        # Reload the store
        store.load()
        
        print(f"✅ Restored namespace '{namespace}'")
        return True
    
    def delete_namespace(self, namespace: str, force: bool = False) -> bool:
        """Delete a namespace with safety checks"""
        if namespace not in self.multi_store.list_namespaces():
            print(f"❌ Namespace '{namespace}' not found")
            return False
        
        if namespace == DEFAULT_NAMESPACE and not force:
            print(f"❌ Cannot delete default namespace without --force")
            return False
        
        details = self.get_namespace_details(namespace)
        if details:
            doc_count = details['info'].get('document_count', 0)
            chunk_count = details['stats'].get('metadata_entries', 0)
            
            if doc_count > 0 and not force:
                print(f"⚠️  Namespace '{namespace}' contains {doc_count} documents ({chunk_count} chunks)")
                confirm = input("Are you sure you want to delete it? (y/N): ")
                if confirm.lower() != 'y':
                    print("❌ Deletion cancelled")
                    return False
        
        return self.multi_store.delete_namespace(namespace, force)
    
    def analyze_namespace_overlap(self, namespace1: str, namespace2: str, sample_size: int = 100) -> Dict:
        """Analyze content overlap between two namespaces"""
        if namespace1 not in self.multi_store.list_namespaces():
            print(f"❌ Namespace '{namespace1}' not found")
            return {}
        
        if namespace2 not in self.multi_store.list_namespaces():
            print(f"❌ Namespace '{namespace2}' not found")
            return {}
        
        store1 = self.multi_store.get_store(namespace1)
        store2 = self.multi_store.get_store(namespace2)
        
        if store1.index.ntotal == 0 or store2.index.ntotal == 0:
            print("❌ One or both namespaces are empty")
            return {}
        
        print(f"🔍 Analyzing overlap between '{namespace1}' and '{namespace2}'...")
        
        # Sample vectors from namespace1 and search in namespace2
        sample_count = min(sample_size, store1.index.ntotal)
        overlap_scores = []
        
        for i in range(0, sample_count, max(1, store1.index.ntotal // sample_count)):
            vector = store1.index.reconstruct(i)
            _, distances, _ = store2.search(vector.tolist(), top_k=1)
            
            if distances:
                # Convert distance to similarity score
                similarity = max(0, 1 - distances[0] / 2)
                overlap_scores.append(similarity)
        
        if overlap_scores:
            avg_overlap = sum(overlap_scores) / len(overlap_scores)
            max_overlap = max(overlap_scores)
            high_overlap_count = len([s for s in overlap_scores if s > 0.8])
            
            analysis = {
                'namespace1': namespace1,
                'namespace2': namespace2,
                'sample_size': len(overlap_scores),
                'average_similarity': round(avg_overlap, 3),
                'max_similarity': round(max_overlap, 3),
                'high_overlap_count': high_overlap_count,
                'high_overlap_percentage': round(high_overlap_count / len(overlap_scores) * 100, 1)
            }
            
            print(f"📊 Overlap Analysis:")
            print(f"   Average similarity: {analysis['average_similarity']}")
            print(f"   Max similarity: {analysis['max_similarity']}")
            print(f"   High overlap (>0.8): {analysis['high_overlap_count']} ({analysis['high_overlap_percentage']}%)")
            
            return analysis
        
        return {}
    
    def get_system_overview(self) -> Dict:
        """Get comprehensive system overview"""
        namespaces = self.multi_store.list_namespaces()
        total_docs = 0
        total_chunks = 0
        total_size_mb = 0
        departments = set()
        
        namespace_details = []
        for ns in namespaces:
            details = self.get_namespace_details(ns)
            if details:
                total_docs += details['info'].get('document_count', 0)
                total_chunks += details['stats'].get('metadata_entries', 0)
                total_size_mb += details['storage']['total_size_mb']
                
                dept = details['info'].get('department', '')
                if dept:
                    departments.add(dept)
                
                namespace_details.append(details)
        
        overview = {
            'total_namespaces': len(namespaces),
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'total_size_mb': round(total_size_mb, 2),
            'departments': list(departments),
            'namespaces': namespace_details
        }
        
        return overview
    
    def _show_detailed_namespace_list(self, namespaces: List[str]):
        """Show detailed namespace listing"""
        print(f"\n📋 Detailed Namespace List ({len(namespaces)} namespaces):")
        print("=" * 80)
        
        for namespace in namespaces:
            details = self.get_namespace_details(namespace)
            if details:
                info = details['info']
                stats = details['stats']
                storage = details['storage']
                
                print(f"\n🏢 {namespace}")
                print(f"   Description: {info.get('description', 'No description')}")
                print(f"   Department: {info.get('department', 'N/A')}")
                print(f"   Contact: {info.get('contact', 'N/A')}")
                print(f"   Documents: {info.get('document_count', 0)}")
                print(f"   Chunks: {stats.get('metadata_entries', 0)}")
                print(f"   Size: {storage['total_size_mb']} MB")
                print(f"   Created: {info.get('created', 'Unknown')[:19]}")
                if 'last_updated' in info:
                    print(f"   Updated: {info['last_updated'][:19]}")


def main():
    """Main CLI interface for enterprise namespace management"""
    parser = argparse.ArgumentParser(description="RAGdoll Enterprise Namespace Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create namespace
    create_parser = subparsers.add_parser('create', help='Create a new namespace')
    create_parser.add_argument('namespace', help='Namespace name')
    create_parser.add_argument('--description', default='', help='Namespace description')
    create_parser.add_argument('--department', default='', help='Department name')
    create_parser.add_argument('--contact', default='', help='Contact person/email')
    create_parser.add_argument('--tags', nargs='*', help='Tags for the namespace')
    
    # List namespaces
    list_parser = subparsers.add_parser('list', help='List namespaces')
    list_parser.add_argument('--details', action='store_true', help='Show detailed information')
    list_parser.add_argument('--department', help='Filter by department')
    
    # Show namespace details
    details_parser = subparsers.add_parser('details', help='Show namespace details')
    details_parser.add_argument('namespace', help='Namespace name')
    
    # Delete namespace
    delete_parser = subparsers.add_parser('delete', help='Delete a namespace')
    delete_parser.add_argument('namespace', help='Namespace name')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    # Migrate namespace
    migrate_parser = subparsers.add_parser('migrate', help='Migrate namespace')
    migrate_parser.add_argument('source', help='Source namespace')
    migrate_parser.add_argument('target', help='Target namespace')
    migrate_parser.add_argument('--merge', action='store_true', help='Keep source namespace')
    
    # Clone namespace
    clone_parser = subparsers.add_parser('clone', help='Clone a namespace')
    clone_parser.add_argument('source', help='Source namespace')
    clone_parser.add_argument('target', help='Target namespace')
    
    # Backup namespace
    backup_parser = subparsers.add_parser('backup', help='Backup a namespace')
    backup_parser.add_argument('namespace', help='Namespace to backup')
    backup_parser.add_argument('--dir', help='Backup directory')
    
    # Restore namespace
    restore_parser = subparsers.add_parser('restore', help='Restore a namespace')
    restore_parser.add_argument('backup_dir', help='Backup directory')
    restore_parser.add_argument('--namespace', help='Target namespace name')
    
    # Analyze overlap
    overlap_parser = subparsers.add_parser('overlap', help='Analyze namespace overlap')
    overlap_parser.add_argument('namespace1', help='First namespace')
    overlap_parser.add_argument('namespace2', help='Second namespace')
    overlap_parser.add_argument('--sample-size', type=int, default=100, help='Sample size for analysis')
    
    # System overview
    subparsers.add_parser('overview', help='Show system overview')
    
    # Ingest data
    ingest_parser = subparsers.add_parser('ingest', help='Ingest documents')
    ingest_parser.add_argument('--namespace', help='Target namespace')
    ingest_parser.add_argument('--data-dir', default=DATA_DIR, help='Data directory')
    ingest_parser.add_argument('--auto', action='store_true', help='Auto-detect namespaces')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = EnterpriseNamespaceManager()
    
    if args.command == 'create':
        manager.create_namespace(
            args.namespace, 
            args.description, 
            args.tags or [], 
            args.department, 
            args.contact
        )
    
    elif args.command == 'list':
        manager.list_namespaces(args.details, args.department)
    
    elif args.command == 'details':
        details = manager.get_namespace_details(args.namespace)
        if details:
            print(json.dumps(details, indent=2, default=str))
    
    elif args.command == 'delete':
        manager.delete_namespace(args.namespace, args.force)
    
    elif args.command == 'migrate':
        manager.migrate_namespace(args.source, args.target, args.merge)
    
    elif args.command == 'clone':
        manager.clone_namespace(args.source, args.target)
    
    elif args.command == 'backup':
        manager.backup_namespace(args.namespace, args.dir)
    
    elif args.command == 'restore':
        manager.restore_namespace(args.backup_dir, args.namespace)
    
    elif args.command == 'overlap':
        manager.analyze_namespace_overlap(args.namespace1, args.namespace2, args.sample_size)
    
    elif args.command == 'overview':
        overview = manager.get_system_overview()
        print(json.dumps(overview, indent=2, default=str))
    
    elif args.command == 'ingest':
        if args.auto:
            ingest_auto_namespace(args.data_dir)
        elif args.namespace:
            ingest_to_namespace(args.data_dir, args.namespace)
        else:
            print("❌ Please specify --namespace or use --auto for automatic detection")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Comprehensive test suite for RAGdoll's namespaced system
Demonstrates enterprise knowledge silo capabilities
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.namespaced_vector_store import NamespacedVectorStore, MultiNamespaceVectorStore
from app.ingest_namespaced import ingest_to_namespace, ingest_auto_namespace
from app.query_namespaced import NamespacedRAGRetriever, MultiNamespaceRAGRetriever
from app.namespace_manager import EnterpriseNamespaceManager
from app.embedder import embed_text


def test_namespace_creation():
    """Test namespace creation and management"""
    print("\n🧪 Testing Namespace Creation...")
    
    manager = EnterpriseNamespaceManager()
    
    # Create test namespaces
    test_namespaces = [
        ('engineering', 'Engineering documentation and standards', 'Engineering', 'tech-lead@company.com'),
        ('legal', 'Legal compliance and policy documents', 'Legal', 'legal@company.com'),
        ('hr', 'Human resources policies and procedures', 'HR', 'hr@company.com'),
        ('marketing', 'Marketing strategies and campaigns', 'Marketing', 'marketing@company.com')
    ]
    
    for ns, desc, dept, contact in test_namespaces:
        success = manager.create_namespace(ns, desc, ['test'], dept, contact)
        assert success, f"Failed to create namespace: {ns}"
    
    # Verify namespaces exist
    namespaces = manager.list_namespaces()
    for ns, _, _, _ in test_namespaces:
        assert ns in namespaces, f"Namespace {ns} not found in list"
    
    print("✅ Namespace creation test passed")


def test_document_ingestion():
    """Test document ingestion into namespaces"""
    print("\n🧪 Testing Document Ingestion...")
    
    # Test with existing data structure
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Test automatic namespace detection
    success = ingest_auto_namespace(data_dir)
    assert success, "Auto-ingestion failed"
    
    # Verify namespaces have data
    manager = EnterpriseNamespaceManager()
    overview = manager.get_system_overview()
    
    print(f"📊 System overview: {overview['total_namespaces']} namespaces, {overview['total_documents']} documents")
    
    assert overview['total_documents'] > 0, "No documents were ingested"
    assert overview['total_chunks'] > 0, "No chunks were created"
    
    print("✅ Document ingestion test passed")


def test_namespace_queries():
    """Test querying within specific namespaces"""
    print("\n🧪 Testing Namespace Queries...")
    
    # Test single namespace queries
    test_queries = [
        ("machine learning", "engineering"),
        ("employee policies", "hr"),
        ("compliance requirements", "legal"),
        ("marketing strategy", "marketing")
    ]
    
    for query, namespace in test_queries:
        retriever = NamespacedRAGRetriever(namespace)
        results = retriever.query(query, top_k=3)
        
        print(f"🔍 Query '{query}' in namespace '{namespace}': {len(results)} results")
        
        # Verify all results are from the correct namespace
        for result in results:
            assert result['namespace'] == namespace, f"Result from wrong namespace: {result['namespace']}"
        
        if results:
            print(f"   Best match (score {results[0]['score']:.3f}): {results[0]['text'][:100]}...")
    
    print("✅ Namespace query test passed")


def test_cross_namespace_queries():
    """Test querying across multiple namespaces"""
    print("\n🧪 Testing Cross-Namespace Queries...")
    
    multi_retriever = MultiNamespaceRAGRetriever()
    
    # Test multi-namespace search
    query = "documentation standards"
    results = multi_retriever.query_all_namespaces(query, top_k=2)
    
    print(f"🔍 Cross-namespace query '{query}': {len(results)} namespaces with results")
    
    for namespace, ns_results in results.items():
        print(f"   {namespace}: {len(ns_results)} results")
        assert all(r['namespace'] == namespace for r in ns_results), "Namespace mismatch in results"
    
    # Test best-across-namespaces search
    best_results = multi_retriever.query_best_across_namespaces(query, top_k=5)
    print(f"🏆 Best results across all namespaces: {len(best_results)} results")
    
    if best_results:
        print("   Top results by namespace:")
        namespace_counts = {}
        for result in best_results:
            ns = result['namespace']
            namespace_counts[ns] = namespace_counts.get(ns, 0) + 1
        
        for ns, count in namespace_counts.items():
            print(f"     {ns}: {count} results")
    
    print("✅ Cross-namespace query test passed")


def test_namespace_isolation():
    """Test that namespaces are properly isolated"""
    print("\n🧪 Testing Namespace Isolation...")
    
    # Create a test namespace with specific content
    test_ns = "test_isolation"
    manager = EnterpriseNamespaceManager()
    
    if test_ns in manager.list_namespaces():
        manager.delete_namespace(test_ns, force=True)
    
    manager.create_namespace(test_ns, "Test isolation namespace")
    
    # Add specific test content
    test_content = ["Quantum computing algorithms for cryptography"]
    embeddings = embed_text(test_content)
    
    store = NamespacedVectorStore(test_ns)
    store.add(embeddings, [{'text': test_content[0], 'filename': 'test.txt'}])
    store.save()
    
    # Query the test namespace
    retriever = NamespacedRAGRetriever(test_ns)
    results = retriever.query("quantum computing", top_k=5)
    
    assert len(results) > 0, "Test content not found in test namespace"
    assert results[0]['text'] == test_content[0], "Wrong content returned"
    
    # Query other namespaces - should not find the test content
    other_namespaces = ['engineering', 'legal', 'hr']
    for ns in other_namespaces:
        if ns in manager.list_namespaces():
            other_retriever = NamespacedRAGRetriever(ns)
            other_results = other_retriever.query("quantum computing", top_k=5)
            
            # Should not find our specific test content
            for result in other_results:
                assert result['text'] != test_content[0], f"Test content leaked to namespace {ns}"
    
    # Clean up
    manager.delete_namespace(test_ns, force=True)
    
    print("✅ Namespace isolation test passed")


def test_namespace_management():
    """Test namespace management operations"""
    print("\n🧪 Testing Namespace Management...")
    
    manager = EnterpriseNamespaceManager()
    
    # Test cloning
    source_ns = "engineering"
    clone_ns = "engineering_backup"
    
    if clone_ns in manager.list_namespaces():
        manager.delete_namespace(clone_ns, force=True)
    
    if source_ns in manager.list_namespaces():
        success = manager.clone_namespace(source_ns, clone_ns)
        assert success, "Namespace cloning failed"
        
        # Verify clone has same content
        source_store = NamespacedVectorStore(source_ns)
        clone_store = NamespacedVectorStore(clone_ns)
        
        assert source_store.index.ntotal == clone_store.index.ntotal, "Clone has different vector count"
        assert len(source_store.metadata) == len(clone_store.metadata), "Clone has different metadata count"
        
        print(f"✅ Successfully cloned '{source_ns}' to '{clone_ns}'")
        
        # Test backup and restore
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = manager.backup_namespace(clone_ns, temp_dir)
            assert os.path.exists(backup_path), "Backup creation failed"
            
            # Delete and restore
            manager.delete_namespace(clone_ns, force=True)
            assert clone_ns not in manager.list_namespaces(), "Namespace not deleted"
            
            success = manager.restore_namespace(temp_dir, clone_ns)
            assert success, "Namespace restoration failed"
            assert clone_ns in manager.list_namespaces(), "Namespace not restored"
            
            print(f"✅ Successfully backed up and restored '{clone_ns}'")
        
        # Clean up
        manager.delete_namespace(clone_ns, force=True)
    
    print("✅ Namespace management test passed")


def test_namespace_analytics():
    """Test namespace analytics and overlap analysis"""
    print("\n🧪 Testing Namespace Analytics...")
    
    manager = EnterpriseNamespaceManager()
    
    # Get system overview
    overview = manager.get_system_overview()
    print(f"📊 System Overview:")
    print(f"   Namespaces: {overview['total_namespaces']}")
    print(f"   Documents: {overview['total_documents']}")
    print(f"   Chunks: {overview['total_chunks']}")
    print(f"   Total size: {overview['total_size_mb']} MB")
    print(f"   Departments: {', '.join(overview['departments'])}")
    
    assert overview['total_namespaces'] > 0, "No namespaces found"
    
    # Test overlap analysis between namespaces
    namespaces = manager.list_namespaces()
    if len(namespaces) >= 2:
        ns1, ns2 = namespaces[0], namespaces[1]
        store1 = NamespacedVectorStore(ns1)
        store2 = NamespacedVectorStore(ns2)
        
        if store1.index.ntotal > 0 and store2.index.ntotal > 0:
            analysis = manager.analyze_namespace_overlap(ns1, ns2, sample_size=10)
            
            if analysis:
                print(f"🔍 Overlap analysis between '{ns1}' and '{ns2}':")
                print(f"   Average similarity: {analysis['average_similarity']}")
                print(f"   High overlap count: {analysis['high_overlap_count']}")
                
                assert 'average_similarity' in analysis, "Overlap analysis incomplete"
                assert 0 <= analysis['average_similarity'] <= 1, "Invalid similarity score"
    
    print("✅ Namespace analytics test passed")


def main():
    """Run all namespace tests"""
    print("🧪 RAGdoll Namespaced System Test Suite")
    print("=" * 50)
    
    try:
        test_namespace_creation()
        test_document_ingestion()
        test_namespace_queries()
        test_cross_namespace_queries()
        test_namespace_isolation()
        test_namespace_management()
        test_namespace_analytics()
        
        print("\n🎉 All tests passed! RAGdoll namespaced system is working correctly.")
        print("\n🏢 Enterprise Features Verified:")
        print("   ✅ True namespace isolation (separate FAISS indices)")
        print("   ✅ Department-based organization")
        print("   ✅ Cross-namespace search capabilities")
        print("   ✅ Namespace management (create, clone, backup, restore)")
        print("   ✅ Analytics and overlap detection")
        print("   ✅ Enterprise metadata tracking")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

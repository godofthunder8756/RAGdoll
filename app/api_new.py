#!/usr/bin/env python3
"""
FastAPI REST API for RAGdoll Enterprise
Provides HTTP endpoints for namespaced document retrieval and management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
import uvicorn
from datetime import datetime
import asyncio
import os

from app.query_namespaced import NamespacedRAGRetriever, MultiNamespaceRAGRetriever
from app.namespace_manager import EnterpriseNamespaceManager
from app.ingest_namespaced import ingest_to_namespace, ingest_auto_namespace
from app.config import DEFAULT_NAMESPACE, DATA_DIR
from app.auth import (
    login_for_access_token, get_current_active_user, get_current_user_profile,
    require_namespace_access, can_read, can_write, can_manage_namespaces, can_admin,
    LoginRequest, Token, User, UserRole
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI router (optional for backward compatibility)
try:
    from app.openai_api import router as openai_router
    OPENAI_AVAILABLE = True
    logger.info("OpenAI integration enabled with GPT-4o support")
except ImportError:
    logger.warning("OpenAI integration not available - install openai package to enable")
    OPENAI_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="RAGdoll Enterprise API",
    description="Enterprise-grade namespaced document retrieval and management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include OpenAI GPT-4o integration routes if available
if OPENAI_AVAILABLE:
    app.include_router(openai_router, prefix="/api/v1/openai", tags=["OpenAI GPT-4o"])
    logger.info("OpenAI GPT-4o integration enabled and routes registered")
else:
    logger.info("OpenAI GPT-4o integration disabled")

# Initialize managers
multi_retriever = MultiNamespaceRAGRetriever()
namespace_manager = EnterpriseNamespaceManager()

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str = Field(..., description="The search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    namespace_filter: Optional[List[str]] = Field(default=None, description="Filter by specific namespaces")

class QueryResult(BaseModel):
    text: str
    score: float
    namespace: str
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]
    total_results: int
    processing_time_ms: float
    namespaces_searched: List[str]

class NamespaceInfo(BaseModel):
    namespace: str
    description: str
    department: Optional[str] = None
    contact: Optional[str] = None
    document_count: int
    chunk_count: int
    created: str
    last_updated: Optional[str] = None
    tags: List[str] = []

class CreateNamespaceRequest(BaseModel):
    namespace: str = Field(..., description="Namespace identifier")
    description: str = Field(default="", description="Namespace description")
    department: Optional[str] = Field(default=None, description="Department name")
    contact: Optional[str] = Field(default=None, description="Contact person/email")
    tags: List[str] = Field(default=[], description="Tags for categorization")

class IngestRequest(BaseModel):
    namespace: Optional[str] = Field(default=None, description="Target namespace (auto-detect if not provided)")
    description: str = Field(default="", description="Description for the namespace")

class OverlapAnalysis(BaseModel):
    namespace1: str
    namespace2: str
    sample_size: int
    average_similarity: float
    max_similarity: float
    high_overlap_count: int
    high_overlap_percentage: float

class SystemOverview(BaseModel):
    total_namespaces: int
    total_documents: int
    total_chunks: int
    total_size_mb: float
    departments: List[str]
    namespaces: List[NamespaceInfo]

# API Endpoints

@app.get("/")
async def root():
    """API health check and information"""
    return {
        "message": "RAGdoll Enterprise API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "auth": {
            "login": "/auth/login",
            "profile": "/auth/profile"
        }
    }

# Authentication Endpoints

@app.post("/auth/login", response_model=Token)
async def login(form_data: LoginRequest):
    """Login to get access token"""
    return login_for_access_token(form_data)

@app.get("/auth/profile", response_model=User)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return get_current_user_profile(current_user)

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        namespaces = namespace_manager.list_namespaces()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "namespaces_available": len(namespaces),
            "api_endpoints": [
                "/auth/login",
                "/auth/profile",
                "/query/{namespace}",
                "/query/multi",
                "/query/cross-namespace",
                "/namespaces",
                "/namespaces/{namespace}",
                "/ingest",
                "/system/overview"
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Query Endpoints

@app.post("/query/{namespace}", response_model=QueryResponse)
async def query_namespace(
    namespace: str,
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Query documents within a specific namespace"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check permissions
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        if not require_namespace_access(namespace, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to namespace '{namespace}'")
        
        if namespace not in namespace_manager.list_namespaces():
            raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' not found")
        
        retriever = NamespacedRAGRetriever(namespace)
        results = retriever.query(
            request.query, 
            top_k=request.top_k, 
            score_threshold=request.score_threshold
        )
        
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return QueryResponse(
            query=request.query,
            results=[QueryResult(**result) for result in results],
            total_results=len(results),
            processing_time_ms=round(processing_time, 2),
            namespaces_searched=[namespace]
        )
        
    except Exception as e:
        logger.error(f"Query failed for namespace {namespace}: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/query/multi", response_model=Dict[str, List[QueryResult]])
async def query_multiple_namespaces(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Query across multiple namespaces, returning results grouped by namespace"""
    try:
        # Check permissions
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Filter namespaces based on user access
        target_namespaces = request.namespace_filter
        if target_namespaces:
            # Check access to requested namespaces
            for ns in target_namespaces:
                if not require_namespace_access(ns, current_user):
                    raise HTTPException(status_code=403, detail=f"Access denied to namespace '{ns}'")
        else:
            # Get all accessible namespaces for user
            all_namespaces = namespace_manager.list_namespaces()
            if UserRole.ADMIN in current_user.roles or "*" in current_user.namespaces:
                target_namespaces = all_namespaces
            else:
                target_namespaces = [ns for ns in all_namespaces if ns in current_user.namespaces]
        
        results = multi_retriever.query_all_namespaces(
            request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            namespace_filter=target_namespaces
        )
        
        # Convert to response format
        response = {}
        for namespace, ns_results in results.items():
            response[namespace] = [QueryResult(**result) for result in ns_results]
        
        return response
        
    except Exception as e:
        logger.error(f"Multi-namespace query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/query/cross-namespace", response_model=QueryResponse)
async def query_cross_namespace(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Query across namespaces and return the globally best results"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check permissions
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Filter namespaces based on user access
        target_namespaces = request.namespace_filter
        if target_namespaces:
            # Check access to requested namespaces
            for ns in target_namespaces:
                if not require_namespace_access(ns, current_user):
                    raise HTTPException(status_code=403, detail=f"Access denied to namespace '{ns}'")
        else:
            # Get all accessible namespaces for user
            all_namespaces = namespace_manager.list_namespaces()
            if UserRole.ADMIN in current_user.roles or "*" in current_user.namespaces:
                target_namespaces = all_namespaces
            else:
                target_namespaces = [ns for ns in all_namespaces if ns in current_user.namespaces]
        
        results = multi_retriever.query_best_across_namespaces(
            request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            namespace_filter=target_namespaces
        )
        
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        namespaces_searched = list(set(r['namespace'] for r in results))
        
        return QueryResponse(
            query=request.query,
            results=[QueryResult(**result) for result in results],
            total_results=len(results),
            processing_time_ms=round(processing_time, 2),
            namespaces_searched=namespaces_searched
        )
        
    except Exception as e:
        logger.error(f"Cross-namespace query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Namespace Management Endpoints

@app.get("/namespaces", response_model=List[str])
async def list_namespaces(
    department: Optional[str] = Query(None, description="Filter by department"),
    current_user: User = Depends(get_current_active_user)
):
    """List all available namespaces"""
    try:
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Filter namespaces based on user access
        all_namespaces = namespace_manager.list_namespaces(department_filter=department)
        
        # Admin can see all, others only their allowed namespaces
        if UserRole.ADMIN in current_user.roles or "*" in current_user.namespaces:
            accessible_namespaces = all_namespaces
        else:
            accessible_namespaces = [ns for ns in all_namespaces if ns in current_user.namespaces]
            
        return accessible_namespaces
    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list namespaces: {str(e)}")

@app.get("/namespaces/details", response_model=List[NamespaceInfo])
async def list_namespaces_detailed(
    department: Optional[str] = Query(None, description="Filter by department"),
    current_user: User = Depends(get_current_active_user)
):
    """List all namespaces with detailed information"""
    try:
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
            
        namespaces = namespace_manager.list_namespaces(department_filter=department)
        
        # Filter based on user access
        if not (UserRole.ADMIN in current_user.roles or "*" in current_user.namespaces):
            namespaces = [ns for ns in namespaces if ns in current_user.namespaces]
        
        detailed_info = []
        
        for namespace in namespaces:
            details = namespace_manager.get_namespace_details(namespace)
            if details:
                info = details['info']
                stats = details['stats']
                
                detailed_info.append(NamespaceInfo(
                    namespace=namespace,
                    description=info.get('description', ''),
                    department=info.get('department'),
                    contact=info.get('contact'),
                    document_count=info.get('document_count', 0),
                    chunk_count=stats.get('metadata_entries', 0),
                    created=info.get('created', ''),
                    last_updated=info.get('last_updated'),
                    tags=info.get('tags', [])
                ))
        
        return detailed_info
    except Exception as e:
        logger.error(f"Failed to get namespace details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get namespace details: {str(e)}")

@app.get("/namespaces/{namespace}", response_model=NamespaceInfo)
async def get_namespace_details(
    namespace: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed information about a specific namespace"""
    try:
        # Check permissions
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        if not require_namespace_access(namespace, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to namespace '{namespace}'")
        
        details = namespace_manager.get_namespace_details(namespace)
        if not details:
            raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' not found")
        
        info = details['info']
        stats = details['stats']
        
        return NamespaceInfo(
            namespace=namespace,
            description=info.get('description', ''),
            department=info.get('department'),
            contact=info.get('contact'),
            document_count=info.get('document_count', 0),
            chunk_count=stats.get('metadata_entries', 0),
            created=info.get('created', ''),
            last_updated=info.get('last_updated'),
            tags=info.get('tags', [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get namespace details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get namespace details: {str(e)}")

@app.post("/namespaces")
async def create_namespace(
    request: CreateNamespaceRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new namespace"""
    try:
        if not can_manage_namespaces(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions to create namespaces")
        
        success = namespace_manager.create_namespace(
            request.namespace,
            request.description,
            request.tags,
            request.department or "",
            request.contact or ""
        )
        
        if success:
            return {"message": f"Namespace '{request.namespace}' created successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to create namespace '{request.namespace}'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create namespace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create namespace: {str(e)}")

@app.delete("/namespaces/{namespace}")
async def delete_namespace(
    namespace: str,
    force: bool = Query(False, description="Force deletion without confirmation"),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a namespace"""
    try:
        if not can_manage_namespaces(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete namespaces")
        
        success = namespace_manager.delete_namespace(namespace, force)
        
        if success:
            return {"message": f"Namespace '{namespace}' deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to delete namespace '{namespace}'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete namespace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete namespace: {str(e)}")

# Ingestion Endpoints

@app.post("/ingest")
async def ingest_documents(
    background_tasks: BackgroundTasks,
    request: IngestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Ingest documents into namespaces"""
    try:
        if not can_write(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions to ingest documents")
        
        if request.namespace:
            # Check access to target namespace
            if not require_namespace_access(request.namespace, current_user):
                raise HTTPException(status_code=403, detail=f"Access denied to namespace '{request.namespace}'")
            
            # Ingest to specific namespace
            background_tasks.add_task(
                ingest_to_namespace,
                DATA_DIR,
                request.namespace,
                request.description
            )
            return {
                "message": f"Started ingestion to namespace '{request.namespace}'",
                "status": "processing"
            }
        else:
            # Auto-detect namespaces (admin only)
            if not can_admin(current_user):
                raise HTTPException(status_code=403, detail="Auto-ingestion requires admin privileges")
            
            background_tasks.add_task(ingest_auto_namespace, DATA_DIR)
            return {
                "message": "Started auto-ingestion with namespace detection",
                "status": "processing"
            }
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

# Analytics Endpoints

@app.get("/analytics/overlap")
async def analyze_namespace_overlap(
    namespace1: str = Query(..., description="First namespace"),
    namespace2: str = Query(..., description="Second namespace"),
    sample_size: int = Query(100, ge=10, le=1000, description="Sample size for analysis"),
    current_user: User = Depends(get_current_active_user)
) -> OverlapAnalysis:
    """Analyze content overlap between two namespaces"""
    try:
        if not can_read(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Check access to both namespaces
        if not require_namespace_access(namespace1, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to namespace '{namespace1}'")
        
        if not require_namespace_access(namespace2, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to namespace '{namespace2}'")
        
        analysis = namespace_manager.analyze_namespace_overlap(namespace1, namespace2, sample_size)
        
        if not analysis:
            raise HTTPException(status_code=400, detail="Failed to analyze namespace overlap")
        
        return OverlapAnalysis(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Overlap analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Overlap analysis failed: {str(e)}")

@app.get("/system/overview", response_model=SystemOverview)
async def get_system_overview(current_user: User = Depends(get_current_active_user)):
    """Get comprehensive system overview and statistics"""
    try:
        if not can_admin(current_user):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        overview = namespace_manager.get_system_overview()
        
        # Convert namespace details to NamespaceInfo objects
        namespace_infos = []
        for ns_detail in overview.get('namespaces', []):
            info = ns_detail.get('info', {})
            stats = ns_detail.get('stats', {})
            
            namespace_infos.append(NamespaceInfo(
                namespace=ns_detail.get('namespace', ''),
                description=info.get('description', ''),
                department=info.get('department'),
                contact=info.get('contact'),
                document_count=info.get('document_count', 0),
                chunk_count=stats.get('metadata_entries', 0),
                created=info.get('created', ''),
                last_updated=info.get('last_updated'),
                tags=info.get('tags', [])
            ))
        
        return SystemOverview(
            total_namespaces=overview['total_namespaces'],
            total_documents=overview['total_documents'],
            total_chunks=overview['total_chunks'],
            total_size_mb=overview['total_size_mb'],
            departments=overview['departments'],
            namespaces=namespace_infos
        )
        
    except Exception as e:
        logger.error(f"Failed to get system overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system overview: {str(e)}")

# Backup/Management Endpoints

@app.post("/namespaces/{namespace}/backup")
async def backup_namespace(
    namespace: str,
    background_tasks: BackgroundTasks,
    backup_dir: Optional[str] = Body(None, description="Custom backup directory"),
    current_user: User = Depends(get_current_active_user)
):
    """Create a backup of a namespace"""
    try:
        if not can_manage_namespaces(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions to backup namespaces")
        
        if not require_namespace_access(namespace, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to namespace '{namespace}'")
        
        if namespace not in namespace_manager.list_namespaces():
            raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' not found")
        
        background_tasks.add_task(
            namespace_manager.backup_namespace,
            namespace,
            backup_dir
        )
        
        return {
            "message": f"Started backup for namespace '{namespace}'",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@app.post("/namespaces/{source_namespace}/clone/{target_namespace}")
async def clone_namespace(
    source_namespace: str,
    target_namespace: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Clone a namespace to a new namespace"""
    try:
        if not can_manage_namespaces(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions to clone namespaces")
        
        if not require_namespace_access(source_namespace, current_user):
            raise HTTPException(status_code=403, detail=f"Access denied to source namespace '{source_namespace}'")
        
        if source_namespace not in namespace_manager.list_namespaces():
            raise HTTPException(status_code=404, detail=f"Source namespace '{source_namespace}' not found")
        
        if target_namespace in namespace_manager.list_namespaces():
            raise HTTPException(status_code=400, detail=f"Target namespace '{target_namespace}' already exists")
        
        background_tasks.add_task(
            namespace_manager.clone_namespace,
            source_namespace,
            target_namespace
        )
        
        return {
            "message": f"Started cloning '{source_namespace}' to '{target_namespace}'",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Clone failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting RAGdoll Enterprise API on {host}:{port}")
    uvicorn.run(
        "app.api_new:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        access_log=True
    )

"""
OpenAI API Endpoints for RAGdoll Enterprise System
FastAPI routes for OpenAI GPT-4o integration with streaming support.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.openai_llm_service import OpenAILLMService

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/chat", tags=["OpenAI Chat"])

# Request/Response models
class ChatRequest(BaseModel):
    query: str = Field(..., description="User question")
    namespace: str = Field(default="default", description="Document namespace")
    model: Optional[str] = Field(default=None, description="OpenAI model to use")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=1, description="Response creativity")
    max_tokens: Optional[int] = Field(default=1000, gt=0, description="Maximum response length")
    top_k: int = Field(default=5, gt=0, le=20, description="Number of documents to retrieve")
    include_sources: bool = Field(default=True, description="Include source documents")

class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Dict[str, int]
    namespace: str
    sources: Optional[list] = None

class StreamChatRequest(ChatRequest):
    stream: bool = Field(default=True, description="Enable streaming")

# Global service instance (will be initialized with API key)
llm_service: Optional[OpenAILLMService] = None

def get_llm_service() -> OpenAILLMService:
    """Get or initialize the LLM service."""
    global llm_service
    if llm_service is None:
        try:
            llm_service = OpenAILLMService()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI service not configured: {str(e)}"
            )
    return llm_service

@router.post("/gpt4", response_model=ChatResponse)
async def chat_with_gpt4(request: ChatRequest) -> ChatResponse:
    """
    Chat with GPT-4o using RAG context.
    
    Retrieves relevant documents from the specified namespace and uses them
    as context for generating an intelligent response with GPT-4o.
    """
    try:
        service = get_llm_service()
        
        result = await service.async_chat_with_context(
            query=request.query,
            namespace=request.namespace,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_k=request.top_k,
            include_sources=request.include_sources
        )
        
        return ChatResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/gpt4/stream")
async def stream_chat_with_gpt4(request: StreamChatRequest):
    """
    Stream chat with GPT-4o using RAG context.
    
    Returns a Server-Sent Events (SSE) stream of the response as it's generated.
    """
    try:
        service = get_llm_service()
        
        async def generate_stream():
            """Generate SSE stream for the chat response."""
            try:
                async for chunk in service.stream_chat_with_context(
                    query=request.query,
                    namespace=request.namespace,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_k=request.top_k,
                    include_sources=request.include_sources
                ):
                    # Format as SSE
                    data = json.dumps(chunk)
                    yield f"data: {data}\n\n"
                
                # Send final SSE message
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                # Send error as SSE
                error_data = json.dumps({
                    "type": "error",
                    "error": str(e)
                })
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stream chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/models")
async def get_available_models():
    """Get list of available OpenAI models."""
    try:
        service = get_llm_service()
        models = service.get_available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")

@router.get("/health")
async def check_openai_health():
    """Check OpenAI service health and API key validity."""
    try:
        service = get_llm_service()
        is_valid = service.validate_api_key()
        
        return {
            "status": "healthy" if is_valid else "error",
            "api_key_valid": is_valid,
            "service": "OpenAI GPT-4o"
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "error",
            "api_key_valid": False,
            "error": str(e),
            "service": "OpenAI GPT-4o"
        }

@router.post("/configure")
async def configure_openai_service(api_key: str):
    """
    Configure or reconfigure the OpenAI service with a new API key.
    
    This endpoint allows runtime configuration of the OpenAI API key.
    """
    global llm_service
    
    try:
        # Create new service instance with the provided API key
        new_service = OpenAILLMService(api_key=api_key)
        
        # Validate the API key
        if not new_service.validate_api_key():
            raise HTTPException(status_code=400, detail="Invalid OpenAI API key")
        
        # Replace global service instance
        llm_service = new_service
        
        return {
            "status": "configured",
            "message": "OpenAI service configured successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration failed")

# Advanced chat endpoints

@router.post("/analyze")
async def analyze_documents(
    query: str,
    namespace: str = "default",
    analysis_type: str = "summary"
):
    """
    Perform advanced document analysis using GPT-4o.
    
    Analysis types:
    - summary: Summarize relevant documents
    - compare: Compare documents on a topic
    - extract: Extract specific information
    """
    try:
        service = get_llm_service()
        
        # Customize prompt based on analysis type
        analysis_prompts = {
            "summary": "Please provide a comprehensive summary of the relevant documents.",
            "compare": "Please compare and contrast the information from different documents.",
            "extract": "Please extract the key information relevant to the query."
        }
        
        prompt_suffix = analysis_prompts.get(analysis_type, analysis_prompts["summary"])
        enhanced_query = f"{query}\n\n{prompt_suffix}"
        
        result = await service.async_chat_with_context(
            query=enhanced_query,
            namespace=namespace,
            temperature=0.3,  # Lower temperature for analysis
            max_tokens=1500,  # More tokens for detailed analysis
            top_k=10,  # More documents for comprehensive analysis
            include_sources=True
        )
        
        return {
            "analysis": result["response"],
            "analysis_type": analysis_type,
            "namespace": namespace,
            "sources_analyzed": len(result.get("sources", [])),
            "usage": result["usage"]
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")

@router.post("/batch")
async def batch_chat(queries: list[str], namespace: str = "default"):
    """
    Process multiple queries in batch for efficient processing.
    """
    try:
        service = get_llm_service()
        results = []
        
        # Process queries concurrently
        tasks = [
            service.async_chat_with_context(
                query=query,
                namespace=namespace,
                include_sources=False  # Exclude sources for batch to reduce payload
            )
            for query in queries
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append({
                    "query": queries[i],
                    "error": str(response),
                    "success": False
                })
            else:
                results.append({
                    "query": queries[i],
                    "response": response["response"],
                    "success": True,
                    "usage": response["usage"]
                })
        
        return {
            "results": results,
            "total_queries": len(queries),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"])
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

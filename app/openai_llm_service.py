# type: ignore
# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false

"""
OpenAI LLM Service for RAGdoll Enterprise System
Provides integration with OpenAI GPT-4o for intelligent Q&A over RAG results.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI
from app.config import OPENAI_API_KEY
from app.query_enhanced import EnhancedMultiNamespaceRAGRetriever

logger = logging.getLogger(__name__)

class OpenAILLMService:
    """
    OpenAI integration service for RAGdoll system.
    Provides both synchronous and asynchronous interfaces for GPT-4o integration.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI service with API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via parameter or OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        self.rag_service = EnhancedMultiNamespaceRAGRetriever()
        
        # Default model and parameters
        self.default_model = "gpt-4o"
        self.default_temperature = 0.7
        self.default_max_tokens = 1000
        
    def _create_system_prompt(self, namespace: str) -> str:
        """Create system prompt based on namespace context."""
        namespace_contexts = {
            'engineering': "You are an AI assistant specialized in technical and engineering documentation. Provide precise, technical answers with relevant code examples when applicable.",
            'legal': "You are an AI assistant specialized in legal documentation and compliance. Provide accurate information while noting that responses should not be considered legal advice.",
            'hr': "You are an AI assistant specialized in human resources policies and procedures. Provide helpful guidance on HR-related topics.",
            'marketing': "You are an AI assistant specialized in marketing materials and brand guidelines. Provide creative and strategic insights.",
            'default': "You are a helpful AI assistant with access to enterprise documentation."
        }
        
        base_prompt = namespace_contexts.get(namespace, namespace_contexts['default'])
        return f"""{base_prompt}

You have access to relevant documents through a RAG (Retrieval-Augmented Generation) system. When answering questions:

1. Use the provided context from retrieved documents as your primary source
2. If the context doesn't contain enough information, clearly state this limitation
3. Cite sources when possible by referencing document names or sections
4. Provide clear, well-structured answers
5. If asked about topics not covered in the retrieved documents, politely redirect to the available information

Always be accurate, helpful, and transparent about the limitations of your knowledge based on the provided context."""

    def _format_context(self, rag_results: List[Dict]) -> str:
        """Format RAG retrieval results into context for LLM."""
        if not rag_results:
            return "No relevant documents found for this query."
        
        context_parts = []
        for i, result in enumerate(rag_results, 1):
            score = result.get('score', 0)
            metadata = result.get('metadata', {})
            content = result.get('content', result.get('text', ''))
            
            filename = metadata.get('filename', f'Document {i}')
            similarity = f"{score * 100:.1f}%" if score else "N/A"
            
            context_parts.append(f"""--- Source {i}: {filename} (Similarity: {similarity}) ---
{content}
""")
        
        return "\n".join(context_parts)

    def chat_with_context(
        self,
        query: str,
        namespace: str = 'default',
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Synchronous chat with RAG context.
        Returns:
            Dict containing response, sources, and metadata
        """
        try:
            rag_results = self.rag_service.query_cross_namespace(query, [namespace], top_k=top_k)
            context = self._format_context(rag_results)

            system_prompt = self._create_system_prompt(namespace)
            user_message = f"""Context from relevant documents:\n{context}\n\nUser Question: {query}\n\nPlease provide a comprehensive answer based on the context above."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = self.client.chat.completions.create(  # type: ignore
                model=model or self.default_model,
                messages=messages,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens
            )  # type: ignore

            result = {
                "response": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else {},
                "namespace": namespace
            }
            if include_sources:
                result["sources"] = [
                    {"content": r.get('content', r.get('text', '')),
                     "metadata": r.get('metadata', {}),
                     "score": r.get('score', 0)} for r in rag_results
                ]
            return result
        except Exception as e:
            logger.error(f"Error in chat_with_context: {e}")
            raise

    async def async_chat_with_context(
        self,
        query: str,
        namespace: str = 'default',
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Asynchronous chat with RAG context.
        Returns:
            Dict containing response, sources, and metadata
        """
        try:
            rag_results = self.rag_service.query_cross_namespace(query, [namespace], top_k=top_k)
            context = self._format_context(rag_results)

            system_prompt = self._create_system_prompt(namespace)
            user_message = f"""Context from relevant documents:\n{context}\n\nUser Question: {query}\n\nPlease provide a comprehensive answer based on the context above."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = await self.async_client.chat.completions.create(  # type: ignore
                model=model or self.default_model,
                messages=messages,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens
            )  # type: ignore

            # Build result inside try
            result = {
                "response": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else {},
                "namespace": namespace
            }
            if include_sources:
                result["sources"] = [
                    {"content": r.get('content', r.get('text', '')),
                     "metadata": r.get('metadata', {}),
                     "score": r.get('score', 0)} for r in rag_results
                ]
            return result
        except Exception as e:
            logger.error(f"Error in async_chat_with_context: {e}")
            raise

    async def stream_chat_with_context(
        self,
        query: str,
        namespace: str = 'default',
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_k: int = 5,
        include_sources: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response with RAG context, yielding partial results.
        """
        try:
            rag_results = self.rag_service.query_cross_namespace(query, [namespace], top_k=top_k)
            context = self._format_context(rag_results)

            if include_sources:
                yield {"type": "sources", "sources": [
                    {"content": r.get('content', r.get('text', '')),
                     "metadata": r.get('metadata', {}),
                     "score": r.get('score', 0)} for r in rag_results
                ]}

            system_prompt = self._create_system_prompt(namespace)
            user_message = f"""Context from relevant documents:\n{context}\n\nUser Question: {query}\n\nPlease provide a comprehensive answer based on the context above."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            stream = await self.async_client.chat.completions.create(  # type: ignore
                model=model or self.default_model,
                messages=messages,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens,
                stream=True
            )  # type: ignore

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {"type": "content", "content": chunk.choices[0].delta.content}
            yield {"type": "done", "namespace": namespace}
        except Exception as e:
            logger.error(f"Error in stream_chat_with_context: {e}")
            yield {"type": "error", "error": str(e)}

    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data if 'gpt' in model.id]
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            return ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]

    def validate_api_key(self) -> bool:
        """Validate the OpenAI API key."""
        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False

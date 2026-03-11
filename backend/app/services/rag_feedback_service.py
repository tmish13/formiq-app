"""
RAG (Retrieval-Augmented Generation) feedback service.

This service uses LangChain and biomechanical knowledge to generate
personalized exercise feedback by retrieving relevant form tips
and combining them with pose analysis results.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.documents import Document
except ImportError:
    # Fallback for older langchain versions
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        from langchain.schema import Document
    except ImportError:
        ChatOpenAI = None
        HumanMessage = None
        SystemMessage = None
        Document = None

from app.core.config import settings
from app.core.vectorstore import vector_store_service
from app.core.circuit_breaker import circuit_breaker, CircuitBreakerConfig, circuit_registry
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


@dataclass
class FeedbackContext:
    """Context information for feedback generation."""
    exercise_name: str
    exercise_type: str  # e.g., "squat"
    form_scores: Dict[str, float]  # e.g., {"posture_score": 85, "stability_score": 70, "depth_score": 90}
    identified_faults: List[str]  # e.g., ["knee_valgus", "forward_lean"]
    user_level: str = "beginner"  # beginner, intermediate, advanced
    additional_context: Optional[str] = None


class RAGFeedbackService:
    """Service for generating RAG-powered exercise feedback."""
    
    def __init__(self):
        """Initialize RAG feedback service."""
        self.llm = None
        self.consecutive_failures = 0
        self._initialize_llm()
        
        # Configure circuit breaker for OpenAI API calls
        openai_config = CircuitBreakerConfig(
            failure_threshold=3,      # Open after 3 failures
            recovery_timeout=120.0,   # Wait 2 minutes before retry
            timeout=30.0,            # 30 second timeout for API calls
            max_retries=2,           # Retry twice before giving up
            initial_backoff=2.0      # Start with 2 second backoff
        )
        self.openai_breaker = circuit_registry.get_breaker("openai_api", openai_config)
        
        # Configure circuit breaker for vector store operations  
        vectorstore_config = CircuitBreakerConfig(
            failure_threshold=5,      # More tolerant for vector store
            recovery_timeout=60.0,    # Shorter recovery time
            timeout=10.0,            # Shorter timeout for local operations
            max_retries=1,           # Single retry for vector store
        )
        self.vectorstore_breaker = circuit_registry.get_breaker("vector_store", vectorstore_config)
    
    def _initialize_llm(self) -> None:
        """Initialize OpenAI LLM."""
        try:
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not provided. RAG feedback will not be available.")
                return
            
            self.llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                model_name=settings.RAG_MODEL_NAME,
                temperature=settings.RAG_TEMPERATURE,
                max_tokens=settings.RAG_MAX_TOKENS
            )
            logger.info(f"Initialized LLM: {settings.RAG_MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
    
    def _prepare_retrieval_query(self, context: FeedbackContext) -> str:
        """Prepare query for vector store retrieval."""
        query_parts = []
        
        # Add exercise type
        query_parts.append(f"{context.exercise_type} form")
        
        # Add identified faults
        for fault in context.identified_faults:
            query_parts.append(fault.replace('_', ' '))
        
        # Add score-based concerns
        if context.form_scores.get("posture_score", 100) < 80:
            query_parts.append("posture alignment torso")
        if context.form_scores.get("stability_score", 100) < 80:
            query_parts.append("stability balance knee tracking")
        if context.form_scores.get("depth_score", 100) < 80:
            query_parts.append("depth range of motion hip")
        
        query = " ".join(query_parts)
        logger.debug(f"Retrieval query: {query}")
        return query
    
    async def _retrieve_relevant_knowledge(
        self, 
        context: FeedbackContext
    ) -> List[Document]:
        """Retrieve relevant biomechanical knowledge with circuit breaker protection."""
        def fallback_empty_docs():
            logger.warning("Vector store circuit breaker active, using empty knowledge base")
            return []
        
        async def vector_search():
            query = self._prepare_retrieval_query(context)
            
            # Note: This wraps the sync vector store call in async context
            # In production, you'd want an async vector store client
            return vector_store_service.similarity_search(
                query=query,
                k=settings.RAG_TOP_K_RESULTS,
                exercise_type=context.exercise_type
            )
        
        try:
            docs = await self.vectorstore_breaker.call(
                vector_search,
                fallback=fallback_empty_docs
            )
            logger.debug(f"Retrieved {len(docs)} relevant documents")
            return docs
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return []
    
    def _build_feedback_prompt(
        self, 
        context: FeedbackContext, 
        retrieved_docs: List[Document]
    ) -> List[Any]:
        """Build prompt for LLM feedback generation."""
        
        # System message with role and instructions
        system_prompt = f"""You are an expert biomechanics coach providing personalized exercise feedback. 

Your task is to analyze exercise performance data and provide constructive, actionable feedback based on biomechanical principles.

Guidelines:
1. Be encouraging and constructive, not critical
2. Focus on the most important issues first (safety, then performance)
3. Provide specific, actionable corrections
4. Reference biomechanical principles when relevant
5. Adapt language to user level: {context.user_level}
6. Keep feedback concise but informative (2-3 key points)

Exercise: {context.exercise_name}
User Level: {context.user_level}"""

        # Human message with analysis data and retrieved knowledge
        score_summary = ", ".join([f"{k.replace('_', ' ')}: {v:.0f}%" for k, v in context.form_scores.items()])
        fault_summary = ", ".join(context.identified_faults) if context.identified_faults else "No major faults detected"
        
        retrieved_knowledge = "\\n\\n".join([
            f"- {doc.metadata.get('title', 'Untitled')}: {doc.page_content}"
            for doc in retrieved_docs
        ]) if retrieved_docs else "No specific guidance available"
        
        human_prompt = f"""Analyze this {context.exercise_type} performance and provide feedback:

PERFORMANCE SCORES:
{score_summary}

IDENTIFIED ISSUES:
{fault_summary}

RELEVANT BIOMECHANICAL GUIDANCE:
{retrieved_knowledge}

{f"ADDITIONAL CONTEXT: {context.additional_context}" if context.additional_context else ""}

Provide personalized feedback that addresses the key issues and helps improve form:"""

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
    
    async def generate_feedback(self, context: FeedbackContext) -> str:
        """
        Generate personalized RAG feedback with circuit breaker protection.
        
        Args:
            context: Feedback context with exercise data and scores
            
        Returns:
            Generated feedback text
        """
        try:
            # Check if RAG is available
            if not self.is_available():
                logger.warning("RAG service not available, using fallback feedback")
                return self._generate_fallback_feedback(context)
            
            # Retrieve relevant knowledge (with circuit breaker)
            retrieved_docs = await self._retrieve_relevant_knowledge(context)
            
            # Generate feedback with OpenAI circuit breaker protection
            def fallback_feedback():
                logger.warning("OpenAI circuit breaker active, using fallback feedback")
                return self._generate_fallback_feedback(context)
            
            async def openai_call():
                # Build prompt
                messages = self._build_feedback_prompt(context, retrieved_docs)
                
                # Generate feedback
                response = self.llm(messages)
                return response.content.strip()
            
            feedback_text = await self.openai_breaker.call(
                openai_call,
                fallback=fallback_feedback
            )
            
            logger.info(f"Generated RAG feedback for {context.exercise_name}")
            return feedback_text
            
        except ExternalServiceError:
            # Re-raise external service errors (circuit breaker handled them)
            raise
        except Exception as e:
            logger.error(f"RAG feedback generation failed unexpectedly: {e}")
            return self._generate_fallback_feedback(context)
    
    def generate_feedback_sync(self, context: FeedbackContext) -> str:
        """Synchronous wrapper for generate_feedback."""
        return asyncio.run(self.generate_feedback(context))
    
    def _generate_fallback_feedback(self, context: FeedbackContext) -> str:
        """Generate fallback feedback when RAG is unavailable."""
        feedback_parts = []
        
        # General encouragement
        feedback_parts.append(f"Great work on your {context.exercise_name}!")
        
        # Score-based feedback
        avg_score = sum(context.form_scores.values()) / len(context.form_scores) if context.form_scores else 85
        
        if avg_score >= 90:
            feedback_parts.append("Your form looks excellent! Keep up the great technique.")
        elif avg_score >= 80:
            feedback_parts.append("Good form overall with room for minor improvements.")
        elif avg_score >= 70:
            feedback_parts.append("Solid technique with some areas to focus on for improvement.")
        else:
            feedback_parts.append("Focus on fundamental movement patterns to improve your form.")
        
        # Specific improvements
        if context.form_scores.get("posture_score", 100) < 80:
            feedback_parts.append("Pay attention to maintaining proper torso alignment.")
        if context.form_scores.get("stability_score", 100) < 80:
            feedback_parts.append("Work on stability and balance throughout the movement.")
        if context.form_scores.get("depth_score", 100) < 80:
            feedback_parts.append("Focus on achieving proper range of motion.")
        
        return " ".join(feedback_parts)
    
    def is_available(self) -> bool:
        """Check if RAG feedback service is available."""
        return (
            settings.RAG_ENABLED and
            self.llm is not None and
            vector_store_service.is_available()
        )


# Global instance
rag_feedback_service = RAGFeedbackService()
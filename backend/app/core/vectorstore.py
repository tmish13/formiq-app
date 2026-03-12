"""
Vector store management for biomechanical knowledge.

This module handles the creation, indexing, and querying of vector embeddings
for biomechanical exercise form knowledge using Chroma DB.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing biomechanical knowledge vector store."""
    
    def __init__(self):
        """Initialize vector store service."""
        self.embeddings = None
        self.vector_store = None
        self.collection_name = "biomechanical_knowledge"
        self._initialize_embeddings()
    
    def _initialize_embeddings(self) -> None:
        """Initialize OpenAI embeddings."""
        try:
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not provided. Vector store will not be available.")
                return
            
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model=settings.EMBEDDING_MODEL
            )
            logger.info(f"Initialized embeddings with model: {settings.EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
    
    def _get_vector_store_path(self) -> Path:
        """Get the path to the persistent vector store."""
        base_path = Path(settings.VECTOR_STORE_PATH)
        if not base_path.is_absolute():
            # Make path relative to backend directory
            backend_dir = Path(__file__).parent.parent.parent
            base_path = backend_dir / base_path
        
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path
    
    def initialize_vector_store(self) -> bool:
        """Initialize or load existing vector store."""
        try:
            if not self.embeddings:
                logger.error("Embeddings not initialized. Cannot create vector store.")
                return False
            
            persist_dir = str(self._get_vector_store_path())
            
            # Initialize Chroma client with persistence
            client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.vector_store = Chroma(
                client=client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=persist_dir
            )
            
            logger.info(f"Vector store initialized at: {persist_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    def load_biomechanical_knowledge(self, force_reload: bool = False) -> bool:
        """Load biomechanical knowledge from JSON files into vector store."""
        try:
            if not self.vector_store:
                if not self.initialize_vector_store():
                    return False
            
            # Check if collection already has documents (unless force reload)
            if not force_reload:
                try:
                    collection = self.vector_store._client.get_collection(self.collection_name)
                    if collection.count() > 0:
                        logger.info(f"Vector store already contains {collection.count()} documents. Use force_reload=True to reload.")
                        return True
                except Exception:
                    # Collection doesn't exist or is empty
                    pass
            
            # Load squat form tips
            squat_tips_path = Path(__file__).parent.parent.parent / "data" / "biomechanical_knowledge" / "squat_form_tips.json"
            
            if not squat_tips_path.exists():
                logger.error(f"Biomechanical knowledge file not found: {squat_tips_path}")
                return False
            
            with open(squat_tips_path, 'r') as f:
                squat_tips = json.load(f)
            
            # Convert to Langchain documents
            documents = []
            for tip in squat_tips:
                content = f"{tip['title']}: {tip['content']}"
                metadata = {
                    'id': tip['id'],
                    'title': tip['title'],
                    'category': tip['category'],
                    'exercise_type': tip['exercise_type'],
                    'fault_type': tip['fault_type'],
                    'severity': tip['severity'],
                    'keywords': ', '.join(tip['keywords']),
                    'affected_joints': ', '.join(tip['affected_joints'])
                }
                
                documents.append(Document(
                    page_content=content,
                    metadata=metadata
                ))
            
            # Clear existing documents if force reload
            if force_reload:
                try:
                    self.vector_store._client.delete_collection(self.collection_name)
                    # Reinitialize after deletion
                    self.initialize_vector_store()
                except Exception as e:
                    logger.warning(f"Could not clear existing collection: {e}")
            
            # Add documents to vector store
            self.vector_store.add_documents(documents)
            logger.info(f"Successfully loaded {len(documents)} biomechanical knowledge documents into vector store")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load biomechanical knowledge: {e}")
            return False
    
    def similarity_search(
        self, 
        query: str, 
        k: int = None,
        exercise_type: str = None,
        fault_type: str = None
    ) -> List[Document]:
        """
        Perform similarity search on biomechanical knowledge.
        
        Args:
            query: Search query text
            k: Number of results to return (defaults to settings.RAG_TOP_K_RESULTS)
            exercise_type: Filter by exercise type (e.g., "squat")
            fault_type: Filter by fault type (e.g., "posture", "stability", "depth")
        
        Returns:
            List of relevant documents
        """
        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
            if k is None:
                k = settings.RAG_TOP_K_RESULTS
            
            # Build metadata filter
            metadata_filter = {}
            if exercise_type:
                metadata_filter["exercise_type"] = exercise_type
            if fault_type:
                metadata_filter["fault_type"] = fault_type
            
            # Perform similarity search
            if metadata_filter:
                docs = self.vector_store.similarity_search(
                    query=query,
                    k=k,
                    filter=metadata_filter
                )
            else:
                docs = self.vector_store.similarity_search(query=query, k=k)
            
            logger.debug(f"Retrieved {len(docs)} documents for query: {query}")
            return docs
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if vector store service is available."""
        return (
            self.embeddings is not None and 
            self.vector_store is not None and
            settings.OPENAI_API_KEY and
            settings.RAG_ENABLED
        )


# Global instance
vector_store_service = VectorStoreService()
#!/usr/bin/env python3
"""
Initialize vector store with biomechanical knowledge.

This script sets up the Chroma vector database and loads
biomechanical form knowledge for RAG-powered feedback.
"""

import os
import sys
from pathlib import Path

# Add backend to path so we can import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.vectorstore import vector_store_service
from app.core.config import settings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize vector store with biomechanical knowledge."""
    logger.info("Starting vector store initialization...")
    
    # Check configuration
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Please set it in your environment or .env file.")
        return False
        
    if not settings.RAG_ENABLED:
        logger.error("RAG_ENABLED is False. Set it to True to initialize vector store.")
        return False
    
    logger.info(f"Vector store path: {settings.VECTOR_STORE_PATH}")
    logger.info(f"RAG enabled: {settings.RAG_ENABLED}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    if not vector_store_service.initialize_vector_store():
        logger.error("Failed to initialize vector store")
        return False
    
    # Load biomechanical knowledge
    logger.info("Loading biomechanical knowledge...")
    if not vector_store_service.load_biomechanical_knowledge(force_reload=True):
        logger.error("Failed to load biomechanical knowledge")
        return False
    
    # Test the system
    logger.info("Testing vector store...")
    test_docs = vector_store_service.similarity_search(
        query="knee alignment squat form",
        exercise_type="squat",
        k=2
    )
    
    if test_docs:
        logger.info(f"✅ Vector store working! Found {len(test_docs)} documents")
        for i, doc in enumerate(test_docs):
            logger.info(f"  {i+1}. {doc.metadata.get('title', 'Untitled')}")
    else:
        logger.warning("⚠️  Vector store initialized but no documents found in test search")
    
    logger.info("Vector store initialization complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
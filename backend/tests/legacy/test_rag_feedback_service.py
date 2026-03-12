"""Tests for RAG feedback service."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from langchain.schema import Document

from app.services.rag_feedback_service import RAGFeedbackService, FeedbackContext
from app.core.config import settings


class TestRAGFeedbackService:
    """Test suite for RAG feedback service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = RAGFeedbackService()
        self.sample_context = FeedbackContext(
            exercise_name="Barbell Squat",
            exercise_type="squat",
            form_scores={
                "posture_score": 75.0,
                "stability_score": 65.0,
                "depth_score": 85.0
            },
            identified_faults=["knee_valgus", "forward_lean"],
            user_level="intermediate",
            additional_context="User has been improving over past 3 sessions"
        )
    
    def test_prepare_retrieval_query(self):
        """Test query preparation for vector store retrieval."""
        query = self.service._prepare_retrieval_query(self.sample_context)
        
        assert "squat form" in query
        assert "knee valgus" in query
        assert "forward lean" in query
        assert "stability balance knee tracking" in query  # Low stability score
        
    def test_prepare_retrieval_query_high_scores(self):
        """Test query preparation with high scores (no additional concerns)."""
        high_score_context = FeedbackContext(
            exercise_name="Perfect Squat",
            exercise_type="squat",
            form_scores={
                "posture_score": 95.0,
                "stability_score": 90.0,
                "depth_score": 92.0
            },
            identified_faults=[]
        )
        
        query = self.service._prepare_retrieval_query(high_score_context)
        assert "squat form" in query
        assert "stability balance" not in query
        assert "posture alignment" not in query
        
    @patch('app.core.vectorstore.vector_store_service')
    def test_retrieve_relevant_knowledge(self, mock_vector_store):
        """Test knowledge retrieval from vector store."""
        # Mock vector store response
        mock_docs = [
            Document(
                page_content="Knee Valgus Prevention: Keep your knees tracking over your toes...",
                metadata={"title": "Knee Valgus Prevention", "exercise_type": "squat"}
            ),
            Document(
                page_content="Torso Angle Control: Maintain an upright torso...",
                metadata={"title": "Torso Angle Control", "exercise_type": "squat"}
            )
        ]
        mock_vector_store.similarity_search.return_value = mock_docs
        
        docs = self.service._retrieve_relevant_knowledge(self.sample_context)
        
        assert len(docs) == 2
        assert "Knee Valgus Prevention" in docs[0].page_content
        mock_vector_store.similarity_search.assert_called_once()
        
    def test_build_feedback_prompt(self):
        """Test LLM prompt construction."""
        retrieved_docs = [
            Document(
                page_content="Knee Valgus Prevention: Keep your knees tracking over your toes",
                metadata={"title": "Knee Valgus Prevention"}
            )
        ]
        
        messages = self.service._build_feedback_prompt(self.sample_context, retrieved_docs)
        
        assert len(messages) == 2  # System + Human message
        
        # Check system message
        system_msg = messages[0].content
        assert "expert biomechanics coach" in system_msg
        assert "intermediate" in system_msg
        
        # Check human message
        human_msg = messages[1].content
        assert "posture score: 75%" in human_msg
        assert "knee_valgus, forward_lean" in human_msg
        assert "Knee Valgus Prevention" in human_msg
        
    @patch('app.services.rag_feedback_service.rag_feedback_service.llm')
    @patch('app.core.vectorstore.vector_store_service')
    def test_generate_feedback_success(self, mock_vector_store, mock_llm):
        """Test successful feedback generation."""
        # Mock vector store
        mock_vector_store.is_available.return_value = True
        mock_vector_store.similarity_search.return_value = [
            Document(
                page_content="Focus on knee alignment",
                metadata={"title": "Knee Tips"}
            )
        ]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Great squat form! Focus on keeping your knees aligned with your toes to improve stability."
        mock_llm.return_value = mock_response
        
        # Mock service availability
        with patch.object(self.service, 'is_available', return_value=True):
            with patch.object(self.service, 'llm', mock_llm):
                feedback = self.service.generate_feedback(self.sample_context)
        
        assert "Great squat form" in feedback
        assert "knees aligned" in feedback
        
    def test_generate_fallback_feedback(self):
        """Test fallback feedback when RAG is unavailable."""
        feedback = self.service._generate_fallback_feedback(self.sample_context)
        
        assert "Great work on your Barbell Squat!" in feedback
        assert "torso alignment" in feedback  # Low posture score
        assert "stability and balance" in feedback  # Low stability score
        
    def test_generate_fallback_feedback_high_scores(self):
        """Test fallback feedback with high scores."""
        high_score_context = FeedbackContext(
            exercise_name="Perfect Squat",
            exercise_type="squat",
            form_scores={
                "posture_score": 95.0,
                "stability_score": 92.0,
                "depth_score": 90.0
            },
            identified_faults=[]
        )
        
        feedback = self.service._generate_fallback_feedback(high_score_context)
        
        assert "Perfect Squat" in feedback
        assert "excellent" in feedback
        assert "torso alignment" not in feedback
        
    @patch('app.core.config.settings.RAG_ENABLED', True)
    @patch('app.core.config.settings.OPENAI_API_KEY', 'test-key')
    def test_is_available_true(self):
        """Test service availability when properly configured."""
        with patch.object(self.service, 'llm', Mock()):
            with patch('app.core.vectorstore.vector_store_service.is_available', return_value=True):
                assert self.service.is_available() is True
                
    @patch('app.core.config.settings.RAG_ENABLED', False)
    def test_is_available_false_disabled(self):
        """Test service availability when RAG is disabled."""
        assert self.service.is_available() is False
        
    def test_is_available_false_no_llm(self):
        """Test service availability when LLM is not initialized."""
        service = RAGFeedbackService()
        service.llm = None
        assert service.is_available() is False
        
    @patch('app.services.rag_feedback_service.rag_feedback_service.is_available')
    def test_generate_feedback_fallback_on_error(self, mock_is_available):
        """Test fallback to simulated feedback on RAG error."""
        mock_is_available.return_value = True
        
        # Mock error in retrieval
        with patch.object(self.service, '_retrieve_relevant_knowledge', side_effect=Exception("Vector store error")):
            feedback = self.service.generate_feedback(self.sample_context)
        
        # Should fall back to simulated feedback
        assert "Great work on your Barbell Squat!" in feedback
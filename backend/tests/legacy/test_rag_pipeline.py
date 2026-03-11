"""Integration tests for RAG pipeline."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock

from app.core.vectorstore import VectorStoreService
from app.services.rag_feedback_service import RAGFeedbackService, FeedbackContext


@pytest.fixture
def temp_vector_store_path():
    """Create temporary directory for vector store."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_biomechanical_data(temp_vector_store_path):
    """Create sample biomechanical knowledge for testing."""
    data_dir = Path(temp_vector_store_path) / "data" / "biomechanical_knowledge"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    sample_data = [
        {
            "id": "test_knee_valgus",
            "title": "Knee Valgus Test",
            "content": "Keep knees aligned with toes to prevent valgus collapse.",
            "category": "knee_alignment",
            "exercise_type": "squat",
            "fault_type": "stability",
            "keywords": ["knee", "valgus", "alignment"],
            "severity": "high",
            "affected_joints": ["knee", "hip"]
        },
        {
            "id": "test_depth",
            "title": "Squat Depth Test",
            "content": "Lower until hip crease is below knee cap for proper depth.",
            "category": "range_of_motion",
            "exercise_type": "squat", 
            "fault_type": "depth",
            "keywords": ["depth", "range of motion"],
            "severity": "medium",
            "affected_joints": ["hip", "knee"]
        }
    ]
    
    with open(data_dir / "squat_form_tips.json", 'w') as f:
        json.dump(sample_data, f)
    
    return data_dir


class TestRAGPipelineIntegration:
    """Integration tests for end-to-end RAG pipeline."""
    
    @patch('app.core.config.settings.OPENAI_API_KEY', 'test-key')
    @patch('app.core.config.settings.RAG_ENABLED', True)
    def test_vector_store_initialization(self, temp_vector_store_path):
        """Test vector store initialization."""
        with patch('app.core.config.settings.VECTOR_STORE_PATH', temp_vector_store_path):
            vector_service = VectorStoreService()
            
            # Mock embeddings since we don't have real OpenAI API
            vector_service.embeddings = Mock()
            
            success = vector_service.initialize_vector_store()
            assert success is True
            assert vector_service.vector_store is not None
    
    @patch('app.core.config.settings.OPENAI_API_KEY', 'test-key')
    @patch('app.core.config.settings.RAG_ENABLED', True)
    @patch('langchain_openai.OpenAIEmbeddings')
    @patch('chromadb.PersistentClient')
    def test_knowledge_loading(
        self, 
        mock_chroma_client,
        mock_embeddings,
        sample_biomechanical_data,
        temp_vector_store_path
    ):
        """Test loading biomechanical knowledge into vector store."""
        # Mock Chroma client
        mock_collection = Mock()
        mock_collection.count.return_value = 0
        mock_client_instance = Mock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance
        
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store._client = mock_client_instance
        
        with patch('app.core.config.settings.VECTOR_STORE_PATH', temp_vector_store_path):
            # Patch the backend data directory path
            with patch.object(Path, 'parent') as mock_parent:
                mock_parent.parent.parent = Path(temp_vector_store_path)
                
                vector_service = VectorStoreService()
                vector_service.embeddings = mock_embeddings
                vector_service.vector_store = mock_vector_store
                
                success = vector_service.load_biomechanical_knowledge()
                
                # Should call add_documents with our test data
                assert mock_vector_store.add_documents.called
                added_docs = mock_vector_store.add_documents.call_args[0][0]
                assert len(added_docs) == 2
                assert "Knee Valgus Test" in added_docs[0].page_content
    
    @patch('app.core.config.settings.OPENAI_API_KEY', 'test-key')
    @patch('app.core.config.settings.RAG_ENABLED', True)
    def test_similarity_search(self):
        """Test similarity search functionality."""
        vector_service = VectorStoreService()
        
        # Mock vector store
        mock_vector_store = Mock()
        mock_docs = [
            Mock(page_content="Test knee alignment tip", metadata={"title": "Knee Tips"})
        ]
        mock_vector_store.similarity_search.return_value = mock_docs
        vector_service.vector_store = mock_vector_store
        
        docs = vector_service.similarity_search(
            query="knee alignment issues",
            exercise_type="squat",
            fault_type="stability"
        )
        
        assert len(docs) == 1
        assert "Test knee alignment tip" in docs[0].page_content
        
        # Check that metadata filter was applied
        call_kwargs = mock_vector_store.similarity_search.call_args[1]
        assert call_kwargs["filter"]["exercise_type"] == "squat"
        assert call_kwargs["filter"]["fault_type"] == "stability"
    
    @patch('app.core.config.settings.OPENAI_API_KEY', 'test-key')
    @patch('app.core.config.settings.RAG_ENABLED', True)
    @patch('app.core.vectorstore.vector_store_service')
    def test_end_to_end_feedback_generation(self, mock_vector_service):
        """Test complete RAG feedback generation pipeline."""
        # Setup mocks
        mock_vector_service.is_available.return_value = True
        mock_vector_service.similarity_search.return_value = [
            Mock(
                page_content="Keep knees aligned with toes to prevent valgus",
                metadata={"title": "Knee Alignment"}
            )
        ]
        
        # Mock LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Focus on keeping your knees aligned with your toes. This will improve your stability score and prevent knee valgus."
        mock_llm.return_value = mock_response
        
        feedback_service = RAGFeedbackService()
        feedback_service.llm = mock_llm
        
        # Test feedback generation
        context = FeedbackContext(
            exercise_name="Barbell Squat",
            exercise_type="squat",
            form_scores={
                "posture_score": 80.0,
                "stability_score": 65.0,
                "depth_score": 85.0
            },
            identified_faults=["knee_valgus"],
            user_level="beginner"
        )
        
        with patch.object(feedback_service, 'is_available', return_value=True):
            feedback = feedback_service.generate_feedback(context)
        
        assert "knees aligned" in feedback
        assert "stability score" in feedback
        
        # Verify vector store was queried
        mock_vector_service.similarity_search.assert_called_once()
        
        # Verify LLM was called with proper context
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        assert len(call_args) == 2  # System + Human message
        assert "stability_score: 65%" in call_args[1].content
    
    def test_service_availability_checks(self):
        """Test various service availability scenarios."""
        # Test when RAG is disabled
        with patch('app.core.config.settings.RAG_ENABLED', False):
            service = RAGFeedbackService()
            assert service.is_available() is False
        
        # Test when OpenAI API key is missing
        with patch('app.core.config.settings.OPENAI_API_KEY', ''):
            service = RAGFeedbackService()
            assert service.is_available() is False
        
        # Test when vector store is unavailable
        with patch('app.core.config.settings.RAG_ENABLED', True):
            with patch('app.core.config.settings.OPENAI_API_KEY', 'test-key'):
                with patch('app.core.vectorstore.vector_store_service.is_available', return_value=False):
                    service = RAGFeedbackService()
                    service.llm = Mock()  # Mock LLM as available
                    assert service.is_available() is False
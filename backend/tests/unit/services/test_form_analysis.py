"""Tests for form analysis service."""
import pytest
from unittest.mock import Mock, patch
from app.services.form_analysis import FormAnalysisService
from app.models.analysis import AnalysisStatus
from app.exceptions import FormAnalysisError
from tests.base import BaseTest

class TestFormAnalysisService(BaseTest):
    """Test suite for FormAnalysisService."""
    
    @pytest.fixture
    def form_analysis_service(self):
        """Create a FormAnalysisService instance."""
        return FormAnalysisService()
    
    @pytest.fixture
    def mock_pose_data(self):
        return {
            'poses': [
                {
                    'keypoints': [
                        {'x': 100, 'y': 100, 'score': 0.9},
                        {'x': 200, 'y': 200, 'score': 0.9},
                        {'x': 300, 'y': 300, 'score': 0.9}
                    ]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_analyze_form_success(self, form_analysis_service, mock_pose_data):
        """Test successful form analysis."""
        # Execute
        result = await form_analysis_service.analyze_form(mock_pose_data)

        # Assert
        assert result['status'] == AnalysisStatus.COMPLETED
        assert 'joint_angles' in result
        assert 'spine_alignment' in result
        assert 'symmetry_score' in result
        assert all(0 <= score <= 100 for score in result['joint_angles'].values())
    
    @pytest.mark.asyncio
    async def test_analyze_form_empty_poses(self, form_analysis_service):
        """Test form analysis with empty poses."""
        # Setup
        empty_data = {'poses': []}

        # Execute & Assert
        with pytest.raises(FormAnalysisError) as exc_info:
            await form_analysis_service.analyze_form(empty_data)
        assert "No poses detected" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_form_invalid_data(self, form_analysis_service):
        """Test form analysis with invalid data."""
        # Setup
        invalid_data = {'poses': [{'invalid': 'data'}]}

        # Execute & Assert
        with pytest.raises(FormAnalysisError) as exc_info:
            await form_analysis_service.analyze_form(invalid_data)
        assert "Invalid pose data format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_form_low_confidence(self, form_analysis_service):
        """Test form analysis with low confidence."""
        # Setup
        low_confidence_data = {
            'poses': [
                {
                    'keypoints': [
                        {'x': 100, 'y': 100, 'score': 0.3},
                        {'x': 200, 'y': 200, 'score': 0.3},
                        {'x': 300, 'y': 300, 'score': 0.3}
                    ]
                }
            ]
        }

        # Execute
        result = await form_analysis_service.analyze_form(low_confidence_data)

        # Assert
        assert result['status'] == AnalysisStatus.COMPLETED
        assert result['confidence_score'] < 0.5
        assert 'warning' in result
        assert 'low confidence' in result['warning'].lower()
    
    @pytest.mark.asyncio
    async def test_analyze_form_multiple_poses(self, form_analysis_service):
        """Test form analysis with multiple poses."""
        # Setup
        multiple_poses_data = {
            'poses': [
                {
                    'keypoints': [
                        {'x': 100, 'y': 100, 'score': 0.9},
                        {'x': 200, 'y': 200, 'score': 0.9},
                        {'x': 300, 'y': 300, 'score': 0.9}
                    ]
                },
                {
                    'keypoints': [
                        {'x': 150, 'y': 150, 'score': 0.9},
                        {'x': 250, 'y': 250, 'score': 0.9},
                        {'x': 350, 'y': 350, 'score': 0.9}
                    ]
                }
            ]
        }

        # Execute
        result = await form_analysis_service.analyze_form(multiple_poses_data)

        # Assert
        assert result['status'] == AnalysisStatus.COMPLETED
        assert 'average_joint_angles' in result
        assert 'pose_count' in result
        assert result['pose_count'] == 2
    
    @pytest.mark.asyncio
    async def test_analyze_form_invalid_video(self, form_analysis_service):
        """Test form analysis with invalid video ID."""
        with pytest.raises(ValueError, match="Video not found"):
            await form_analysis_service.analyze_form(999)
    
    @pytest.mark.asyncio
    async def test_analyze_form_processing_error(self, form_analysis_service):
        """Test form analysis with processing error."""
        # Create test data
        user = await self.create_test_user()
        video = await self.create_test_video(user_id=user["id"])
        
        # Mock video processing error
        with patch("app.services.form_analysis.VideoProcessor") as mock_processor:
            mock_processor.return_value.process_video.side_effect = Exception("Processing failed")
            
            with pytest.raises(Exception, match="Failed to analyze form"):
                await form_analysis_service.analyze_form(video["id"])
    
    @pytest.mark.asyncio
    async def test_get_form_history(self, form_analysis_service):
        """Test retrieving form analysis history."""
        # Create test data
        user = await self.create_test_user()
        video = await self.create_test_video(user_id=user["id"])
        form_check = await self.create_test_form_check(video_id=video["id"])
        
        # Get history
        history = await form_analysis_service.get_form_history(user["id"])
        
        # Verify results
        assert len(history) == 1
        assert history[0]["video_id"] == video["id"]
        assert history[0]["score"] == form_check["score"]
    
    @pytest.mark.asyncio
    async def test_get_form_history_empty(self, form_analysis_service):
        """Test retrieving empty form analysis history."""
        # Create test user without any form checks
        user = await self.create_test_user()
        
        # Get history
        history = await form_analysis_service.get_form_history(user["id"])
        
        # Verify results
        assert len(history) == 0 
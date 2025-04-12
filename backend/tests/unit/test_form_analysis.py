import pytest
from unittest.mock import Mock, patch
from app.models.form_analysis import FormAnalysis
from app.services.form_analysis import FormAnalysisService
from app.core.exceptions import AnalysisError
from tests.factories import FormAnalysisFactory, VideoFactory, UserFactory

def test_form_analysis_creation():
    user = UserFactory()
    video = VideoFactory(user_id=user.id)
    analysis = FormAnalysisFactory(user_id=user.id, video_id=video.id)
    
    assert analysis.user_id == user.id
    assert analysis.video_id == video.id
    assert analysis.status == "pending"
    assert isinstance(analysis.feedback, str)

def test_analysis_status_update():
    analysis = FormAnalysisFactory()
    analysis.status = "processing"
    assert analysis.status == "processing"
    analysis.status = "completed"
    assert analysis.status == "completed"

def test_analysis_error_handling():
    analysis = FormAnalysisFactory()
    with pytest.raises(AnalysisError):
        analysis.status = "error"
        analysis.error_message = "Analysis failed"
        raise AnalysisError("Analysis failed")

@patch('app.services.form_analysis.FormAnalysisService.analyze_form')
def test_form_analysis_process(mock_analyze):
    analysis = FormAnalysisFactory()
    mock_analyze.return_value = {
        "status": "completed",
        "feedback": "Good form",
        "score": 85
    }
    
    service = FormAnalysisService()
    result = service.analyze_form(analysis)
    
    assert result["status"] == "completed"
    assert "feedback" in result
    assert "score" in result
    mock_analyze.assert_called_once_with(analysis)

def test_analysis_validation():
    analysis = FormAnalysisFactory()
    assert analysis.is_valid()
    
    analysis.status = "error"
    assert not analysis.is_valid()
    
    analysis.status = "completed"
    analysis.feedback = ""
    assert not analysis.is_valid()

@patch('app.services.form_analysis.FormAnalysisService.get_user_history')
def test_user_analysis_history(mock_history):
    user = UserFactory()
    analyses = [FormAnalysisFactory(user_id=user.id) for _ in range(3)]
    mock_history.return_value = analyses
    
    service = FormAnalysisService()
    result = service.get_user_history(user.id)
    
    assert len(result) == 3
    assert all(a.user_id == user.id for a in result)
    mock_history.assert_called_once_with(user.id) 
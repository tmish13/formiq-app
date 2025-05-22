import pytest
from unittest.mock import Mock, patch, AsyncMock # AsyncMock if service methods are async
from app.services.form_analysis import FormAnalysisService
# Assuming FormAnalysis model might be used for type hinting or constructing mock return values
from app.models.form_analysis import FormAnalysis 
from tests.utils.factories import FormAnalysisFactory, UserFactory # FIXED: Corrected import path

# If FormAnalysisService has dependencies (like a DB session or other services),
# they should be mocked here.
@pytest.fixture
def mock_db_session_for_fas(): # FAS for FormAnalysisService
    return AsyncMock() # Or Mock(spec=Session) if synchronous

@pytest.fixture
def form_analysis_service(mock_db_session_for_fas):
    # If FormAnalysisService takes db session in constructor:
    # return FormAnalysisService(db=mock_db_session_for_fas)
    # If it has no constructor dependencies or they are different, adjust accordingly.
    return FormAnalysisService() # Assuming default constructor or mocked dependencies injected elsewhere

@pytest.mark.asyncio # If analyze_form is async
async def test_form_analysis_service_process(form_analysis_service: FormAnalysisService):
    """Test the analyze_form method of FormAnalysisService."""
    # Create a mock FormAnalysis object that the service method might expect
    mock_analysis_input = FormAnalysisFactory.build() # Using .build() as it's input to a mocked method
    
    expected_result = {
        "status": "completed",
        "feedback": "Good form based on mock analysis",
        "score": 90
    }
    
    # Patch the actual analysis logic within the service if it calls out to complex sub-processes
    # or if analyze_form itself is the top-level method being unit tested with mocked dependencies.
    # The original test patched 'app.services.form_analysis.FormAnalysisService.analyze_form'
    # which means it was testing something that *calls* analyze_form, or it was an integration test.
    # For a unit test of analyze_form method itself, we'd mock its internal calls or dependencies.
    # Let's assume analyze_form is complex and we mock a helper it calls, or it's simple enough.

    # If analyze_form is a simple method on the service that orchestrates calls to a (mocked) model
    # or other (mocked) services, then we can test it directly.
    # For this example, let's assume analyze_form itself contains the logic and doesn't call out,
    # or its external calls are handled by mocked dependencies of the service.
    
    # To truly unit test analyze_form, we need to know its dependencies.
    # If it depends on, e.g., an AI model client, that client should be mocked.
    # For now, let's assume analyze_form works on the input and produces a dict.
    # If analyze_form is just a wrapper, this test becomes trivial unless we mock what it wraps.

    # Re-evaluating the original patch: @patch('app.services.form_analysis.FormAnalysisService.analyze_form')
    # This implies the test wasn't unit-testing analyze_form itself, but a caller of it.
    # Let's adapt: Assume we are testing `analyze_form` method itself, and it might call a private method `_perform_deep_analysis`

    with patch.object(form_analysis_service, '_perform_deep_analysis', new_callable=AsyncMock) as mock_deep_analyze:
        mock_deep_analyze.return_value = expected_result # What the internal deep analysis would return
        
        # If analyze_form takes the model instance and updates it, or returns data:
        result_data = await form_analysis_service.analyze_form(video_id=mock_analysis_input.video_id, user_id=mock_analysis_input.user_id) # Adapt params as needed
        # Or, if it takes the analysis object itself:
        # result_data = await form_analysis_service.analyze_form(mock_analysis_input)

    assert result_data["status"] == "completed"
    assert "feedback" in result_data
    assert "score" in result_data
    mock_deep_analyze.assert_called_once() # Or called with specific args

@pytest.mark.asyncio # If get_user_history is async
async def test_form_analysis_service_user_history(form_analysis_service: FormAnalysisService, mock_db_session_for_fas):
    """Test the get_user_history method of FormAnalysisService."""
    user = UserFactory.build()
    # Create a list of mock FormAnalysis objects
    expected_analyses = [FormAnalysisFactory.build(user_id=user.id) for _ in range(3)]
    
    # If get_user_history directly uses the db session passed to FormAnalysisService:
    # Example: mock_db_session_for_fas.query(FormAnalysis)... .all() returning expected_analyses
    # For a pure unit test, we mock the DB interaction part.
    # Let's assume get_user_history is a method that does a DB query.
    # We need to mock that query.
    # This example assumes FormAnalysisService has a `self.db` attribute.
    
    # If FormAnalysisService uses a repository pattern, mock the repository method.
    # For simplicity, if it queries directly:
    mock_query_result = AsyncMock()
    mock_query_result.all.return_value = expected_analyses
    
    mock_db_session_for_fas.execute = AsyncMock(return_value=mock_query_result) # Simplified mock for execute -> scalar/all
    # A more precise mock would be: mock_db_session_for_fas.query(FormAnalysis).filter(...).all = AsyncMock(return_value=expected_analyses)
    # However, SQLAlchemy 2.0 style uses select() and db.execute().
    # Let's assume a mock that covers the result of db.execute(...).scalars().all()
    mock_scalars = AsyncMock()
    mock_scalars.all.return_value = expected_analyses
    mock_db_session_for_fas.execute.return_value.scalars.return_value = mock_scalars

    # The original test patched 'app.services.form_analysis.FormAnalysisService.get_user_history'
    # again, implying testing a caller. Here we test the method itself.
    
    retrieved_analyses = await form_analysis_service.get_user_history(user_id=user.id)
    
    assert len(retrieved_analyses) == 3
    assert all(a.user_id == user.id for a in retrieved_analyses)
    # Assert that the db session was called correctly
    mock_db_session_for_fas.execute.assert_called_once() # Or more specific call_args check 
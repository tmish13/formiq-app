from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import Settings
from app.models.form_check import FormCheck
from app.models.exercise import ExerciseTemplate
# from ..core.utils.pose_estimation import calculate_pose_metrics
import logging
import numpy as np

logger = logging.getLogger(__name__)

class PersonalizedFeedbackService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        # Placeholder for an LLM client if we were to integrate one directly
        # self.llm_client = LangflowClient(api_key=settings.LANGFLOW_API_KEY)

    async def generate_personalized_feedback(
        self,
        form_check: FormCheck, # Changed input
        user_id: str # user_id still needed for history
    ) -> Dict[str, Any]:
        """Generate personalized feedback based on user history and a specific FormCheck.
        
        This version aims to use the new ML scores from the FormCheck object
        to generate LLM-based feedback (currently placeholder).
        """
        
        if not form_check.exercise:
            # Ensure the exercise relationship is loaded if needed for exercise_name
            # This might require eager loading when form_check is fetched or a separate query.
            # For now, we'll try to access it and handle potential errors or None.
            logger.warning(f"FormCheck {form_check.id} does not have exercise relationship loaded.")
            # Attempt to load it if not loaded - requires form_check to be a persisted SQLAlchemy model instance
            # This is a simplified approach; robust loading should happen when form_check is fetched.
            if isinstance(form_check, FormCheck) and hasattr(form_check, '_sa_instance_state'): # Check if SQLAlchemy model
                await self.db.refresh(form_check, ["exercise"])
            
        exercise_name = form_check.exercise.name if form_check.exercise else "Unknown Exercise"
        exercise_id_str = str(form_check.exercise_id) # For history fetching

        history = await self._get_user_history(user_id, exercise_id_str, exercise_name) # Pass exercise_name for filtering
        
        progress_metrics = self._calculate_progress_metrics(history, form_check) # Pass current form_check too
        
        # Extract new ML scores from the current FormCheck
        current_ml_scores = {
            "posture_score": form_check.posture_score,
            "hypertrophy_form_score": form_check.hypertrophy_form_score,
            "stability_score": form_check.stability_score,
            # Add other relevant current analysis data if needed by LLM
            "overall_score_from_rules": form_check.score, # Example, if dynamic analysis score is still relevant
            "reps_detected": form_check.reps_detected
        }

        # Generate LLM-based feedback (placeholder)
        llm_feedback_text = await self._get_llm_feedback(
            current_scores=current_ml_scores,
            exercise_name=exercise_name,
            progress_metrics=progress_metrics
        )
        
        # For now, let's keep the old suggestion logic, but it could also be LLM-driven
        # Note: current_analysis dict is no longer directly passed. Adapt if _generate_suggestions needs it.
        # For this iteration, let's simplify and assume suggestions might come from LLM too, or are separate.
        suggestions = self._generate_suggestions_from_progress(progress_metrics)

        return {
            "feedback": llm_feedback_text, # Main feedback from LLM
            "suggestions": suggestions, # Can be from LLM or separate logic
            "progress_metrics": progress_metrics, # Historical progress
            "current_scores_summary": current_ml_scores # Summary of current ML scores used
        }

    async def _get_llm_feedback(
        self, 
        current_scores: Dict[str, Any], 
        exercise_name: str, 
        progress_metrics: Dict[str, Any]
    ) -> str:
        """
        (Placeholder) Construct prompt and get feedback from LLM.
        """
        prompt = f"""
        Analyze the user's performance for {exercise_name}.
        Current Scores:
        - Posture: {current_scores.get('posture_score', 'N/A')}
        - Hypertrophy Form: {current_scores.get('hypertrophy_form_score', 'N/A')}
        - Stability: {current_scores.get('stability_score', 'N/A')}
        - Reps Detected: {current_scores.get('reps_detected', 'N/A')}
        Historical Progress for {exercise_name}:
        - Overall Trend: {progress_metrics.get('trend', 'N/A')}
        - Improvement Areas: {progress_metrics.get('improvement_areas', 'N/A')}
        - Strengths: {progress_metrics.get('strengths', 'N/A')}
        - Consistency: {progress_metrics.get('consistency_score', 'N/A')}
        Provide concise, actionable feedback and encouragement.
        Focus on 1-2 key areas based on the current scores and historical trends.
        """
        logger.info(f"PersonalizedFeedbackService: Generated LLM Prompt (len {len(prompt)}):\n{prompt}")
        
        # Simulate LLM call
        # In a real scenario: response = await self.llm_client.generate(prompt)
        simulated_llm_response = (
            f"Great effort on the {exercise_name}! \
            Your posture score is {current_scores.get('posture_score', 'good')} and stability is {current_scores.get('stability_score', 'solid')}. \
            To further enhance hypertrophy, focus on [specific tip based on hypertrophy_form_score and exercise]. \
            Keep an eye on {progress_metrics.get('improvement_areas',['consistency'])[0] if progress_metrics.get('improvement_areas') else 'overall form'} based on your trends."
        )
        logger.info(f"PersonalizedFeedbackService: Simulated LLM Response: {simulated_llm_response}")
        return simulated_llm_response

    async def _get_user_history(
        self,
        user_id: str,
        exercise_id_str: str, # Changed from exercise_type (name) to ID for more precise filtering
        exercise_name_for_log: str # Keep for logging
    ) -> List[FormCheck]:
        """Get user's exercise history for a specific exercise ID for the past 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Assuming form_check.exercise_id directly refers to ExerciseTemplate.id
        stmt = (
            select(FormCheck)
            .options(selectinload(FormCheck.exercise)) # Eager load exercise for name if needed by caller
            .filter(
                FormCheck.user_id == user_id,
                FormCheck.exercise_id == exercise_id_str, # Filter by exercise_id (UUID)
                FormCheck.created_at >= thirty_days_ago,
                FormCheck.status == "completed" # Only completed analyses
            )
            .order_by(FormCheck.created_at.desc())
            .limit(20) # Limit history to avoid overly long processing
        )
        logger.debug(f"Fetching history for user {user_id}, exercise ID {exercise_id_str} ({exercise_name_for_log})")
        result = await self.db.execute(stmt)
        history_items = result.scalars().all()
        logger.debug(f"Found {len(history_items)} items in history for user {user_id}, exercise ID {exercise_id_str}.")
        return history_items

    def _calculate_progress_metrics(
        self,
        history: List[FormCheck],
        current_form_check: FormCheck # Add current form check to include its scores in latest metric
    ) -> Dict[str, Any]:
        """Calculate user's progress metrics based on exercise history, including new ML scores."""
        
        # Include current form_check scores as the most recent data point if history is used for trends
        # For simplicity, this example will primarily use history for trends and current for latest.
        # A more advanced trend could incorporate the current_form_check into the series.

        if not history and not current_form_check: # Should not happen if called after a form check
            logger.warning("_calculate_progress_metrics called with no history and no current_form_check")
            return {
                "trend": "neutral", "improvement_areas": [], "strengths": [],
                "consistency_score": 0.0, "metric_trends": {}
            }

        # Define metrics to track, now including new ML scores
        # Old metrics from h_item.results: "alignment", "stability", "symmetry", "consistency"
        # New metrics from h_item directly: "posture_score", "hypertrophy_form_score", "stability_score"
        
        # Let's define a unified way to access these, preferring new scores if available
        def get_metric_value(fc: FormCheck, metric_key: str) -> Optional[float]:
            if metric_key == "posture_score": return fc.posture_score
            if metric_key == "hypertrophy_form_score": return fc.hypertrophy_form_score
            if metric_key == "stability_score": return fc.stability_score # This will override old 'stability'
            # Fallback to old structure if new scores are not the target or not present
            if fc.results and isinstance(fc.results, dict):
                if metric_key in fc.results: return float(fc.results[metric_key])
                if "metrics" in fc.results and isinstance(fc.results["metrics"], dict):
                    return float(fc.results["metrics"].get(metric_key, 0.0))
            return None # Or 0.0 if a default is preferred for missing historical data

        # For trend calculation, we use historical data. 
        # If current_form_check is also to be part of the trend, prepend it to history (oldest first for trend calc).
        # For now, history is just history. Latest is from current_form_check.
        
        tracked_metrics_for_trends = ["posture_score", "hypertrophy_form_score", "stability_score"] # New primary metrics
        # Add old ones if still relevant for historical comparison & trends, ensure no name clashes or handle them
        # e.g., "original_stability" if stability_score is the new one.
        # For now, focusing on trends of new scores from history where they *might* exist.
        # This part needs careful thought on how to handle transition from old scores to new scores in history.
        # Assuming for MVP, we primarily look at trends if these new scores were hypothetically backfilled or start appearing.

        metric_trends = {}
        all_history_for_trends = history # Does not include current_form_check for trend calculation here

        for metric_name in tracked_metrics_for_trends:
            values = []
            for h_item in all_history_for_trends: # Iterate oldest to newest if history is desc, reverse for trend calc
                val = get_metric_value(h_item, metric_name)
                if val is not None: values.append(val)
            
            # Trend calculation expects values in chronological order (oldest to newest)
            # History is fetched .desc() so it's newest to oldest. Reverse for trend calc.
            metric_trends[metric_name] = self._calculate_metric_trend(list(reversed(values)))

        # Improvement areas & strengths based on LATEST scores (from current_form_check)
        # and trends from history.
        latest_posture = get_metric_value(current_form_check, "posture_score")
        latest_hypertrophy = get_metric_value(current_form_check, "hypertrophy_form_score")
        latest_stability = get_metric_value(current_form_check, "stability_score")

        improvement_areas = []
        if latest_posture is not None and latest_posture < 0.7: improvement_areas.append("posture")
        if metric_trends.get("posture_score", 0) < -0.05 and "posture" not in improvement_areas: improvement_areas.append("posture (declining trend)")
        
        if latest_hypertrophy is not None and latest_hypertrophy < 0.7: improvement_areas.append("hypertrophy-related form")
        if metric_trends.get("hypertrophy_form_score", 0) < -0.05 and "hypertrophy-related form" not in improvement_areas: improvement_areas.append("hypertrophy-related form (declining trend)")

        if latest_stability is not None and latest_stability < 0.7: improvement_areas.append("stability")
        if metric_trends.get("stability_score", 0) < -0.05 and "stability" not in improvement_areas: improvement_areas.append("stability (declining trend)")

        strengths = []
        if latest_posture is not None and latest_posture >= 0.85: strengths.append("posture")
        if latest_hypertrophy is not None and latest_hypertrophy >= 0.85: strengths.append("hypertrophy-related form")
        if latest_stability is not None and latest_stability >= 0.85: strengths.append("stability")
        
        # Consistency can still be calculated from historical `score` or a general quality metric if available
        # For now, let's simplify consistency or assume it's derived from variation in primary scores.
        # Placeholder for consistency:
        consistency_score_val = 0.75 # Placeholder
        if history:
            # Example: consistency of overall rule-based score if available in history
            historical_overall_scores = [h.score for h in history if h.score is not None]
            if len(historical_overall_scores) >= 2:
                consistency_score_val = 1 - (np.std(historical_overall_scores) / np.mean(historical_overall_scores)) if np.mean(historical_overall_scores) else 0
                consistency_score_val = max(0, min(1, consistency_score_val)) # Clamp to 0-1
        
        sum_of_trends = sum(val for val in metric_trends.values() if val is not None)
        count_of_trends = sum(1 for val in metric_trends.values() if val is not None)
        average_trend_val = sum_of_trends / count_of_trends if count_of_trends > 0 else 0

        overall_trend = "neutral"
        if average_trend_val > 0.05: overall_trend = "improving"
        elif average_trend_val < -0.05: overall_trend = "declining"

        return {
            "trend": overall_trend,
            "improvement_areas": improvement_areas,
            "strengths": strengths,
            "consistency_score": round(consistency_score_val, 2),
            "metric_trends": metric_trends # Trends of posture, hypertrophy, stability scores
        }

    def _calculate_metric_trend(self, values: List[float]) -> float:
        """Calculate the trend of a metric over time using simple linear regression slope."""
        if len(values) < 2:
            return 0.0
        
        x_coords = list(range(len(values)))
        n = len(values)
        
        mean_x = sum(x_coords) / n
        mean_y = sum(values) / n
        
        numerator = sum((x_coords[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x_coords[i] - mean_x) ** 2 for i in range(n))
        
        return round(numerator / denominator, 3) if denominator != 0 else 0.0

    def _get_latest_metric(self, history: List[FormCheck], metric: str) -> float:
        # This method might be less relevant if we get latest from current_form_check directly
        # in _calculate_progress_metrics. Or it's used for other historical metrics.
        if not history:
            return 0.0
        latest_item = history[0] # Newest item
        # Adapt to use get_metric_value helper
        val = self._get_metric_value_from_formcheck(latest_item, metric) # changed to new helper
        return val if val is not None else 0.0

    # Added helper to DRY metric access from a single FormCheck
    def _get_metric_value_from_formcheck(self, fc: FormCheck, metric_key: str) -> Optional[float]:
        if metric_key == "posture_score": return fc.posture_score
        if metric_key == "hypertrophy_form_score": return fc.hypertrophy_form_score
        if metric_key == "stability_score": return fc.stability_score
        if fc.results and isinstance(fc.results, dict):
            if metric_key in fc.results: return float(fc.results[metric_key])
            if "metrics" in fc.results and isinstance(fc.results["metrics"], dict):
                return float(fc.results["metrics"].get(metric_key, 0.0))
        return None

    def _generate_suggestions_from_progress(
        self,
        progress_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized suggestions based on progress metrics."""
        # This is the old _generate_suggestions, renamed and taking only progress_metrics
        # It can be a fallback if LLM suggestions are not used, or a supplement.
        suggestions = []
        for area in progress_metrics.get("improvement_areas", []):
            if "posture" in area:
                suggestions.append("Practice with lighter weights or bodyweight, focusing on posture cues. A mirror can be very helpful.")
            elif "hypertrophy-related form" in area:
                suggestions.append("Ensure you're achieving full range of motion and controlling the tempo, especially the eccentric (lowering) phase.")
            elif "stability" in area:
                suggestions.append("Consider incorporating unilateral (single-leg or single-arm) exercises and core strengthening work.")
            elif area == "alignment": # old metric, keep for example
                suggestions.append("Practice with lighter weights or bodyweight, focusing on proper alignment cues.")
            # Add more specific suggestions if possible

        if progress_metrics.get("trend") == "improving" and progress_metrics.get("consistency_score", 0.0) >= 0.7:
            suggestions.append("You're showing solid improvement and consistency! You might be ready to gradually increase the intensity or complexity.")
        elif progress_metrics.get("trend") == "declining":
            suggestions.append("Consider slightly reducing weight or intensity to really nail down the form on each rep.")
        
        if not suggestions:
            suggestions.append("Keep focusing on quality movement. For specific exercise tips, check our exercise library!")
        return suggestions

from fastapi import Depends

async def get_async_personalized_feedback_service(
    # db: AsyncSession = Depends(get_async_db), # Original problematic Depends
    # settings: Settings = Depends(get_settings) # Original problematic Depends
) -> PersonalizedFeedbackService:
    from app.core.deps import get_async_db, get_settings # ADDING LOCAL IMPORTS
    from sqlalchemy.ext.asyncio import AsyncSession # For type hint
    from app.core.config import Settings # For type hint
    from fastapi import Depends as FastAPI_Depends # Alias to avoid conflict if Depends is used differently above

    db: AsyncSession = FastAPI_Depends(get_async_db)
    settings: Settings = FastAPI_Depends(get_settings)
    return PersonalizedFeedbackService(db=db, settings=settings) 
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import Settings
from app.models.form_check import FormCheck
from app.models.exercise import ExerciseTemplate
# from ..core.utils.pose_estimation import calculate_pose_metrics
import logging

logger = logging.getLogger(__name__)

class PersonalizedFeedbackService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def generate_personalized_feedback(
        self,
        user_id: str,
        current_analysis: Dict[str, Any],
        exercise_type: str
    ) -> Dict[str, Any]:
        """Generate personalized feedback based on user history and current analysis."""
        
        history = await self._get_user_history(user_id, exercise_type)
        
        progress_metrics = self._calculate_progress_metrics(history)
        
        feedback = self._generate_feedback(current_analysis, progress_metrics)
        
        suggestions = self._generate_suggestions(current_analysis, progress_metrics)
        
        return {
            "feedback": feedback,
            "suggestions": suggestions,
            "progress_metrics": progress_metrics
        }

    async def _get_user_history(
        self,
        user_id: str,
        exercise_type: str
    ) -> List[FormCheck]:
        """Get user's exercise history for the past 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        stmt = (
            select(FormCheck)
            .join(FormCheck.exercise)
            .filter(
                FormCheck.user_id == user_id,
                ExerciseTemplate.name == exercise_type,
                FormCheck.created_at >= thirty_days_ago
            )
            .order_by(FormCheck.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def _calculate_progress_metrics(
        self,
        history: List[FormCheck]
    ) -> Dict[str, Any]:
        """Calculate user's progress metrics based on exercise history."""
        if not history:
            return {
                "trend": "neutral",
                "improvement_areas": [],
                "strengths": [],
                "consistency_score": 0.0,
                "metric_trends": {}
            }

        metric_trends = {}
        possible_metrics = ["alignment", "stability", "symmetry", "consistency"]
        for metric_name in possible_metrics:
            values = []
            for h_item in history:
                if h_item.results and isinstance(h_item.results, dict) and metric_name in h_item.results:
                    values.append(float(h_item.results[metric_name]))
                elif h_item.results and isinstance(h_item.results, dict) and "metrics" in h_item.results and isinstance(h_item.results["metrics"], dict):
                    values.append(float(h_item.results["metrics"].get(metric_name, 0.0)))
                else:
                    values.append(0.0)
            metric_trends[metric_name] = self._calculate_metric_trend(values)

        improvement_areas = [
            metric for metric, trend_val in metric_trends.items()
            if trend_val < 0 or (trend_val == 0 and self._get_latest_metric(history, metric) < 0.7)
        ]
        
        strengths = [
            metric for metric, trend_val in metric_trends.items()
            if trend_val > 0 and self._get_latest_metric(history, metric) >= 0.8
        ]

        consistency_values = []
        for h_item in history:
            if h_item.results and isinstance(h_item.results, dict) and "consistency" in h_item.results:
                consistency_values.append(float(h_item.results["consistency"]))
            elif h_item.results and isinstance(h_item.results, dict) and "metrics" in h_item.results and isinstance(h_item.results["metrics"], dict):
                consistency_values.append(float(h_item.results["metrics"].get("consistency", 0.0)))
            else:
                consistency_values.append(0.0)
                
        consistency_score = len([val for val in consistency_values if val >= 0.7]) / len(consistency_values) if consistency_values else 0.0
        
        sum_trends = sum(metric_trends.values())
        overall_trend = "neutral"
        if sum_trends > 0.1:
            overall_trend = "improving"
        elif sum_trends < -0.1:
            overall_trend = "declining"

        return {
            "trend": overall_trend,
            "improvement_areas": improvement_areas,
            "strengths": strengths,
            "consistency_score": round(consistency_score, 2),
            "metric_trends": metric_trends
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
        """Get the latest value for a specific metric."""
        if not history:
            return 0.0
        latest_item = history[0]
        if latest_item.results and isinstance(latest_item.results, dict) and metric in latest_item.results:
            return float(latest_item.results[metric])
        elif latest_item.results and isinstance(latest_item.results, dict) and "metrics" in latest_item.results and isinstance(latest_item.results["metrics"], dict):
            return float(latest_item.results["metrics"].get(metric, 0.0))
        return 0.0

    def _generate_feedback(
        self,
        current_analysis: Dict[str, Any],
        progress_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized feedback based on current analysis and progress metrics."""
        feedback = []

        if progress_metrics.get("trend") == "improving":
            feedback.append("Your form has been improving consistently! Keep up the great work.")
        elif progress_metrics.get("trend") == "declining":
            feedback.append("Let's focus on maintaining proper form throughout your exercises. Reviewing basics might help.")

        for area in progress_metrics.get("improvement_areas", []):
            feedback.append(f"Continue working on your {area} - try focusing on this aspect during your next session.")

        for strength in progress_metrics.get("strengths", []):
            feedback.append(f"Great job maintaining excellent {strength}!")

        consistency_score = progress_metrics.get("consistency_score", 0.0)
        if consistency_score >= 0.8:
            feedback.append("You're maintaining very consistent form across sessions! That's key to progress.")
        elif consistency_score < 0.5 and len(progress_metrics.get("metric_trends", {})) > 0:
            feedback.append("Try to maintain more consistent form across your sessions. Focus on one or two cues each time.")

        if not feedback:
            feedback.append("Keep focusing on your form and consistency for the best results.")

        return feedback

    def _generate_suggestions(
        self,
        current_analysis: Dict[str, Any],
        progress_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized suggestions based on current analysis and progress metrics."""
        suggestions = []

        for area in progress_metrics.get("improvement_areas", []):
            if area == "alignment":
                suggestions.append("Practice with lighter weights or bodyweight, focusing on proper alignment cues.")
            elif area == "stability":
                suggestions.append("Consider incorporating unilateral (single-leg or single-arm) exercises to improve stability.")
            elif area == "symmetry":
                suggestions.append("Pay close attention to equal engagement and movement on both sides of your body. Using a mirror can help.")

        if progress_metrics.get("trend") == "improving" and progress_metrics.get("consistency_score", 0.0) >= 0.7:
            suggestions.append("You're showing solid improvement and consistency! You might be ready to gradually increase the intensity or complexity of your workouts.")
        elif progress_metrics.get("trend") == "declining":
            suggestions.append("Consider slightly reducing weight or intensity to really nail down the form on each rep.")

        if progress_metrics.get("consistency_score", 0.0) < 0.7 and len(progress_metrics.get("metric_trends", {})) > 0:
            suggestions.append("Focus on achieving consistent form in each session. Pick one or two key aspects to concentrate on each time.")

        if not suggestions:
            suggestions.append("Keep practicing and stay mindful of your technique. Consistent effort builds good habits!")
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
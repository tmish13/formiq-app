from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.database.form_analysis import FormAnalysis
from ..models.form_analysis import FormAnalysisMetrics
from ..core.utils.pose_estimation import calculate_pose_metrics

class PersonalizedFeedbackService:
    def __init__(self, db: Session):
        self.db = db

    async def generate_personalized_feedback(
        self,
        user_id: str,
        current_analysis: Dict[str, Any],
        exercise_type: str
    ) -> Dict[str, Any]:
        """Generate personalized feedback based on user history and current analysis."""
        
        # Get user's exercise history for the past 30 days
        history = await self._get_user_history(user_id, exercise_type)
        
        # Calculate user's progress metrics
        progress_metrics = self._calculate_progress_metrics(history)
        
        # Generate personalized feedback
        feedback = self._generate_feedback(current_analysis, progress_metrics)
        
        # Generate personalized suggestions
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
    ) -> List[FormAnalysis]:
        """Get user's exercise history for the past 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        return self.db.query(FormAnalysis).filter(
            FormAnalysis.user_id == user_id,
            FormAnalysis.exercise_type == exercise_type,
            FormAnalysis.created_at >= thirty_days_ago
        ).order_by(FormAnalysis.created_at.desc()).all()

    def _calculate_progress_metrics(
        self,
        history: List[FormAnalysis]
    ) -> Dict[str, Any]:
        """Calculate user's progress metrics based on exercise history."""
        if not history:
            return {
                "trend": "neutral",
                "improvement_areas": [],
                "strengths": [],
                "consistency_score": 0.0
            }

        # Calculate trends in metrics
        metric_trends = {
            "alignment": self._calculate_metric_trend([h.metrics["alignment"] for h in history]),
            "stability": self._calculate_metric_trend([h.metrics["stability"] for h in history]),
            "symmetry": self._calculate_metric_trend([h.metrics["symmetry"] for h in history]),
            "consistency": self._calculate_metric_trend([h.metrics["consistency"] for h in history])
        }

        # Identify improvement areas and strengths
        improvement_areas = [
            metric for metric, trend in metric_trends.items()
            if trend < 0 or (trend == 0 and self._get_latest_metric(history, metric) < 0.7)
        ]
        
        strengths = [
            metric for metric, trend in metric_trends.items()
            if trend > 0 and self._get_latest_metric(history, metric) >= 0.8
        ]

        # Calculate consistency score
        consistency_score = len([h for h in history if h.metrics["consistency"] >= 0.7]) / len(history)

        return {
            "trend": "improving" if sum(metric_trends.values()) > 0 else "declining",
            "improvement_areas": improvement_areas,
            "strengths": strengths,
            "consistency_score": consistency_score,
            "metric_trends": metric_trends
        }

    def _calculate_metric_trend(self, values: List[float]) -> float:
        """Calculate the trend of a metric over time."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        x = list(range(len(values)))
        y = values
        n = len(values)
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0

    def _get_latest_metric(self, history: List[FormAnalysis], metric: str) -> float:
        """Get the latest value for a specific metric."""
        return history[0].metrics[metric] if history else 0.0

    def _generate_feedback(
        self,
        current_analysis: Dict[str, Any],
        progress_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized feedback based on current analysis and progress metrics."""
        feedback = []

        # Add progress-based feedback
        if progress_metrics["trend"] == "improving":
            feedback.append("Your form has been improving consistently!")
        elif progress_metrics["trend"] == "declining":
            feedback.append("Let's focus on maintaining proper form throughout your exercises.")

        # Add metric-specific feedback
        for area in progress_metrics["improvement_areas"]:
            feedback.append(f"Continue working on your {area} - try focusing on this aspect during your next session.")

        for strength in progress_metrics["strengths"]:
            feedback.append(f"Great job maintaining excellent {strength}!")

        # Add consistency feedback
        if progress_metrics["consistency_score"] >= 0.8:
            feedback.append("You're maintaining very consistent form across sessions!")
        elif progress_metrics["consistency_score"] < 0.5:
            feedback.append("Try to maintain more consistent form across your sessions.")

        return feedback

    def _generate_suggestions(
        self,
        current_analysis: Dict[str, Any],
        progress_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized suggestions based on current analysis and progress metrics."""
        suggestions = []

        # Add improvement area suggestions
        for area in progress_metrics["improvement_areas"]:
            if area == "alignment":
                suggestions.append("Practice with lighter weights while focusing on proper alignment.")
            elif area == "stability":
                suggestions.append("Consider incorporating balance exercises into your routine.")
            elif area == "symmetry":
                suggestions.append("Pay attention to equal engagement on both sides of your body.")
            elif area == "consistency":
                suggestions.append("Try using a metronome to maintain consistent tempo.")

        # Add progression suggestions
        if progress_metrics["trend"] == "improving":
            suggestions.append("You're ready to gradually increase the intensity of your workouts.")
        elif progress_metrics["trend"] == "declining":
            suggestions.append("Consider reducing weight/intensity to focus on form.")

        # Add consistency suggestions
        if progress_metrics["consistency_score"] < 0.7:
            suggestions.append("Record your exercises more frequently to track your progress better.")

        return suggestions 
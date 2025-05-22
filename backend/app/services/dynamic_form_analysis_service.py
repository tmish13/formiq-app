"""
Dynamic form analysis service module.

This service uses the database-backed exercise configurations to analyze form.
It replaces the hardcoded rule-based analysis with a dynamic rules engine.
"""
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings

from app.services.exercise_config_service import ExerciseConfigService
from app.services.form_check_service import FormCheckService
from app.models.exercise_config import ExerciseConfig
from app.models.form_check import FormCheck, FeedbackItem
from app.models.video import Video
from app.models.enums import FeedbackType, FeedbackSeverity
from app.core.exceptions import ValidationError, NotFoundException

logger = logging.getLogger(__name__)

class DynamicFormAnalysisService:
    """
    Service for analyzing exercise form using dynamic configurations.
    
    This service replaces hardcoded form analysis with dynamic database-backed rules.
    """
    
    def __init__(self, db: AsyncSession, settings: Settings, exercise_config_service: ExerciseConfigService, form_check_service: FormCheckService):
        self.db = db
        self.settings = settings
        self.exercise_config_service = exercise_config_service
        self.form_check_service = form_check_service

    async def _get_exercise_config_model_async(self, exercise_template_id: UUID) -> Optional[ExerciseConfig]:
        """
        Get the active exercise configuration model for an exercise template.
        """
        config_model = await self.exercise_config_service.get_active_config_for_exercise_async(exercise_id=exercise_template_id)
        return config_model
    
    async def segment_repetitions(
        self, 
        angle_data_sequence: List[Dict[str, Any]],
        config: ExerciseConfig
    ) -> List[List[Dict[str, Any]]]:
        """
        Segments a sequence of angle data into repetitions based on movement phase transitions.
        Each repetition is a list of angle data frames.
        
        Placeholder implementation.
        """
        logger.info(f"Attempting to segment {len(angle_data_sequence)} frames into repetitions using config: {config.name}")
        
        if not angle_data_sequence or not config or not config.movement_phases:
            logger.warning("Insufficient data for segmentation: missing angle data, config, or movement phases.")
            return []

        # Placeholder: treats the whole sequence as one rep for now
        # Actual implementation will iterate through frames, detect phase changes based on config.movement_phases triggers
        # and group frames into lists, each list representing one repetition.
        logger.warning("segment_repetitions is a placeholder and treats the whole sequence as one rep.")
        return [angle_data_sequence] 

    async def evaluate_rep(
        self, 
        rep_angle_data: List[Dict[str, Any]],
        config: ExerciseConfig
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Evaluates a single repetition against the exercise configuration.
        Checks joint angles per frame, per phase, aggregates violations, and generates feedback.

        Placeholder implementation.
        """
        logger.info(f"Evaluating repetition with {len(rep_angle_data)} frames using config: {config.name}")
        all_rep_issues = []
        current_rep_score = 100.0

        if not rep_angle_data or not config:
            logger.warning("Insufficient data for rep evaluation: missing angle data or config.")
            return [], 0.0

        # Placeholder: This is a very simplified evaluation.
        # Actual implementation will:
        # 1. Iterate through each frame in rep_angle_data.
        # 2. For each frame, detect its movement_phase using a refined version of self.detect_movement_phase.
        # 3. Check joint_angle_rules for that frame and phase using a refined self.check_joint_angles.
        # 4. Collect all issues.
        # 5. Generate specific feedback items based on config.feedback_templates and these issues.
        # 6. Calculate a score for the rep based on the severity and number of issues.
        
        # Example of using existing helpers for a single frame (e.g., midpoint of rep)
        if rep_angle_data:
            example_frame_angles = rep_angle_data[len(rep_angle_data) // 2].get("angles", {})
            
            # Simplified phase detection for the example frame
            # In reality, phase detection needs to be robust for each frame in sequence
            current_phase = self.detect_movement_phase(
                config.movement_phases,
                example_frame_angles 
            ) 
            logger.info(f"Example frame in rep is in phase: {current_phase}")

            frame_issues = self.check_joint_angles(
                config.joint_angle_rules,
                example_frame_angles,
                current_phase
            )
            all_rep_issues.extend(frame_issues)
            
            # Rudimentary score adjustment for placeholder
            if frame_issues:
                current_rep_score -= len(frame_issues) * 10 
                current_rep_score = max(0, current_rep_score)


        # Convert raw issues to feedback items (simplified)
        # Actual feedback generation needs to map specific issues to templates
        generated_feedback_for_rep = self.generate_feedback(
            config.feedback_templates,
            all_rep_issues, 
            "general_rep_phase"
        )
        
        logger.warning(f"evaluate_rep is a placeholder. Found {len(all_rep_issues)} issues. Rep score: {current_rep_score}. Generated {len(generated_feedback_for_rep)} feedback items.")
        # For now, returning raw issues as feedback and a placeholder score
        return generated_feedback_for_rep, current_rep_score

    async def analyze_form_dynamically(
        self,
        video: Video
    ) -> FormCheck:
        """
        Analyze exercise form using dynamic configuration for a given video.
        Segments video into repetitions, evaluates each rep, aggregates feedback, and updates FormCheck.
        """
        logger.info(f"Starting dynamic form analysis for video ID: {video.id}")

        if not video.exercise_template_id:
            logger.error(f"Video {video.id} is missing exercise_template_id. Cannot perform dynamic analysis.")
            raise ValidationError("Video is missing exercise_template_id, required for dynamic analysis.")

        if not video.angle_data or not isinstance(video.angle_data, list) or not video.angle_data:
             logger.error(f"Video {video.id} has no angle data. Cannot perform analysis.")
             # Optionally create/update FormCheck with an error status here
             # For now, raising an exception or returning early.
             raise ValidationError("Video angle data is missing or empty, cannot perform analysis.")


        form_check = await self.form_check_service.get_or_create_form_check_for_video(video_id=video.id)
        logger.info(f"Using FormCheck ID: {form_check.id} for video ID: {video.id}")

        config = await self._get_exercise_config_model_async(video.exercise_template_id)
        
        if not config:
            logger.warning(f"No active ExerciseConfig found for exercise_template_id {video.exercise_template_id} (Video ID: {video.id}). Cannot perform analysis.")
            form_check.status = "analysis_failed"
            form_check.overall_feedback = "Analysis failed: No valid exercise configuration found."
            # Consider adding an error type FeedbackItem
            await self.db.commit()
            return form_check
            
        logger.info(f"Using ExerciseConfig: {config.name} (Version: {config.version}) for video ID: {video.id}")

        all_feedback_items_for_video = []
        total_score = 0
        num_reps = 0

        try:
            # Ensure angle_data is a list of dicts, as expected by segmentation and evaluation
            # The Video model stores angle_data as JSON, which SQLAlchemy might return as string if not handled.
            # Assuming video.angle_data is already correctly parsed into List[Dict[str, Any]]
            # where each dict is e.g. {"frame_num": i, "angles": {"joint1": val1, ...}}
            # or simply List[Dict[str, float]] representing angles per frame.
            # For now, we assume video.angle_data is List[Dict{"angles": Dict[str, float]}] as per model
            
            angle_data_list = video.angle_data 
            if isinstance(video.angle_data, str): # Double check if it's a JSON string
                try:
                    angle_data_list = json.loads(video.angle_data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse angle_data JSON for video {video.id}")
                    raise ValidationError("Angle data is not valid JSON.")

            if not isinstance(angle_data_list, list):
                 logger.error(f"Angle data for video {video.id} is not a list after potential parsing.")
                 raise ValidationError("Angle data is not in the expected list format.")


            repetitions = await self.segment_repetitions(angle_data_list, config)
            num_reps = len(repetitions)
            logger.info(f"Segmented into {num_reps} repetitions for video ID: {video.id}")

            if not repetitions:
                logger.warning(f"No repetitions segmented for video ID: {video.id}. Analysis may be limited.")
                form_check.overall_feedback = "No repetitions were detected in the video."
                # No score change if no reps

            for i, rep_frames in enumerate(repetitions):
                logger.info(f"Evaluating Rep {i+1}/{num_reps} for video ID: {video.id}")
                rep_feedback_issues, rep_score = await self.evaluate_rep(rep_frames, config)
                
                # The feedback items from evaluate_rep might need further processing 
                # to match FeedbackItem schema if they are just raw issues.
                # For now, assuming they are suitably formatted dicts for create_feedback_items_in_db
                all_feedback_items_for_video.extend(rep_feedback_issues)
                total_score += rep_score
            
            if num_reps > 0:
                form_check.overall_score = total_score / num_reps
            else:
                form_check.overall_score = 0 # Or keep previous score / set to a specific value
            
            logger.info(f"Overall score for video ID {video.id}: {form_check.overall_score} based on {num_reps} reps.")

            # Persist feedback items
            if all_feedback_items_for_video:
                # Augment feedback items with form_check_id before saving
                # Assuming generate_feedback returns list of dicts that create_feedback_items_in_db can handle
                # This part needs to ensure the dicts match what create_feedback_items_in_db expects.
                # The current generate_feedback in the snippet returns dicts with "message", "severity", "type".
                # create_feedback_items_in_db expects timestamp etc.
                
                # Placeholder for timestamp - in reality, this should come from the frame data within the rep
                placeholder_timestamp = 0.0 
                formatted_feedback_for_db = []
                for fb_item_dict in all_feedback_items_for_video:
                    # Ensure the dict structure is compatible with FeedbackItem creation
                    # Add missing fields if necessary (e.g., timestamp, joint_angles)
                    # For now, we assume fb_item_dict contains 'message', 'severity', 'type'
                    # and 'joint_angles' & 'suggestions' might be added by a more detailed evaluate_rep
                    db_fb_item = {
                        "type": FeedbackType(fb_item_dict.get("type", "form")),
                        "message": fb_item_dict.get("message", "No message"),
                        "timestamp": placeholder_timestamp,
                        "severity": FeedbackSeverity(fb_item_dict.get("severity", "low")),
                        "joint_angles": fb_item_dict.get("joint_angles_data"),
                        "suggestions": fb_item_dict.get("suggestions_data")
                    }
                    formatted_feedback_for_db.append(db_fb_item)

                if formatted_feedback_for_db:
                    await self.create_feedback_items_in_db(form_check.id, formatted_feedback_for_db)
                    logger.info(f"Stored {len(formatted_feedback_for_db)} feedback items for FormCheck ID: {form_check.id}")
                else:
                    logger.info(f"No detailed feedback items to store for FormCheck ID: {form_check.id}")


            # Simple overall feedback
            if not all_feedback_items_for_video and num_reps > 0:
                form_check.overall_feedback = "Good form! No major issues detected."
            elif num_reps > 0 :
                form_check.overall_feedback = f"Found {len(all_feedback_items_for_video)} areas for improvement across {num_reps} repetitions. Overall score: {form_check.overall_score:.2f}"
            elif not form_check.overall_feedback: # If no reps and no specific message yet
                 form_check.overall_feedback = "Analysis complete. Could not detect repetitions to score."


            form_check.status = "analysis_complete"
            await self.db.commit()
            await self.db.refresh(form_check)
            logger.info(f"Dynamic form analysis completed for video ID: {video.id}. FormCheck ID: {form_check.id}, Status: {form_check.status}, Score: {form_check.overall_score}")

        except ValidationError as ve:
            logger.error(f"Validation error during analysis for video {video.id}: {ve}")
            form_check.status = "analysis_failed"
            form_check.overall_feedback = f"Analysis failed: {str(ve)}"
            await self.db.commit() # Save error state
            raise # Re-raise to be caught by Celery task
        except Exception as e:
            logger.error(f"Unexpected error during dynamic form analysis for video ID: {video.id}: {str(e)}", exc_info=True)
            if form_check: # form_check might not be defined if error is very early
                form_check.status = "analysis_failed"
                form_check.overall_feedback = "An unexpected error occurred during analysis."
                await self.db.commit()
            raise ServerErrorException(f"Dynamic form analysis failed for video {video.id}: {e}") from e
        
        return form_check
    
    def detect_movement_phase(
        self,
        phases_config: Any,
        joint_angles: Dict[str, float]
    ) -> str:
        """
        Detect the current movement phase based on joint angles.
        Accepts either a Pydantic model for phases (from ExerciseConfig) or a dict.
        """
        phase_items = []
        if hasattr(phases_config, 'items'):
            phase_items = phases_config.items()
        elif isinstance(phases_config, dict):
            phase_items = phases_config.items()
        else:
            logger.warning("Phases config is not a dictionary or Pydantic model. Cannot detect phase.")
            return "unknown"

        for phase_name, phase_data_model in phase_items:
            triggers_dict = {}
            if hasattr(phase_data_model, 'triggers') and phase_data_model.triggers:
                 if isinstance(phase_data_model.triggers, dict):
                    triggers_dict = phase_data_model.triggers
                 elif hasattr(phase_data_model.triggers, 'model_dump'):
                    triggers_dict = phase_data_model.triggers.model_dump()

            next_triggers_list = triggers_dict.get("next", [])
            if not next_triggers_list:
                continue

            all_satisfied = True
            for trigger_model in next_triggers_list:
                joint = trigger_model.joint if hasattr(trigger_model, 'joint') else trigger_model.get("joint")
                value = trigger_model.value if hasattr(trigger_model, 'value') else trigger_model.get("value")
                comparator = trigger_model.comparator if hasattr(trigger_model, 'comparator') else trigger_model.get("comparator")
                
                if not joint or joint not in joint_angles or value is None or not comparator:
                    all_satisfied = False
                    break 
                    
                angle = joint_angles[joint]
                
                satisfied = False
                if comparator == "<" and (angle < value): satisfied = True
                elif comparator == ">" and (angle > value): satisfied = True
                elif comparator == "==" and (angle == value): satisfied = True
                elif comparator == "<=" and (angle <= value): satisfied = True
                elif comparator == ">=" and (angle >= value): satisfied = True
                
                if not satisfied:
                    all_satisfied = False
                    break
            
            if all_satisfied:
                return phase_name
        
        return "unknown"
    
    def check_joint_angles(
        self,
        rules_config: Any,
        joint_angles: Dict[str, float],
        phase: str
    ) -> List[Dict[str, Any]]:
        """
        Check joint angles against phase-specific rules.
        Accepts Pydantic model for rules_config (from ExerciseConfig) or dict.
        """
        issues = []
        
        phases_rules_model = None
        if hasattr(rules_config, 'phases'):
            phases_rules_model = rules_config.phases 
        elif isinstance(rules_config, dict) and "phases" in rules_config:
             phases_rules_model = rules_config["phases"]
        else:
            logger.warning("Joint angle rules 'phases' structure not found in config.")
            return issues

        current_phase_rules_model = None
        if phases_rules_model and hasattr(phases_rules_model, 'get'):
            current_phase_rules_model = phases_rules_model.get(phase)
            if not current_phase_rules_model and "default" in phases_rules_model:
                 current_phase_rules_model = phases_rules_model.get("default")
        elif phases_rules_model and isinstance(phases_rules_model, dict):
            current_phase_rules_model = phases_rules_model.get(phase)
            if not current_phase_rules_model and "default" in phases_rules_model:
                 current_phase_rules_model = phases_rules_model.get("default")

        if not current_phase_rules_model:
            return issues
        
        angle_rules_map = {}
        if hasattr(current_phase_rules_model, 'angles'):
            angle_rules_map = current_phase_rules_model.angles
        elif isinstance(current_phase_rules_model, dict) and "angles" in current_phase_rules_model:
            angle_rules_map = current_phase_rules_model["angles"]

        if not angle_rules_map:
            return issues

        for joint, rule_model in angle_rules_map.items():
            if joint not in joint_angles:
                continue
                
            angle = joint_angles[joint]
            
            min_angle = rule_model.min_angle if hasattr(rule_model, 'min_angle') else rule_model.get("min_angle")
            max_angle = rule_model.max_angle if hasattr(rule_model, 'max_angle') else rule_model.get("max_angle")
            ideal_angle = rule_model.ideal_angle if hasattr(rule_model, 'ideal_angle') else rule_model.get("ideal_angle")
            tolerance_val = getattr(rule_model, 'tolerance', None) if hasattr(rule_model, 'tolerance') else rule_model.get("tolerance")
            tolerance = tolerance_val if tolerance_val is not None else 15.0


            current_deviation = 0.0
            issue_type = None
            expected_val_dict: Dict[str, Any] = {}


            if min_angle is not None and angle < min_angle:
                current_deviation = min_angle - angle
                issue_type = "below_min"
                expected_val_dict = {"min": min_angle}
            elif max_angle is not None and angle > max_angle:
                current_deviation = angle - max_angle
                issue_type = "above_max"
                expected_val_dict = {"max": max_angle}
            elif ideal_angle is not None and tolerance is not None:
                lower_bound_ideal = ideal_angle - tolerance
                upper_bound_ideal = ideal_angle + tolerance
                if angle < lower_bound_ideal or angle > upper_bound_ideal:
                    current_deviation = (lower_bound_ideal - angle) if angle < lower_bound_ideal else (angle - upper_bound_ideal)
                    issue_type = "non_ideal"
                    expected_val_dict = {"ideal": ideal_angle, "tolerance": tolerance}
            
            if issue_type:
                severity_tolerance_val = getattr(rule_model, 'severity_tolerance', tolerance)
                issues.append({
                    "joint": joint,
                    "actual": angle,
                    "expected": expected_val_dict,
                    "issue_type": issue_type,
                    "deviation": current_deviation,
                    "severity": self.calculate_severity(current_deviation, severity_tolerance_val)
                })
        
        return issues
    
    def calculate_severity(self, deviation: float, tolerance_for_severity: float) -> str:
        """
        Calculate severity based on deviation from expected angle.
        Tolerance here refers to how much deviation is allowed before it's considered an issue for severity calculation.
        """
        if tolerance_for_severity <= 0:
            tolerance_for_severity = 15.0

        abs_deviation = abs(deviation)

        if abs_deviation == 0:
            return FeedbackSeverity.NONE.value
        elif abs_deviation <= tolerance_for_severity / 2:
            return FeedbackSeverity.LOW.value
        elif abs_deviation <= tolerance_for_severity:
            return FeedbackSeverity.MEDIUM.value
        else:
            return FeedbackSeverity.HIGH.value

    def generate_feedback(
        self,
        templates_config: Any,
        issues: List[Dict[str, Any]],
        phase: str
    ) -> List[Dict[str, Any]]:
        """
        Generate specific feedback based on issues and templates.
        Accepts Pydantic model for templates_config (from ExerciseConfig) or dict.
        """
        feedback_list = []
        
        template_items = []
        if hasattr(templates_config, 'items'):
             template_items = templates_config.items()
        elif isinstance(templates_config, dict):
            template_items = templates_config.items()
        else:
            logger.warning("Feedback templates config is not a dictionary or Pydantic model.")
            for issue in issues:
                 feedback_list.append({
                    "message": f"Issue detected with {issue.get('joint', 'unknown joint')}: {issue.get('issue_type', 'general issue')}. Actual: {issue.get('actual', 0):.1f}, Expected: {issue.get('expected', {})}.",
                    "severity": issue.get("severity", FeedbackSeverity.LOW.value),
                    "type": FeedbackType.FORM.value,
                    "details": f"Phase: {phase}, Deviation: {issue.get('deviation', 0):.1f}"
                })
            return feedback_list

        for issue in issues:
            matched_template_key = None
            if not matched_template_key and issue.get("issue_type"):
                for key, template_model in template_items:
                    if key == f"{issue.get('joint')}_{issue.get('issue_type')}":
                        matched_template_key = key
                        break
                if not matched_template_key:
                    for key, template_model in template_items:
                        if key == issue.get("issue_type"):
                            matched_template_key = key
                            break


            if matched_template_key:
                template_model = templates_config.get(matched_template_key)
                if template_model:
                    message = getattr(template_model, 'message', "Template message missing")
                    severity = getattr(template_model, 'severity', FeedbackSeverity.LOW.value)
                    feedback_type = getattr(template_model, 'type', FeedbackType.FORM.value)
                    details = getattr(template_model, 'details', None)
                    
                    feedback_list.append({
                        "message": message.format(joint=issue.get('joint'), actual=issue.get('actual'), expected=issue.get('expected')),
                        "severity": severity,
                        "type": feedback_type,
                        "details": details,
                        "raw_issue": issue
                    })
            else:
                feedback_list.append({
                    "message": f"Issue with {issue.get('joint', 'N/A')}: {issue.get('issue_type', 'general issue')}. Actual: {issue.get('actual', 0):.1f}, Expected: {issue.get('expected', {})}.",
                    "severity": issue.get("severity", FeedbackSeverity.LOW.value),
                    "type": FeedbackType.FORM.value,
                    "details": f"Phase: {phase}, Deviation: {issue.get('deviation', 0):.1f}"
                })
        return feedback_list
    
    async def create_feedback_items_in_db(
        self,
        form_check_id: UUID,
        feedback_data_list: List[Dict[str, Any]]
    ) -> List[FeedbackItem]:
        """
        Create FeedbackItem records in the database.
        
        Args:
            form_check_id (UUID): The ID of the FormCheck this feedback belongs to.
            feedback_data_list (List[Dict[str, Any]]): List of feedback data dictionaries.
            
        Returns:
            List[FeedbackItem]: List of created FeedbackItem objects.
        """
        created_items: List[FeedbackItem] = []
        if not feedback_data_list:
            return created_items

        for feedback_data in feedback_data_list:
            severity_value = feedback_data.get("severity")
            type_value = feedback_data.get("type")

            try:
                severity_enum = FeedbackSeverity(severity_value) if isinstance(severity_value, str) else FeedbackSeverity.INFO
            except ValueError:
                logger.warning(f"Invalid severity value: {severity_value}, defaulting to INFO.")
                severity_enum = FeedbackSeverity.INFO
            
            try:
                type_enum = FeedbackType(type_value) if isinstance(type_value, str) else FeedbackType.GENERAL
            except ValueError:
                logger.warning(f"Invalid feedback type value: {type_value}, defaulting to GENERAL.")
                type_enum = FeedbackType.GENERAL

            db_item = FeedbackItem(
                form_check_id=form_check_id,
                message=feedback_data.get("message", "N/A"),
                details=feedback_data.get("details", {}),
                type=type_enum,
                severity=severity_enum,
            )
            self.db.add(db_item)
            created_items.append(db_item)
        
        try:
            await self.db.flush()
            for item in created_items:
                await self.db.refresh(item)
        except Exception as e:
            logger.error(f"Error creating feedback items in DB: {str(e)}")
            await self.db.rollback()
            return []
            
        return created_items

from fastapi import Depends
try:
    from app.core.deps import get_async_exercise_config_service
    from app.core.deps import get_async_form_check_service
except ImportError:
    logger.warning("get_async_exercise_config_service or get_async_form_check_service not found in app.core.deps, using placeholder(s). Ensure they are registered in api/deps.py.")
    # Placeholder for get_async_exercise_config_service if it wasn't imported
    if 'get_async_exercise_config_service' not in locals():
        async def get_async_exercise_config_service_placeholder():
            raise NotImplementedError("get_async_exercise_config_service provider not found.")
        get_async_exercise_config_service = get_async_exercise_config_service_placeholder
    # Placeholder for get_async_form_check_service if it wasn't imported
    if 'get_async_form_check_service' not in locals():
        async def get_async_form_check_service_placeholder():
            raise NotImplementedError("get_async_form_check_service provider not found.")
        get_async_form_check_service = get_async_form_check_service_placeholder

async def get_async_dynamic_form_analysis_service(
    # db: AsyncSession = Depends(get_async_db), # Original problematic dependency
    # settings: Settings = Depends(get_settings), # Original problematic dependency
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    form_check_service: FormCheckService = Depends(get_async_form_check_service)
) -> DynamicFormAnalysisService:
    """Get dynamic form analysis service instance asynchronously."""
    from app.core.deps import get_async_db, get_settings # RE-ADDING LOCAL IMPORTS
    from sqlalchemy.ext.asyncio import AsyncSession 
    from fastapi import Depends 
    
    db: AsyncSession = Depends(get_async_db)
    settings: Settings = Depends(get_settings)
    
    return DynamicFormAnalysisService(
        db=db, 
        settings=settings, 
        exercise_config_service=exercise_config_service, 
        form_check_service=form_check_service
    )

# Placeholder for dependent service getters if they were previously in this file
# and need to be defined/imported for get_async_dynamic_form_analysis_service
# e.g.
# async def get_async_exercise_config_service(): ...
# async def get_async_form_check_service(): ... 
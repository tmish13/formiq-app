"""
Biomechanics service for form analysis and feedback.

This module provides detailed biomechanical analysis and feedback for common exercise forms,
including descriptions of issues, risk levels, corrections, and exercise-specific insights.
"""
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

class RiskLevel(str, Enum):
    """Risk levels for form issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ExerciseType(str, Enum):
    """Supported exercise types."""
    SQUAT = "squat"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"
    OVERHEAD_PRESS = "overhead_press"
    PULLUP = "pullup"
    PUSHUP = "pushup"
    BARBELL_ROW = "barbell_row"

class FormIssue:
    """Class representing a form issue with biomechanical details and corrections."""
    
    def __init__(
        self,
        name: str,
        description: str,
        risk_level: RiskLevel,
        corrections: List[str],
        affected_joints: List[str],
        muscle_imbalances: Optional[List[str]] = None,
        injury_risks: Optional[List[str]] = None,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None
    ):
        """Initialize form issue.
        
        Args:
            name: Name of the form issue
            description: Detailed description of the issue
            risk_level: Risk level for potential injury
            corrections: List of corrections to fix the issue
            affected_joints: Joints affected by this issue
            muscle_imbalances: Muscle imbalances that may cause this issue
            injury_risks: Potential injuries that could result
            image_url: Reference image URL showing the issue
            video_url: Reference video URL demonstrating the correction
        """
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.corrections = corrections
        self.affected_joints = affected_joints
        self.muscle_imbalances = muscle_imbalances or []
        self.injury_risks = injury_risks or []
        self.image_url = image_url
        self.video_url = video_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the form issue
        """
        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "corrections": self.corrections,
            "affected_joints": self.affected_joints,
            "muscle_imbalances": self.muscle_imbalances,
            "injury_risks": self.injury_risks,
            "image_url": self.image_url,
            "video_url": self.video_url
        }

class BiomechanicsService:
    """Service providing biomechanical form analysis and feedback."""
    
    def __init__(self):
        """Initialize the biomechanics service with form issues database."""
        self.form_issues = {
            # SQUAT ISSUES
            "knee_valgus": FormIssue(
                name="Knee Valgus (Knees Caving In)",
                description="The knees collapse inward during the squat, creating a knock-kneed position. This misaligns the knee joint and creates dangerous lateral forces.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Actively push knees outward during descent",
                    "Strengthen glute medius with lateral band walks",
                    "Improve ankle mobility with dorsiflexion stretches",
                    "Try using a resistance band around knees as a cue"
                ],
                affected_joints=["knee", "hip", "ankle"],
                muscle_imbalances=["weak gluteus medius", "overactive adductors", "weak external hip rotators"],
                injury_risks=["ACL tear", "meniscus damage", "patellofemoral pain syndrome"]
            ),
            "butt_wink": FormIssue(
                name="Butt Wink (Posterior Pelvic Tilt)",
                description="The pelvis tucks under (posterior tilt) at the bottom of the squat, causing lumbar flexion under load.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Limit squat depth to where form can be maintained",
                    "Work on hip mobility, especially hip flexors",
                    "Strengthen core stabilizers",
                    "Consider stance width adjustments"
                ],
                affected_joints=["lumbar spine", "pelvis", "hip"],
                muscle_imbalances=["tight hamstrings", "weak core stabilizers", "limited hip mobility"],
                injury_risks=["disc herniation", "lower back strain"]
            ),
            "forward_lean": FormIssue(
                name="Excessive Forward Lean",
                description="Torso leans too far forward during the squat, shifting weight to toes and increasing spinal stress.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Focus on maintaining upright torso position",
                    "Improve ankle dorsiflexion",
                    "Strengthen core and upper back",
                    "Consider heel elevation if ankle mobility is limited"
                ],
                affected_joints=["thoracic spine", "lumbar spine", "ankle"],
                muscle_imbalances=["weak core", "tight calves", "weak upper back"],
                injury_risks=["lower back strain", "spinal disc compression"]
            ),
            "heels_rising": FormIssue(
                name="Heels Rising",
                description="Heels lift off the ground during squat, indicating ankle mobility restrictions and shifting balance.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Work on ankle mobility with calf stretches",
                    "Temporarily use a small heel elevation (plate or wedge)",
                    "Adjust stance width or foot angle",
                    "Focus on weight distribution through midfoot"
                ],
                affected_joints=["ankle", "knee"],
                muscle_imbalances=["tight calves", "weak anterior tibialis"],
                injury_risks=["patellar tendinitis", "ankle instability", "knee strain"]
            ),
            "asymmetric_weight_shift": FormIssue(
                name="Asymmetric Weight Shift",
                description="Weight shifts more to one side during the squat, indicating potential strength or mobility imbalance.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Perform unilateral exercises to address the weaker side",
                    "Focus on equal weight distribution while squatting",
                    "Check for potential anatomical differences or previous injuries",
                    "Use video feedback or a mirror for visual cues"
                ],
                affected_joints=["hip", "knee", "ankle"],
                muscle_imbalances=["uneven strength development", "compensatory movement patterns"],
                injury_risks=["SI joint dysfunction", "hip impingement", "muscle strain"]
            ),
            
            # DEADLIFT ISSUES
            "rounded_lower_back": FormIssue(
                name="Rounded Lower Back",
                description="Lumbar spine flexes during the deadlift, placing dangerous stress on vertebral discs.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Focus on hip hinge pattern with neutral spine",
                    "Strengthen core and back extensors",
                    "Consider reducing weight until form improves",
                    "Practice bracing techniques to maintain spinal position"
                ],
                affected_joints=["lumbar spine", "sacroiliac"],
                muscle_imbalances=["weak erector spinae", "weak core stabilizers", "dominant hamstrings"],
                injury_risks=["disc herniation", "spinal fracture", "muscle strain"]
            ),
            "shoulders_rolling_forward": FormIssue(
                name="Shoulders Rolling Forward",
                description="Shoulders protract and roll forward during the deadlift, compromising upper back tension.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Cue 'put shoulders in back pockets' before lifting",
                    "Engage lats by bending the bar around shins",
                    "Strengthen upper back with rows and pull-ups",
                    "Practice proper setup with light weights"
                ],
                affected_joints=["shoulder", "thoracic spine"],
                muscle_imbalances=["weak rhomboids", "weak trapezius", "dominant chest muscles"],
                injury_risks=["shoulder impingement", "upper back strain"]
            ),
            "knees_too_far_forward": FormIssue(
                name="Knees Too Far Forward",
                description="Knees track too far forward in the initial pull, creating a squat pattern instead of a hip hinge.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Focus on hip hinge movement pattern",
                    "Set hips higher in starting position",
                    "Keep shins more vertical at setup",
                    "Practice with Romanian deadlifts to learn proper hinge"
                ],
                affected_joints=["knee", "hip", "low back"],
                muscle_imbalances=["dominant quadriceps", "weak hamstrings/glutes"],
                injury_risks=["knee strain", "lower back stress"]
            ),
            "bar_path_swinging": FormIssue(
                name="Bar Path Swinging Away",
                description="Bar swings away from the body during the lift, creating inefficient leverage and back stress.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Keep bar in contact with legs throughout the movement",
                    "Engage lats to keep bar close",
                    "Focus on dragging the bar up the legs",
                    "Consider using a bar with center knurling for feedback"
                ],
                affected_joints=["lumbar spine", "shoulder"],
                muscle_imbalances=["weak lats", "poor coordination"],
                injury_risks=["lower back strain", "bicep tear"]
            ),
            "hyperextending_at_top": FormIssue(
                name="Hyperextending at Top",
                description="Excessive backward lean at lockout, creating unsafe spinal compression.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Focus on neutral spine at lockout",
                    "Squeeze glutes without leaning back",
                    "Think 'tall and stacked' at the top position",
                    "Video feedback to recognize proper lockout position"
                ],
                affected_joints=["lumbar spine", "thoracic spine"],
                muscle_imbalances=["overactive spinal erectors", "weak core stabilizers"],
                injury_risks=["spinal facet joint impingement", "compression fracture"]
            ),
            
            # BENCH PRESS ISSUES
            "arching_excessively": FormIssue(
                name="Arching Excessively",
                description="Extreme lumbar arch that reduces range of motion and can strain lower back.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Maintain a moderate, natural arch",
                    "Focus on scapular retraction and depression instead of extreme arching",
                    "Strengthen core stability for safe positioning",
                    "Consider lower weight with full range of motion"
                ],
                affected_joints=["lumbar spine", "thoracic spine"],
                muscle_imbalances=["tight hip flexors", "weak core stabilizers"],
                injury_risks=["lower back strain", "reduced pectoral development"]
            ),
            "elbows_flaring": FormIssue(
                name="Elbows Flaring Out",
                description="Elbows move excessively outward (90° to torso), placing stress on shoulder joint.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Keep elbows at approximately 45-70° angle to torso",
                    "Focus on tucking elbows during descent",
                    "Consider narrower grip if comfortable",
                    "Strengthen rotator cuff muscles"
                ],
                affected_joints=["shoulder", "elbow"],
                muscle_imbalances=["weak rotator cuff", "overactive anterior deltoid"],
                injury_risks=["rotator cuff impingement", "shoulder strain"]
            ),
            "wrists_bending_back": FormIssue(
                name="Wrists Bending Back",
                description="Wrists hyperextend under the bar, creating unstable platform and wrist strain.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Position bar directly over forearms, not in palm",
                    "Keep wrists straight and locked",
                    "Consider wrist wraps for heavy loads",
                    "Grip the bar tightly to maintain position"
                ],
                affected_joints=["wrist", "forearm"],
                muscle_imbalances=["weak grip and forearm strength"],
                injury_risks=["wrist sprain", "carpal tunnel aggravation"]
            ),
            "bouncing_off_chest": FormIssue(
                name="Bouncing Off Chest",
                description="Using chest momentum to propel bar upward, reducing control and increasing injury risk.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Pause briefly at bottom position",
                    "Focus on controlled eccentric (lowering) phase",
                    "Reduce weight if control is compromised",
                    "Practice tempo bench press (slow lowering)"
                ],
                affected_joints=["shoulder", "sternum", "ribs"],
                muscle_imbalances=["rely on momentum vs. muscle strength"],
                injury_risks=["pectoral strain", "costochondral separation"]
            ),
            "butt_rising_off_bench": FormIssue(
                name="Butt Rising Off Bench",
                description="Hips leave the bench during press, creating unstable base and inefficient power transfer.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Focus on maintaining three points of contact (head, upper back, glutes)",
                    "Engage core and glutes to stabilize position",
                    "Use leg drive properly (horizontally, not vertically)",
                    "Reduce weight until proper form can be maintained"
                ],
                affected_joints=["lumbar spine", "hip"],
                muscle_imbalances=["weak core stabilizers", "improper technique"],
                injury_risks=["lower back strain", "reduced chest engagement"]
            ),
            
            # OVERHEAD PRESS ISSUES
            "excessive_lumbar_arch": FormIssue(
                name="Excessive Lumbar Arch",
                description="Over-arching lower back to push weights overhead, creating unsafe spinal compression.",
                risk_level=RiskLevel.HIGH,
                corrections=[
                    "Engage core to maintain neutral spine position",
                    "Tuck pelvis slightly to reduce arch",
                    "Consider bracing core with belt for heavy lifts",
                    "Scale weight back to maintain proper form"
                ],
                affected_joints=["lumbar spine", "thoracic spine"],
                muscle_imbalances=["weak core", "tight hip flexors", "weak glutes"],
                injury_risks=["spondylolisthesis", "disc compression", "facet joint strain"]
            ),
            "flaring_elbows": FormIssue(
                name="Flaring Elbows",
                description="Elbows move too far out to sides, creating suboptimal pressing angle and shoulder stress.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Keep elbows closer to frontal plane (45° angle)",
                    "Envision forearms as pillars pushing straight up",
                    "Engage lats for stabilization",
                    "Consider slightly narrower grip width"
                ],
                affected_joints=["shoulder", "elbow"],
                muscle_imbalances=["weak rotator cuff", "poor scapular control"],
                injury_risks=["shoulder impingement", "biceps tendinitis"]
            ),
            "shrugging_shoulders": FormIssue(
                name="Shrugging Shoulders",
                description="Elevating shoulders toward ears during the press, engaging traps instead of deltoids.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Actively depress and retract shoulder blades",
                    "Think 'shoulders down and back' throughout lift",
                    "Strengthen lower trapezius and rhomboids",
                    "Practice proper shoulder positioning with light weights"
                ],
                affected_joints=["shoulder", "cervical spine"],
                muscle_imbalances=["overactive upper trapezius", "weak lower trapezius"],
                injury_risks=["neck strain", "shoulder impingement"]
            ),
            "forward_head_position": FormIssue(
                name="Forward Head Position",
                description="Head juts forward during press, disrupting cervical spine alignment.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Maintain neutral head position aligned with spine",
                    "Move head slightly back as bar passes face, then return to neutral",
                    "Engage deep neck flexors",
                    "Focus on vertical bar path"
                ],
                affected_joints=["cervical spine", "upper thoracic spine"],
                muscle_imbalances=["weak deep neck flexors", "tight upper trapezius"],
                injury_risks=["cervical strain", "thoracic outlet syndrome"]
            ),
            
            # PULLUP ISSUES
            "kipping": FormIssue(
                name="Kipping/Using Momentum",
                description="Using lower body swing to generate momentum, reducing upper body engagement.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Focus on strict pull-ups with controlled movement",
                    "Strengthen core to minimize swinging",
                    "If needed, use assistance bands rather than momentum",
                    "Practice negative pull-ups to build strength"
                ],
                affected_joints=["shoulder", "lumbar spine"],
                muscle_imbalances=["insufficient upper body strength", "overreliance on momentum"],
                injury_risks=["shoulder strain", "lower back stress"]
            ),
            "incomplete_range": FormIssue(
                name="Incomplete Range of Motion",
                description="Not fully extending arms at bottom or chin not clearing bar at top, limiting development.",
                risk_level=RiskLevel.LOW,
                corrections=[
                    "Focus on full extension at bottom of movement",
                    "Pull until chin clears the bar at top",
                    "Reduce repetitions but maintain full range",
                    "Use video feedback to confirm proper range"
                ],
                affected_joints=["shoulder", "elbow"],
                muscle_imbalances=["partial muscle development", "strength imbalances"],
                injury_risks=["muscle imbalance", "reduced functional strength"]
            ),
            "half_rep_pullups": FormIssue(
                name="Half Rep Pull-ups",
                description="Performing partial repetitions with limited range of motion, diminishing effectiveness.",
                risk_level=RiskLevel.LOW,
                corrections=[
                    "Start with assisted full-range pull-ups if needed",
                    "Focus on quality over quantity",
                    "Use negative (eccentric) training to build strength",
                    "Record form to ensure full range of motion"
                ],
                affected_joints=["shoulder", "elbow"],
                muscle_imbalances=["partial muscle development", "strength gaps in range"],
                injury_risks=["muscle imbalance", "uneven development"]
            ),
            "shoulder_shrugging": FormIssue(
                name="Shoulder Shrugging",
                description="Elevating shoulders toward ears during pull, engaging traps over lats.",
                risk_level=RiskLevel.MEDIUM,
                corrections=[
                    "Keep shoulders down and away from ears",
                    "Focus on engaging lats ('put shoulders in back pockets')",
                    "Practice scapular depression exercises",
                    "Visualize pulling with back rather than arms"
                ],
                affected_joints=["shoulder", "scapulothoracic"],
                muscle_imbalances=["overactive upper trapezius", "underactive lats"],
                injury_risks=["shoulder impingement", "neck strain"]
            )
        }
        
        # Define exercise-specific common issues for quick reference
        self.exercise_common_issues = {
            ExerciseType.SQUAT: [
                "knee_valgus",
                "butt_wink",
                "forward_lean",
                "heels_rising",
                "asymmetric_weight_shift"
            ],
            ExerciseType.DEADLIFT: [
                "rounded_lower_back",
                "shoulders_rolling_forward",
                "knees_too_far_forward",
                "bar_path_swinging",
                "hyperextending_at_top"
            ],
            ExerciseType.BENCH_PRESS: [
                "arching_excessively",
                "elbows_flaring",
                "wrists_bending_back",
                "bouncing_off_chest",
                "butt_rising_off_bench"
            ],
            ExerciseType.OVERHEAD_PRESS: [
                "excessive_lumbar_arch",
                "flaring_elbows",
                "shrugging_shoulders",
                "forward_head_position"
            ],
            ExerciseType.PULLUP: [
                "kipping",
                "incomplete_range",
                "half_rep_pullups",
                "shoulder_shrugging"
            ],
            ExerciseType.PUSHUP: [
                "sagging_hips",
                "elbows_flaring",
                "incomplete_range",
                "neck_protruding"
            ],
            ExerciseType.BARBELL_ROW: [
                "rounded_lower_back",
                "excessive_body_movement",
                "incomplete_range",
                "asymmetric_pulling"
            ]
        }
        
        # Define joint angle normal ranges for reference
        self.joint_angle_references = {
            "squat": {
                "knee_flexion": {"min": 110, "max": 125, "description": "Degree of knee bend at bottom position"},
                "hip_flexion": {"min": 100, "max": 120, "description": "Degree of hip bend at bottom position"},
                "ankle_dorsiflexion": {"min": 15, "max": 25, "description": "Ankle bend at bottom position"},
                "lumbar_flexion": {"min": -5, "max": 5, "description": "Should remain neutral, minimal flexion"}
            },
            "deadlift": {
                "hip_flexion": {"min": 90, "max": 110, "description": "Hip angle at start position"},
                "knee_flexion": {"min": 70, "max": 90, "description": "Knee bend at start position"},
                "lumbar_flexion": {"min": -5, "max": 5, "description": "Should remain neutral throughout lift"}
            },
            "bench_press": {
                "shoulder_abduction": {"min": 45, "max": 70, "description": "Angle of upper arm to torso"},
                "elbow_flexion": {"min": 85, "max": 95, "description": "Elbow angle at bottom position"}
            }
        }
    
    def get_issue(self, issue_id: str) -> Optional[FormIssue]:
        """Get form issue by ID.
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Form issue or None if not found
        """
        return self.form_issues.get(issue_id)
    
    def get_common_issues_for_exercise(self, exercise_type: str) -> List[FormIssue]:
        """Get common form issues for a specific exercise.
        
        Args:
            exercise_type: Type of exercise
            
        Returns:
            List of common form issues for the exercise
        """
        if exercise_type not in self.exercise_common_issues:
            return []
        
        return [
            self.form_issues[issue_id]
            for issue_id in self.exercise_common_issues[exercise_type]
            if issue_id in self.form_issues
        ]
    
    def get_joint_angles_reference(self, exercise_type: str) -> Dict[str, Dict[str, Any]]:
        """Get reference joint angles for a specific exercise.
        
        Args:
            exercise_type: Type of exercise
            
        Returns:
            Dictionary of joint angle references
        """
        return self.joint_angle_references.get(exercise_type, {})
    
    def analyze_joint_angles(
        self, 
        exercise_type: str, 
        joint_angles: Dict[str, float]
    ) -> List[Tuple[str, str, float]]:
        """Analyze joint angles against reference values.
        
        Args:
            exercise_type: Type of exercise
            joint_angles: Dictionary of joint angles to analyze
            
        Returns:
            List of tuples (joint_name, status, deviation_percent)
            where status is 'normal', 'high', or 'low'
        """
        results = []
        references = self.joint_angle_references.get(exercise_type, {})
        
        for joint, angle in joint_angles.items():
            if joint in references:
                min_val = references[joint]["min"]
                max_val = references[joint]["max"]
                
                if angle < min_val:
                    # Calculate percentage below normal range
                    deviation = (min_val - angle) / min_val * 100
                    results.append((joint, "low", deviation))
                elif angle > max_val:
                    # Calculate percentage above normal range
                    deviation = (angle - max_val) / max_val * 100
                    results.append((joint, "high", deviation))
                else:
                    # Within normal range, deviation is 0
                    results.append((joint, "normal", 0))
        
        return results
    
    def get_injury_risk_factors(
        self, 
        exercise_type: str, 
        joint_angles: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Analyze form for potential injury risk factors.
        
        Args:
            exercise_type: Type of exercise
            joint_angles: Dictionary of joint angles
            
        Returns:
            List of potential injury risk factors with descriptions
        """
        risk_factors = []
        
        # Get common issues for this exercise
        common_issues = self.get_common_issues_for_exercise(exercise_type)
        
        # Analyze joint angles against references
        angle_analysis = self.analyze_joint_angles(exercise_type, joint_angles)
        
        # Add risk factors based on joint angle deviations
        for joint, status, deviation in angle_analysis:
            # Only include significant deviations
            if status != "normal" and deviation > 10:
                if exercise_type == "squat":
                    if joint == "knee_flexion" and status == "low":
                        risk_factors.append({
                            "name": "Insufficient Depth",
                            "description": "Not reaching adequate squat depth limits muscle development and mobility benefits",
                            "severity": "low",
                            "recommendation": "Work on ankle and hip mobility to achieve greater depth"
                        })
                    elif joint == "lumbar_flexion" and status == "high":
                        risk_factors.append({
                            "name": "Lumbar Flexion (Butt Wink)",
                            "description": "Lower back is rounding at the bottom of the squat, increasing disc pressure",
                            "severity": "high",
                            "recommendation": "Limit depth to where neutral spine can be maintained, work on hip mobility"
                        })
                
                elif exercise_type == "deadlift":
                    if joint == "lumbar_flexion" and status == "high":
                        risk_factors.append({
                            "name": "Rounded Lower Back",
                            "description": "Spine is flexing under load, placing significant stress on spinal discs",
                            "severity": "high",
                            "recommendation": "Focus on maintaining rigid neutral spine, strengthen core and back"
                        })
        
        return risk_factors
    
    def get_all_issues_by_severity(self, severity: RiskLevel) -> List[FormIssue]:
        """Get all form issues of a specific severity level.
        
        Args:
            severity: Risk level to filter by
            
        Returns:
            List of form issues matching the severity
        """
        return [
            issue for issue in self.form_issues.values()
            if issue.risk_level == severity
        ] 
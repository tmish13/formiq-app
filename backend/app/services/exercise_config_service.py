import logging
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete, desc, func
from sqlalchemy.orm import selectinload


from app.models.exercise_config import ExerciseConfig
from app.models.exercise import ExerciseTemplate
from app.schemas.exercise_config import (
    ExerciseConfigCreate,
    ExerciseConfigUpdate,
    ExerciseConfigInDB, # To be used as ResponseSchema
    JointAngleRules,
    MovementPhase,
    FeedbackTemplate,
    ClassificationMetadata
)
from app.services.base_service import BaseService
from app.core.config import Settings
from app.core.exceptions import NotFoundException, ConflictException, ServerErrorException
# from app.repositories.exercise_config_repository import ExerciseConfigRepository # No longer needed

logger = logging.getLogger(__name__)

# Hardcoded default configurations (remains for utility)
EXERCISE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "squat": {
        "name": "Default Squat Configuration",
        "joint_angle_rules": {
            "phases": {
                "start": {
                    "angles": {
                        "leftKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "rightKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "leftHip": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "rightHip": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                    }
                },
                "descent": {
                    "angles": {
                        "leftKnee": {"min_angle": 70, "max_angle": 120, "ideal_angle": 90, "tolerance": 15},
                        "rightKnee": {"min_angle": 70, "max_angle": 120, "ideal_angle": 90, "tolerance": 15},
                        "leftHip": {"min_angle": 70, "max_angle": 120, "ideal_angle": 90, "tolerance": 15},
                        "rightHip": {"min_angle": 70, "max_angle": 120, "ideal_angle": 90, "tolerance": 15},
                    }
                },
                "ascent": {
                    "angles": {
                        "leftKnee": {"min_angle": 120, "max_angle": 180, "ideal_angle": 175, "tolerance": 15},
                        "rightKnee": {"min_angle": 120, "max_angle": 180, "ideal_angle": 175, "tolerance": 15},
                        "leftHip": {"min_angle": 120, "max_angle": 180, "ideal_angle": 175, "tolerance": 15},
                        "rightHip": {"min_angle": 120, "max_angle": 180, "ideal_angle": 175, "tolerance": 15},
                    }
                },
            },
            "joints": ["leftKnee", "rightKnee", "leftHip", "rightHip", "leftAnkle", "rightAnkle", "leftShoulder", "rightShoulder"]
        },
        "movement_phases": {
            "start_phase": {
                "description": "Standing upright, ready to begin squat.",
                "triggers": {
                    "next": [{"joint": "leftHip", "condition": "angle", "value": 150, "comparator": "<"}]
                }
            },
            "descent_phase": {
                "description": "Lowering body into squat position.",
                "triggers": {
                    "next": [{"joint": "leftKnee", "condition": "angle", "value": 95, "comparator": "<"}],
                    "previous": [{"joint": "leftHip", "condition": "angle", "value": 160, "comparator": ">"}]
                }
            },
            "ascent_phase": {
                "description": "Returning to standing position.",
                "triggers": {
                    "next": [{"joint": "leftKnee", "condition": "angle", "value": 170, "comparator": ">"}], # End of rep
                    "previous": [{"joint": "leftKnee", "condition": "angle", "value": 100, "comparator": ">"}]
                }
            }
        },
        "feedback_templates": {
            "knee_valgus_descent": {
                "message": "Keep your knees aligned with your toes during descent.",
                "severity": "medium",
                "type": "alignment"
            },
            "shallow_squat": {
                "message": "Try to squat deeper to reach parallel.",
                "severity": "low",
                "type": "range"
            },
            "fast_descent": {
                "message": "Control your descent, avoid dropping too quickly.",
                "severity": "medium",
                "type": "tempo"
            }
        },
        "classification_metadata": {
            "keypoints": ["leftKnee", "rightKnee", "leftHip", "rightHip"],
            "frame_count": 60, # Approximate for a 2s rep at 30fps
            "features": {"joint_angle_ranges": {"leftKnee": [70, 180]}}
        }
    },
    "bicep_curl": {
        "name": "Default Bicep Curl Configuration",
        "joint_angle_rules": {
             "phases": {
                "start": { # Elbow extended
                    "angles": {
                        "leftElbow": {"min_angle": 150, "max_angle": 180, "ideal_angle": 170, "tolerance": 10},
                        "rightElbow": {"min_angle": 150, "max_angle": 180, "ideal_angle": 170, "tolerance": 10},
                    }
                },
                "flexion": { # Lifting phase
                     "angles": {
                        "leftElbow": {"min_angle": 20, "max_angle": 90, "ideal_angle": 45, "tolerance": 15},
                        "rightElbow": {"min_angle": 20, "max_angle": 90, "ideal_angle": 45, "tolerance": 15},
                    }
                },
                "extension": { # Lowering phase
                     "angles": {
                        "leftElbow": {"min_angle": 90, "max_angle": 180, "ideal_angle": 170, "tolerance": 15},
                        "rightElbow": {"min_angle": 90, "max_angle": 180, "ideal_angle": 170, "tolerance": 15},
                    }
                },
            },
            "joints": ["leftElbow", "rightElbow", "leftShoulder", "rightShoulder"]
        },
        "movement_phases": {
            "start_phase": {
                "description": "Arm extended, weight held at thigh level.",
                "triggers": {
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 140, "comparator": "<"}]
                }
            },
            "flexion_phase": {
                "description": "Bending elbow, lifting weight towards shoulder.",
                "triggers": {
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 50, "comparator": "<"}],
                    "previous": [{"joint": "leftElbow", "condition": "angle", "value": 150, "comparator": ">"}]
                }
            },
            "extension_phase": {
                "description": "Lowering weight back to starting position.",
                "triggers": {
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 160, "comparator": ">"}], # End of rep
                    "previous": [{"joint": "leftElbow", "condition": "angle", "value": 60, "comparator": ">"}]
                }
            }
        },
        "feedback_templates": {
            "elbow_flare": {
                "message": "Keep your elbows tucked in.",
                "severity": "medium",
                "type": "alignment"
            },
            "incomplete_rom_top": {
                "message": "Try to bring the weight all the way up.",
                "severity": "low",
                "type": "range"
            },
            "swinging_body": {
                "message": "Avoid using momentum by swinging your body.",
                "severity": "high",
                "type": "form"
            }
        },
        "classification_metadata": {
            "keypoints": ["leftElbow", "rightElbow", "leftShoulder", "rightShoulder"],
            "frame_count": 45,
            "features": {"joint_angle_ranges": {"leftElbow": [20, 180]}}
        }
    },
    "lunge": {
        "name": "Default Lunge Configuration",
        "joint_angle_rules": {
            "phases": {
                "start_stance": { # Both feet together, upright
                    "angles": {
                        "leadKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "trailKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "leadHip": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "torsoTilt": {"min_angle": -10, "max_angle": 10, "ideal_angle": 0, "tolerance": 5}
                    }
                },
                "descent": { # Lowering into lunge
                    "angles": {
                        "leadKnee": {"min_angle": 80, "max_angle": 100, "ideal_angle": 90, "tolerance": 10},
                        "trailKnee": {"min_angle": 80, "max_angle": 120, "ideal_angle": 90, "tolerance": 10}, # Trail knee approaches floor
                        "torsoTilt": {"min_angle": -10, "max_angle": 15, "ideal_angle": 0, "tolerance": 5}
                    }
                },
                "ascent": { # Pushing back up
                    "angles": {
                        "leadKnee": {"min_angle": 100, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "torsoTilt": {"min_angle": -10, "max_angle": 10, "ideal_angle": 0, "tolerance": 5}
                    }
                }
            },
            "joints": ["leadKnee", "trailKnee", "leadHip", "trailHip", "torsoTilt", "leadAnkle", "trailAnkle"]
        },
        "movement_phases": {
            "start_phase": { # Standing, feet together or split stance initial
                "name": "Start Stance",
                "description": "Starting position for lunge.",
                "triggers": { # Trigger to begin descent/step
                    "next": [{"joint": "leadHip", "condition": "angle", "value": 150, "comparator": "<"}] 
                }
            },
            "descent_phase": {
                "name": "Descent",
                "description": "Lowering into the lunge.",
                "triggers": {
                    "next": [{"joint": "leadKnee", "condition": "angle", "value": 95, "comparator": "<"}] # Reaching bottom of lunge
                }
            },
            "bottom_phase": {
                "name": "Bottom Hold",
                "description": "Lowest point of the lunge.",
                "triggers": {
                    "next": [{"joint": "leadKnee", "condition": "angle", "value": 100, "comparator": ">"}] # Starting ascent
                }
            },
            "ascent_phase": {
                "name": "Ascent",
                "description": "Returning to starting position.",
                "triggers": {
                    "start_phase": [{"joint": "leadHip", "condition": "angle", "value": 160, "comparator": ">"}] # Rep end
                }
            }
        },
        "feedback_templates": {
            "knee_forward_lunge": {"message": "Ensure your front knee doesn't go past your toes.", "severity": "medium", "type": "alignment"},
            "torso_lean_lunge": {"message": "Keep your torso upright.", "severity": "medium", "type": "posture"}
        },
        "classification_metadata": {"keypoints": ["leadKnee", "leadHip", "torsoTilt"], "frame_count": 50}
    },
    "deadlift": {
        "name": "Default Deadlift Configuration",
        "joint_angle_rules": {
            "phases": {
                "setup": {
                    "angles": {
                        "backTilt": {"min_angle": -5, "max_angle": 20, "ideal_angle": 5, "tolerance": 5}, # Slight forward tilt, no rounding
                        "hips": {"min_angle": 60, "max_angle": 100, "ideal_angle": 80, "tolerance": 10}, # Hips lower than shoulders ideally
                        "knees": {"min_angle": 70, "max_angle": 120, "ideal_angle": 90, "tolerance": 15}
                    }
                },
                "lift_phase": { # Ascent
                    "angles": {
                        "backTilt": {"min_angle": -5, "max_angle": 10, "ideal_angle": 0, "tolerance": 5},
                        "hips": {"min_angle": 150, "max_angle": 180, "ideal_angle": 175, "tolerance": 5}, # Full extension
                        "knees": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 5}
                    }
                },
                "lower_phase": { # Descent
                     "angles": {
                        "backTilt": {"min_angle": -5, "max_angle": 20, "ideal_angle": 5, "tolerance": 5}
                    }
                }
            },
            "joints": ["backTilt", "hips", "knees", "leftShoulder", "rightShoulder"]
        },
        "movement_phases": {
            "start_phase": { # Bar on floor, setup position
                "name": "Setup",
                "description": "Addressing the bar, proper setup.",
                "triggers": { 
                    "next": [{"joint": "hips", "condition": "angle", "value": 100, "comparator": ">"}] # Start of lift (hips extending)
                }
            },
            "ascent_phase": {
                "name": "Ascent",
                "description": "Lifting the bar to full lockout.",
                "triggers": {
                    "next": [{"joint": "hips", "condition": "angle", "value": 170, "comparator": ">"}] # Reaching lockout
                }
            },
            "top_hold_phase": {
                "name": "Lockout",
                "description": "Standing fully upright with the bar.",
                "triggers": {
                    "next": [{"joint": "hips", "condition": "angle", "value": 165, "comparator": "<"}] # Starting descent
                }
            },
            "descent_phase": {
                "name": "Descent",
                "description": "Lowering the bar back to the floor.",
                "triggers": {
                    "start_phase": [{"joint": "hips", "condition": "angle", "value": 90, "comparator": "<"}] # Bar on floor, rep end
                }
            }
        },
        "feedback_templates": {
            "rounded_back_deadlift": {"message": "Maintain a flat back throughout the lift.", "severity": "high", "type": "posture"},
            "hips_shoot_up_deadlift": {"message": "Ensure your hips and shoulders rise together.", "severity": "medium", "type": "coordination"}
        },
        "classification_metadata": {"keypoints": ["backTilt", "hips", "knees"], "frame_count": 60}
    },
    "pushup": {
        "name": "Default Pushup Configuration",
        "joint_angle_rules": {
            "phases": {
                "top_position": {
                    "angles": {
                        "leftElbow": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "rightElbow": {"min_angle": 160, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "torsoToGroundAngle": {"min_angle": -5, "max_angle": 5, "ideal_angle": 0, "tolerance": 5} # Body straight
                    }
                },
                "descent": {
                    "angles": {
                        "leftElbow": {"min_angle": 70, "max_angle": 100, "ideal_angle": 90, "tolerance": 10},
                        "rightElbow": {"min_angle": 70, "max_angle": 100, "ideal_angle": 90, "tolerance": 10},
                        "torsoToGroundAngle": {"min_angle": -5, "max_angle": 5, "ideal_angle": 0, "tolerance": 5}
                    }
                },
                "ascent": {
                    "angles": {
                        "leftElbow": {"min_angle": 100, "max_angle": 180, "ideal_angle": 175, "tolerance": 10},
                        "rightElbow": {"min_angle": 100, "max_angle": 180, "ideal_angle": 175, "tolerance": 10}
                    }
                }
            },
            "joints": ["leftElbow", "rightElbow", "leftShoulder", "rightShoulder", "torsoToGroundAngle"]
        },
        "movement_phases": {
            "start_phase": { # Top of pushup, arms extended
                "name": "Top Position",
                "description": "Starting at the top of the pushup.",
                "triggers": { 
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 150, "comparator": "<"}] # Bending elbows for descent
                }
            },
            "descent_phase": {
                "name": "Descent",
                "description": "Lowering body towards the floor.",
                "triggers": {
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 95, "comparator": "<"}] # Reaching bottom
                }
            },
            "bottom_phase": {
                "name": "Bottom Position",
                "description": "Chest close to the floor.",
                "triggers": {
                    "next": [{"joint": "leftElbow", "condition": "angle", "value": 100, "comparator": ">"}] # Starting ascent
                }
            },
            "ascent_phase": {
                "name": "Ascent",
                "description": "Pushing back up to the top position.",
                "triggers": {
                    "start_phase": [{"joint": "leftElbow", "condition": "angle", "value": 160, "comparator": ">"}] # Rep end
                }
            }
        },
        "feedback_templates": {
            "hips_sag_pushup": {"message": "Keep your core engaged and body straight, avoid hip sag.", "severity": "medium", "type": "posture"},
            "elbow_flare_pushup": {"message": "Tuck your elbows slightly, don't let them flare out too wide.", "severity": "low", "type": "alignment"}
        },
        "classification_metadata": {"keypoints": ["leftElbow", "leftShoulder", "torsoToGroundAngle"], "frame_count": 40}
    }
}


class ExerciseConfigService(BaseService[ExerciseConfig, ExerciseConfigCreate, ExerciseConfigUpdate]):
    """
    Service for managing Exercise Configurations.
    Handles CRUD operations, versioning, and default configurations.
    """

    def __init__(self, db: AsyncSession, settings: Settings):
        super().__init__(db, ExerciseConfig, settings)
        self.response_schema = ExerciseConfigInDB


    async def convert_hardcoded_to_db_schema(
        self, 
        exercise_name_key: str, 
        exercise_id: UUID
    ) -> Optional[ExerciseConfigCreate]:
        """
        Converts a hardcoded exercise default configuration to an ExerciseConfigCreate schema.
        Returns None if the exercise_name_key is not found in EXERCISE_DEFAULTS.
        """
        default_config = EXERCISE_DEFAULTS.get(exercise_name_key)
        if not default_config:
            logger.warning(f"No default config found for key: {exercise_name_key}")
            return None

        # Validate and structure the nested Pydantic models
        try:
            jar_data = default_config.get("joint_angle_rules", {})
            mp_data = default_config.get("movement_phases", {})
            ft_data = default_config.get("feedback_templates", {})
            cm_data = default_config.get("classification_metadata")

            jar = JointAngleRules(**jar_data)
            
            movement_phases_structured = {}
            for phase_key, phase_value in mp_data.items():
                movement_phases_structured[phase_key] = MovementPhase(**phase_value)
            
            feedback_templates_structured = {}
            for ft_key, ft_value in ft_data.items():
                feedback_templates_structured[ft_key] = FeedbackTemplate(**ft_value)

            classification_metadata_structured = ClassificationMetadata(**cm_data) if cm_data else None
            
            return ExerciseConfigCreate(
                name=default_config["name"],
            exercise_id=exercise_id,
                version=1, # Default to version 1
                is_active=True,
                joint_angle_rules=jar,
                movement_phases=movement_phases_structured,
                feedback_templates=feedback_templates_structured,
                classification_metadata=classification_metadata_structured,
            )
        except Exception as e:
            logger.error(f"Error converting hardcoded config for {exercise_name_key} to schema: {e}", exc_info=True)
            return None

    async def create_default_configs_async(self) -> List[ExerciseConfig]:
        """
        Creates default ExerciseConfig records from EXERCISE_DEFAULTS
        if they don't already exist for the respective exercises.
        This is an instance method now, using self.db.
        """
        created_configs = []
        
        # Fetch all exercise templates to map names to UUIDs
        stmt_templates = select(ExerciseTemplate)
        result_templates = await self.db.execute(stmt_templates)
        exercise_templates = result_templates.scalars().all()
        
        exercise_map: Dict[str, ExerciseTemplate] = {template.name.lower().replace(" ", "_"): template for template in exercise_templates}

        for key, _ in EXERCISE_DEFAULTS.items():
            exercise_template = exercise_map.get(key)
            if not exercise_template:
                logger.warning(f"ExerciseTemplate for default config key '{key}' not found. Skipping.")
                continue

            # Check if an active config already exists for this exercise
            stmt_existing = select(ExerciseConfig).filter(
                ExerciseConfig.exercise_id == exercise_template.id,
                ExerciseConfig.is_active == True
            )
            result_existing = await self.db.execute(stmt_existing)
            existing_config = result_existing.scalars().first()

            if not existing_config:
                config_schema = await self.convert_hardcoded_to_db_schema(key, exercise_template.id)
                if config_schema:
                    try:
                        # Use the BaseService create method
                        created_config = await super().create_async(obj_in=config_schema)
                        created_configs.append(created_config)
                        logger.info(f"Created default config for {exercise_template.name} (ID: {exercise_template.id})")
                    except ConflictException:
                         logger.warning(f"Default config for {exercise_template.name} might have been created concurrently.")
                    except Exception as e:
                        logger.error(f"Error creating default config for {exercise_template.name}: {e}", exc_info=True)
                else:
                    logger.info(f"Config schema could not be generated for {exercise_template.name}. Skipping default creation.")
            else:
                logger.info(f"Active config already exists for {exercise_template.name}. Skipping default creation.")
        
        await self.db.commit() # Commit once after all potential creations
        return created_configs


    async def get_or_create_config_async(
        self, 
        exercise_id: UUID, 
        exercise_name_key: Optional[str] = None
    ) -> ExerciseConfig:
        """
        Retrieves the active configuration for an exercise, or creates a default one if none exists.
        """
        active_config = await self.get_active_config_for_exercise_async(exercise_id)
        if active_config:
            return active_config

        logger.info(f"No active config found for exercise {exercise_id}. Attempting to create default.")
        
        if not exercise_name_key:
            # Try to derive exercise_name_key from exercise_id if not provided
            exercise_template = await self.db.get(ExerciseTemplate, exercise_id)
            if not exercise_template:
                raise NotFoundException(f"ExerciseTemplate with id {exercise_id} not found for creating default config.")
            exercise_name_key = exercise_template.name.lower().replace(" ", "_")

        config_schema = await self.convert_hardcoded_to_db_schema(exercise_name_key, exercise_id)
        if not config_schema:
            raise ServerErrorException(f"Could not generate default config schema for exercise {exercise_id} ({exercise_name_key}).")

        try:
            # Use BaseService create method
            created_config = await super().create_async(obj_in=config_schema)
            await self.db.commit() # Commit after successful creation
            logger.info(f"Created default config for exercise {exercise_id} via get_or_create.")
            return created_config
        except ConflictException:
            logger.warning(f"Default config for exercise {exercise_id} was likely created concurrently. Refetching.")
            # If it was created concurrently, try fetching again
            active_config = await self.get_active_config_for_exercise_async(exercise_id)
            if active_config:
                return active_config
            raise ServerErrorException("Failed to get or create config after suspected concurrent creation.")

        except Exception as e:
            logger.error(f"Error in get_or_create_config for exercise {exercise_id}: {e}", exc_info=True)
            raise ServerErrorException(f"Unexpected error creating default config for exercise {exercise_id}.")


    async def get_active_config_by_template_slug_async(self, slug: str) -> Optional[ExerciseConfig]:
        """
        Gets the active exercise configuration for a given exercise template slug.
        First finds the ExerciseTemplate by slug, then gets its active ExerciseConfig.
        Returns None if the slug is not found or no active config exists.
        """
        logger.debug(f"Attempting to get active config for template slug: {slug}")
        stmt_template = select(ExerciseTemplate).filter(ExerciseTemplate.slug == slug)
        result_template = await self.db.execute(stmt_template)
        exercise_template: Optional[ExerciseTemplate] = result_template.scalars().first()

        if not exercise_template:
            logger.info(f"No ExerciseTemplate found for slug: {slug}")
            return None
        
        logger.debug(f"Found ExerciseTemplate ID: {exercise_template.id} for slug: {slug}. Getting active config.")
        return await self.get_active_config_for_exercise_async(exercise_template.id)

    async def get_active_config_for_exercise_async(self, exercise_id: UUID) -> Optional[ExerciseConfig]:
        """
        Gets the latest active configuration for a given exercise.
        """
        stmt = (
            select(ExerciseConfig)
            .filter(ExerciseConfig.exercise_id == exercise_id, ExerciseConfig.is_active == True)
            .order_by(desc(ExerciseConfig.version))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_new_version_async(
        self, 
        *,
        obj_in: ExerciseConfigCreate,
        deactivate_previous: bool = True
    ) -> ExerciseConfig:
        """
        Creates a new version of an exercise configuration.
        Optionally deactivates all previous active versions for the same exercise.
        The new config's version number is automatically set.
        """
        if deactivate_previous:
            update_stmt = (
                sqlalchemy_update(ExerciseConfig)
                .where(ExerciseConfig.exercise_id == obj_in.exercise_id, ExerciseConfig.is_active == True)
                .values(is_active=False)
            )
            await self.db.execute(update_stmt)

        # Get the latest version number for this exercise to increment
        latest_version_stmt = (
            select(func.max(ExerciseConfig.version))
            .filter(ExerciseConfig.exercise_id == obj_in.exercise_id)
        )
        latest_version_result = await self.db.execute(latest_version_stmt)
        current_max_version = latest_version_result.scalar_one_or_none() or 0
        
        # Create a new mutable copy for obj_in to set the version
        new_config_data = obj_in.model_copy(update={"version": current_max_version + 1, "is_active": True})

        # Use BaseService create method
        created_config = await super().create_async(obj_in=new_config_data)
        # No explicit commit here, BaseService handles it or expects it to be handled by the caller/unit of work
        logger.info(f"Created new version {created_config.version} for config {created_config.name} (Exercise ID: {obj_in.exercise_id})")
        return created_config

    # Standard CRUD provided by BaseService, but we can add specific loaders or filters

    async def get_config_async(self, id: UUID, load_exercise: bool = False) -> Optional[ExerciseConfig]:
        """Gets an exercise configuration by ID, optionally loading the related exercise."""
        load_options = [selectinload(ExerciseConfig.exercise)] if load_exercise else None
        return await super().get_async(id=id, load_options=load_options)

    async def get_all_configs_async(
        self,
        *,
        exercise_id: Optional[UUID] = None,
        active_only: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        load_exercise: bool = False
    ) -> List[ExerciseConfig]:
        """Gets all exercise configurations, with optional filters and exercise loading."""
        filters = []
        if exercise_id is not None:
            filters.append(ExerciseConfig.exercise_id == exercise_id)
        if active_only is not None:
            filters.append(ExerciseConfig.is_active == active_only)
        
        load_options = [selectinload(ExerciseConfig.exercise)] if load_exercise else None
        
        return await super().get_multi_async(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by=desc(ExerciseConfig.updated_at), # Default ordering
            load_options=load_options
        )

    async def create_config_async(self, *, obj_in: ExerciseConfigCreate) -> ExerciseConfig:
        """Creates an exercise configuration. Version is managed by obj_in or defaults."""
        # Check for duplicates based on name and exercise_id for the same version
        # This is a simple check, more complex uniqueness might be needed.
        existing_stmt = select(ExerciseConfig).filter(
            ExerciseConfig.exercise_id == obj_in.exercise_id,
            ExerciseConfig.name == obj_in.name,
            ExerciseConfig.version == obj_in.version
        )
        result = await self.db.execute(existing_stmt)
        if result.scalars().first():
            raise ConflictException(f"ExerciseConfig with name '{obj_in.name}' and version {obj_in.version} already exists for this exercise.")
        
        # Default is_active to True if not provided, though schema might handle this
        if obj_in.is_active is None:
            obj_in.is_active = True
            
        return await super().create_async(obj_in=obj_in)

    async def update_config_async(self, *, id: UUID, obj_in: ExerciseConfigUpdate) -> Optional[ExerciseConfig]:
        """Updates an exercise configuration."""
        db_obj = await super().get_async(id=id)
        if not db_obj:
            return None # Or raise NotFoundException
        
        # If name or version is being updated, check for potential duplicates with the new values.
        if obj_in.name is not None or obj_in.version is not None:
            current_name = obj_in.name if obj_in.name is not None else db_obj.name
            current_version = obj_in.version if obj_in.version is not None else db_obj.version
            
            if (obj_in.name is not None and obj_in.name != db_obj.name) or \
               (obj_in.version is not None and obj_in.version != db_obj.version):
                
                conflict_stmt = select(ExerciseConfig).filter(
                    ExerciseConfig.id != id, # Exclude the current object
                    ExerciseConfig.exercise_id == db_obj.exercise_id,
                    ExerciseConfig.name == current_name,
                    ExerciseConfig.version == current_version
                )
                result = await self.db.execute(conflict_stmt)
                if result.scalars().first():
                    raise ConflictException(f"Another ExerciseConfig with name '{current_name}' and version {current_version} already exists for this exercise.")

        return await super().update_async(id=id, obj_in=obj_in)

    async def delete_config_async(self, *, id: UUID) -> Optional[ExerciseConfig]:
        """Deletes an exercise configuration by ID."""
        return await super().remove_async(id=id)

    async def get_reference_pose_data_async(self, exercise_config_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves the reference_pose_data for a given ExerciseConfig ID.

        Args:
            exercise_config_id: The UUID of the ExerciseConfig.

        Returns:
            A dictionary containing the reference pose data if found and not empty,
            otherwise None.
        """
        logger.debug(f"Fetching reference_pose_data for ExerciseConfig ID: {exercise_config_id}")
        exercise_config = await self.get_config_async(id=exercise_config_id)

        if not exercise_config:
            logger.warning(f"ExerciseConfig not found for ID: {exercise_config_id} when fetching reference_pose_data.")
            return None

        if not exercise_config.reference_pose_data:
            logger.info(f"No reference_pose_data found or is empty for ExerciseConfig ID: {exercise_config_id}.")
            return None
        
        # Ensure it's a dictionary before returning, though JSON type should handle this from DB
        if not isinstance(exercise_config.reference_pose_data, dict):
            logger.error(
                f"reference_pose_data for ExerciseConfig ID: {exercise_config_id} is not a dict, type: "
                f"{type(exercise_config.reference_pose_data)}. Returning None."
            )
            return None

        logger.debug(f"Successfully fetched reference_pose_data for ExerciseConfig ID: {exercise_config_id}")
        return exercise_config.reference_pose_data


# Dependency Providers
async def get_async_exercise_config_service(
    db: AsyncSession, # Correctly will be injected by FastAPI
    settings: Settings # Correctly will be injected by FastAPI
) -> ExerciseConfigService:
    return ExerciseConfigService(db=db, settings=settings)

# Synchronous provider (optional, if needed for non-async parts of the app, though discouraged)
# For now, let's assume full async or raise error if sync is attempted.
def get_exercise_config_service() -> ExerciseConfigService:
    # This would typically require a synchronous session, settings, etc.
    # Or, it could be a factory that raises an error if called in an async context.
    raise NotImplementedError(
        "Synchronous ExerciseConfigService is not implemented. Use get_async_exercise_config_service."
    )
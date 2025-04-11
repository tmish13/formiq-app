"""Form Analysis API Documentation."""
from typing import Dict, Any

FORM_ANALYSIS_TAGS = ["Form Analysis"]

FORM_ANALYSIS_DOCS: Dict[str, Any] = {
    "analyze_form": {
        "summary": "Analyze exercise form from video or keypoints",
        "description": """
        Analyzes exercise form using AI-powered pose detection and provides detailed feedback.
        
        The analysis includes:
        - Overall confidence score
        - Joint angle measurements
        - Form correction suggestions
        - Movement quality assessment
        - Safety risk evaluation
        
        Supports both video upload and real-time keypoint analysis.
        
        Rate Limits:
        - Free tier: 100 requests/day
        - Pro tier: Unlimited requests
        
        Video Requirements:
        - Max size: 50MB
        - Formats: MP4, MOV, WebM
        - Resolution: 720p or higher recommended
        - Duration: Maximum 60 seconds
        """,
        "parameters": [{
            "name": "exercise_type",
            "in": "query",
            "required": True,
            "schema": {
                "type": "string",
                "enum": ["squat", "pushup", "plank", "lunge", "deadlift"]
            },
            "description": "Type of exercise being performed"
        }],
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "video": {
                                "type": "string",
                                "format": "binary",
                                "description": "Video file of exercise performance"
                            }
                        }
                    }
                },
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "keypoints": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "score": {"type": "number"},
                                        "name": {"type": "string"}
                                    }
                                },
                                "description": "Array of pose keypoints for real-time analysis"
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Successful Analysis",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "confidence": {
                                    "type": "number",
                                    "description": "Overall confidence score (0-1)"
                                },
                                "feedback": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of form correction suggestions"
                                },
                                "angles": {
                                    "type": "object",
                                    "description": "Joint angle measurements"
                                },
                                "is_reliable": {
                                    "type": "boolean",
                                    "description": "Whether the analysis meets confidence thresholds"
                                }
                            }
                        },
                        "example": {
                            "confidence": 0.92,
                            "feedback": [
                                "Keep your back straight",
                                "Lower your hips further"
                            ],
                            "angles": {
                                "knee": 85,
                                "hip": 95,
                                "ankle": 70
                            },
                            "is_reliable": true
                        }
                    }
                }
            },
            "400": {
                "description": "Invalid Request",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "INVALID_REQUEST",
                                "message": "Invalid video format or missing required fields"
                            }
                        }
                    }
                }
            },
            "413": {
                "description": "Payload Too Large",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "FILE_TOO_LARGE",
                                "message": "Video file exceeds 50MB limit"
                            }
                        }
                    }
                }
            }
        }
    },
    
    "get_analysis_history": {
        "summary": "Retrieve analysis history",
        "description": """
        Returns a paginated list of previous form analyses with filtering options.
        
        Results can be filtered by:
        - Date range
        - Exercise type
        - Confidence score threshold
        - Analysis status
        
        Results include:
        - Analysis results
        - Video thumbnails
        - Progress tracking
        - Trend analysis
        """,
        "parameters": [{
            "name": "exercise_type",
            "in": "query",
            "schema": {
                "type": "string",
                "enum": ["squat", "pushup", "plank", "lunge", "deadlift"]
            }
        }, {
            "name": "start_date",
            "in": "query",
            "schema": {"type": "string", "format": "date"}
        }, {
            "name": "end_date",
            "in": "query",
            "schema": {"type": "string", "format": "date"}
        }, {
            "name": "min_confidence",
            "in": "query",
            "schema": {"type": "number", "minimum": 0, "maximum": 1}
        }, {
            "name": "page",
            "in": "query",
            "schema": {"type": "integer", "default": 1}
        }, {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "default": 20, "maximum": 100}
        }],
        "responses": {
            "200": {
                "description": "Analysis History",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "date": {"type": "string", "format": "date-time"},
                                            "exercise_type": {"type": "string"},
                                            "confidence": {"type": "number"},
                                            "feedback": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                },
                                "total": {"type": "integer"},
                                "page": {"type": "integer"},
                                "pages": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
    }
} 
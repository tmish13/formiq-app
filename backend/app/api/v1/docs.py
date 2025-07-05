"""API documentation utilities."""
from typing import Dict, List, Union, Optional, Any, Type
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

# Standard error response models for documentation
class ErrorDetail(BaseModel):
    """Error detail model for documentation."""
    loc: Optional[List[str]] = None
    msg: Optional[str] = None
    type: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response model for documentation."""
    error: Dict[str, Any]
    request_id: Optional[str] = None

# Dictionary of common error responses for reuse
COMMON_RESPONSES = {
    200: {
        "description": "Success",
        "content": {
            "application/json": {
                "example": {
                    "result": "success",
                    "data": {}
                }
            }
        }
    },
    204: {
        "description": "Success - No Content",
    },
    400: {
        "description": "Bad Request",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 400,
                        "type": "validation_error",
                        "message": "Invalid input data",
                        "code": "INVALID_INPUT"
                    },
                    "request_id": "1613745489123"
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 401,
                        "type": "authentication_error",
                        "message": "Authentication failed",
                        "code": "AUTHENTICATION_FAILED"
                    },
                    "request_id": "1613745489124"
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 403,
                        "type": "authorization_error",
                        "message": "Not authorized to access this resource",
                        "code": "AUTHORIZATION_FAILED"
                    },
                    "request_id": "1613745489125"
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 404,
                        "type": "http_error",
                        "message": "Resource not found",
                        "code": "HTTP_404"
                    },
                    "request_id": "1613745489126"
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 422,
                        "type": "validation_error",
                        "message": "Validation error",
                        "code": "VALIDATION_ERROR",
                        "details": [
                            {
                                "loc": ["body", "email"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    },
                    "request_id": "1613745489127"
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 429,
                        "type": "rate_limit_error",
                        "message": "Rate limit exceeded",
                        "code": "RATE_LIMIT_EXCEEDED"
                    },
                    "request_id": "1613745489128"
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 500,
                        "type": "internal_error",
                        "message": "Internal server error",
                        "code": "INTERNAL_SERVER_ERROR"
                    },
                    "request_id": "1613745489129"
                }
            }
        }
    },
    503: {
        "description": "Service Unavailable",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "status_code": 503,
                        "type": "service_unavailable",
                        "message": "Service temporarily unavailable",
                        "code": "SERVICE_UNAVAILABLE"
                    },
                    "request_id": "1613745489130"
                }
            }
        }
    }
}

def add_error_responses(*status_codes: int) -> Dict[Union[int, str], Dict[str, Any]]:
    """
    Helper function to include standard error responses in API endpoint documentation.
    
    Args:
        *status_codes: Status codes to include in the documentation
        
    Returns:
        Dict of error responses for use with FastAPI's responses parameter
    """
    responses = {}
    for code in status_codes:
        if code in COMMON_RESPONSES:
            responses[str(code)] = COMMON_RESPONSES[code]
    return responses

def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate a custom OpenAPI schema with enhanced documentation.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dict containing the enhanced OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    try:
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    except Exception as e:
        # If there's an issue with schema generation, return a basic schema
        print(f"Error generating OpenAPI schema: {e}")
        openapi_schema = {
            "openapi": "3.0.2",
            "info": {
                "title": app.title,
                "version": app.version,
                "description": app.description,
            },
            "paths": {},
        }
    
    # Add global security scheme for bearer token authentication
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add security requirement to all operations
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"].values():
            for operation in path.values():
                # Only add security to protected endpoints (excluding auth endpoints)
                if (
                    "tags" in operation 
                    and "auth" not in operation["tags"] 
                    and "public" not in operation.get("x-tags", [])
                ):
                    operation["security"] = operation.get("security", []) + [{"BearerAuth": []}]
    
    # Add custom documentation info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    # Add contact info
    openapi_schema["info"]["contact"] = {
        "name": "FormIQ API Support",
        "email": "support@formiq.ai",
        "url": "https://formiq.ai/support"
    }
    
    # Add terms of service and license
    openapi_schema["info"]["termsOfService"] = "https://formiq.ai/terms"
    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://formiq.ai/license"
    }
    
    # Store the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema 
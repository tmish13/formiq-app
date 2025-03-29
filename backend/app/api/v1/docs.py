"""OpenAPI documentation customization."""
from fastapi.openapi.utils import get_openapi
from app.core.config import settings

def custom_openapi(app):
    """Generate custom OpenAPI schema."""
    if not hasattr(app, 'openapi_schema'):
        openapi_schema = get_openapi(
            title=settings.PROJECT_NAME,
            version=settings.VERSION,
            description=settings.DESCRIPTION,
            routes=app.routes,
        )
        
        # Add custom security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [{"bearerAuth": []}]
        
        # Add custom tags
        openapi_schema["tags"] = [
            {
                "name": "auth",
                "description": "Authentication and authorization operations"
            },
            {
                "name": "users",
                "description": "User management operations"
            },
            {
                "name": "workouts",
                "description": "Workout management operations"
            },
            {
                "name": "subscriptions",
                "description": "Subscription management operations"
            },
            {
                "name": "health",
                "description": "Health check operations"
            }
        ]
        
        app.openapi_schema = openapi_schema
    
    return app.openapi_schema 
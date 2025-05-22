"""Services package."""
from app.services.base_service import BaseService
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.video_service import VideoService
# from app.services.form_analysis_service import FormAnalysisService # Old import
from app.services.form_check_service import FormCheckService # New import

__all__ = [
    "BaseService", 
    "UserService", 
    "AuthService", 
    "VideoService", 
    # "FormAnalysisService", # Old name
    "FormCheckService"   # New name
] 
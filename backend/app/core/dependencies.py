from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .auth import get_current_user
from .services import UserService, FormCheckService
from .repositories import UserRepository, FormCheckRepository

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_form_check_repository(db: Session = Depends(get_db)) -> FormCheckRepository:
    return FormCheckRepository(db)

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

def get_form_check_service(repo: FormCheckRepository = Depends(get_form_check_repository)) -> FormCheckService:
    return FormCheckService(repo)

def get_current_active_user(
    current_user = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    if not user_service.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.models.form_check import FormCheck
from app.models.user import User
from app.schemas.form_check import FormCheckCreate, FormCheckUpdate, FormCheckResponse
from app.services.form_check import FormCheckService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
form_check_service = FormCheckService()

@router.post("/", response_model=FormCheckResponse)
def create_form_check(
    *,
    db: Session = Depends(deps.get_db),
    form_check_in: FormCheckCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create new form check."""
    form_check_data = form_check_in.dict()
    form_check_data["user_id"] = current_user.id
    form_check = form_check_service.create_form_check(db, form_check_data=form_check_data)
    return form_check

@router.get("/", response_model=List[FormCheckResponse])
def read_form_checks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve form checks."""
    form_checks = form_check_service.get_user_form_checks(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return form_checks

@router.get("/exercise/{exercise_type}", response_model=List[FormCheckResponse])
def read_exercise_form_checks(
    *,
    db: Session = Depends(deps.get_db),
    exercise_type: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve form checks for a specific exercise type."""
    form_checks = form_check_service.get_exercise_form_checks(
        db, user_id=current_user.id, exercise_type=exercise_type
    )
    return form_checks

@router.get("/latest", response_model=List[FormCheckResponse])
def read_latest_form_checks(
    *,
    db: Session = Depends(deps.get_db),
    limit: int = 10,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve latest form checks."""
    form_checks = form_check_service.get_latest_form_checks(
        db, user_id=current_user.id, limit=limit
    )
    return form_checks

@router.put("/{form_check_id}", response_model=FormCheckResponse)
def update_form_check(
    *,
    db: Session = Depends(deps.get_db),
    form_check_id: int,
    form_check_in: FormCheckUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update form check."""
    form_check = db.query(FormCheck).filter(
        FormCheck.id == form_check_id,
        FormCheck.user_id == current_user.id
    ).first()
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )
    form_check = form_check_service.update_form_check(
        db, form_check=form_check, form_check_data=form_check_in.dict(exclude_unset=True)
    )
    return form_check

@router.delete("/{form_check_id}", response_model=FormCheckResponse)
def delete_form_check(
    *,
    db: Session = Depends(deps.get_db),
    form_check_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete form check."""
    form_check = db.query(FormCheck).filter(
        FormCheck.id == form_check_id,
        FormCheck.user_id == current_user.id
    ).first()
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )
    form_check = form_check_service.delete_form_check(db, form_check=form_check)
    return form_check 
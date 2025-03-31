"""Form check router module."""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.core.storage import upload_video, delete_video
from app.repositories.form_check_repository import FormCheckRepository
from app.schemas.form_check import FormCheck, FormCheckCreate, FormCheckUpdate

router = APIRouter()


@router.get("/", response_model=List[FormCheck])
def read_form_checks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Get form checks."""
    form_check_repository = FormCheckRepository(db)
    form_checks = form_check_repository.get_multi(skip=skip, limit=limit)
    return form_checks


@router.post("/", response_model=FormCheck)
def create_form_check(
    *,
    db: Session = Depends(get_db),
    video: UploadFile = File(...),
    exercise_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Create form check."""
    form_check_repository = FormCheckRepository(db)
    video_url = upload_video(video)
    form_check_in = FormCheckCreate(
        video_url=video_url,
        exercise_id=exercise_id,
        user_id=current_user.id
    )
    form_check = form_check_repository.create(obj_in=form_check_in.dict())
    return form_check


@router.get("/{form_check_id}", response_model=FormCheck)
def read_form_check(
    *,
    db: Session = Depends(get_db),
    form_check_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Get form check by ID."""
    form_check_repository = FormCheckRepository(db)
    form_check = form_check_repository.get(id=form_check_id)
    if not form_check:
        raise HTTPException(
            status_code=404,
            detail="The form check with this id does not exist in the system",
        )
    return form_check


@router.put("/{form_check_id}", response_model=FormCheck)
def update_form_check(
    *,
    db: Session = Depends(get_db),
    form_check_id: int,
    form_check_in: FormCheckUpdate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Update form check."""
    form_check_repository = FormCheckRepository(db)
    form_check = form_check_repository.get(id=form_check_id)
    if not form_check:
        raise HTTPException(
            status_code=404,
            detail="The form check with this id does not exist in the system",
        )
    form_check = form_check_repository.update(db_obj=form_check, obj_in=form_check_in.dict(exclude_unset=True))
    return form_check


@router.delete("/{form_check_id}", response_model=FormCheck)
def delete_form_check(
    *,
    db: Session = Depends(get_db),
    form_check_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Delete form check."""
    form_check_repository = FormCheckRepository(db)
    form_check = form_check_repository.get(id=form_check_id)
    if not form_check:
        raise HTTPException(
            status_code=404,
            detail="The form check with this id does not exist in the system",
        )
    delete_video(form_check.video_url)
    form_check = form_check_repository.delete(id=form_check_id)
    return form_check 
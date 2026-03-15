"""Training session persistence endpoints for Train Analysis (WorkoutsPage)."""
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.training_session import TrainingSession
from app.models.user import User
from app.schemas.training_session import TrainingSessionCreate, TrainingSessionRead

router = APIRouter()


@router.post(
    "/",
    response_model=TrainingSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Persist a completed Train Analysis workout session",
)
async def create_training_session(
    body: TrainingSessionCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> TrainingSession:
    # Idempotent: client retries after a network error return the existing row.
    existing = await db.get(TrainingSession, body.id)
    if existing is not None and existing.user_id == current_user.id:
        return existing

    session = TrainingSession(
        id=body.id,
        user_id=current_user.id,
        started_at=body.started_at,
        goal=body.goal,
        sets_json=body.sets_json,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get(
    "/",
    response_model=List[TrainingSessionRead],
    summary="List Train Analysis sessions for the current user",
)
async def list_training_sessions(
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> List[TrainingSession]:
    result = await db.execute(
        select(TrainingSession)
        .where(TrainingSession.user_id == current_user.id)
        .order_by(TrainingSession.started_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

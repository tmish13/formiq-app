"""Squat session persistence endpoints."""
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.squat_session import SquatSession
from app.models.user import User
from app.schemas.squat_session import SquatSessionCreate, SquatSessionRead

router = APIRouter()


@router.post(
    "/",
    response_model=SquatSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save a squat training session",
)
async def create_squat_session(
    body: SquatSessionCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> SquatSession:
    session = SquatSession(
        id=uuid4(),
        user_id=current_user.id,
        **body.model_dump(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get(
    "/",
    response_model=List[SquatSessionRead],
    summary="List squat training sessions for the current user",
)
async def list_squat_sessions(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
    limit: int = Query(200, ge=1, le=1000),
) -> List[SquatSession]:
    result = await db.execute(
        select(SquatSession)
        .where(SquatSession.user_id == current_user.id)
        .order_by(SquatSession.date.desc())
        .limit(limit)
    )
    return result.scalars().all()

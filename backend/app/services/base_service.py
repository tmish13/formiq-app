from typing import Generic, TypeVar, Type, Optional, List, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm.decl_api import DeclarativeBase
from app.core.config import Settings
from app.models.base import BaseModel
from app.core.exceptions import ServiceError
from sqlalchemy.exc import IntegrityError
from fastapi import status
import logging
import os

import sqlalchemy as sa

# Define TypeVars for Model, Create Schema, and Update Schema
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = logging.getLogger(__name__)


def _reject_unknown_fields(db_obj: Any, update_data: dict) -> dict:
    """Refuse to silently drop keys the model has no attribute for.

    A bare `setattr(db_obj, field, value)` accepts anything. Python attaches
    the attribute to the instance, SQLAlchemy ignores it because it is not
    mapped, the commit succeeds, and the value is gone. Nothing raises and
    nothing logs.

    That is not hypothetical. Three fields were lost this way for the life of
    the project:

      * `error_details` -- six call sites, including every finalized failure.
        Every FAILED form check was reason-less as a result (G-37).
      * `summary` and `analysis_completed_at` -- written on every finalize and
        read back at form_check_service.py:483, against nothing.

    The column added in migration 0011 fixes those two instances. This closes
    the class. It raises outside production so a test or a dev run fails loudly,
    and only logs in production, where dropping a field is still better than
    500ing a user's request over a field name.
    """
    mapper = sa.inspect(type(db_obj))
    known = set(mapper.attrs.keys()) | {c.key for c in mapper.columns}
    unknown = [k for k in update_data if k not in known]
    if not unknown:
        return update_data

    msg = (f"{type(db_obj).__name__} has no attribute(s) {sorted(unknown)}; "
           f"they would be silently discarded. Add the column, or stop writing "
           f"the key.")
    logger.error("BaseService: %s", msg)
    if os.getenv("ENVIRONMENT", "development") != "production":
        raise ServiceError(msg)
    return {k: v for k, v in update_data.items() if k in known}

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base service with repository pattern and error handling for both sync and async sessions."""
    
    def __init__(self, db: Union[Session, AsyncSession], model: Type[ModelType], settings: Optional[Settings] = None):
        self.db = db
        self.settings = settings
        self.model = model
        self._is_async = isinstance(db, AsyncSession)

    async def get_async(self, id: Any) -> Optional[ModelType]:
        """Get a single record by ID asynchronously."""
        try:
            result = await self.db.execute(select(self.model).filter(self.model.id == id))
            return result.scalars().first()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__}: {str(e)}")

    def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by ID synchronously."""
        if self._is_async:
            raise ServiceError("Use get_async for async sessions")
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__}: {str(e)}")

    async def get_multi_async(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100, 
        filter_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and optional filtering/ordering asynchronously."""
        try:
            stmt = select(self.model)
            
            if filter_conditions:
                for condition in filter_conditions:
                    stmt = stmt.where(condition)
            
            if order_by:
                stmt = stmt.order_by(*order_by)

            stmt = stmt.offset(skip).limit(limit)
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__} list: {str(e)}")

    def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records with pagination synchronously."""
        if self._is_async:
            raise ServiceError("Use get_multi_async for async sessions")
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__} list: {str(e)}")

    async def create_async(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record asynchronously."""
        try:
            # For Pydantic V1, use .dict(). For V2, use .model_dump().
            # Assuming Pydantic V1 based on other logs (e.g., validator warnings).
            import uuid as _uuid
            obj_in_data = {k: v for k, v in obj_in.dict().items() if v is not None}
            db_obj = self.model(**obj_in_data)
            # Async sessions don't always trigger Python-side column defaults.
            # Ensure UUID primary key is set before flush.
            if getattr(db_obj, 'id', None) is None:
                db_obj.id = _uuid.uuid4()
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:  # Catch specific DB errors like unique constraints
            await self.db.rollback()
            logger.error(f"Database integrity error creating {self.model.__name__}: {str(e)}")
            # You might want to map this to a more specific HTTP error, e.g., 409 Conflict
            raise ServiceError(f"Database integrity error: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise ServiceError(f"Failed to create {self.model.__name__}: {str(e)}")

    def create(self, *, obj_in: dict) -> ModelType:
        """Create a new record synchronously."""
        if self._is_async:
            raise ServiceError("Use create_async for async sessions")
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to create {self.model.__name__}: {str(e)}")

    async def update_async(self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, dict]) -> ModelType:
        """Update an existing record asynchronously."""
        if not isinstance(obj_in, dict):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        # Outside the try, deliberately. A key the model does not have is a
        # programming error, not a database failure: reporting it as one would
        # bury the field name under "Failed to update FormCheck" and trigger a
        # rollback of a transaction that never got as far as the database.
        update_data = _reject_unknown_fields(db_obj, update_data)

        try:
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            self.db.add(db_obj)
            logger.info(f"BaseService: Attempting commit for {self.model.__name__} ID {db_obj.id}, session {id(self.db)}")
            await self.db.commit()
            logger.info(f"BaseService: Commit successful for {self.model.__name__} ID {db_obj.id}, session {id(self.db)}")
            await self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.error(f"BaseService: Error during update/commit for {self.model.__name__} (ID might be {db_obj.id if 'db_obj' in locals() else 'unknown'}), session {id(self.db)}. Error: {e}", exc_info=True)
            await self.db.rollback()
            logger.info(f"BaseService: Rolled back session {id(self.db)} after error.")
            raise ServiceError(f"Failed to update {self.model.__name__}: {str(e)}")

    def update(self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, dict]) -> ModelType:
        """Update an existing record synchronously."""
        if self._is_async:
            raise ServiceError("Use update_async for async sessions")
        try:
            if not isinstance(obj_in, dict):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field, value in update_data.items():
                setattr(db_obj, field, value)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to update {self.model.__name__}: {str(e)}")

    async def delete_async(self, *, id: int) -> ModelType:
        """Delete a record by ID asynchronously."""
        try:
            result = await self.db.execute(select(self.model).filter(self.model.id == id))
            obj = result.scalars().first()
            if not obj:
                raise ServiceError(f"{self.model.__name__} not found")
            await self.db.delete(obj)
            await self.db.commit()
            return obj
        except Exception as e:
            await self.db.rollback()
            raise ServiceError(f"Failed to delete {self.model.__name__}: {str(e)}")

    def delete(self, *, id: int) -> ModelType:
        """Delete a record by ID synchronously."""
        if self._is_async:
            raise ServiceError("Use delete_async for async sessions")
        try:
            obj = self.db.query(self.model).get(id)
            if not obj:
                raise ServiceError(f"{self.model.__name__} not found")
            self.db.delete(obj)
            self.db.commit()
            return obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to delete {self.model.__name__}: {str(e)}") 
from typing import Generic, TypeVar, Type, Optional, List, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm.decl_api import DeclarativeBase
from app.core.config import Settings
from app.models.base import BaseModel
from app.core.exceptions import ServiceError

# Define TypeVars for Model, Create Schema, and Update Schema
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

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

    async def create_async(self, *, obj_in: dict) -> ModelType:
        """Create a new record asynchronously."""
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.db.rollback()
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
        try:
            if not isinstance(obj_in, dict):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field, value in update_data.items():
                setattr(db_obj, field, value)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.db.rollback()
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
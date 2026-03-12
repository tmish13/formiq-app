"""Base repository module for database operations."""
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Union
from uuid import UUID
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta
from app.models.base import Base
from app.core.exceptions import NotFoundException, DatabaseException

# Define ModelType as bound to DeclarativeMeta instead of Base
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)

class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations for both sync and async sessions."""
    
    def __init__(self, model: Type[ModelType], db: Union[Session, AsyncSession]):
        """
        Initialize repository with model and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Database session (sync or async)
        """
        self.model = model
        self.db = db
        self._mapper = inspect(model)
        self._is_async = isinstance(db, AsyncSession)

    def _get_column_type(self, column_name: str) -> Optional[Type]:
        """Get the Python type of a model column."""
        if column_name in self._mapper.columns:
            return self._mapper.columns[column_name].type.python_type
        return None

    def _convert_value(self, field: str, value: Any) -> Any:
        """Convert a value to the correct type for a model field."""
        if value is None:
            return None
            
        column_type = self._get_column_type(field)
        if column_type is None:
            return value
            
        try:
            # Handle UUID fields specially
            if column_type == UUID and isinstance(value, str):
                return UUID(value)
            # Handle other type conversions
            return column_type(value)
        except (ValueError, TypeError):
            return value

    def get(self, id: Union[int, str, UUID]) -> Optional[ModelType]:
        """
        Get a single record by ID synchronously.
        
        Args:
            id: Record identifier
            
        Returns:
            Optional[ModelType]: Found record or None
        """
        if self._is_async:
            raise DatabaseException("Use get_async for async sessions")
            
        id_column = self._mapper.primary_key[0]
        typed_id = self._convert_value(id_column.name, id)
        return self.db.query(self.model).filter(id_column == typed_id).first()

    async def get_async(self, id: Union[int, str, UUID]) -> Optional[ModelType]:
        """
        Get a single record by ID asynchronously.
        
        Args:
            id: Record identifier
            
        Returns:
            Optional[ModelType]: Found record or None
        """
        if not self._is_async:
            raise DatabaseException("Use get for sync sessions")
            
        id_column = self._mapper.primary_key[0]
        typed_id = self._convert_value(id_column.name, id)
        
        stmt = select(self.model).filter(id_column == typed_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        **filters: Any
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering synchronously.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filter criteria
            
        Returns:
            List[ModelType]: List of found records
        """
        if self._is_async:
            raise DatabaseException("Use get_multi_async for async sessions")
            
        query = self.db.query(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                typed_value = self._convert_value(field, value)
                query = query.filter(getattr(self.model, field) == typed_value)
                
        return query.offset(skip).limit(limit).all()

    async def get_multi_async(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        **filters: Any
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering asynchronously.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filter criteria
            
        Returns:
            List[ModelType]: List of found records
        """
        if not self._is_async:
            raise DatabaseException("Use get_multi for sync sessions")
            
        stmt = select(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                typed_value = self._convert_value(field, value)
                stmt = stmt.filter(getattr(self.model, field) == typed_value)
                
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def create(self, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record synchronously.
        
        Args:
            obj_in: Dictionary of model field values
            
        Returns:
            ModelType: Created record
            
        Raises:
            DatabaseException: If creation fails
        """
        if self._is_async:
            raise DatabaseException("Use create_async for async sessions")
            
        try:
            # Convert input values to correct types
            converted_data = {
                field: self._convert_value(field, value)
                for field, value in obj_in.items()
                if hasattr(self.model, field)
            }
            
            db_obj = self.model(**converted_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to create {self.model.__name__}: {str(e)}")

    async def create_async(self, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record asynchronously.
        
        Args:
            obj_in: Dictionary of model field values
            
        Returns:
            ModelType: Created record
            
        Raises:
            DatabaseException: If creation fails
        """
        if not self._is_async:
            raise DatabaseException("Use create for sync sessions")
            
        try:
            # Convert input values to correct types
            converted_data = {
                field: self._convert_value(field, value)
                for field, value in obj_in.items()
                if hasattr(self.model, field)
            }
            
            db_obj = self.model(**converted_data)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseException(f"Failed to create {self.model.__name__}: {str(e)}")

    def update(
        self, 
        *, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record synchronously.
        
        Args:
            db_obj: Existing database object
            obj_in: Dictionary of fields to update
            
        Returns:
            ModelType: Updated record
            
        Raises:
            DatabaseException: If update fails
        """
        if self._is_async:
            raise DatabaseException("Use update_async for async sessions")
            
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    typed_value = self._convert_value(field, value)
                    setattr(db_obj, field, typed_value)
            
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to update {self.model.__name__}: {str(e)}")

    async def update_async(
        self, 
        *, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record asynchronously.
        
        Args:
            db_obj: Existing database object
            obj_in: Dictionary of fields to update
            
        Returns:
            ModelType: Updated record
            
        Raises:
            DatabaseException: If update fails
        """
        if not self._is_async:
            raise DatabaseException("Use update for sync sessions")
            
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    typed_value = self._convert_value(field, value)
                    setattr(db_obj, field, typed_value)
            
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseException(f"Failed to update {self.model.__name__}: {str(e)}")

    def delete(self, *, id: Union[int, str, UUID]) -> ModelType:
        """
        Delete a record by ID synchronously.
        
        Args:
            id: Record identifier
            
        Returns:
            ModelType: Deleted record
            
        Raises:
            NotFoundException: If record doesn't exist
            DatabaseException: If deletion fails
        """
        if self._is_async:
            raise DatabaseException("Use delete_async for async sessions")
            
        try:
            id_column = self._mapper.primary_key[0]
            typed_id = self._convert_value(id_column.name, id)
            obj = self.db.query(self.model).get(typed_id)
            
            if not obj:
                raise NotFoundException(f"{self.model.__name__} with id {id} not found")
            
            self.db.delete(obj)
            self.db.commit()
            return obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to delete {self.model.__name__}: {str(e)}")

    async def delete_async(self, *, id: Union[int, str, UUID]) -> ModelType:
        """
        Delete a record by ID asynchronously.
        
        Args:
            id: Record identifier
            
        Returns:
            ModelType: Deleted record
            
        Raises:
            NotFoundException: If record doesn't exist
            DatabaseException: If deletion fails
        """
        if not self._is_async:
            raise DatabaseException("Use delete for sync sessions")
            
        try:
            id_column = self._mapper.primary_key[0]
            typed_id = self._convert_value(id_column.name, id)
            
            stmt = select(self.model).filter(id_column == typed_id)
            result = await self.db.execute(stmt)
            obj = result.scalars().first()
            
            if not obj:
                raise NotFoundException(f"{self.model.__name__} with id {id} not found")
            
            await self.db.delete(obj)
            await self.db.commit()
            return obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise DatabaseException(f"Failed to delete {self.model.__name__}: {str(e)}")

    def exists(self, **filters: Any) -> bool:
        """
        Check if a record exists with given filters synchronously.
        
        Args:
            **filters: Filter criteria
            
        Returns:
            bool: True if record exists, False otherwise
        """
        if self._is_async:
            raise DatabaseException("Use exists_async for async sessions")
            
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                typed_value = self._convert_value(field, value)
                query = query.filter(getattr(self.model, field) == typed_value)
        return self.db.query(query.exists()).scalar()

    async def exists_async(self, **filters: Any) -> bool:
        """
        Check if a record exists with given filters asynchronously.
        
        Args:
            **filters: Filter criteria
            
        Returns:
            bool: True if record exists, False otherwise
        """
        if not self._is_async:
            raise DatabaseException("Use exists for sync sessions")
            
        stmt = select(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                typed_value = self._convert_value(field, value)
                stmt = stmt.filter(getattr(self.model, field) == typed_value)
        
        result = await self.db.execute(select(stmt.exists()))
        return result.scalar() 
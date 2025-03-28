from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.core.logging import logger
from app.core.exceptions import DatabaseException, NotFoundException, ValidationException

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    CRUD base class with default methods to Create, Read, Update, Delete (CRUD).
    
    Attributes:
        model: A SQLAlchemy model class
    """

    def __init__(self, model: Type[ModelType]):
        """
        CRUD base class.
        
        Args:
            model: A SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: ID of the record
            
        Returns:
            Record if found, None otherwise
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}", error=str(e))
            raise DatabaseException(f"Error getting {self.model.__name__}")

    def get_by_field(self, db: Session, field: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by field value.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
            
        Returns:
            Record if found, None otherwise
        """
        try:
            return db.query(self.model).filter(getattr(self.model, field) == value).first()
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}_by_{field}", error=str(e))
            raise DatabaseException(f"Error getting {self.model.__name__} by {field}")

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        try:
            return db.query(self.model).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}_list", error=str(e))
            raise DatabaseException(f"Error getting {self.model.__name__} list")

    def get_multi_by_field(
        self, db: Session, *, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records by field value with pagination.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        try:
            return (
                db.query(self.model)
                .filter(getattr(self.model, field) == value)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}_list_by_{field}", error=str(e))
            raise DatabaseException(f"Error getting {self.model.__name__} list by {field}")

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Input data
            
        Returns:
            Created record
        """
        try:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"{self.model.__name__.lower()}_created", id=db_obj.id)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"integrity_error_creating_{self.model.__name__.lower()}", error=str(e))
            raise ValidationException(f"Integrity error creating {self.model.__name__}")
        except Exception as e:
            db.rollback()
            logger.error(f"error_creating_{self.model.__name__.lower()}", error=str(e))
            raise DatabaseException(f"Error creating {self.model.__name__}")

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db: Database session
            db_obj: Record to update
            obj_in: New data
            
        Returns:
            Updated record
        """
        try:
            obj_data = jsonable_encoder(db_obj)
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)
                
            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])
                    
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"{self.model.__name__.lower()}_updated", id=db_obj.id)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"integrity_error_updating_{self.model.__name__.lower()}", error=str(e))
            raise ValidationException(f"Integrity error updating {self.model.__name__}")
        except Exception as e:
            db.rollback()
            logger.error(f"error_updating_{self.model.__name__.lower()}", error=str(e))
            raise DatabaseException(f"Error updating {self.model.__name__}")

    def delete(self, db: Session, *, id: int) -> ModelType:
        """
        Delete a record.
        
        Args:
            db: Database session
            id: ID of the record
            
        Returns:
            Deleted record
            
        Raises:
            NotFoundException: If record not found
        """
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                raise NotFoundException(f"{self.model.__name__} not found")
                
            db.delete(obj)
            db.commit()
            logger.info(f"{self.model.__name__.lower()}_deleted", id=id)
            return obj
        except NotFoundException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"error_deleting_{self.model.__name__.lower()}", error=str(e))
            raise DatabaseException(f"Error deleting {self.model.__name__}")

    def exists(self, db: Session, id: int) -> bool:
        """
        Check if a record exists.
        
        Args:
            db: Database session
            id: ID of the record
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            result = db.query(self.model).filter(self.model.id == id).first() is not None
            return result
        except Exception as e:
            logger.error(f"error_checking_{self.model.__name__.lower()}_exists", error=str(e))
            raise DatabaseException(f"Error checking if {self.model.__name__} exists")

    def count(self, db: Session) -> int:
        """
        Count all records.
        
        Args:
            db: Database session
            
        Returns:
            Number of records
        """
        try:
            return db.query(self.model).count()
        except Exception as e:
            logger.error(f"error_counting_{self.model.__name__.lower()}", error=str(e))
            raise DatabaseException(f"Error counting {self.model.__name__} records") 
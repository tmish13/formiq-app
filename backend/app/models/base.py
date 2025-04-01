"""Base model module providing common functionality for all models."""
from datetime import datetime
from typing import Dict, Any, TypeVar, Type, Optional
from sqlalchemy import Column, DateTime, func, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from pydantic import BaseModel as PydanticBaseModel
from app.db.base_class import Base
from app.core.exceptions import ValidationError

T = TypeVar('T', bound='BaseModel')

class BaseModel(Base):
    """
    Base model with common fields and methods.
    
    This class provides common functionality for all models including:
    - UUID primary key
    - Creation and update timestamps
    - Dictionary conversion
    - Validation methods
    - Common utility methods
    
    All models should inherit from this class.
    """
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create model instance from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing model data
            
        Returns:
            T: New model instance
            
        Raises:
            ValidationError: If data validation fails
        """
        return cls(**data)

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update model instance with dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing update data
            
        Raises:
            ValidationError: If data validation fails
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def validate_field(cls, field: str, value: Any) -> None:
        """
        Validate a single field value.
        
        Args:
            field (str): Field name to validate
            value (Any): Value to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not hasattr(cls, field):
            raise ValidationError(f"Invalid field: {field}")

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        This method should be overridden by child classes to add
        custom validation logic.
        
        Raises:
            ValidationError: If validation fails
        """
        pass

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__} {self.id}>" 
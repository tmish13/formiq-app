"""Base model module providing common functionality for all models."""
from datetime import datetime
from typing import Dict, Any, TypeVar, Type, Optional, List, Set
from sqlalchemy import Column, DateTime, func, String, inspect, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator
import uuid
from pydantic import BaseModel as PydanticBaseModel
from app.db.base_class import Base
from app.core.exceptions import ValidationError
from sqlalchemy.ext.declarative import declared_attr
import re
import json

T = TypeVar('T', bound='BaseModel')

class SQLiteUUID(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

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

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs):
        """Initialize a new model instance.
        
        Args:
            **kwargs: Keyword arguments for model attributes
        """
        # Get valid fields for this model
        valid_fields = inspect(self.__class__).columns.keys()
        
        # Filter out invalid fields
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        # Call SQLAlchemy's __init__
        super().__init__(**filtered_kwargs)
        
        # Validate after initialization
        self.validate()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle UUID objects
            if isinstance(value, uuid.UUID):
                value = str(value)
            # Handle datetime objects
            elif isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        return result
    
    def to_dict_with_relationships(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary including relationships.
        
        Args:
            include (Optional[List[str]]): List of relationship attributes to include
            
        Returns:
            Dict[str, Any]: Dictionary representation of the model with relationships
        """
        result = self.to_dict()
        
        if not include:
            # Get all relationship attributes
            mapper = inspect(self.__class__)
            include = [rel.key for rel in mapper.relationships]
        
        for rel_name in include:
            if hasattr(self, rel_name):
                rel_obj = getattr(self, rel_name)
                if rel_obj is not None:
                    if isinstance(rel_obj, list):
                        result[rel_name] = [
                            item.to_dict() if hasattr(item, 'to_dict') else item
                            for item in rel_obj
                        ]
                    else:
                        result[rel_name] = rel_obj.to_dict() if hasattr(rel_obj, 'to_dict') else rel_obj
        
        return result

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
        # Filter out keys that don't match model attributes
        valid_fields = inspect(cls).columns.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Create instance and validate
        instance = cls(**filtered_data)
        instance.validate()
        return instance

    @classmethod
    def _validate_required_fields(cls, data: Dict[str, Any]) -> None:
        """
        Validate required fields in the data dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing model data
            
        Raises:
            ValidationError: If required fields are missing
        """
        required_fields = cls._get_required_fields()
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    @classmethod
    def _get_required_fields(cls) -> Set[str]:
        """
        Get required fields for the model.
        
        Returns:
            Set[str]: Set of required field names
        """
        required_fields = set()
        for column in cls.__table__.columns:
            if not column.nullable and column.default is None and column.server_default is None:
                # The column is required if it's not nullable and has no default value
                required_fields.add(column.name)
        
        # Remove id field as it's generated automatically
        if 'id' in required_fields:
            required_fields.remove('id')
        
        return required_fields

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
        
        # Validate after update
        self.validate()

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
        
        column = cls.__table__.columns.get(field)
        if column is not None:
            # Check if the field is required and value is None
            if column.primary_key and value is None:
                # For PKs, if it's None, it means it's a new object and will be defaulted by DB or Python default.
                # So, we don't raise a validation error here.
                return 
            
            # If the column has a server_default or a Python-side default, and the current value is None,
            # it's assumed the default will take effect. Skip nullability check for these during this pre-flush validation.
            if value is None and (column.server_default is not None or column.default is not None):
                return
            
            if not column.nullable and value is None:
                raise ValidationError(f"Field '{field}' cannot be null")
            
            # Check field type if possible
            cls._validate_field_type(field, value, column)

    @classmethod
    def _validate_field_type(cls, field: str, value: Any, column) -> None:
        """
        Validate the type of a field value.
        
        Args:
            field (str): Field name to validate
            value (Any): Value to validate
            column: SQLAlchemy column object
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            return
        
        # Basic type checking
        try:
            if hasattr(column.type, 'python_type'):
                expected_type = column.type.python_type
                
                # Handle UUID special case
                if expected_type is uuid.UUID and isinstance(value, str):
                    try:
                        uuid.UUID(value)
                    except ValueError:
                        raise ValidationError(f"Field '{field}' must be a valid UUID")
                
                # Skip type checking for ARRAY and JSON types which don't have reliable python_type
                elif str(column.type) not in ('ARRAY', 'JSON'):
                    if not isinstance(value, expected_type):
                        raise ValidationError(f"Field '{field}' must be of type {expected_type.__name__}")
        except Exception as e:
            # Log the error but don't fail validation if type checking itself fails
            pass

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        This method should be overridden by child classes to add
        custom validation logic.
        
        Raises:
            ValidationError: If validation fails
        """
        for column in self.__table__.columns:
            value = getattr(self, column.name, None)
            self.validate_field(column.name, value)

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__} {self.id}>"

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically from class name."""
        # Convert CamelCase to snake_case and pluralize
        name = re.sub('(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        if not name.endswith('s'):
            name += 's'  # Simple pluralization
        return name

    def to_json(self) -> str:
        """
        Convert model to JSON string.
        
        Returns:
            JSON string representation of the model
        """
        return json.dumps(self.to_dict())

    @classmethod
    def create(cls: Type[T], **kwargs) -> T:
        """
        Create a new instance with the given attributes.
        
        Args:
            **kwargs: Model field values
            
        Returns:
            A new instance of the model
            
        Raises:
            ValidationError: If data validation fails
        """
        instance = cls(**kwargs)
        instance.validate()
        return instance 
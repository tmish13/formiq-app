"""
Migration versions package.

This package contains database migration versions.

The migration sequence is as follows:
1. 001_initial_schema.py - Initial schema creation 
2. 002_add_foreign_keys.py - Add foreign key constraints
3. 003_add_indexes.py - Add indexes for performance

To create a new migration, use the command:
alembic revision --autogenerate -m "description"
"""

__all__ = [] 
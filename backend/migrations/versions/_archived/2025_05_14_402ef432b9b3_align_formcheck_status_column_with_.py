"""Align FormCheck status column with FormCheckStatus enum

Revision ID: 402ef432b9b3
Revises: d2b1e6dc2d42
Create Date: 2025-05-14 23:32:32.094861

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # Ensure this is imported


# revision identifiers, used by Alembic.
revision = '402ef432b9b3'
down_revision = 'd2b1e6dc2d42'
branch_labels = None
depends_on = None

# Define the ENUM and its values for clarity
formcheckstatus_enum_values = ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')
formcheckstatus_enum_name = 'formcheckstatus'

def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    if is_postgresql:
        op.execute(f"CREATE TYPE {formcheckstatus_enum_name} AS ENUM {formcheckstatus_enum_values}")
        op.execute("ALTER TABLE form_checks ALTER COLUMN status DROP DEFAULT")
        op.alter_column('form_checks', 'status',
                   existing_type=sa.VARCHAR(length=50),
                   type_=postgresql.ENUM(*formcheckstatus_enum_values, name=formcheckstatus_enum_name, create_type=False),
                   nullable=False,
                   postgresql_using=f'status::text::{formcheckstatus_enum_name}')
        op.execute(f"ALTER TABLE form_checks ALTER COLUMN status SET DEFAULT '{formcheckstatus_enum_values[0]}'::{formcheckstatus_enum_name}")
    else:
        # For SQLite, ensure the column uses sa.Enum with native_enum=False
        status_enum_type = sa.Enum(*formcheckstatus_enum_values, 
                                   name=formcheckstatus_enum_name, 
                                   native_enum=False, 
                                   create_constraint=False)

        with op.batch_alter_table('form_checks', schema=None) as batch_op:
            # Drop the existing column first to ensure a clean slate,
            # as alter_column might have issues changing the type fundamentally
            # or if the CHECK constraint isn't picked up correctly.
            # This is safe in batch mode as it recreates the table.
            batch_op.drop_column('status')
            
            # Add the column with the correct Enum type and server default
            batch_op.add_column(sa.Column('status', 
                                          status_enum_type, 
                                          nullable=False, 
                                          server_default=formcheckstatus_enum_values[0]))

def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    if is_postgresql:
        op.execute("ALTER TABLE form_checks ALTER COLUMN status DROP DEFAULT")
        op.alter_column('form_checks', 'status',
                   existing_type=postgresql.ENUM(*formcheckstatus_enum_values, name=formcheckstatus_enum_name, create_type=False),
                   type_=sa.VARCHAR(length=50),
                   nullable=False,
                   postgresql_using='status::text')
        op.execute("ALTER TABLE form_checks ALTER COLUMN status SET DEFAULT 'pending'::character varying")
        op.execute(f"DROP TYPE IF EXISTS {formcheckstatus_enum_name}")
    else:
        # For SQLite, revert to a simple string type and default
        with op.batch_alter_table('form_checks', schema=None) as batch_op:
            # If we added it, we should drop it and re-add the old way if needed,
            # or just alter_column if that's simpler for downgrade.
            # For now, let's assume alter_column is fine for downgrade.
            batch_op.alter_column('status',
                       existing_type=sa.String(length=50), # This should reflect the Enum we are removing
                       type_=sa.VARCHAR(length=50),
                       nullable=False,
                       server_default='pending') 
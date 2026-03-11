"""Add details column to form_checks and posture_v1_inference_logs table

Revision ID: 2026_02_14_add_details_and_telemetry
Revises: 2025_12_06_supplementary_indexes
Create Date: 2026-02-14

- Adds nullable JSON `details` column to `form_checks`
- Creates `posture_v1_inference_logs` table for inference telemetry
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '2026_02_14_add_details_and_telemetry'
down_revision = '2025_12_06_supplementary_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add details JSON column to form_checks
    op.add_column('form_checks', sa.Column('details', sa.JSON(), nullable=True))

    # Create posture_v1_inference_logs table
    op.create_table(
        'posture_v1_inference_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column('form_check_id', UUID(as_uuid=True), sa.ForeignKey('form_checks.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('video_id', UUID(as_uuid=True), nullable=True),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('prob_fault', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('threshold_mode', sa.String(20), nullable=True),
        sa.Column('posture_v1_mode', sa.String(10), nullable=True),
        sa.Column('sequence_length', sa.Integer(), nullable=True),
        sa.Column('missing_ratio', sa.Float(), nullable=True),
        sa.Column('outlier_z_gt3', sa.Integer(), nullable=True),
        sa.Column('outlier_z_gt6', sa.Integer(), nullable=True),
        sa.Column('angle_validity', sa.JSON(), nullable=True),
        sa.Column('gate_flags', sa.JSON(), nullable=True),
        sa.Column('top_signals', sa.JSON(), nullable=True),
        sa.Column('named_scores', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('posture_v1_inference_logs')
    op.drop_column('form_checks', 'details')

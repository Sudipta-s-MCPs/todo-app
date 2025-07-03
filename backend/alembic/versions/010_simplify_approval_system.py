"""
Simplify approval system - remove is_approved field
Created: 2025-07-02 16:45:00 PST

Revision ID: 010_simplify_approval_system
Revises: 009_add_user_approval_system
Create Date: 2025-07-02 16:45:00 PST
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '010_simplify_approval_system'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove redundant is_approved field, keep only approval_status"""
    # Drop the is_approved column
    op.drop_column('users', 'is_approved')


def downgrade() -> None:
    """Re-add is_approved field"""
    # Re-add is_approved column
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))
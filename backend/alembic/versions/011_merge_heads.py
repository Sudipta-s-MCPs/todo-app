"""Merge multiple heads

Revision ID: 011_merge_heads
Revises: 010, 010_simplify_approval_system
Create Date: 2025-07-02 16:50:00 PST
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '011_merge_heads'
down_revision = ('010', '010_simplify_approval_system')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge heads and ensure is_approved column is dropped"""
    # Check if is_approved column exists and drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'is_approved' in columns:
        op.drop_column('users', 'is_approved')


def downgrade() -> None:
    """Re-add is_approved column"""
    # Re-add is_approved column
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))
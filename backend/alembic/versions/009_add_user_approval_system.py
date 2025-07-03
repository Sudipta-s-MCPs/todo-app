"""add_user_approval_system

Revision ID: e0483510bdff
Revises: 008
Create Date: 2025-07-02 15:39:16.095558

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add approval columns to users table
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('approval_status', sa.String(50), nullable=False, server_default='pending'))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('rejection_reason', sa.Text(), nullable=True))
    
    # Create foreign key for approved_by
    op.create_foreign_key(
        'fk_users_approved_by',
        'users', 'users',
        ['approved_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # Update existing admin users to be approved
    op.execute("UPDATE users SET is_approved = true, approval_status = 'approved' WHERE is_admin = true")


def downgrade() -> None:
    # Drop foreign key first
    op.drop_constraint('fk_users_approved_by', 'users', type_='foreignkey')
    
    # Drop columns
    op.drop_column('users', 'rejection_reason')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'approval_status')
    op.drop_column('users', 'is_approved')
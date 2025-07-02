"""Add system settings table

Revision ID: 007_add_system_settings
Revises: 006_add_storage_metadata_to_attachments
Create Date: 2025-01-02 07:15:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_system_settings'
down_revision = '006_add_storage_metadata_to_attachments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(50), nullable=False, server_default='string'),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_readonly', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('previous_value', sa.Text(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)
    op.create_index('ix_system_settings_category', 'system_settings', ['category'])
    
    # Add foreign key to users table for updated_by
    op.create_foreign_key(
        'fk_system_settings_updated_by',
        'system_settings',
        'users',
        ['updated_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_system_settings_updated_by', 'system_settings', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_system_settings_category', table_name='system_settings')
    op.drop_index('ix_system_settings_key', table_name='system_settings')
    
    # Drop table
    op.drop_table('system_settings')
"""Fix NULL is_readonly values in system_settings table

Revision ID: 012_fix_readonly_null_values
Revises: 011_merge_heads
Create Date: 2025-07-02 17:55:00 PST
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '012_fix_readonly_null_values'
down_revision = '6658ff559adf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix NULL is_readonly values in system_settings table"""
    # Update all NULL is_readonly values to false
    op.execute("""
        UPDATE system_settings 
        SET is_readonly = false 
        WHERE is_readonly IS NULL
    """)
    
    # Also update any NULL is_sensitive values to false for consistency
    op.execute("""
        UPDATE system_settings 
        SET is_sensitive = false 
        WHERE is_sensitive IS NULL
    """)


def downgrade() -> None:
    """No downgrade needed - this fixes data integrity"""
    pass
"""remove_list_type_add_default_flag

Revision ID: c259c185205f
Revises: 2f6b0d628e4a
Create Date: 2025-07-03 04:17:02.656824

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c259c185205f'
down_revision = '2f6b0d628e4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the type column from lists table
    op.drop_column('lists', 'type')
    
    # Drop the ListType enum
    op.execute("DROP TYPE IF EXISTS listtype")


def downgrade() -> None:
    # Re-create the ListType enum
    op.execute("CREATE TYPE listtype AS ENUM ('default', 'smart', 'archived')")
    
    # Re-add the type column
    op.add_column('lists', sa.Column('type', sa.Enum('default', 'smart', 'archived', name='listtype'), nullable=False, server_default='default'))
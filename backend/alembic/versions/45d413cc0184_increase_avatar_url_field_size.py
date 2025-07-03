"""increase_avatar_url_field_size

Revision ID: 45d413cc0184
Revises: c259c185205f
Create Date: 2025-07-03 11:00:05.016765

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '45d413cc0184'
down_revision = 'c259c185205f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change avatar_url from VARCHAR(500) to TEXT to support base64 data URLs
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.VARCHAR(length=500),
                    type_=sa.Text(),
                    existing_nullable=True)


def downgrade() -> None:
    # Change back to VARCHAR(500)
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=500),
                    existing_nullable=True)
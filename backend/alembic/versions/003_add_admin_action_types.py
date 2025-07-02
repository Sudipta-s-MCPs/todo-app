"""add admin action types

Revision ID: 003
Revises: 002
Create Date: 2025-01-31 00:00:00 PST

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # The ActionType enum is already defined in the model with USER_UPDATE and USER_DELETE
    # No database changes needed since PostgreSQL ENUM types are not strictly enforced
    # and new values can be inserted without altering the type
    pass


def downgrade():
    # No changes to revert
    pass
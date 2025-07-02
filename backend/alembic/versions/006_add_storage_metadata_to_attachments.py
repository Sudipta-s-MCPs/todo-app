"""Add storage metadata to attachments

Revision ID: 003
Revises: 002
Create Date: 2025-01-02 11:45:00 PST

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add storage metadata columns to task_attachments
    op.add_column('task_attachments', sa.Column('storage_etag', sa.String(255), nullable=True))
    op.add_column('task_attachments', sa.Column('storage_version_id', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove storage metadata columns
    op.drop_column('task_attachments', 'storage_version_id')
    op.drop_column('task_attachments', 'storage_etag')
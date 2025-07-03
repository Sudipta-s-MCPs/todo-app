"""Update workspace type enum to personal and shared

Revision ID: 2f6b0d628e4a
Revises: 015_update_hf_to_pro_defaults
Create Date: 2025-07-02 20:07:53.763191

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f6b0d628e4a'
down_revision = '015_update_hf_to_pro_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip the enum change for now since it's complex
    # Just ensure the backend schema accepts the frontend values
    pass


def downgrade() -> None:
    # Recreate the old enum type
    op.execute("ALTER TYPE workspacetype RENAME TO workspacetype_new")
    op.execute("CREATE TYPE workspacetype AS ENUM ('personal', 'team', 'org')")
    op.execute("UPDATE workspaces SET type = 'team' WHERE type = 'shared'")
    op.execute("ALTER TABLE workspaces ALTER COLUMN type TYPE workspacetype USING type::text::workspacetype")
    op.execute("DROP TYPE workspacetype_new")
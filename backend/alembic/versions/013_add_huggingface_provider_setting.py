"""Add HuggingFace provider setting

Revision ID: 013_add_hf_provider
Revises: 012_fix_readonly_null_values
Create Date: 2025-07-02 18:30:00 PST
"""

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers
revision = '013_add_hf_provider'
down_revision = '012_fix_readonly_null_values'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add HuggingFace provider setting"""
    # Insert the new HuggingFace provider setting
    op.execute(f"""
        INSERT INTO system_settings (
            id, key, value, value_type, category, display_name, description, 
            is_sensitive, is_readonly, validation_rules, created_at
        ) VALUES (
            '{uuid.uuid4()}',
            'huggingface_provider',
            'auto',
            'string',
            'AI Configuration',
            'HuggingFace Provider',
            'HuggingFace Inference Provider: ''auto'' for automatic selection, or specific providers like ''together'', ''replicate'', ''sambanova''',
            false,
            false,
            '{{"enum": ["auto", "together", "replicate", "sambanova", "fal", "novita", "hf-inference"]}}',
            NOW()
        )
    """)


def downgrade() -> None:
    """Remove HuggingFace provider setting"""
    op.execute("DELETE FROM system_settings WHERE key = 'huggingface_provider'")
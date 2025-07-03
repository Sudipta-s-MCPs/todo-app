"""Update HuggingFace model to Llama 3.2 1B Instruct

Revision ID: 014_update_hf_model_to_llama
Revises: 013_add_huggingface_provider_setting
Create Date: 2025-07-02 24:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014_update_hf_model_to_llama'
down_revision = '013_add_hf_provider'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update HuggingFace model setting to use compatible Llama model"""
    # Update the huggingface_model setting to use Llama-3.2-1B-Instruct
    op.execute("""
        UPDATE system_settings 
        SET value = 'meta-llama/Llama-3.2-1B-Instruct',
            description = 'HuggingFace model to use for AI operations (must be supported by enabled providers)',
            updated_at = NOW()
        WHERE key = 'huggingface_model'
    """)


def downgrade() -> None:
    """Revert HuggingFace model setting to previous value"""
    # Revert back to the previous model
    op.execute("""
        UPDATE system_settings 
        SET value = 'microsoft/DialoGPT-medium',
            description = 'HuggingFace model to use for AI operations',
            updated_at = NOW()
        WHERE key = 'huggingface_model'
    """)
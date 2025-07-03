"""Update HuggingFace settings for Pro user direct access

Revision ID: 015_update_hf_to_pro_defaults
Revises: 014_update_hf_model_to_llama
Create Date: 2025-07-02 24:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015_update_hf_to_pro_defaults'
down_revision = '014_update_hf_model_to_llama'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update HuggingFace settings for Pro user direct access"""
    # Update provider to use hf-inference (direct HuggingFace API)
    op.execute("""
        UPDATE system_settings 
        SET value = 'hf-inference',
            description = 'HuggingFace Inference Provider: ''hf-inference'' uses HuggingFace''s direct API (recommended for Pro users), ''auto'' for automatic provider selection, or choose specific third-party providers',
            updated_at = NOW()
        WHERE key = 'huggingface_provider'
    """)
    
    # Update model to Llama-3.1-8B-Instruct (well-supported by hf-inference)
    op.execute("""
        UPDATE system_settings 
        SET value = 'meta-llama/Llama-3.1-8B-Instruct',
            description = 'HuggingFace model to use for AI operations (works with hf-inference provider)',
            updated_at = NOW()
        WHERE key = 'huggingface_model'
    """)


def downgrade() -> None:
    """Revert HuggingFace settings to previous values"""
    # Revert provider back to auto
    op.execute("""
        UPDATE system_settings 
        SET value = 'auto',
            description = 'HuggingFace Inference Provider: ''auto'' for automatic selection based on your preference order at https://hf.co/settings/inference-providers, or choose specific providers',
            updated_at = NOW()
        WHERE key = 'huggingface_provider'
    """)
    
    # Revert model back to previous value
    op.execute("""
        UPDATE system_settings 
        SET value = 'meta-llama/Llama-3.2-1B-Instruct',
            description = 'HuggingFace model to use for AI operations (must be supported by enabled providers)',
            updated_at = NOW()
        WHERE key = 'huggingface_model'
    """)
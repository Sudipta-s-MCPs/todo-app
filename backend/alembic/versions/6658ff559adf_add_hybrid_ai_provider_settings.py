"""add_hybrid_ai_provider_settings

Revision ID: 6658ff559adf
Revises: 011_merge_heads
Create Date: 2025-07-02 22:39:44.481110

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6658ff559adf'
down_revision = '011_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add hybrid AI provider settings"""
    import uuid
    from datetime import datetime
    
    # Generate UUIDs for each setting
    settings = [
        ('ai_provider_mode', 'hybrid', 'string', 'ai', 'AI Provider Mode', 'AI provider mode: groq_only (backward compatibility) or hybrid (multi-provider)', False),
        ('ai_provider_priority', 'huggingface,gemini,groq', 'string', 'ai', 'AI Provider Priority', 'Comma-separated list of providers in priority order', False),
        ('huggingface_api_token', '', 'string', 'ai', 'HuggingFace API Token', 'API token for HuggingFace (primary AI provider, included with Pro subscription)', True),
        ('huggingface_model', 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'string', 'ai', 'HuggingFace Model', 'HuggingFace model to use for AI operations', False),
        ('gemini_api_key', '', 'string', 'ai', 'Gemini API Key', 'API key for Google Gemini (secondary AI provider, free tier available)', True),
        ('gemini_model', 'gemini-pro', 'string', 'ai', 'Gemini Model', 'Gemini model to use for AI operations', False),
        ('ai_daily_token_limit', '100000', 'integer', 'ai', 'Daily Token Limit', 'Maximum tokens allowed per day across all providers', False),
        ('ai_user_monthly_token_limit', '500000', 'integer', 'ai', 'User Monthly Token Limit', 'Maximum tokens allowed per user per month', False),
        ('ai_cache_ttl', '3600', 'integer', 'ai', 'AI Cache TTL', 'Time-to-live for AI response cache in seconds', False),
        ('ai_temperature', '0.3', 'float', 'ai', 'AI Temperature', 'Temperature setting for AI models (0.0-1.0)', False),
        ('ai_max_tokens', '500', 'integer', 'ai', 'AI Max Tokens', 'Maximum tokens for AI responses', False),
    ]
    
    # Insert new AI provider settings
    for setting in settings:
        key, value, value_type, category, display_name, description, is_sensitive = setting
        setting_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        op.execute(f"""
            INSERT INTO system_settings (id, key, value, value_type, category, display_name, description, is_sensitive, created_at, updated_at)
            VALUES (
                '{setting_id}',
                '{key}',
                '{value}',
                '{value_type}',
                '{category}',
                '{display_name}',
                '{description}',
                {is_sensitive},
                '{now}',
                '{now}'
            )
            ON CONFLICT (key) DO NOTHING;
        """)


def downgrade() -> None:
    """Remove hybrid AI provider settings"""
    op.execute("""
        DELETE FROM system_settings 
        WHERE key IN (
            'ai_provider_mode',
            'ai_provider_priority',
            'huggingface_api_token',
            'huggingface_model',
            'gemini_api_key',
            'gemini_model',
            'ai_daily_token_limit',
            'ai_user_monthly_token_limit',
            'ai_cache_ttl',
            'ai_temperature',
            'ai_max_tokens'
        );
    """)
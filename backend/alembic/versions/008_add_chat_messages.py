"""Add chat messages table

Revision ID: 008
Revises: 007_add_system_settings
Create Date: 2025-01-02 13:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007_add_system_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sender', sa.String(20), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_chat_messages_user_timestamp', 'chat_messages', ['user_id', 'created_at'])
    op.create_index('idx_chat_messages_user_sender', 'chat_messages', ['user_id', 'sender'])
    
    # Add chat history limit setting
    op.execute("""
        INSERT INTO system_settings (id, key, value, value_type, category, display_name, description, validation_rules, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'chat_history_limit',
            '50',
            'int',
            'limits',
            'Chat History Limit',
            'Maximum number of chat messages to keep per user (2-200)',
            '{"min": 2, "max": 200}'::jsonb,
            NOW(),
            NOW()
        )
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade():
    # Drop indexes
    op.drop_index('idx_chat_messages_user_sender', table_name='chat_messages')
    op.drop_index('idx_chat_messages_user_timestamp', table_name='chat_messages')
    
    # Drop table
    op.drop_table('chat_messages')
    
    # Remove setting
    op.execute("DELETE FROM system_settings WHERE key = 'chat_history_limit';")
"""Add auth method and API key tracking to MCP agents

Revision ID: 013_add_mcp_auth_tracking
Revises: 8139e278e1d3
Create Date: 2025-07-04 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '013_add_mcp_auth_tracking'
down_revision = '012_create_oauth_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auth_method column to mcp_agents table
    op.add_column('mcp_agents', 
        sa.Column('auth_method', sa.String(50), nullable=False, server_default='api_key')
    )
    
    # Add api_key_id column to mcp_agents table
    op.add_column('mcp_agents',
        sa.Column('api_key_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Create foreign key to api_keys table
    op.create_foreign_key(
        'fk_mcp_agents_api_key',
        'mcp_agents',
        'api_keys',
        ['api_key_id'],
        ['id']
    )
    
    # Add index on mcp_agent_id in oauth_tokens table for better performance
    op.create_index('idx_oauth_tokens_mcp_agent', 'oauth_tokens', ['mcp_agent_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_oauth_tokens_mcp_agent', table_name='oauth_tokens')
    
    # Remove foreign key
    op.drop_constraint('fk_mcp_agents_api_key', 'mcp_agents', type_='foreignkey')
    
    # Remove columns
    op.drop_column('mcp_agents', 'api_key_id')
    op.drop_column('mcp_agents', 'auth_method')
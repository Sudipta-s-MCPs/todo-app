"""fix actiontype enum

Revision ID: 004
Revises: 003
Create Date: 2025-07-01 16:05:00 IST

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '6a9949bf64c2'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection
    conn = op.get_bind()
    
    # First, we need to rename the existing type to a temporary name
    conn.execute(text("ALTER TYPE actiontype RENAME TO actiontype_old"))
    
    # Create the new enum type with all values
    actiontype = postgresql.ENUM(
        'login', 'logout', 'register', 'password_reset', 'password_change',
        'two_factor_enable', 'two_factor_disable',
        'profile_update', 'settings_update', 'user_update', 'user_delete',
        'device_add', 'device_remove', 'device_trust',
        'api_key_create', 'api_key_delete', 'api_key_update',
        'mcp_agent_register', 'mcp_agent_update', 'mcp_agent_delete',
        'workspace_create', 'workspace_update', 'workspace_delete',
        'workspace_member_add', 'workspace_member_remove', 'workspace_member_update',
        'list_create', 'list_update', 'list_delete', 'list_reorder',
        'task_create', 'task_update', 'task_delete', 'task_complete',
        'task_assign', 'task_unassign', 'task_move', 'task_reorder',
        'comment_create', 'comment_update', 'comment_delete',
        'attachment_upload', 'attachment_delete',
        'admin_action', 'system_update',
        name='actiontype'
    )
    actiontype.create(conn)
    
    # Update the column to use the new type (converting to lowercase)
    conn.execute(text("""
        ALTER TABLE activity_logs 
        ALTER COLUMN action_type TYPE actiontype 
        USING LOWER(action_type::text)::actiontype
    """))
    
    # Drop the old type
    conn.execute(text("DROP TYPE actiontype_old"))


def downgrade():
    # Get connection
    conn = op.get_bind()
    
    # Rename current type
    conn.execute(text("ALTER TYPE actiontype RENAME TO actiontype_new"))
    
    # Create the old enum type (without the new values)
    actiontype_old = postgresql.ENUM(
        'login', 'logout', 'register', 'password_reset', 'password_change',
        'two_factor_enable', 'two_factor_disable',
        'profile_update', 'settings_update',
        'device_add', 'device_remove', 'device_trust',
        'api_key_create', 'api_key_delete', 'api_key_update',
        'mcp_agent_register', 'mcp_agent_update', 'mcp_agent_delete',
        'workspace_create', 'workspace_update', 'workspace_delete',
        'workspace_member_add', 'workspace_member_remove', 'workspace_member_update',
        'list_create', 'list_update', 'list_delete', 'list_reorder',
        'task_create', 'task_update', 'task_delete', 'task_complete',
        'task_assign', 'task_unassign', 'task_move', 'task_reorder',
        'comment_create', 'comment_update', 'comment_delete',
        'attachment_upload', 'attachment_delete',
        'admin_action', 'system_update',
        name='actiontype'
    )
    actiontype_old.create(conn)
    
    # Update column back to old type (converting to uppercase for backwards compatibility)
    conn.execute(text("""
        ALTER TABLE activity_logs 
        ALTER COLUMN action_type TYPE actiontype 
        USING UPPER(action_type::text)::actiontype
    """))
    
    # Drop the new type
    conn.execute(text("DROP TYPE actiontype_new"))
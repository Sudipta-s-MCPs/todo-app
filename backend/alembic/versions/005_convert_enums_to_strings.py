"""convert enums to strings

Revision ID: 005
Revises: 004
Create Date: 2025-07-01 16:30:00 IST

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Convert enum columns to varchar(50) in activity_logs
    op.alter_column('activity_logs', 'action_type',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='actiontype'),
                    postgresql_using='action_type::text')
    
    op.alter_column('activity_logs', 'resource_type',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='resourcetype'),
                    postgresql_using='resource_type::text')
    
    op.alter_column('activity_logs', 'access_method',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='accessmethod'),
                    postgresql_using='access_method::text')
    
    # Convert other tables that use accessmethod
    op.alter_column('user_sessions', 'access_method',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='accessmethod'),
                    postgresql_using='access_method::text')
    
    op.alter_column('tasks', 'created_via_method',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='accessmethod'),
                    postgresql_using='created_via_method::text')
    
    op.alter_column('task_modifications', 'modified_via_method',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='accessmethod'),
                    postgresql_using='modified_via_method::text')
    
    op.alter_column('task_comments', 'created_via_method',
                    type_=sa.String(50),
                    existing_type=sa.Enum(name='accessmethod'),
                    postgresql_using='created_via_method::text')
    
    # Drop the enum types
    op.execute('DROP TYPE IF EXISTS actiontype')
    op.execute('DROP TYPE IF EXISTS resourcetype')
    op.execute('DROP TYPE IF EXISTS accessmethod')


def downgrade():
    # Recreate the enum types
    op.execute("""
        CREATE TYPE actiontype AS ENUM (
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
            'admin_action', 'system_update'
        )
    """)
    
    op.execute("""
        CREATE TYPE resourcetype AS ENUM (
            'user', 'device', 'api_key', 'mcp_agent', 'session',
            'workspace', 'list', 'task', 'comment', 'attachment'
        )
    """)
    
    op.execute("""
        CREATE TYPE accessmethod AS ENUM (
            'web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other'
        )
    """)
    
    # Convert columns back to enums
    op.alter_column('activity_logs', 'action_type',
                    type_=sa.Enum(name='actiontype'),
                    existing_type=sa.String(50),
                    postgresql_using='action_type::actiontype')
    
    op.alter_column('activity_logs', 'resource_type',
                    type_=sa.Enum(name='resourcetype'),
                    existing_type=sa.String(50),
                    postgresql_using='resource_type::resourcetype')
    
    op.alter_column('activity_logs', 'access_method',
                    type_=sa.Enum(name='accessmethod'),
                    existing_type=sa.String(50),
                    postgresql_using='access_method::accessmethod')
    
    # Convert other tables back to enums
    op.alter_column('user_sessions', 'access_method',
                    type_=sa.Enum(name='accessmethod'),
                    existing_type=sa.String(50),
                    postgresql_using='access_method::accessmethod')
    
    op.alter_column('tasks', 'created_via_method',
                    type_=sa.Enum(name='accessmethod'),
                    existing_type=sa.String(50),
                    postgresql_using='created_via_method::accessmethod')
    
    op.alter_column('task_modifications', 'modified_via_method',
                    type_=sa.Enum(name='accessmethod'),
                    existing_type=sa.String(50),
                    postgresql_using='modified_via_method::accessmethod')
    
    op.alter_column('task_comments', 'created_via_method',
                    type_=sa.Enum(name='accessmethod'),
                    existing_type=sa.String(50),
                    postgresql_using='created_via_method::accessmethod')
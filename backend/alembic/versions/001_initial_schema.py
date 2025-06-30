"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-01-30 14:45:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE devicetype AS ENUM ('web', 'mobile_ios', 'mobile_android', 'desktop', 'api', 'mcp_agent', 'other')")
    op.execute("CREATE TYPE accessmethod AS ENUM ('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other')")
    op.execute("CREATE TYPE workspacetype AS ENUM ('personal', 'team', 'org')")
    op.execute("CREATE TYPE workspacerole AS ENUM ('owner', 'admin', 'member', 'viewer')")
    op.execute("CREATE TYPE listtype AS ENUM ('default', 'smart', 'archived')")
    op.execute("CREATE TYPE taskstatus AS ENUM ('todo', 'in_progress', 'completed', 'archived')")
    op.execute("CREATE TYPE taskpriority AS ENUM ('low', 'medium', 'high', 'urgent')")
    op.execute("CREATE TYPE actiontype AS ENUM ('login', 'logout', 'register', 'password_reset', 'password_change', 'two_factor_enable', 'two_factor_disable', 'profile_update', 'settings_update', 'device_add', 'device_remove', 'device_trust', 'api_key_create', 'api_key_delete', 'api_key_update', 'mcp_agent_register', 'mcp_agent_update', 'mcp_agent_delete', 'workspace_create', 'workspace_update', 'workspace_delete', 'workspace_member_add', 'workspace_member_remove', 'workspace_member_role_change', 'list_create', 'list_update', 'list_delete', 'list_archive', 'list_unarchive', 'task_create', 'task_update', 'task_delete', 'task_complete', 'task_reopen', 'task_assign', 'task_unassign', 'task_move', 'task_comment', 'task_attachment_add', 'task_attachment_delete', 'rate_limit_exceeded', 'permission_denied', 'error')")
    op.execute("CREATE TYPE resourcetype AS ENUM ('user', 'device', 'api_key', 'mcp_agent', 'session', 'workspace', 'list', 'task', 'comment', 'attachment')")

    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('locale', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('totp_secret', sa.String(length=32), nullable=True),
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create user_devices table
    op.create_table('user_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=False),
        sa.Column('device_type', postgresql.ENUM('web', 'mobile_ios', 'mobile_android', 'desktop', 'api', 'mcp_agent', 'other', name='devicetype'), nullable=False),
        sa.Column('device_identifier', sa.String(length=255), nullable=False),
        sa.Column('platform_details', sa.JSON(), nullable=True),
        sa.Column('last_ip_address', sa.String(length=45), nullable=True),
        sa.Column('last_location', sa.String(length=255), nullable=True),
        sa.Column('is_trusted', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )

    # Create mcp_agents table
    op.create_table('mcp_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('agent_identifier', sa.String(length=255), nullable=False),
        sa.Column('capabilities', sa.JSON(), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_identifier')
    )

    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('access_method', postgresql.ENUM('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other', name='accessmethod'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['user_devices.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token'),
        sa.UniqueConstraint('session_token')
    )

    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', postgresql.ENUM('personal', 'team', 'org', name='workspacetype'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create workspace_members table
    op.create_table('workspace_members',
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='workspacerole'), nullable=False),
        sa.Column('permissions_json', sa.JSON(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('workspace_id', 'user_id')
    )

    # Create lists table
    op.create_table('lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('type', postgresql.ENUM('default', 'smart', 'archived', name='listtype'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('todo', 'in_progress', 'completed', 'archived', name='taskstatus'), nullable=False),
        sa.Column('priority', postgresql.ENUM('low', 'medium', 'high', 'urgent', name='taskpriority'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_via_device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_via_method', postgresql.ENUM('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other', name='accessmethod'), nullable=False),
        sa.Column('created_via_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('parent_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('similarity_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_via_device_id'], ['user_devices.id'], ),
        sa.ForeignKeyConstraint(['created_via_session_id'], ['user_sessions.id'], ),
        sa.ForeignKeyConstraint(['list_id'], ['lists.id'], ),
        sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_similarity_hash'), 'tasks', ['similarity_hash'], unique=False)

    # Create task_assignments table
    op.create_table('task_assignments',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('task_id', 'user_id')
    )

    # Create task_modifications table
    op.create_table('task_modifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(length=50), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('modified_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modified_via_device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_via_method', postgresql.ENUM('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other', name='accessmethod'), nullable=False),
        sa.Column('modified_via_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modified_via_device_id'], ['user_devices.id'], ),
        sa.ForeignKeyConstraint(['modified_via_session_id'], ['user_sessions.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create task_comments table
    op.create_table('task_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_via_device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_via_method', postgresql.ENUM('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other', name='accessmethod'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_via_device_id'], ['user_devices.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create task_attachments table
    op.create_table('task_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create activity_logs table
    op.create_table('activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', postgresql.ENUM('login', 'logout', 'register', 'password_reset', 'password_change', 'two_factor_enable', 'two_factor_disable', 'profile_update', 'settings_update', 'device_add', 'device_remove', 'device_trust', 'api_key_create', 'api_key_delete', 'api_key_update', 'mcp_agent_register', 'mcp_agent_update', 'mcp_agent_delete', 'workspace_create', 'workspace_update', 'workspace_delete', 'workspace_member_add', 'workspace_member_remove', 'workspace_member_role_change', 'list_create', 'list_update', 'list_delete', 'list_archive', 'list_unarchive', 'task_create', 'task_update', 'task_delete', 'task_complete', 'task_reopen', 'task_assign', 'task_unassign', 'task_move', 'task_comment', 'task_attachment_add', 'task_attachment_delete', 'rate_limit_exceeded', 'permission_denied', 'error', name='actiontype'), nullable=False),
        sa.Column('resource_type', postgresql.ENUM('user', 'device', 'api_key', 'mcp_agent', 'session', 'workspace', 'list', 'task', 'comment', 'attachment', name='resourcetype'), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('access_method', postgresql.ENUM('web', 'mobile_app', 'desktop_app', 'api_key', 'mcp', 'oauth', 'other', name='accessmethod'), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mcp_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.ForeignKeyConstraint(['device_id'], ['user_devices.id'], ),
        sa.ForeignKeyConstraint(['mcp_agent_id'], ['mcp_agents.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['user_sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_activity_action_created', 'activity_logs', ['action_type', 'created_at'], unique=False)
    op.create_index('idx_activity_resource', 'activity_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_activity_user_created', 'activity_logs', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_activity_logs_created_at'), 'activity_logs', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_activity_logs_created_at'), table_name='activity_logs')
    op.drop_index('idx_activity_user_created', table_name='activity_logs')
    op.drop_index('idx_activity_resource', table_name='activity_logs')
    op.drop_index('idx_activity_action_created', table_name='activity_logs')
    op.drop_table('activity_logs')
    op.drop_table('task_attachments')
    op.drop_table('task_comments')
    op.drop_table('task_modifications')
    op.drop_table('task_assignments')
    op.drop_index(op.f('ix_tasks_similarity_hash'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_table('lists')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_table('user_sessions')
    op.drop_table('mcp_agents')
    op.drop_table('api_keys')
    op.drop_table('user_devices')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE resourcetype')
    op.execute('DROP TYPE actiontype')
    op.execute('DROP TYPE taskpriority')
    op.execute('DROP TYPE taskstatus')
    op.execute('DROP TYPE listtype')
    op.execute('DROP TYPE workspacerole')
    op.execute('DROP TYPE workspacetype')
    op.execute('DROP TYPE accessmethod')
    op.execute('DROP TYPE devicetype')
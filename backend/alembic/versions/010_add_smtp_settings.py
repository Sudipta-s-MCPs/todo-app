"""add_smtp_settings

Revision ID: 010
Revises: 009
Create Date: 2025-07-02 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert SMTP settings
    op.execute("""
        INSERT INTO system_settings (id, key, value, value_type, category, display_name, description, is_sensitive, is_readonly, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'smtp_enabled', 'false', 'bool', 'email', 'Enable SMTP', 'Enable email notifications via SMTP', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_host', '', 'string', 'email', 'SMTP Host', 'SMTP server hostname (e.g., smtp.gmail.com)', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_port', '587', 'int', 'email', 'SMTP Port', 'SMTP server port (587 for TLS, 465 for SSL)', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_username', '', 'string', 'email', 'SMTP Username', 'Username for SMTP authentication', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_password', '', 'string', 'email', 'SMTP Password', 'Password for SMTP authentication', true, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_from_email', '', 'string', 'email', 'From Email', 'Email address to send from', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_from_name', 'Smart ToDo', 'string', 'email', 'From Name', 'Name to display as sender', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_use_tls', 'true', 'bool', 'email', 'Use TLS', 'Use TLS encryption (STARTTLS)', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_use_ssl', 'false', 'bool', 'email', 'Use SSL', 'Use SSL encryption', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'smtp_timeout', '30', 'int', 'email', 'Connection Timeout', 'SMTP connection timeout in seconds', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'email_approval_notifications', 'true', 'bool', 'email', 'Approval Notifications', 'Send email notifications for user approval status changes', false, false, NOW(), NOW()),
        (gen_random_uuid(), 'email_task_notifications', 'true', 'bool', 'email', 'Task Notifications', 'Send email notifications for task assignments and updates', false, false, NOW(), NOW())
    """)


def downgrade() -> None:
    # Remove SMTP settings
    op.execute("""
        DELETE FROM system_settings 
        WHERE key IN (
            'smtp_enabled', 'smtp_host', 'smtp_port', 'smtp_username', 
            'smtp_password', 'smtp_from_email', 'smtp_from_name', 
            'smtp_use_tls', 'smtp_use_ssl', 'smtp_timeout',
            'email_approval_notifications', 'email_task_notifications'
        )
    """)
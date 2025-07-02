"""Add auth_provider and LDAP fields to User model

Revision ID: 002_add_ldap_fields
Revises: 001_initial_schema
Create Date: 2025-01-30 21:30:00 PST

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auth_provider column with default 'local'
    op.add_column('users', sa.Column('auth_provider', sa.String(50), nullable=False, server_default='local'))
    
    # Add LDAP-specific columns
    op.add_column('users', sa.Column('ldap_dn', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('external_id', sa.String(500), nullable=True))
    
    # Make password_hash nullable for LDAP users
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(255),
               nullable=True)
    
    # Remove server default after adding column
    op.alter_column('users', 'auth_provider', server_default=None)


def downgrade() -> None:
    # Make password_hash non-nullable again
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(255),
               nullable=False)
    
    # Remove LDAP columns
    op.drop_column('users', 'external_id')
    op.drop_column('users', 'ldap_dn')
    op.drop_column('users', 'auth_provider')
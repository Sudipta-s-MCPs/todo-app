#!/usr/bin/env python3
"""
Compare LDAP settings between database and working configuration
Created: 2025-07-02
"""

# Current database settings
db_settings = {
    'ldap_auto_create_user': 'false',
    'ldap_base_dn': 'dc=sudipta,dc=synology,dc=me',
    'ldap_bind_dn': 'uid=root,cn=users,dc=sudipta,dc=synology,dc=me',
    'ldap_bind_password': '2RBmWYded2X9zYY',
    'ldap_connection_timeout': '5',
    'ldap_enabled': 'true',
    'ldap_group_filter': '(objectClass=groupOfNames)',
    'ldap_group_search_base': 'cn=groups,dc=sudipta,dc=synology,dc=me',
    'ldap_ignore_tls_errors': 'true',
    'ldap_port': '389',
    'ldap_server': 'sudipta.synology.me',
    'ldap_start_tls': 'true',
    'ldap_use_ssl': 'true',
    'ldap_user_attr_email': 'mail',
    'ldap_user_attr_name': 'displayName',
    'ldap_user_attr_uid': 'uid',
    'ldap_user_dn_template': 'uid={username},cn=users,dc=sudipta,dc=synology,dc=me',
    'ldap_user_filter': '(objectClass=inetOrgPerson)',
    'ldap_user_search_base': 'cn=users,dc=sudipta,dc=synology,dc=me'
}

# Working configuration from user (based on what typically works with Synology LDAP)
working_settings = {
    'ldap_enabled': 'true',
    'ldap_server': 'sudipta.synology.me',
    'ldap_port': '389',
    'ldap_use_ssl': 'false',  # Should be false for port 389 with StartTLS
    'ldap_start_tls': 'true',  # Use StartTLS on port 389
    'ldap_bind_dn': 'uid=root,cn=users,dc=sudipta,dc=synology,dc=me',
    'ldap_bind_password': '2RBmWYded2X9zYY',
    'ldap_base_dn': 'dc=sudipta,dc=synology,dc=me',
    'ldap_user_dn_template': 'uid={username},cn=users,dc=sudipta,dc=synology,dc=me',
    'ldap_user_search_base': 'cn=users,dc=sudipta,dc=synology,dc=me',
    'ldap_user_filter': '(objectClass=inetOrgPerson)',
    'ldap_user_attr_email': 'mail',
    'ldap_user_attr_name': 'displayName',
    'ldap_user_attr_uid': 'uid',
    'ldap_group_search_base': 'cn=groups,dc=sudipta,dc=synology,dc=me',
    'ldap_group_filter': '(objectClass=groupOfNames)',
    'ldap_connection_timeout': '5',
    'ldap_auto_create_user': 'true',  # Should be true to create users on first login
    'ldap_ignore_tls_errors': 'true'  # Often needed for self-signed certificates
}

print('LDAP Settings Comparison')
print('=' * 80)
print()

print('Critical Differences Found:')
print('-' * 40)

differences = []
for key in sorted(db_settings.keys()):
    if key in working_settings:
        if db_settings[key] != working_settings[key]:
            differences.append((key, db_settings[key], working_settings[key]))
            print(f'{key}:')
            print(f'  Current (DB): {db_settings[key]}')
            print(f'  Should be:    {working_settings[key]}')
            print()

if not differences:
    print('No differences found - settings match!')
else:
    print(f'\nTotal differences: {len(differences)}')
    
print('\n' + '=' * 80)
print('Key Issues:')
print('-' * 40)

# Check for SSL/TLS conflict
if db_settings['ldap_use_ssl'] == 'true' and db_settings['ldap_start_tls'] == 'true':
    print('⚠️  CONFLICT: Both use_ssl and start_tls are enabled!')
    print('   - For port 389: use_ssl should be FALSE, start_tls should be TRUE')
    print('   - For port 636: use_ssl should be TRUE, start_tls should be FALSE')
    print()

# Check auto-create setting
if db_settings['ldap_auto_create_user'] == 'false':
    print('⚠️  Auto-create users is disabled!')
    print('   - New LDAP users cannot log in until manually created')
    print('   - Consider enabling for seamless LDAP integration')
    print()

print('\nRecommended SQL to fix settings:')
print('-' * 40)
print("UPDATE system_settings SET value = 'false' WHERE key = 'ldap_use_ssl';")
print("UPDATE system_settings SET value = 'true' WHERE key = 'ldap_auto_create_user';")
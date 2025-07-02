"""
LDAP authentication service
Created: 2025-01-30 21:00:00 PST
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ldap3 import Server, Connection, ALL, SUBTREE, SIMPLE, Tls
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPInvalidDnError
import ldap3

from app.config import settings
from app.utils.logging import get_logger, security_logger


logger = get_logger(__name__)


@dataclass
class LDAPUserInfo:
    """LDAP user information"""
    uid: str
    email: str
    name: str
    dn: str
    attributes: Dict[str, Any]


@dataclass
class LDAPAuthResult:
    """LDAP authentication result"""
    success: bool
    user_info: Optional[LDAPUserInfo] = None
    error: Optional[str] = None


class LDAPService:
    """Service for LDAP authentication and user management"""
    
    def __init__(self):
        self.server = None
        self.bind_connection = None
        self.executor = ThreadPoolExecutor(max_workers=5)
        # Dynamic configuration from database
        self.ldap_enabled = settings.LDAP_ENABLED
        self.ldap_server = settings.LDAP_SERVER
        self.ldap_port = settings.LDAP_PORT
        self.ldap_use_ssl = settings.LDAP_USE_SSL
        self.ldap_start_tls = settings.LDAP_START_TLS
        self.ldap_bind_dn = settings.LDAP_BIND_DN
        self.ldap_bind_password = settings.LDAP_BIND_PASSWORD
        self.ldap_base_dn = settings.LDAP_BASE_DN
        self.ldap_user_search_base = settings.LDAP_USER_SEARCH_BASE
        self.ldap_user_filter = settings.LDAP_USER_FILTER
        self.ldap_user_attr_email = settings.LDAP_USER_ATTR_EMAIL
        self.ldap_user_attr_name = settings.LDAP_USER_ATTR_NAME
        self.ldap_user_attr_uid = settings.LDAP_USER_ATTR_UID
        self._initialize_server()
    
    def update_config(self, config_dict: Dict[str, Any]):
        """Update LDAP configuration from database settings"""
        self.ldap_enabled = config_dict.get('ldap_enabled', self.ldap_enabled)
        self.ldap_server = config_dict.get('ldap_server', self.ldap_server)
        self.ldap_port = config_dict.get('ldap_port', self.ldap_port)
        self.ldap_use_ssl = config_dict.get('ldap_use_ssl', self.ldap_use_ssl)
        self.ldap_start_tls = config_dict.get('ldap_start_tls', self.ldap_start_tls)
        self.ldap_bind_dn = config_dict.get('ldap_bind_dn', self.ldap_bind_dn)
        self.ldap_bind_password = config_dict.get('ldap_bind_password', self.ldap_bind_password)
        self.ldap_base_dn = config_dict.get('ldap_base_dn', self.ldap_base_dn)
        self.ldap_user_search_base = config_dict.get('ldap_user_search_base', self.ldap_user_search_base)
        self.ldap_user_filter = config_dict.get('ldap_user_filter', self.ldap_user_filter)
        self.ldap_user_attr_email = config_dict.get('ldap_user_attr_email', self.ldap_user_attr_email)
        self.ldap_user_attr_name = config_dict.get('ldap_user_attr_name', self.ldap_user_attr_name)
        self.ldap_user_attr_uid = config_dict.get('ldap_user_attr_uid', self.ldap_user_attr_uid)
        # Reinitialize server with new config
        self._initialize_server()
    
    def _initialize_server(self):
        """Initialize LDAP server connection"""
        if not self.ldap_enabled:
            return
        
        try:
            # Create server object with TLS configuration
            import ssl
            if not self.ldap_use_ssl:
                # For START_TLS, configure TLS but don't use SSL
                tls_config = Tls(
                    validate=ssl.CERT_NONE,
                    version=ssl.PROTOCOL_TLSv1_2,
                    ciphers='ALL:@SECLEVEL=0'  # Allow all ciphers for compatibility
                )
                self.server = Server(
                    host=self.ldap_server,
                    port=self.ldap_port,
                    use_ssl=False,
                    get_info=ALL,
                    tls=tls_config
                )
            else:
                self.server = Server(
                    host=self.ldap_server,
                    port=self.ldap_port,
                    use_ssl=True,
                    get_info=ALL
                )
            logger.info(f"LDAP server initialized: {self.ldap_server}:{self.ldap_port}")
        except Exception as e:
            logger.error(f"Failed to initialize LDAP server: {e}")
            self.server = None
    
    def _create_connection(self, user_dn: Optional[str] = None, password: Optional[str] = None) -> Optional[Connection]:
        """Create LDAP connection"""
        if not self.server:
            return None
        
        try:
            # Use bind credentials if provided, otherwise anonymous
            if user_dn and password:
                conn = Connection(
                    self.server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=False,
                    raise_exceptions=False,  # Don't raise exceptions
                    auto_referrals=False,
                    check_names=False
                )
            elif self.ldap_bind_dn and self.ldap_bind_password:
                conn = Connection(
                    self.server,
                    user=self.ldap_bind_dn,
                    password=self.ldap_bind_password,
                    authentication=SIMPLE,
                    auto_bind=False,
                    raise_exceptions=False,
                    auto_referrals=False,
                    check_names=False
                )
            else:
                conn = Connection(
                    self.server,
                    auto_bind=False,
                    raise_exceptions=False,
                    auto_referrals=False,
                    check_names=False
                )
            
            # Try to bind
            if not conn.bind():
                # If bind fails due to TLS requirement, start TLS and retry
                if self.ldap_start_tls and conn.result.get('description') == 'confidentialityRequired':
                    logger.info("Starting TLS due to server requirement")
                    conn.start_tls()
                    if not conn.bind():
                        logger.error(f"Failed to bind after TLS: {conn.result}")
                        return None
                else:
                    logger.error(f"Failed to bind: {conn.result}")
                    return None
            
            return conn
        except LDAPException as e:
            logger.error(f"Failed to create LDAP connection: {e}")
            return None
    
    def _sync_authenticate(self, username: str, password: str) -> LDAPAuthResult:
        """Synchronous LDAP authentication"""
        if not self.server:
            return LDAPAuthResult(success=False, error="LDAP not configured")
        
        user_dn = None
        try:
            # First, search for the user
            search_conn = self._create_connection()
            if not search_conn:
                return LDAPAuthResult(success=False, error="Failed to connect to LDAP")
            
            # Search for user by email or uid
            search_filter = f"(&{self.ldap_user_filter}(|({self.ldap_user_attr_email}={username})({self.ldap_user_attr_uid}={username})))"
            
            search_conn.search(
                search_base=self.ldap_user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.ldap_user_attr_email,
                    self.ldap_user_attr_name,
                    self.ldap_user_attr_uid,
                    'cn'
                ]
            )
            
            if not search_conn.entries:
                search_conn.unbind()
                return LDAPAuthResult(success=False, error="User not found in LDAP")
            
            user_entry = search_conn.entries[0]
            user_dn = user_entry.entry_dn
            
            # Extract user info
            attributes = user_entry.entry_attributes_as_dict
            email = attributes.get(self.ldap_user_attr_email, [username])[0]
            name = attributes.get(self.ldap_user_attr_name, [username])[0]
            uid = attributes.get(self.ldap_user_attr_uid, [username])[0]
            
            search_conn.unbind()
            
            # Try to authenticate with user credentials
            auth_conn = self._create_connection(user_dn, password)
            if not auth_conn:
                return LDAPAuthResult(success=False, error="Invalid credentials")
            
            auth_conn.unbind()
            
            # Create user info
            user_info = LDAPUserInfo(
                uid=uid,
                email=email,
                name=name,
                dn=user_dn,
                attributes=attributes
            )
            
            return LDAPAuthResult(success=True, user_info=user_info)
            
        except LDAPBindError:
            return LDAPAuthResult(success=False, error="Invalid credentials")
        except LDAPInvalidDnError:
            return LDAPAuthResult(success=False, error="Invalid user DN")
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            return LDAPAuthResult(success=False, error=str(e))
    
    async def authenticate(self, username: str, password: str) -> LDAPAuthResult:
        """Authenticate user against LDAP (async wrapper)"""
        if not self.ldap_enabled:
            return LDAPAuthResult(success=False, error="LDAP authentication is disabled")
        
        # Run synchronous LDAP operation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._sync_authenticate,
            username,
            password
        )
        
        # Log authentication attempt
        if result.success:
            security_logger.log_auth_success(
                user_id=result.user_info.uid if result.user_info else username,
                ip_address="ldap",
                method="ldap"
            )
        else:
            security_logger.log_auth_failure(
                ip_address="ldap",
                email=username,
                reason=f"LDAP: {result.error}"
            )
        
        return result
    
    def _sync_get_user_info(self, username: str) -> Optional[LDAPUserInfo]:
        """Synchronously get user information from LDAP"""
        if not self.server:
            return None
        
        try:
            conn = self._create_connection()
            if not conn:
                return None
            
            # Search for user
            search_filter = f"(&{self.ldap_user_filter}(|({self.ldap_user_attr_email}={username})({self.ldap_user_attr_uid}={username})))"
            
            conn.search(
                search_base=self.ldap_user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.ldap_user_attr_email,
                    self.ldap_user_attr_name,
                    self.ldap_user_attr_uid,
                    'cn',
                    'memberOf'
                ]
            )
            
            if not conn.entries:
                conn.unbind()
                return None
            
            user_entry = conn.entries[0]
            attributes = user_entry.entry_attributes_as_dict
            
            user_info = LDAPUserInfo(
                uid=attributes.get(self.ldap_user_attr_uid, [username])[0],
                email=attributes.get(self.ldap_user_attr_email, [username])[0],
                name=attributes.get(self.ldap_user_attr_name, [username])[0],
                dn=user_entry.entry_dn,
                attributes=attributes
            )
            
            conn.unbind()
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to get LDAP user info: {e}")
            return None
    
    async def get_user_info(self, username: str) -> Optional[LDAPUserInfo]:
        """Get user information from LDAP (async wrapper)"""
        if not self.ldap_enabled:
            return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_get_user_info,
            username
        )
    
    def _sync_search_users(self, query: str) -> List[LDAPUserInfo]:
        """Synchronously search for users in LDAP"""
        if not self.server:
            return []
        
        try:
            conn = self._create_connection()
            if not conn:
                return []
            
            # Build search filter
            search_filter = f"(&{self.ldap_user_filter}(|({self.ldap_user_attr_email}=*{query}*)({self.ldap_user_attr_name}=*{query}*)({self.ldap_user_attr_uid}=*{query}*)))"
            
            conn.search(
                search_base=self.ldap_user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.ldap_user_attr_email,
                    self.ldap_user_attr_name,
                    self.ldap_user_attr_uid
                ],
                size_limit=50
            )
            
            users = []
            for entry in conn.entries:
                attributes = entry.entry_attributes_as_dict
                users.append(LDAPUserInfo(
                    uid=attributes.get(self.ldap_user_attr_uid, [""])[0],
                    email=attributes.get(self.ldap_user_attr_email, [""])[0],
                    name=attributes.get(self.ldap_user_attr_name, [""])[0],
                    dn=entry.entry_dn,
                    attributes=attributes
                ))
            
            conn.unbind()
            return users
            
        except Exception as e:
            logger.error(f"Failed to search LDAP users: {e}")
            return []
    
    async def search_users(self, query: str) -> List[LDAPUserInfo]:
        """Search for users in LDAP (async wrapper)"""
        if not self.ldap_enabled:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_search_users,
            query
        )
    
    def _sync_test_connection(self) -> bool:
        """Synchronously test LDAP connection"""
        if not self.server:
            return False
        
        try:
            conn = self._create_connection()
            if not conn:
                return False
            
            # Try a simple search to verify connection
            conn.search(
                search_base=self.ldap_base_dn,
                search_filter="(objectClass=*)",
                search_scope=SUBTREE,
                size_limit=1
            )
            
            conn.unbind()
            return True
            
        except Exception as e:
            logger.error(f"LDAP connection test failed: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test LDAP connection (async wrapper)"""
        if not self.ldap_enabled:
            return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_test_connection
        )
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Global LDAP service instance
ldap_service = LDAPService()


# Helper functions
async def sync_user_from_ldap(user, ldap_info: LDAPUserInfo):
    """Sync user data from LDAP"""
    user.name = ldap_info.name
    user.ldap_dn = ldap_info.dn
    user.external_id = ldap_info.uid
    
    # Mark as verified since they authenticated via LDAP
    user.is_verified = True
    
    # Update last active
    from datetime import datetime
    user.last_active_at = datetime.utcnow()
    
    return user


async def create_user_from_ldap(ldap_info: LDAPUserInfo, db):
    """Create a new user from LDAP information"""
    from app.models.user import User
    from datetime import datetime
    
    # For LDAP users, if email is not available, use uid@domain
    email = ldap_info.email
    if not email or email == ldap_info.uid:
        # Create a pseudo-email for LDAP users without email
        email = f"{ldap_info.uid}@{settings.LDAP_DEFAULT_DOMAIN if hasattr(settings, 'LDAP_DEFAULT_DOMAIN') else 'ldap.local'}"
    
    user = User(
        email=email,
        name=ldap_info.name,
        password_hash=None,  # No local password for LDAP users
        auth_provider="ldap",
        ldap_dn=ldap_info.dn,
        external_id=ldap_info.uid,
        is_verified=True,  # LDAP users are pre-verified
        is_active=True,
        created_at=datetime.utcnow(),
        last_active_at=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user
"""
Security controls for authentication hardening
Implements rate limiting, brute force protection, account lockout, and audit logging
"""
import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from database import get_db_connection


class SecurityConfig:
    """Security configuration constants"""
    
    # Rate limiting settings
    MAX_ATTEMPTS_PER_IP_HOUR = 20  # Max attempts per IP per hour
    MAX_ATTEMPTS_PER_EMAIL_HOUR = 5  # Max attempts per email per hour
    RATE_LIMIT_WINDOW_MINUTES = 60  # Rate limit window
    
    # Account lockout settings
    MAX_FAILED_ATTEMPTS = 5  # Max failed attempts before lockout
    LOCKOUT_DURATION_MINUTES = 30  # Initial lockout duration
    PROGRESSIVE_LOCKOUT_MULTIPLIER = 2  # Multiply lockout time for repeat offenses
    MAX_LOCKOUT_DURATION_HOURS = 24  # Maximum lockout duration
    
    # Password policy (already implemented in auth_utils)
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # TOTP settings
    TOTP_SECRET_LENGTH = 32  # bytes
    TOTP_BACKUP_CODES_COUNT = 10
    TOTP_WINDOW_SIZE = 1  # Allow 1 step before/after current time


class RateLimiter:
    """Rate limiting for authentication attempts"""
    
    @staticmethod
    def check_rate_limit(identifier: str, identifier_type: str) -> Dict[str, Any]:
        """Check if identifier is rate limited"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Clean up old records first
                cursor.execute("""
                    DELETE FROM auth_rate_limits 
                    WHERE window_start < %s
                    AND (blocked_until IS NULL OR blocked_until < %s)
                """, (
                    datetime.now(timezone.utc) - timedelta(hours=1),
                    datetime.now(timezone.utc)
                ))
                
                # Check current rate limit
                cursor.execute("""
                    SELECT attempt_count, blocked_until
                    FROM auth_rate_limits
                    WHERE identifier = %s AND identifier_type = %s
                    AND window_start > %s
                """, (
                    identifier, 
                    identifier_type,
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ))
                
                result = cursor.fetchone()
                
                if not result:
                    return {'allowed': True, 'attempts_remaining': SecurityConfig.MAX_ATTEMPTS_PER_IP_HOUR}
                
                attempt_count, blocked_until = result
                
                # Check if currently blocked
                if blocked_until and blocked_until > datetime.now(timezone.utc):
                    return {
                        'allowed': False,
                        'blocked_until': blocked_until.isoformat(),
                        'reason': 'rate_limited'
                    }
                
                # Check attempt limits
                max_attempts = (SecurityConfig.MAX_ATTEMPTS_PER_IP_HOUR 
                              if identifier_type == 'ip' 
                              else SecurityConfig.MAX_ATTEMPTS_PER_EMAIL_HOUR)
                
                if attempt_count >= max_attempts:
                    # Block for 1 hour
                    blocked_until = datetime.now(timezone.utc) + timedelta(hours=1)
                    cursor.execute("""
                        UPDATE auth_rate_limits 
                        SET blocked_until = %s
                        WHERE identifier = %s AND identifier_type = %s
                    """, (blocked_until, identifier, identifier_type))
                    conn.commit()
                    
                    return {
                        'allowed': False,
                        'blocked_until': blocked_until.isoformat(),
                        'reason': 'rate_limit_exceeded'
                    }
                
                return {
                    'allowed': True,
                    'attempts_remaining': max_attempts - attempt_count
                }
                
        except Exception:
            # If rate limiting fails, allow the request (fail open)
            return {'allowed': True, 'attempts_remaining': 1}
    
    @staticmethod
    def record_attempt(identifier: str, identifier_type: str, success: bool = False) -> bool:
        """Record an authentication attempt"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if success:
                    # Clear rate limit on successful auth
                    cursor.execute("""
                        DELETE FROM auth_rate_limits
                        WHERE identifier = %s AND identifier_type = %s
                    """, (identifier, identifier_type))
                else:
                    # Increment attempt count
                    cursor.execute("""
                        INSERT INTO auth_rate_limits (identifier, identifier_type, attempt_count)
                        VALUES (%s, %s, 1)
                        ON CONFLICT (identifier, identifier_type) 
                        DO UPDATE SET 
                            attempt_count = auth_rate_limits.attempt_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE auth_rate_limits.window_start > %s
                    """, (
                        identifier, 
                        identifier_type,
                        datetime.now(timezone.utc) - timedelta(hours=1)
                    ))
                
                conn.commit()
                return True
                
        except Exception:
            return False


class AccountLockout:
    """Account lockout management for brute force protection"""
    
    @staticmethod
    def check_account_lockout(email: str) -> Dict[str, Any]:
        """Check if account is locked out"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT failed_attempts, locked_until, lockout_reason
                    FROM account_lockouts
                    WHERE email = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (email,))
                
                result = cursor.fetchone()
                
                if not result:
                    return {'locked': False, 'failed_attempts': 0}
                
                failed_attempts, locked_until, lockout_reason = result
                
                # Check if lockout has expired
                if locked_until and locked_until > datetime.now(timezone.utc):
                    return {
                        'locked': True,
                        'locked_until': locked_until.isoformat(),
                        'reason': lockout_reason,
                        'failed_attempts': failed_attempts
                    }
                
                return {'locked': False, 'failed_attempts': failed_attempts}
                
        except Exception:
            # If lockout check fails, allow the request (fail open)
            return {'locked': False, 'failed_attempts': 0}
    
    @staticmethod
    def record_failed_attempt(user_id: str, email: str) -> Dict[str, Any]:
        """Record a failed login attempt and potentially lock account"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get current failed attempts
                cursor.execute("""
                    SELECT id, failed_attempts
                    FROM account_lockouts
                    WHERE email = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (email,))
                
                result = cursor.fetchone()
                
                if result:
                    lockout_id, failed_attempts = result
                    new_failed_attempts = failed_attempts + 1
                    
                    # Update existing record
                    cursor.execute("""
                        UPDATE account_lockouts
                        SET failed_attempts = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (new_failed_attempts, lockout_id))
                else:
                    # Create new record
                    new_failed_attempts = 1
                    cursor.execute("""
                        INSERT INTO account_lockouts (user_id, email, failed_attempts)
                        VALUES (%s, %s, %s)
                    """, (user_id, email, new_failed_attempts))
                
                # Check if account should be locked
                if new_failed_attempts >= SecurityConfig.MAX_FAILED_ATTEMPTS:
                    # Calculate lockout duration (progressive)
                    lockout_multiplier = min(new_failed_attempts - SecurityConfig.MAX_FAILED_ATTEMPTS + 1, 8)
                    lockout_minutes = SecurityConfig.LOCKOUT_DURATION_MINUTES * (
                        SecurityConfig.PROGRESSIVE_LOCKOUT_MULTIPLIER ** (lockout_multiplier - 1)
                    )
                    
                    # Cap at maximum lockout duration
                    max_lockout_minutes = SecurityConfig.MAX_LOCKOUT_DURATION_HOURS * 60
                    lockout_minutes = min(lockout_minutes, max_lockout_minutes)
                    
                    locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
                    
                    cursor.execute("""
                        UPDATE account_lockouts
                        SET locked_at = CURRENT_TIMESTAMP,
                            locked_until = %s,
                            lockout_reason = 'failed_attempts'
                        WHERE email = %s
                    """, (locked_until, email))
                    
                    conn.commit()
                    
                    return {
                        'locked': True,
                        'locked_until': locked_until.isoformat(),
                        'failed_attempts': new_failed_attempts,
                        'lockout_duration_minutes': lockout_minutes
                    }
                
                conn.commit()
                return {
                    'locked': False,
                    'failed_attempts': new_failed_attempts,
                    'attempts_remaining': SecurityConfig.MAX_FAILED_ATTEMPTS - new_failed_attempts
                }
                
        except Exception:
            return {'locked': False, 'failed_attempts': 0}
    
    @staticmethod
    def clear_failed_attempts(email: str) -> bool:
        """Clear failed attempts on successful login"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM account_lockouts
                    WHERE email = %s
                """, (email,))
                
                conn.commit()
                return True
                
        except Exception:
            return False


class SecurityAuditLogger:
    """Security audit logging for authentication events"""
    
    @staticmethod
    def log_auth_event(
        event_type: str,
        email: str = None,
        user_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        event_details: Dict[str, Any] = None,
        risk_score: int = 0
    ) -> bool:
        """Log an authentication security event"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO auth_audit_log (
                        user_id, email, ip_address, user_agent, 
                        event_type, event_details, risk_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    email,
                    ip_address,
                    user_agent,
                    event_type,
                    json.dumps(event_details or {}),
                    risk_score
                ))
                
                conn.commit()
                return True
                
        except Exception:
            return False
    
    @staticmethod
    def get_suspicious_activity(email: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get suspicious activity for an email in the last N hours"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT event_type, ip_address, user_agent, event_details, 
                           risk_score, created_at
                    FROM auth_audit_log
                    WHERE email = %s 
                    AND created_at > %s
                    AND risk_score > 50
                    ORDER BY created_at DESC
                """, (
                    email,
                    datetime.now(timezone.utc) - timedelta(hours=hours)
                ))
                
                results = cursor.fetchall()
                
                return [{
                    'event_type': row[0],
                    'ip_address': str(row[1]) if row[1] else None,
                    'user_agent': row[2],
                    'event_details': json.loads(row[3]) if row[3] else {},
                    'risk_score': row[4],
                    'created_at': row[5].isoformat()
                } for row in results]
                
        except Exception:
            return []


class TOTPManager:
    """TOTP (Time-based One-Time Password) management for 2FA preparation"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        secret_bytes = secrets.token_bytes(SecurityConfig.TOTP_SECRET_LENGTH)
        return base64.b32encode(secret_bytes).decode('utf-8')
    
    @staticmethod
    def generate_backup_codes() -> List[str]:
        """Generate backup codes for TOTP"""
        codes = []
        for _ in range(SecurityConfig.TOTP_BACKUP_CODES_COUNT):
            code = ''.join(secrets.choice('0123456789') for _ in range(8))
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    @staticmethod
    def setup_totp(user_id: str) -> Dict[str, Any]:
        """Set up TOTP for a user (preparation only - not enabled)"""
        try:
            secret = TOTPManager.generate_secret()
            backup_codes = TOTPManager.generate_backup_codes()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO user_totp (user_id, secret_key, backup_codes, is_enabled)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        secret_key = EXCLUDED.secret_key,
                        backup_codes = EXCLUDED.backup_codes,
                        is_enabled = false,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, secret, backup_codes, False))
                
                conn.commit()
                
                return {
                    'secret': secret,
                    'backup_codes': backup_codes,
                    'qr_code_url': f"otpauth://totp/TutorSystem:{user_id}?secret={secret}&issuer=TutorSystem"
                }
                
        except Exception:
            return {}
    
    @staticmethod
    def is_totp_enabled(user_id: str) -> bool:
        """Check if TOTP is enabled for a user"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT is_enabled FROM user_totp WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else False
                
        except Exception:
            return False


def extract_client_info(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract client information from Lambda event"""
    headers = event.get('headers', {})
    
    # Try to get real IP from various headers (API Gateway, CloudFront, etc.)
    ip_address = (
        headers.get('X-Forwarded-For', '').split(',')[0].strip() or
        headers.get('X-Real-IP', '') or
        headers.get('CF-Connecting-IP', '') or  # CloudFlare
        event.get('requestContext', {}).get('identity', {}).get('sourceIp', '') or
        '127.0.0.1'
    )
    
    user_agent = headers.get('User-Agent', 'Unknown')
    
    return {
        'ip_address': ip_address,
        'user_agent': user_agent
    }


def calculate_risk_score(
    email: str,
    ip_address: str,
    user_agent: str,
    event_type: str,
    failed_attempts: int = 0
) -> int:
    """Calculate risk score for an authentication event"""
    risk_score = 0
    
    # Base risk by event type
    event_risks = {
        'login_failed': 20,
        'login_success': 0,
        'register': 10,
        'password_reset': 15,
        'account_locked': 80,
        'suspicious_activity': 90
    }
    
    risk_score += event_risks.get(event_type, 10)
    
    # Increase risk based on failed attempts
    if failed_attempts > 0:
        risk_score += min(failed_attempts * 10, 50)
    
    # TODO: Add more sophisticated risk scoring:
    # - Geolocation analysis
    # - Device fingerprinting
    # - Behavioral analysis
    # - Known bad IP lists
    
    return min(risk_score, 100)
"""
Security configuration module for SearXNG-Cool
Centralizes all security-related settings and utilities
"""
import os
from datetime import timedelta
from typing import Dict, Any, Optional
import secrets
import hashlib
from urllib.parse import quote_plus


class SecurityConfig:
    """Security configuration with environment variable support"""
    
    def __init__(self):
        self.load_from_env()
    
    def load_from_env(self):
        """Load security settings from environment variables"""
        # Core security
        self.SECRET_KEY = os.environ.get('SECRET_KEY', self._generate_fallback_key())
        self.JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', self._generate_fallback_key())
        self.SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', secrets.token_hex(16))
        
        # Session security
        self.SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
        self.SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
        self.SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
        self.PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '600'))
        
        # JWT settings
        self.JWT_ACCESS_TOKEN_EXPIRES = timedelta(
            seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', '900'))
        )
        self.JWT_REFRESH_TOKEN_EXPIRES = timedelta(
            seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', '2592000'))
        )
        self.JWT_COOKIE_SECURE = os.environ.get('JWT_COOKIE_SECURE', 'True') == 'True'
        self.JWT_CSRF_IN_COOKIES = os.environ.get('JWT_CSRF_IN_COOKIES', 'True') == 'True'
        
        # Database
        self.DATABASE_URL = self._build_database_url()
        
        # Redis
        self.REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # CORS
        cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080')
        self.CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(',')]
        self.CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'True') == 'True'
        
        # Environment
        self.FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
        self.FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False') == 'True'
        
    def _generate_fallback_key(self) -> str:
        """Generate a fallback key for development only"""
        if self.FLASK_ENV == 'development':
            return secrets.token_hex(32)
        raise ValueError("Security keys must be set in production environment")
    
    def _build_database_url(self) -> str:
        """Build database URL from components or use direct URL"""
        # First check for direct URL
        if db_url := os.environ.get('DATABASE_URL'):
            return db_url
        
        # Build from components
        user = os.environ.get('DB_USER', 'searxng_user')
        password = os.environ.get('DB_PASSWORD')
        if not password:
            raise ValueError("DB_PASSWORD must be set")
        
        # URL encode the password to handle special characters
        password = quote_plus(password)
        host = os.environ.get('DB_HOST', 'localhost')
        port = os.environ.get('DB_PORT', '5432')
        database = os.environ.get('DB_NAME', 'searxng_cool_music')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'SESSION_COOKIE_SECURE': self.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': self.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': self.SESSION_COOKIE_SAMESITE,
            'PERMANENT_SESSION_LIFETIME': self.PERMANENT_SESSION_LIFETIME,
            'SQLALCHEMY_DATABASE_URI': self.DATABASE_URL,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "pool_size": 10,
                "max_overflow": 20,
            }
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT-specific configuration"""
        return {
            'JWT_SECRET_KEY': self.JWT_SECRET_KEY,
            'JWT_ACCESS_TOKEN_EXPIRES': self.JWT_ACCESS_TOKEN_EXPIRES,
            'JWT_REFRESH_TOKEN_EXPIRES': self.JWT_REFRESH_TOKEN_EXPIRES,
            'JWT_COOKIE_SECURE': self.JWT_COOKIE_SECURE,
            'JWT_CSRF_IN_COOKIES': self.JWT_CSRF_IN_COOKIES,
            'JWT_CSRF_CHECK_FORM': True,
            'JWT_SESSION_COOKIE': False,
        }
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for responses"""
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }


class PasswordHasher:
    """Secure password hashing utilities"""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash a password using bcrypt or fallback to PBKDF2"""
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        except ImportError:
            # Fallback to PBKDF2
            if not salt:
                salt = secrets.token_hex(16)
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return f"{salt}${key.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against a hash"""
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except ImportError:
            # Fallback to PBKDF2
            salt, key = hashed.split('$')
            test_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return test_key.hex() == key


class APIKeyValidator:
    """API key validation utilities"""
    
    @staticmethod
    def validate_spotify_keys(client_id: str, client_secret: str) -> bool:
        """Validate Spotify API credentials format"""
        return (
            len(client_id) == 32 and 
            len(client_secret) == 32 and
            client_id.isalnum() and
            client_secret.isalnum()
        )
    
    @staticmethod
    def validate_genius_key(api_key: str) -> bool:
        """Validate Genius API key format"""
        return len(api_key) > 20 and api_key.isalnum()
    
    @staticmethod
    def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
        """Mask sensitive values for logging"""
        if not value or len(value) <= visible_chars:
            return "***"
        return f"{value[:visible_chars]}...{value[-2:]}"


# Global instance
security_config = SecurityConfig()


def apply_security_headers(app):
    """Apply security headers to Flask app"""
    headers = security_config.get_security_headers()
    
    @app.after_request
    def set_security_headers(response):
        for header, value in headers.items():
            response.headers[header] = value
        return response
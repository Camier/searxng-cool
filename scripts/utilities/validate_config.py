#!/usr/bin/env python3
"""
Configuration Validation Script
Validates environment configuration and security settings
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import security_config
from orchestrator.config_loader import load_config, validate_config


class ConfigValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
    def validate_env_file(self) -> bool:
        """Check if .env file exists and is properly formatted"""
        env_path = project_root / '.env'
        
        if not env_path.exists():
            self.errors.append("❌ .env file not found. Copy .env.example to .env")
            return False
            
        # Load environment variables
        load_dotenv(env_path)
        
        # Check file permissions
        stat = env_path.stat()
        if stat.st_mode & 0o077:
            self.warnings.append("⚠️  .env file has overly permissive permissions. Run: chmod 600 .env")
            
        self.info.append("✅ .env file found and loaded")
        return True
    
    def validate_required_vars(self) -> bool:
        """Validate required environment variables"""
        required_vars = {
            'DATABASE_URL': 'PostgreSQL connection string',
            'JWT_SECRET_KEY': 'JWT signing key'
        }
        
        all_present = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                self.errors.append(f"❌ Missing required: {var} ({description})")
                all_present = False
            else:
                self.info.append(f"✅ {var} is set")
                
        return all_present
    
    def validate_database_url(self) -> bool:
        """Validate DATABASE_URL format"""
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return False
            
        # PostgreSQL URL pattern
        pattern = r'^postgresql://([^:]+):([^@]+)@([^/]+)/(.+)$'
        match = re.match(pattern, db_url)
        
        if not match:
            self.errors.append(f"❌ Invalid DATABASE_URL format: {db_url}")
            return False
            
        user, password, host, database = match.groups()
        
        # Security checks
        if password == 'password' or len(password) < 8:
            self.warnings.append("⚠️  Weak database password detected")
            
        if host == 'localhost' or host.startswith('127.'):
            self.info.append("✅ Database configured for local connection")
        else:
            self.warnings.append(f"⚠️  Database configured for remote host: {host}")
            
        return True
    
    def validate_jwt_secret(self) -> bool:
        """Validate JWT secret strength"""
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return False
            
        if len(jwt_secret) < 32:
            self.errors.append("❌ JWT_SECRET_KEY too short (minimum 32 characters)")
            return False
            
        if jwt_secret == '35252cc1a9e34982a35fa65632c09f17':
            self.errors.append("❌ Using default JWT_SECRET_KEY! Generate a new one with: openssl rand -hex 32")
            return False
            
        # Check entropy
        if len(set(jwt_secret)) < 10:
            self.warnings.append("⚠️  JWT_SECRET_KEY has low entropy")
            
        self.info.append("✅ JWT_SECRET_KEY appears secure")
        return True
    
    def validate_redis_urls(self) -> bool:
        """Validate Redis configuration"""
        redis_urls = {
            'REDIS_URL': 0,
            'SOCKETIO_REDIS_URL': 1,
            'RATE_LIMIT_STORAGE_URL': 2
        }
        
        all_valid = True
        seen_dbs = set()
        
        for var, expected_db in redis_urls.items():
            url = os.getenv(var, f'redis://localhost:6379/{expected_db}')
            
            # Parse Redis URL
            pattern = r'^redis://(?:([^:]+):([^@]+)@)?([^:/]+)(?::(\d+))?/(\d+)$'
            match = re.match(pattern, url)
            
            if not match:
                self.errors.append(f"❌ Invalid {var} format: {url}")
                all_valid = False
                continue
                
            _, _, host, port, db = match.groups()
            db = int(db)
            
            if db in seen_dbs:
                self.warnings.append(f"⚠️  {var} uses same Redis DB as another service")
            seen_dbs.add(db)
            
        if all_valid:
            self.info.append("✅ Redis configuration valid")
            
        return all_valid
    
    def validate_api_keys(self) -> None:
        """Validate API key formats"""
        api_keys = {
            'LASTFM_API_KEY': ('lastfm', 'Last.fm'),
            'SPOTIFY_CLIENT_ID': ('spotify', 'Spotify'),
            'DISCOGS_TOKEN': ('discogs', 'Discogs')
        }
        
        for var, (service, name) in api_keys.items():
            key = os.getenv(var)
            if key:
                if security_config.validate_api_key(service, key):
                    self.info.append(f"✅ {name} API key format valid")
                else:
                    self.warnings.append(f"⚠️  {name} API key format invalid")
            else:
                self.info.append(f"ℹ️  {name} API key not configured")
    
    def validate_security_settings(self) -> None:
        """Validate security-related settings"""
        # Check debug mode
        if os.getenv('DEBUG', 'false').lower() == 'true':
            self.warnings.append("⚠️  DEBUG mode enabled - disable for production")
            
        # Check environment
        flask_env = os.getenv('FLASK_ENV', 'production')
        if flask_env != 'production':
            self.warnings.append(f"⚠️  FLASK_ENV set to '{flask_env}' - use 'production' for deployment")
            
        # Check CORS origins
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if '*' in cors_origins:
            self.errors.append("❌ CORS_ORIGINS contains wildcard (*) - security risk!")
            
        # Check session security
        if os.getenv('SESSION_COOKIE_SECURE', 'true').lower() != 'true':
            self.warnings.append("⚠️  SESSION_COOKIE_SECURE disabled - enable for HTTPS")
    
    def validate_orchestrator_config(self) -> bool:
        """Validate orchestrator YAML configuration"""
        try:
            config = load_config()
            validate_config(config)
            self.info.append("✅ Orchestrator configuration valid")
            return True
        except FileNotFoundError as e:
            self.errors.append(f"❌ Configuration file not found: {e}")
            return False
        except ValueError as e:
            self.errors.append(f"❌ Configuration validation failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"❌ Configuration error: {e}")
            return False
    
    def run_validation(self) -> bool:
        """Run all validations"""
        print("🔍 Validating configuration...\n")
        
        # Run all checks
        checks = [
            ("Environment file", self.validate_env_file),
            ("Required variables", self.validate_required_vars),
            ("Database URL", self.validate_database_url),
            ("JWT secret", self.validate_jwt_secret),
            ("Redis URLs", self.validate_redis_urls),
            ("Orchestrator config", self.validate_orchestrator_config),
        ]
        
        all_passed = True
        for name, check in checks:
            if callable(check):
                result = check()
                if result is False:
                    all_passed = False
        
        # Additional checks that don't return pass/fail
        self.validate_api_keys()
        self.validate_security_settings()
        
        # Print results
        print("\n📊 Validation Results:\n")
        
        if self.errors:
            print("❌ Errors (must fix):")
            for error in self.errors:
                print(f"   {error}")
            print()
            
        if self.warnings:
            print("⚠️  Warnings (should review):")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
            
        if self.info:
            print("ℹ️  Information:")
            for info in self.info:
                print(f"   {info}")
            print()
        
        if not self.errors:
            print("✅ Configuration validation passed!")
            return True
        else:
            print("❌ Configuration validation failed!")
            return False


def main():
    """Main entry point"""
    validator = ConfigValidator()
    success = validator.run_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
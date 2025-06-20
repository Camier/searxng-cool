"""
Configuration module for SearXNG-Cool
"""
from .security import SecurityConfig, security_config, require_api_key, apply_security_headers

__all__ = [
    'SecurityConfig',
    'security_config',
    'require_api_key',
    'apply_security_headers'
]
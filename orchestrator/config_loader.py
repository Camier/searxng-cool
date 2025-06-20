#!/usr/bin/env python3
"""
Configuration Loading Utility for SearXNG-Cool
Provides secure configuration loading with environment variable substitution
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def expand_env_vars(value: Any) -> Any:
    """
    Recursively expand environment variables in configuration values.
    
    Supports patterns like:
    - ${VAR} - Simple substitution
    - ${VAR:-default} - With default value
    - ${VAR:?error} - Required variable with error message
    
    Args:
        value: Configuration value to process
        
    Returns:
        Processed value with environment variables expanded
    """
    if isinstance(value, str):
        # Pattern to match ${VAR}, ${VAR:-default}, ${VAR:?error}
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            var_expr = match.group(1)
            
            # Handle ${VAR:?error} pattern
            if ':?' in var_expr:
                var_name, error_msg = var_expr.split(':?', 1)
                env_value = os.environ.get(var_name)
                if env_value is None:
                    raise ValueError(f"Required environment variable {var_name} is not set: {error_msg}")
                return env_value
            
            # Handle ${VAR:-default} pattern
            elif ':-' in var_expr:
                var_name, default_value = var_expr.split(':-', 1)
                return os.environ.get(var_name, default_value)
            
            # Handle simple ${VAR} pattern
            else:
                var_name = var_expr
                env_value = os.environ.get(var_name)
                if env_value is None:
                    logger.warning(f"Environment variable {var_name} not found, keeping original value")
                    return match.group(0)  # Return original ${VAR} if not found
                return env_value
        
        return re.sub(pattern, replace_env_var, value)
    
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    
    else:
        return value


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution.
    
    Args:
        config_path: Path to configuration file. If None, uses default location.
        
    Returns:
        Configuration dictionary with expanded environment variables
        
    Raises:
        FileNotFoundError: If configuration file is not found
        yaml.YAMLError: If YAML parsing fails
        ValueError: If required environment variables are missing
    """
    if config_path is None:
        # Default to orchestrator.yml in config directory
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'orchestrator.yml'
        )
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Expand environment variables
        config = expand_env_vars(raw_config)
        
        logger.info(f"✅ Configuration loaded successfully from {config_path}")
        return config
    
    except yaml.YAMLError as e:
        logger.error(f"❌ Failed to parse YAML configuration: {e}")
        raise
    
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        raise


def get_database_uri(config: Optional[Dict[str, Any]] = None) -> str:
    """
    Get database URI from configuration or environment.
    
    Args:
        config: Configuration dictionary. If None, loads from default location.
        
    Returns:
        Database URI string
    """
    if config is None:
        config = load_config()
    
    try:
        return config['DATABASE']['SQLALCHEMY_DATABASE_URI']
    except KeyError:
        # Fallback to environment variable
        db_uri = os.environ.get('DATABASE_URL')
        if db_uri:
            return db_uri
        
        # Last resort - construct from components
        from urllib.parse import quote_plus
        
        db_user = os.environ.get('DB_USER', 'searxng_user')
        db_pass = os.environ.get('DB_PASSWORD')
        if not db_pass:
            raise ValueError("DB_PASSWORD environment variable must be set")
        db_pass = quote_plus(db_pass)  # URL encode the password
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'searxng_cool_music')
        
        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration structure and required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['DATABASE', 'JWT', 'SERVER']
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate DATABASE section
    if 'SQLALCHEMY_DATABASE_URI' not in config['DATABASE']:
        raise ValueError("Missing SQLALCHEMY_DATABASE_URI in DATABASE section")
    
    # Validate JWT section
    jwt_config = config['JWT']
    if 'JWT_SECRET_KEY' not in jwt_config:
        raise ValueError("Missing JWT_SECRET_KEY in JWT section")
    
    # Validate SERVER section
    server_config = config['SERVER']
    required_server_fields = ['HOST', 'PORT']
    for field in required_server_fields:
        if field not in server_config:
            raise ValueError(f"Missing {field} in SERVER section")
    
    logger.info("✅ Configuration validation passed")
    return True


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config()
        validate_config(config)
        db_uri = get_database_uri(config)
        print(f"Database URI: {db_uri}")
        print("✅ Configuration test passed")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
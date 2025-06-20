#!/usr/bin/env python3
"""
Configuration loader that properly handles environment variables
"""
import os
import yaml
import re
from pathlib import Path

def expand_env_vars(value):
    """Expand environment variables in config values"""
    if isinstance(value, str):
        # First check for ${VAR:?error} pattern (required vars)
        required_pattern = r'\$\{([^}:]+):\?([^}]*)\}'
        required_match = re.match(required_pattern, value)
        if required_match:
            var_name = required_match.group(1)
            error_msg = required_match.group(2) or f"{var_name} is required"
            if var_name not in os.environ:
                raise ValueError(f"Environment variable {var_name} is required: {error_msg}")
            return os.environ[var_name]
        
        # Match ${VAR:-default} pattern
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ''
            return os.environ.get(var_name, default_value)
        
        return re.sub(pattern, replacer, value)
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(v) for v in value]
    else:
        return value

def load_config():
    """Load and process configuration file"""
    config_path = Path(__file__).parent.parent / 'config' / 'orchestrator.yml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Recursively expand all environment variables
    config = expand_env_vars(config)
    
    # Convert string numbers to integers where needed
    if 'JWT' in config:
        if 'JWT_ACCESS_TOKEN_EXPIRES' in config['JWT']:
            config['JWT']['JWT_ACCESS_TOKEN_EXPIRES'] = int(config['JWT']['JWT_ACCESS_TOKEN_EXPIRES'])
        if 'JWT_REFRESH_TOKEN_EXPIRES' in config['JWT']:
            config['JWT']['JWT_REFRESH_TOKEN_EXPIRES'] = int(config['JWT']['JWT_REFRESH_TOKEN_EXPIRES'])
    
    return config
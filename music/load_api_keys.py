"""
Secure API key loader for music engines

Loads API keys from environment variables or .env file
Never logs or exposes actual key values
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class APIKeyLoader:
    """Securely load and manage API keys"""
    
    def __init__(self, env_file: str = None):
        """
        Initialize API key loader
        
        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file or os.path.join(
            Path(__file__).parent.parent, '.env'
        )
        
        # Try to load from .env file if it exists
        if os.path.exists(self.env_file):
            self._load_env_file()
            
    def _load_env_file(self):
        """Load environment variables from .env file"""
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
                            
            logger.info(f"Loaded environment from {self.env_file}")
            
        except Exception as e:
            logger.warning(f"Failed to load .env file: {str(e)}")
            
    def get_api_keys(self) -> Dict[str, str]:
        """
        Get all API keys from environment
        
        Returns:
            Dictionary of API keys (values masked for security)
        """
        keys = {}
        
        # List of expected API keys
        api_key_names = [
            'DISCOGS_API_TOKEN',
            'DISCOGS_CONSUMER_KEY',
            'DISCOGS_CONSUMER_SECRET',
            'JAMENDO_API_KEY',
            'LASTFM_API_KEY',
            'LASTFM_API_SECRET',
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET',
            'YOUTUBE_API_KEY',
            'GENIUS_ACCESS_TOKEN'
        ]
        
        for key_name in api_key_names:
            value = os.environ.get(key_name)
            if value:
                # Mask the value for security
                masked_value = self._mask_value(value)
                keys[key_name] = masked_value
                
        return keys
        
    def get_key(self, key_name: str) -> str:
        """
        Get specific API key
        
        Args:
            key_name: Name of the API key
            
        Returns:
            API key value or empty string
        """
        return os.environ.get(key_name, '')
        
    def _mask_value(self, value: str) -> str:
        """Mask sensitive value for logging"""
        if not value:
            return ''
            
        if len(value) <= 8:
            return '*' * len(value)
            
        # Show first 4 and last 4 characters
        return f"{value[:4]}...{value[-4:]}"
        
    def validate_required_keys(self, required: list) -> Dict[str, bool]:
        """
        Validate that required keys are present
        
        Args:
            required: List of required key names
            
        Returns:
            Dictionary of key names and their presence status
        """
        status = {}
        
        for key_name in required:
            value = os.environ.get(key_name)
            status[key_name] = bool(value and value.strip())
            
        return status
        
    def inject_into_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject API keys into engine configuration
        
        Args:
            config: Engine configuration dictionary
            
        Returns:
            Updated configuration with API keys
        """
        # Map of config keys to environment variables
        key_mapping = {
            'discogs': {
                'api_token': 'DISCOGS_API_TOKEN',
                'consumer_key': 'DISCOGS_CONSUMER_KEY',
                'consumer_secret': 'DISCOGS_CONSUMER_SECRET'
            },
            'jamendo': {
                'api_key': 'JAMENDO_API_KEY'
            },
            'lastfm': {
                'api_key': 'LASTFM_API_KEY',
                'api_secret': 'LASTFM_API_SECRET'
            },
            'spotify': {
                'client_id': 'SPOTIFY_CLIENT_ID',
                'client_secret': 'SPOTIFY_CLIENT_SECRET'
            },
            'youtube_music': {
                'api_key': 'YOUTUBE_API_KEY'
            },
            'genius': {
                'access_token': 'GENIUS_ACCESS_TOKEN'
            }
        }
        
        # Inject keys into config
        for engine_name, engine_config in config.get('engines', {}).items():
            if engine_name in key_mapping:
                for config_key, env_key in key_mapping[engine_name].items():
                    value = self.get_key(env_key)
                    if value:
                        engine_config[config_key] = value
                        
        return config
        
    def report_status(self):
        """Log API key status (masked for security)"""
        keys = self.get_api_keys()
        
        if not keys:
            logger.warning("No API keys found in environment")
            return
            
        logger.info("API Keys Status:")
        for key_name, masked_value in keys.items():
            if masked_value:
                logger.info(f"  {key_name}: {masked_value}")
            else:
                logger.warning(f"  {key_name}: Not configured")
                

# Singleton instance
api_key_loader = APIKeyLoader()


def get_api_key(key_name: str) -> str:
    """
    Get API key value
    
    Args:
        key_name: Name of the API key
        
    Returns:
        API key value or empty string
    """
    return api_key_loader.get_key(key_name)
    
    
def validate_music_engine_keys() -> bool:
    """
    Validate that at least basic music engine keys are present
    
    Returns:
        True if minimum required keys are present
    """
    # At minimum, we need either Discogs or Jamendo
    required_sets = [
        ['DISCOGS_API_TOKEN'],
        ['JAMENDO_API_KEY']
    ]
    
    for required_set in required_sets:
        status = api_key_loader.validate_required_keys(required_set)
        if all(status.values()):
            return True
            
    return False
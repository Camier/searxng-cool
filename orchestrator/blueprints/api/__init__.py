# API blueprint for programmatic access
from .routes import api_bp
from .music_routes import music_api_bp

__all__ = ['api_bp', 'music_api_bp']
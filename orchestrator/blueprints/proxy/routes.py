"""
Proxy Blueprint - Routes SearXNG requests through the orchestrator
Handles all non-auth, non-api, non-websocket requests and forwards them to SearXNG core
"""

import requests
from flask import Blueprint, request, Response, current_app, stream_with_context
from urllib.parse import urljoin, urlencode
import yaml
import os

proxy_bp = Blueprint('proxy', __name__)

# Load SearXNG configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'orchestrator.yml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

SEARXNG_BASE_URL = config['SEARXNG']['CORE_URL']

# Remove root route - nginx will handle direct SearXNG proxying
# @proxy_bp.route('/', defaults={'path': ''})  # Disabled - nginx handles this
@proxy_bp.route('/<path:path>')
def proxy_to_searxng(path):
    """
    Proxy all requests to SearXNG core instance
    """
    # Construct the target URL
    target_url = urljoin(SEARXNG_BASE_URL, path)
    
    # Forward query parameters
    if request.query_string:
        target_url += '?' + request.query_string.decode('utf-8')
    
    try:
        # Forward the request to SearXNG
        if request.method == 'GET':
            resp = requests.get(
                target_url,
                headers=dict(request.headers),
                allow_redirects=False,
                stream=True
            )
        elif request.method == 'POST':
            resp = requests.post(
                target_url,
                data=request.get_data(),
                headers=dict(request.headers),
                allow_redirects=False,
                stream=True
            )
        else:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                data=request.get_data(),
                allow_redirects=False,
                stream=True
            )
        
        # Create response with proper headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                  if name.lower() not in excluded_headers]
        
        # Handle different content types
        if resp.headers.get('content-type', '').startswith('text/html'):
            # For HTML responses, we might want to modify content in the future
            # (e.g., inject auth status, modify theme paths, etc.)
            content = resp.content.decode('utf-8', errors='ignore')
            return Response(content, resp.status_code, headers)
        else:
            # For other content types (CSS, JS, images), stream directly
            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    yield chunk
            
            return Response(
                stream_with_context(generate()),
                resp.status_code,
                headers
            )
    
    except requests.exceptions.ConnectionError:
        return Response(
            'SearXNG core service is not available. Please check if the service is running.',
            503,
            {'Content-Type': 'text/plain'}
        )
    except Exception as e:
        current_app.logger.error(f'Proxy error: {str(e)}')
        return Response(
            'Internal proxy error occurred.',
            500,
            {'Content-Type': 'text/plain'}
        )

@proxy_bp.route('/search')
def search_proxy():
    """
    Enhanced search endpoint with potential authentication checks
    """
    # In the future, we can add authentication checks here
    # For now, just proxy to SearXNG
    return proxy_to_searxng('search')

@proxy_bp.route('/autocompleter')
def autocomplete_proxy():
    """
    Autocomplete endpoint proxy
    """
    return proxy_to_searxng('autocompleter')

@proxy_bp.route('/preferences')
def preferences_proxy():
    """
    Preferences endpoint proxy
    """
    return proxy_to_searxng('preferences')

@proxy_bp.route('/stats')
def stats_proxy():
    """
    Stats endpoint proxy
    """
    return proxy_to_searxng('stats')

@proxy_bp.route('/status')
def status():
    """
    Orchestrator status endpoint
    """
    try:
        # Check if SearXNG core is responding
        resp = requests.get(f"{SEARXNG_BASE_URL}/", timeout=5)
        searxng_status = 'healthy' if resp.status_code == 200 else 'unhealthy'
    except:
        searxng_status = 'unreachable'
    
    return {
        'orchestrator': 'healthy',
        'searxng_core': searxng_status,
        'base_url': SEARXNG_BASE_URL
    }
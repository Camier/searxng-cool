"""
API Blueprint - Provides programmatic access to search functionality
"""

import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from orchestrator.utils.auth import jwt_required_with_user
import yaml
import os

api_bp = Blueprint('api', __name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'orchestrator.yml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

SEARXNG_BASE_URL = config['SEARXNG']['CORE_URL']

@api_bp.route('/search', methods=['GET', 'POST'])
@jwt_required_with_user()
def api_search(current_user):
    """
    API endpoint for search with authentication
    """
    
    # Get search parameters
    if request.method == 'POST':
        data = request.get_json()
        query = data.get('q', '')
        categories = data.get('categories', '')
        engines = data.get('engines', '')
        language = data.get('language', 'en')
        format_type = data.get('format', 'json')
    else:
        query = request.args.get('q', '')
        categories = request.args.get('categories', '')
        engines = request.args.get('engines', '')
        language = request.args.get('language', 'en')
        format_type = request.args.get('format', 'json')
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required'
        }), 400
    
    try:
        # Forward search to SearXNG core
        search_params = {
            'q': query,
            'format': format_type,
            'language': language
        }
        
        if categories:
            search_params['categories'] = categories
        if engines:
            search_params['engines'] = engines
        
        resp = requests.get(f"{SEARXNG_BASE_URL}/search", params=search_params)
        
        if resp.status_code == 200:
            return jsonify({
                'success': True,
                'user': current_user.username,
                'query': query,
                'results': resp.json() if format_type == 'json' else resp.text
            })
        else:
            return jsonify({
                'error': 'Search request failed',
                'status_code': resp.status_code
            }), resp.status_code
    
    except Exception as e:
        return jsonify({
            'error': f'API search error: {str(e)}'
        }), 500

@api_bp.route('/engines', methods=['GET'])
@jwt_required_with_user()
def api_engines(current_user):
    """
    Get available search engines
    """
    try:
        resp = requests.get(f"{SEARXNG_BASE_URL}/config")
        if resp.status_code == 200:
            return resp.json()
        else:
            return jsonify({'error': 'Failed to fetch engines'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/status')
def api_status():
    """
    API service status
    """
    return jsonify({
        'service': 'api',
        'status': 'healthy',
        'endpoints': ['/search', '/engines'],
        'authentication': 'required'
    })
"""
Tests for Discogs music search engine

Tests API integration, rate limiting, caching, and result parsing
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../searxng-core/searxng-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from searx.engines.music.discogs import DiscogsEngine
from searx.engines.music.base import APIError, RateLimitError


class TestDiscogsEngine:
    """Test suite for Discogs engine"""
    
    @pytest.fixture
    def engine_config(self):
        """Engine configuration for testing"""
        return {
            'enabled': True,
            'api_token': 'test_token',
            'rate_limit': 60,
            'rate_period': 60,
            'cache_ttl': 86400,
            'timeout': 10,
            'base_url': 'https://api.discogs.com',
            'user_agent': 'TestAgent/1.0'
        }
        
    @pytest.fixture
    def engine(self, engine_config):
        """Create engine instance"""
        return DiscogsEngine(engine_config)
        
    @pytest.fixture
    def mock_response(self):
        """Mock API response"""
        return {
            'results': [
                {
                    'id': 123456,
                    'type': 'release',
                    'title': 'Selected Ambient Works 85-92',
                    'artist': 'Aphex Twin',
                    'year': 1992,
                    'format': ['CD', 'Album'],
                    'country': 'UK',
                    'label': ['Apollo'],
                    'catno': 'AMB 3922 CD',
                    'thumb': 'https://img.discogs.com/thumb.jpg',
                    'uri': '/release/123456',
                    'community': {
                        'want': 5432,
                        'have': 8765
                    },
                    'genre': ['Electronic'],
                    'style': ['Ambient', 'IDM']
                },
                {
                    'id': 234567,
                    'type': 'master',
                    'title': 'Drukqs',
                    'artist': 'Aphex Twin',
                    'year': 2001,
                    'thumb': 'https://img.discogs.com/thumb2.jpg',
                    'uri': '/master/234567',
                    'genre': ['Electronic'],
                    'style': ['IDM', 'Experimental']
                }
            ],
            'pagination': {
                'page': 1,
                'pages': 5,
                'per_page': 50,
                'items': 237
            }
        }
        
    def test_engine_initialization(self, engine):
        """Test engine is properly initialized"""
        assert engine.name == 'discogs'
        assert engine.enabled is True
        assert engine.timeout == 10
        assert engine.per_page == 50
        
    def test_disabled_without_api_token(self):
        """Test engine is disabled without API token"""
        config = {'enabled': True}
        engine = DiscogsEngine(config)
        assert engine.enabled is False
        
    @patch('requests.Session.get')
    def test_search_success(self, mock_get, engine, mock_response):
        """Test successful search"""
        # Mock response
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.headers = {'X-Discogs-Ratelimit-Remaining': '45'}
        mock_get.return_value = mock_resp
        
        # Perform search
        results = engine.search('aphex twin', {'pageno': 1})
        
        # Verify request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'aphex twin' in str(call_args)
        assert 'token=test_token' in str(call_args)
        
        # Verify results
        assert len(results) == 2
        assert results[0]['title'] == 'Selected Ambient Works 85-92'
        assert results[0]['artist'] == 'Aphex Twin'
        assert results[0]['year'] == 1992
        assert results[0]['source'] == 'discogs'
        assert 'want' in results[0]['metadata']
        
    @patch('requests.Session.get')
    def test_search_with_filters(self, mock_get, engine, mock_response):
        """Test search with filters"""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.headers = {}
        mock_get.return_value = mock_resp
        
        # Search with filters
        params = {
            'pageno': 1,
            'year': 1992,
            'format': 'CD',
            'country': 'UK'
        }
        results = engine.search('ambient', params)
        
        # Verify filters in request
        call_args = str(mock_get.call_args)
        assert 'year=1992' in call_args
        assert 'format=CD' in call_args
        assert 'country=UK' in call_args
        
    @patch('requests.Session.get')
    def test_rate_limit_error(self, mock_get, engine):
        """Test rate limit handling"""
        mock_resp = Mock()
        mock_resp.status_code = 429
        mock_resp.headers = {'Retry-After': '60'}
        mock_get.return_value = mock_resp
        
        # Should raise rate limit error
        with pytest.raises(APIError) as exc_info:
            engine.search('test', {})
            
        assert 'rate limit' in str(exc_info.value).lower()
        
    def test_result_normalization(self, engine, mock_response):
        """Test result normalization"""
        raw_results = mock_response['results']
        normalized = engine._normalize_results(raw_results, 'test query')
        
        # Check first result (release)
        release = normalized[0]
        assert release['url'] == 'https://www.discogs.com/release/123456'
        assert release['format'] == 'CD, Album'
        assert release['quality'] > 0 and release['quality'] <= 1
        assert 'Community: 8765 have, 5432 want' in release['content']
        
        # Check second result (master)
        master = normalized[1]
        assert master['url'] == 'https://www.discogs.com/master/234567'
        assert 'Master Release' in master['content']
        
    def test_parse_release_types(self, engine):
        """Test parsing different release types"""
        # Test release
        release_item = {
            'type': 'release',
            'title': 'Test Album',
            'artist': 'Test Artist (2)',
            'year': 2020,
            'format': ['Vinyl', 'LP'],
            'uri': '/release/123',
            'community': {'want': 10, 'have': 20}
        }
        
        results = engine._parse_response({'results': [release_item]})
        assert len(results) == 1
        assert results[0]['artist'] == 'Test Artist'  # Number removed
        
        # Test artist
        artist_item = {
            'type': 'artist',
            'title': 'Test Artist',
            'uri': '/artist/456',
            'profile': 'Artist bio'
        }
        
        results = engine._parse_response({'results': [artist_item]})
        assert len(results) == 1
        assert results[0]['content'] == 'Artist Profile'
        
    def test_cache_key_generation(self, engine):
        """Test cache key generation"""
        key1 = engine._generate_cache_key('test', {'page': 1})
        key2 = engine._generate_cache_key('test', {'page': 1})
        key3 = engine._generate_cache_key('test', {'page': 2})
        
        assert key1 == key2  # Same query/params = same key
        assert key1 != key3  # Different params = different key
        assert key1.startswith('music:search:discogs:')
        
    @patch('requests.Session.get')
    def test_get_release_details(self, mock_get, engine):
        """Test getting detailed release information"""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 123456,
            'title': 'Test Release',
            'artists': [{'name': 'Test Artist'}],
            'tracklist': [
                {'position': 'A1', 'title': 'Track 1'},
                {'position': 'A2', 'title': 'Track 2'}
            ]
        }
        mock_get.return_value = mock_resp
        
        details = engine.get_release_details(123456)
        
        assert details is not None
        assert details['id'] == 123456
        assert details['title'] == 'Test Release'
        assert len(details['tracklist']) == 2
        
    def test_quality_scoring(self, engine):
        """Test quality score calculation"""
        # Exact title match
        result1 = {
            'title': 'Aphex Twin',
            'artist': 'Aphex Twin',
            'year': 1992,
            'duration': 300,
            'thumbnail': 'http://example.com/thumb.jpg',
            'playable_url': 'http://example.com/play'
        }
        score1 = engine._calculate_quality_score(result1, 'aphex twin', 0)
        
        # Partial match
        result2 = {
            'title': 'Some Other Album',
            'artist': 'Various Artists'
        }
        score2 = engine._calculate_quality_score(result2, 'aphex twin', 5)
        
        assert score1 > score2  # Better match should score higher
        assert score1 <= 1.0
        assert score2 >= 0.0
        
    def test_error_handling(self, engine):
        """Test various error scenarios"""
        # Test with invalid response
        with pytest.raises(Exception):
            engine._parse_response({'invalid': 'data'})
            
        # Test with empty results
        results = engine._parse_response({'results': []})
        assert results == []
        
        # Test with None values
        item = {
            'type': 'release',
            'title': None,
            'artist': None,
            'uri': '/test'
        }
        results = engine._parse_response({'results': [item]})
        assert results[0]['title'] == ''
        assert results[0]['artist'] == 'Unknown Artist'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
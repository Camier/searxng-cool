#!/usr/bin/env python3
"""
Comprehensive test framework for SearXNG music engines
"""
import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import quote

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../searxng-core/searxng-core'))


class MusicEngineTestFramework:
    """Test framework for validating music search engines"""
    
    def __init__(self, base_url="http://localhost:8888"):
        self.base_url = base_url
        self.test_queries = {
            'generic': 'electronic music',
            'artist': 'radiohead',
            'album': 'dark side of the moon',
            'track': 'bohemian rhapsody',
            'classical': 'beethoven symphony',
            'jazz': 'miles davis',
            'world': 'ravi shankar',
            'podcast': 'joe rogan',  # For services that support podcasts
            'radio': 'bbc radio'     # For radio services
        }
        self.results = {}
        
    def test_engine(self, engine_name: str, shortcut: str, query_type: str = 'generic') -> Dict[str, Any]:
        """Test a single engine with specified query type"""
        query = self.test_queries.get(query_type, 'test')
        search_url = f"{self.base_url}/search?q={quote(f'!{shortcut} {query}')}"
        
        result = {
            'engine': engine_name,
            'shortcut': shortcut,
            'query': query,
            'query_type': query_type,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'response_time': 0,
            'result_count': 0,
            'errors': [],
            'warnings': [],
            'metadata': {}
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.get(search_url, timeout=15)
            result['response_time'] = time.time() - start_time
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                # Parse HTML response
                content = response.text
                
                # Count results
                result['result_count'] = content.count('result-default')
                
                # Check for specific engine results
                if result['result_count'] > 0:
                    result['success'] = True
                    
                    # Validate expected fields based on engine type
                    self._validate_results(engine_name, content, result)
                    
                    # Extract metadata
                    self._extract_metadata(engine_name, content, result)
                else:
                    result['errors'].append("No results found")
                    
            else:
                result['errors'].append(f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            result['errors'].append("Request timeout")
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            
        return result
    
    def _validate_results(self, engine_name: str, content: str, result: Dict[str, Any]):
        """Validate engine-specific requirements"""
        content_lower = content.lower()
        
        # Common validations
        if 'thumbnail' not in content_lower and 'img' not in content_lower:
            result['warnings'].append("No thumbnails found")
            
        # Engine-specific validations
        validations = {
            'archive_audio': {
                'required': ['archive.org', 'identifier'],
                'optional': ['downloads', 'collection']
            },
            'genius': {
                'required': ['genius.com', 'lyrics'],
                'optional': ['verified', 'annotation']
            },
            'youtube_music': {
                'required': ['youtube.com', 'watch'],
                'optional': ['duration', 'views']
            },
            'soundcloud_enhanced': {
                'required': ['soundcloud.com', 'play'],
                'optional': ['waveform', 'download', 'likes']
            },
            'bandcamp_enhanced': {
                'required': ['bandcamp.com'],
                'optional': ['price', 'format', 'label']
            }
        }
        
        if engine_name in validations:
            for field in validations[engine_name]['required']:
                if field not in content_lower:
                    result['errors'].append(f"Missing required field: {field}")
                    
            for field in validations[engine_name]['optional']:
                if field not in content_lower:
                    result['warnings'].append(f"Missing optional field: {field}")
    
    def _extract_metadata(self, engine_name: str, content: str, result: Dict[str, Any]):
        """Extract engine-specific metadata"""
        # Count specific features
        result['metadata']['has_thumbnails'] = 'thumbnail' in content.lower()
        result['metadata']['has_audio_preview'] = 'iframe' in content.lower()
        result['metadata']['has_download_links'] = 'download' in content.lower()
        
        # Engine-specific metadata
        if 'archive.org' in content:
            result['metadata']['has_collection_info'] = 'collection' in content.lower()
            result['metadata']['has_download_count'] = 'downloads' in content.lower()
            
        elif 'genius.com' in content:
            result['metadata']['has_lyrics'] = 'lyrics' in content.lower()
            result['metadata']['has_annotations'] = 'annotation' in content.lower()
            
    def test_all_engines(self, engines: List[Dict[str, str]]) -> Dict[str, Any]:
        """Test all provided engines"""
        results = {
            'test_run': datetime.now().isoformat(),
            'base_url': self.base_url,
            'total_engines': len(engines),
            'engines_tested': 0,
            'successful': 0,
            'failed': 0,
            'engine_results': {},
            'summary': {}
        }
        
        for engine in engines:
            engine_name = engine['name']
            shortcut = engine['shortcut']
            query_types = engine.get('query_types', ['generic'])
            
            print(f"\n🔍 Testing {engine_name} ({shortcut})...")
            
            engine_results = []
            for query_type in query_types:
                print(f"  - Query type: {query_type}")
                result = self.test_engine(engine_name, shortcut, query_type)
                engine_results.append(result)
                
                if result['success']:
                    print(f"    ✅ Success: {result['result_count']} results in {result['response_time']:.2f}s")
                else:
                    print(f"    ❌ Failed: {', '.join(result['errors'])}")
                    
            results['engine_results'][engine_name] = engine_results
            results['engines_tested'] += 1
            
            # Update counters
            if all(r['success'] for r in engine_results):
                results['successful'] += 1
            else:
                results['failed'] += 1
                
        # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary statistics"""
        summary = {
            'success_rate': (results['successful'] / results['total_engines'] * 100) if results['total_engines'] > 0 else 0,
            'average_response_time': 0,
            'fastest_engine': None,
            'slowest_engine': None,
            'most_results': None,
            'common_errors': {},
            'common_warnings': {}
        }
        
        # Calculate statistics
        response_times = []
        for engine_name, engine_results in results['engine_results'].items():
            for result in engine_results:
                if result['success']:
                    response_times.append((engine_name, result['response_time'], result['result_count']))
                    
                # Track common errors/warnings
                for error in result['errors']:
                    summary['common_errors'][error] = summary['common_errors'].get(error, 0) + 1
                for warning in result['warnings']:
                    summary['common_warnings'][warning] = summary['common_warnings'].get(warning, 0) + 1
                    
        if response_times:
            summary['average_response_time'] = sum(rt[1] for rt in response_times) / len(response_times)
            summary['fastest_engine'] = min(response_times, key=lambda x: x[1])
            summary['slowest_engine'] = max(response_times, key=lambda x: x[1])
            summary['most_results'] = max(response_times, key=lambda x: x[2])
            
        return summary
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save test results to file"""
        if filename is None:
            filename = f"/tmp/music_engine_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"\n💾 Test results saved to: {filename}")
        
    def print_summary(self, results: Dict[str, Any]):
        """Print a formatted summary of test results"""
        summary = results['summary']
        
        print("\n" + "=" * 50)
        print("📊 Music Engine Test Summary")
        print("=" * 50)
        print(f"Total Engines Tested: {results['engines_tested']}")
        print(f"✅ Successful: {results['successful']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Average Response Time: {summary['average_response_time']:.2f}s")
        
        if summary['fastest_engine']:
            print(f"\n⚡ Fastest Engine: {summary['fastest_engine'][0]} ({summary['fastest_engine'][1]:.2f}s)")
        if summary['slowest_engine']:
            print(f"🐌 Slowest Engine: {summary['slowest_engine'][0]} ({summary['slowest_engine'][1]:.2f}s)")
        if summary['most_results']:
            print(f"📈 Most Results: {summary['most_results'][0]} ({summary['most_results'][2]} results)")
            
        if summary['common_errors']:
            print("\n❌ Common Errors:")
            for error, count in sorted(summary['common_errors'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {error}: {count} occurrences")
                
        if summary['common_warnings']:
            print("\n⚠️ Common Warnings:")
            for warning, count in sorted(summary['common_warnings'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {warning}: {count} occurrences")


if __name__ == '__main__':
    # Define engines to test
    engines_to_test = [
        {
            'name': 'discogs_api',
            'shortcut': 'disc',
            'query_types': ['artist', 'album']
        },
        {
            'name': 'jamendo_music',
            'shortcut': 'jam',
            'query_types': ['generic', 'jazz']
        },
        {
            'name': 'archive_audio',
            'shortcut': 'arc',
            'query_types': ['generic', 'classical', 'podcast']
        },
        {
            'name': 'soundcloud',
            'shortcut': 'sc',
            'query_types': ['generic', 'artist']
        },
        {
            'name': 'bandcamp',
            'shortcut': 'bc',
            'query_types': ['generic', 'album']
        },
        {
            'name': 'genius_lyrics',
            'shortcut': 'gen',
            'query_types': ['artist', 'track']
        },
        {
            'name': 'youtube_music',
            'shortcut': 'ytm',
            'query_types': ['generic', 'artist', 'track']
        },
        {
            'name': 'soundcloud_enhanced',
            'shortcut': 'sce',
            'query_types': ['generic', 'artist']
        },
        {
            'name': 'bandcamp_enhanced',
            'shortcut': 'bce',
            'query_types': ['generic', 'album']
        },
        {
            'name': 'mixcloud',
            'shortcut': 'mc',
            'query_types': ['generic', 'jazz']
        },
        {
            'name': 'mixcloud_enhanced',
            'shortcut': 'mce',
            'query_types': ['generic', 'jazz']
        },
        {
            'name': 'radio_paradise',
            'shortcut': 'rp',
            'query_types': ['generic', 'artist']
        }
    ]
    
    # Run tests
    tester = MusicEngineTestFramework()
    results = tester.test_all_engines(engines_to_test)
    
    # Print and save results
    tester.print_summary(results)
    tester.save_results(results)
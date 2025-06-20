#!/usr/bin/env python3
import json
import os
from collections import defaultdict

def analyze_results():
    results_dir = "music_engine_results"
    
    # Track unique URLs by engine
    engine_urls = defaultdict(set)
    
    # Track all results by engine
    engine_results = defaultdict(list)
    
    # Track errors by engine
    engine_errors = defaultdict(list)
    
    # Process each result file
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and filename != 'summary.txt':
            filepath = os.path.join(results_dir, filename)
            
            with open(filepath, 'r') as f:
                try:
                    data = json.load(f)
                    
                    # Extract engine name from filename
                    parts = filename.replace('.json', '').split('_')
                    if 'enhanced' in filename:
                        engine = ' '.join(parts[:-2]) + ' enhanced'
                        query = parts[-1]
                    elif 'music' in filename or 'lyrics' in filename:
                        engine = ' '.join(parts[:-1])
                        query = parts[-1]
                    else:
                        engine = parts[0]
                        query = parts[1]
                    
                    # Check for errors
                    if 'error' in data:
                        engine_errors[engine].append({
                            'query': query,
                            'error': data['error']
                        })
                    elif 'results' in data:
                        # Analyze results
                        for result in data['results']:
                            url = result.get('url', '')
                            engine_urls[engine].add(url)
                            
                            # Store result info
                            engine_results[engine].append({
                                'query': query,
                                'title': result.get('title', 'No title'),
                                'url': url,
                                'engine_name': result.get('engine_name', 'Unknown'),
                                'metadata': result.get('metadata', {})
                            })
                
                except json.JSONDecodeError as e:
                    print(f"Error parsing {filename}: {e}")
    
    # Generate report
    print("=== Music Engine Analysis Report ===\n")
    
    # Check for duplicate results across engines
    all_urls = set()
    url_to_engines = defaultdict(list)
    
    for engine, urls in engine_urls.items():
        for url in urls:
            url_to_engines[url].append(engine)
            all_urls.add(url)
    
    # Find URLs that appear in multiple engines
    duplicate_urls = {url: engines for url, engines in url_to_engines.items() if len(engines) > 1}
    
    print(f"Total unique URLs across all engines: {len(all_urls)}")
    print(f"URLs appearing in multiple engines: {len(duplicate_urls)}\n")
    
    # Analyze each engine
    for engine in sorted(engine_urls.keys()):
        print(f"\n=== {engine.upper()} ===")
        
        # Basic stats
        total_results = len(engine_results[engine])
        unique_urls = len(engine_urls[engine])
        
        print(f"Total results: {total_results}")
        print(f"Unique URLs: {unique_urls}")
        
        # Sample results
        print("\nSample results:")
        seen_queries = set()
        for result in engine_results[engine][:10]:
            if result['query'] not in seen_queries:
                seen_queries.add(result['query'])
                print(f"  Query '{result['query']}': {result['title']}")
                if result['metadata']:
                    artist = result['metadata'].get('artist', 'Unknown')
                    track = result['metadata'].get('track', '')
                    if artist or track:
                        print(f"    Artist: {artist}, Track: {track}")
        
        # Check if this engine's results are unique
        engine_unique_urls = set()
        for url in engine_urls[engine]:
            if len(url_to_engines[url]) == 1:
                engine_unique_urls.add(url)
        
        print(f"\nURLs unique to this engine: {len(engine_unique_urls)}")
        
        # Errors
        if engine in engine_errors:
            print(f"\nErrors encountered:")
            for error in engine_errors[engine]:
                print(f"  Query '{error['query']}': {error['error']}")
    
    # Check if all engines return the same results
    print("\n\n=== DUPLICATE ANALYSIS ===")
    
    # Get results for a specific query across all engines
    query_results = defaultdict(lambda: defaultdict(list))
    
    for engine, results in engine_results.items():
        for result in results:
            query_results[result['query']][engine].append(result['url'])
    
    # Check if results are identical
    for query in ['electronic', 'jazz', 'rock', 'test']:
        print(f"\nQuery: '{query}'")
        engines_with_query = query_results[query]
        
        if engines_with_query:
            # Get URLs from first engine as reference
            reference_engine = list(engines_with_query.keys())[0]
            reference_urls = set(engines_with_query[reference_engine])
            
            identical_count = 0
            different_count = 0
            
            for engine, urls in engines_with_query.items():
                if set(urls) == reference_urls:
                    identical_count += 1
                else:
                    different_count += 1
            
            print(f"  Engines with identical results: {identical_count}")
            print(f"  Engines with different results: {different_count}")
            
            if identical_count == len(engines_with_query):
                print(f"  WARNING: All {identical_count} engines returned identical results!")

if __name__ == "__main__":
    analyze_results()
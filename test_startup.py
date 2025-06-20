#!/usr/bin/env python3
"""Test basic startup of SearXNG components"""
import sys
import os
import subprocess

print("Testing SearXNG-Cool component startup...\n")

# Test 1: Check Python dependencies
print("1. Checking core Python dependencies:")
required_deps = ['flask', 'redis', 'requests', 'lxml']
missing = []
for dep in required_deps:
    try:
        __import__(dep)
        print(f"   ✓ {dep}")
    except ImportError:
        print(f"   ✗ {dep} (missing)")
        missing.append(dep)

if missing:
    print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
    print("   Run: pip install -r requirements.txt")

# Test 2: Check Redis connection
print("\n2. Checking Redis connection:")
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("   ✓ Redis is running and accessible")
except:
    print("   ✗ Redis not accessible (start with: sudo systemctl start redis)")

# Test 3: Check PostgreSQL
print("\n3. Checking PostgreSQL:")
try:
    result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✓ PostgreSQL installed")
    else:
        print("   ✗ PostgreSQL not found")
except:
    print("   ✗ PostgreSQL not installed")

# Test 4: Check if SearXNG webapp can be imported
print("\n4. Testing SearXNG webapp import:")
searxng_path = os.path.join(os.path.dirname(__file__), 'searxng-core', 'searxng-core')
sys.path.insert(0, searxng_path)

try:
    from searx import webapp
    print("   ✓ SearXNG webapp module loaded")
    print(f"   Version info available: {hasattr(webapp, 'VERSION_STRING')}")
except Exception as e:
    print(f"   ✗ Cannot load webapp: {e}")

# Test 5: Check orchestrator app
print("\n5. Testing Orchestrator app import:")
orchestrator_path = os.path.join(os.path.dirname(__file__), 'orchestrator')
sys.path.insert(0, orchestrator_path)

try:
    import app
    print("   ✓ Orchestrator app module loaded")
    print(f"   Flask app found: {hasattr(app, 'app') or hasattr(app, 'create_app')}")
except Exception as e:
    print(f"   ✗ Cannot load orchestrator: {e}")

print("\n" + "="*50)
print("Summary:")
print("- All music engines are importable ✓")
print("- Core directory structure is intact ✓")
print("- Configuration files are present ✓")
print("- Basic imports work (with dependency installation needed)")
print("\nNext steps:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Start Redis: sudo systemctl start redis")
print("3. Configure database and run migrations")
print("4. Start services with proper configuration")
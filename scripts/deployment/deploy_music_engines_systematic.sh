#!/bin/bash
# Systematic deployment of music engines for SearXNG-Cool
# Following established deployment patterns with validation and rollback

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Deployment configuration
DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/music_engines_$DEPLOYMENT_ID"
LOG_DIR="logs/deployment"
DEPLOYMENT_LOG="$LOG_DIR/music_engines_$DEPLOYMENT_ID.log"

# Function to log messages
log() {
    local level=$1
    shift
    local message="$@"
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$DEPLOYMENT_LOG"
}

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

# Create deployment directories
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

echo "🎵 SearXNG-Cool Music Engines Systematic Deployment"
echo "=================================================="
echo "Deployment ID: $DEPLOYMENT_ID"
echo ""

log "INFO" "Starting music engines deployment"

# Step 1: Pre-deployment validation
echo "📋 Step 1: Pre-deployment Validation"
echo "-----------------------------------"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "searxng-core" ]; then
    print_status "error" "Must run from searxng-cool root directory"
    exit 1
fi
print_status "success" "Running from correct directory"

# Check git status
if ! git diff --quiet; then
    print_status "warning" "Uncommitted changes detected"
    read -p "Continue with uncommitted changes? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        print_status "info" "Activating virtual environment"
        source venv/bin/activate
    else
        print_status "error" "No virtual environment found"
        exit 1
    fi
fi
print_status "success" "Python environment ready"

# Step 2: API Key Validation
echo ""
echo "🔑 Step 2: API Key Validation"
echo "----------------------------"

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_status "warning" "No .env file found"
        echo "Required API keys:"
        echo "  - DISCOGS_API_TOKEN"
        echo "  - JAMENDO_API_KEY"
        
        read -p "Create .env from template? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            print_status "info" "Created .env - please add your API keys and re-run"
            exit 0
        else
            print_status "warning" "Proceeding without API keys"
        fi
    fi
else
    # Validate API keys
    python -c "
from music.load_api_keys import validate_music_engine_keys
if validate_music_engine_keys():
    print('✅ At least one music engine has valid API keys')
else:
    print('⚠️  No valid API keys found - some engines will be disabled')
"
fi

# Step 3: Backup current state
echo ""
echo "💾 Step 3: Creating Backup"
echo "-------------------------"

# Backup SearXNG settings
if [ -f "searxng-core/searxng-core/searx/settings.yml" ]; then
    cp "searxng-core/searxng-core/searx/settings.yml" "$BACKUP_DIR/settings.yml.backup"
    print_status "success" "Backed up settings.yml"
fi

# Backup existing music engines if any
if [ -d "searxng-core/searxng-core/searx/engines/music" ]; then
    cp -r "searxng-core/searxng-core/searx/engines/music" "$BACKUP_DIR/"
    print_status "success" "Backed up existing music engines"
fi

# Create rollback script
cat > "$BACKUP_DIR/rollback.sh" << 'EOF'
#!/bin/bash
echo "🔄 Rolling back music engines deployment..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../.."

# Restore settings
if [ -f "$SCRIPT_DIR/settings.yml.backup" ]; then
    cp "$SCRIPT_DIR/settings.yml.backup" searxng-core/searxng-core/searx/settings.yml
    echo "✅ Restored settings.yml"
fi

# Restore music engines
if [ -d "$SCRIPT_DIR/music" ]; then
    rm -rf searxng-core/searxng-core/searx/engines/music
    cp -r "$SCRIPT_DIR/music" searxng-core/searxng-core/searx/engines/
    echo "✅ Restored music engines"
fi

echo "✅ Rollback complete"
EOF

chmod +x "$BACKUP_DIR/rollback.sh"
print_status "success" "Created rollback script: $BACKUP_DIR/rollback.sh"

# Step 4: Install dependencies
echo ""
echo "📦 Step 4: Installing Dependencies"
echo "---------------------------------"

pip install -q redis requests pytest pytest-cov python-dotenv
print_status "success" "Python dependencies installed"

# Step 5: Deploy music engines
echo ""
echo "🚀 Step 5: Deploying Music Engines"
echo "---------------------------------"

# Ensure music engines are in the right place
if [ ! -d "searxng-core/searxng-core/searx/engines/music" ]; then
    print_status "error" "Music engines directory not found in searxng-core"
    print_status "info" "The engines should be in: searxng-core/searxng-core/searx/engines/music/"
    exit 1
fi

print_status "success" "Music engines found in correct location"

# Step 6: Update SearXNG settings
echo ""
echo "⚙️  Step 6: Updating SearXNG Configuration"
echo "----------------------------------------"

SETTINGS_FILE="searxng-core/searxng-core/searx/settings.yml"

# Check if music engines are already configured
if grep -q "engine: music.discogs" "$SETTINGS_FILE" 2>/dev/null; then
    print_status "info" "Music engines already configured in settings.yml"
else
    print_status "warning" "Music engines not found in settings.yml"
    echo ""
    echo "Add the following to the 'engines:' section of $SETTINGS_FILE:"
    echo ""
    cat << 'EOF'
  - name: discogs
    engine: music.discogs
    shortcut: disc
    categories: music
    timeout: 10.0
    disabled: false
    
  - name: jamendo
    engine: music.jamendo
    shortcut: jam
    categories: music
    timeout: 5.0
    disabled: false
    
  - name: soundcloud
    engine: music.soundcloud
    shortcut: sc
    categories: music
    timeout: 8.0
    disabled: false
    
  - name: bandcamp
    engine: music.bandcamp
    shortcut: bc
    categories: music
    timeout: 10.0
    disabled: false
EOF
    echo ""
    read -p "Would you like me to add these automatically? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # This is a simplified addition - in production you'd use a proper YAML parser
        echo "⚠️  Manual edit required - automatic YAML editing not implemented"
        echo "Please add the engines manually to $SETTINGS_FILE"
    fi
fi

# Step 7: Run tests
echo ""
echo "🧪 Step 7: Running Tests"
echo "-----------------------"

# Run unit tests
cd music/tests
if python -m pytest test_discogs.py -v; then
    print_status "success" "Unit tests passed"
else
    print_status "warning" "Some unit tests failed"
fi
cd ../..

# Step 8: Restart services
echo ""
echo "🔄 Step 8: Restarting Services"
echo "-----------------------------"

# Check if services are running
if pgrep -f "searx.webapp" > /dev/null; then
    print_status "info" "SearXNG is running"
    read -p "Restart SearXNG to apply changes? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Kill existing SearXNG
        pkill -f "searx.webapp" || true
        sleep 2
        
        # Start SearXNG
        cd searxng-core/searxng-core
        source ../searxng-venv/bin/activate
        nohup python -m searx.webapp --host 127.0.0.1 --port 8888 > ../../logs/searxng.log 2>&1 &
        cd ../..
        
        sleep 5
        print_status "success" "SearXNG restarted"
    fi
else
    print_status "warning" "SearXNG not running - start it manually"
fi

# Step 9: Validation
echo ""
echo "✅ Step 9: Post-deployment Validation"
echo "------------------------------------"

# Run music engine validator
if [ -f ".env" ]; then
    print_status "info" "Running music engine validation..."
    python validation/music_engine_validator.py || true
else
    print_status "warning" "Skipping validation - no .env file"
fi

# Step 10: Start monitoring
echo ""
echo "📊 Step 10: Monitoring Setup"
echo "---------------------------"

read -p "Start validation workers for continuous monitoring? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./validation/start_workers.sh
fi

# Summary
echo ""
echo "🎉 Deployment Summary"
echo "===================="
echo "Deployment ID: $DEPLOYMENT_ID"
echo "Backup Location: $BACKUP_DIR"
echo "Rollback Script: $BACKUP_DIR/rollback.sh"
echo "Logs: $DEPLOYMENT_LOG"
echo ""
echo "📋 Next Steps:"
echo "1. If not done automatically, add music engines to settings.yml"
echo "2. Restart all services (./start-all-services.sh)"
echo "3. Test music search:"
echo "   - !disc aphex twin"
echo "   - !jam electronic"
echo "   - !sc techno"
echo "   - !bc ambient"
echo ""
echo "🔄 To rollback: $BACKUP_DIR/rollback.sh"
echo ""

log "INFO" "Music engines deployment completed"

# Git status reminder
if ! git diff --quiet; then
    echo "📝 Don't forget to commit your changes:"
    echo "   git add -A"
    echo "   git commit -m 'feat: Add music search engines to SearXNG'"
fi
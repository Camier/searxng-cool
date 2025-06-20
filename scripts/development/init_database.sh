#!/bin/bash
"""
Development Database Initialization Script
Sets up SearXNG-Cool database for development with comprehensive validation
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DB_UTILS_DIR="$PROJECT_ROOT/scripts/utilities/database"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if virtual environment is active
check_virtualenv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        error "Virtual environment not activated!"
        echo "Please run: source venv/bin/activate"
        exit 1
    fi
    success "Virtual environment active: $VIRTUAL_ENV"
}

# Check if required files exist
check_dependencies() {
    log "Checking dependencies..."
    
    local required_files=(
        "$PROJECT_ROOT/config/orchestrator.yml"
        "$PROJECT_ROOT/migrations/migration_app.py"
        "$DB_UTILS_DIR/db_manager.py"
        "$DB_UTILS_DIR/db_cli.py"
        "$DB_UTILS_DIR/db_validator.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file missing: $file"
            exit 1
        fi
    done
    
    success "All required files present"
}

# Check PostgreSQL service
check_postgresql() {
    log "Checking PostgreSQL service..."
    
    if ! command -v pg_isready &> /dev/null; then
        error "PostgreSQL client tools not found!"
        echo "Install with: sudo apt-get install postgresql-client"
        exit 1
    fi
    
    # Test if PostgreSQL is accessible
    if ! pg_isready -h localhost &> /dev/null; then
        error "PostgreSQL server not accessible!"
        echo "Make sure PostgreSQL is running: sudo systemctl start postgresql"
        exit 1
    fi
    
    success "PostgreSQL service accessible"
}

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Install from requirements if it exists
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
    fi
    
    # Install additional database-specific dependencies
    pip install psycopg2-binary click tabulate
    
    success "Python dependencies installed"
}

# Test database connection
test_connection() {
    log "Testing database connection..."
    
    cd "$PROJECT_ROOT"
    
    if python -c "
import sys
sys.path.insert(0, '.')
from scripts.utilities.database.db_manager import DatabaseManager
db_manager = DatabaseManager()
if db_manager.test_connection():
    print('✅ Database connection successful')
    sys.exit(0)
else:
    print('❌ Database connection failed')
    sys.exit(1)
" 2>/dev/null; then
        success "Database connection verified"
    else
        error "Database connection failed!"
        echo ""
        echo "Please check:"
        echo "1. PostgreSQL is running: sudo systemctl status postgresql"
        echo "2. Database exists: sudo -u postgres createdb searxng_cool_music"
        echo "3. User has permissions: sudo -u postgres createuser -s searxng_user"
        echo "4. Configuration is correct in config/orchestrator.yml"
        exit 1
    fi
}

# Run database initialization
initialize_database() {
    log "Initializing database with CLI tool..."
    
    cd "$PROJECT_ROOT"
    
    # Make CLI executable
    chmod +x "$DB_UTILS_DIR/db_cli.py"
    
    # Run initialization
    if python "$DB_UTILS_DIR/db_cli.py" init; then
        success "Database initialization completed"
    else
        error "Database initialization failed!"
        exit 1
    fi
}

# Run validation suite
run_validation() {
    log "Running comprehensive validation suite..."
    
    cd "$PROJECT_ROOT"
    
    if python "$DB_UTILS_DIR/db_validator.py"; then
        success "All validation tests passed"
    else
        warning "Some validation tests failed - check output above"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Display final status
show_status() {
    log "Displaying final database status..."
    
    cd "$PROJECT_ROOT"
    python "$DB_UTILS_DIR/db_cli.py" status
}

# Create helpful aliases and shortcuts
create_shortcuts() {
    log "Creating helpful shortcuts..."
    
    local shortcuts_file="$PROJECT_ROOT/db_shortcuts.sh"
    
    cat > "$shortcuts_file" << 'EOF'
#!/bin/bash
# Database shortcuts for SearXNG-Cool development

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_CLI="$PROJECT_ROOT/scripts/utilities/database/db_cli.py"

# Shortcut functions
alias db-status="python $DB_CLI status"
alias db-health="python $DB_CLI status"
alias db-migrate="python $DB_CLI migrate"
alias db-upgrade="python $DB_CLI upgrade"
alias db-backup="python $DB_CLI backup"
alias db-optimize="python $DB_CLI optimize"
alias db-validate="python $PROJECT_ROOT/scripts/utilities/database/db_validator.py"

# Helper functions
db-init() {
    echo "🚀 Initializing database..."
    python "$DB_CLI" init
}

db-reset() {
    echo "⚠️ This will reset the database! All data will be lost."
    read -p "Are you sure? Type 'reset' to confirm: " confirm
    if [[ "$confirm" == "reset" ]]; then
        python "$DB_CLI" downgrade base
        python "$DB_CLI" upgrade
        echo "✅ Database reset completed"
    else
        echo "❌ Reset cancelled"
    fi
}

db-quick-backup() {
    backup_name="backup_$(date +%Y%m%d_%H%M%S).sql"
    python "$DB_CLI" backup "$backup_name"
    echo "✅ Backup created: $backup_name"
}

echo "📊 Database shortcuts loaded!"
echo "Available commands:"
echo "  db-status      - Show database status"
echo "  db-migrate     - Create new migration"
echo "  db-upgrade     - Apply migrations"
echo "  db-backup      - Create backup"
echo "  db-optimize    - Optimize database"
echo "  db-validate    - Run validation suite"
echo "  db-init        - Initialize database"
echo "  db-reset       - Reset database (DANGEROUS)"
echo "  db-quick-backup - Quick backup with timestamp"
EOF

    chmod +x "$shortcuts_file"
    
    success "Shortcuts created: $shortcuts_file"
    echo "To load shortcuts: source db_shortcuts.sh"
}

# Main execution
main() {
    echo "🚀 SearXNG-Cool Database Development Setup"
    echo "=========================================="
    echo ""
    
    # Pre-flight checks
    check_virtualenv
    check_dependencies
    check_postgresql
    
    # Setup
    install_dependencies
    test_connection
    
    # Database operations
    initialize_database
    run_validation
    
    # Finalization
    create_shortcuts
    show_status
    
    echo ""
    echo "🎉 Database development setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Load shortcuts: source db_shortcuts.sh"
    echo "2. Check status: db-status"
    echo "3. Start developing!"
    echo ""
    echo "For more commands: python scripts/utilities/database/db_cli.py --help"
}

# Handle script interruption
trap 'error "Setup interrupted!"; exit 1' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
#!/usr/bin/env python3
"""
Database Management CLI for SearXNG-Cool
Production-grade command-line interface for database operations
"""

import os
import sys
import click
import logging
import subprocess
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from db_manager import DatabaseManager, DatabaseHealth, MigrationStatus
from orchestrator.config_loader import load_config, validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """SearXNG-Cool Database Management CLI
    
    Production-grade database management with safety checks and monitoring.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        config = load_config()
        validate_config(config)
        ctx.obj['db_manager'] = DatabaseManager(config)
    except Exception as e:
        click.echo(f"❌ Failed to initialize database manager: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize database with comprehensive validation and setup"""
    click.echo("🚀 Initializing SearXNG-Cool database...")
    
    db_manager = ctx.obj['db_manager']
    
    # Step 1: Test connectivity
    click.echo("\n1️⃣ Testing database connectivity...")
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed. Please check your configuration.", err=True)
        sys.exit(1)
    click.echo("✅ Database connection successful")
    
    # Step 2: Check migration status
    click.echo("\n2️⃣ Checking migration status...")
    migration_status = db_manager.get_migration_status()
    click.echo(f"Current revision: {migration_status.current_revision or 'None'}")
    
    if not migration_status.is_up_to_date:
        click.echo("⚠️ Database migrations are not up to date")
        if click.confirm("Run database migrations now?"):
            if not _run_migrations():
                click.echo("❌ Migration failed", err=True)
                sys.exit(1)
        else:
            click.echo("⚠️ Database initialization incomplete - migrations not applied")
            sys.exit(1)
    else:
        click.echo("✅ Database migrations are up to date")
    
    # Step 3: Health check
    click.echo("\n3️⃣ Performing health check...")
    health = db_manager.check_database_health()
    _display_health_status(health)
    
    # Step 4: Optimization
    if health.issues:
        click.echo("\n4️⃣ Issues detected - running optimization...")
        if click.confirm("Run database optimization to fix issues?"):
            _run_optimization(db_manager)
    
    click.echo("\n🎉 Database initialization completed successfully!")


@cli.command()
@click.pass_context
def status(ctx):
    """Show comprehensive database status and health information"""
    db_manager = ctx.obj['db_manager']
    
    click.echo("📊 SearXNG-Cool Database Status\n")
    
    # Connection test
    click.echo("🔗 Connection Status:")
    if db_manager.test_connection():
        click.echo("  ✅ Database is accessible")
    else:
        click.echo("  ❌ Database connection failed")
        return
    
    # Migration status
    click.echo("\n📋 Migration Status:")
    migration_status = db_manager.get_migration_status()
    click.echo(f"  Current revision: {migration_status.current_revision or 'None'}")
    click.echo(f"  Up to date: {'✅' if migration_status.is_up_to_date else '❌'}")
    
    # Health check
    click.echo("\n🏥 Health Check:")
    health = db_manager.check_database_health()
    _display_health_status(health, detailed=True)


@cli.command()
@click.option('--message', '-m', required=True, help='Migration description')
@click.option('--autogenerate', is_flag=True, help='Auto-generate migration from model changes')
@click.pass_context
def migrate(ctx, message, autogenerate):
    """Create a new database migration"""
    click.echo(f"📝 Creating migration: {message}")
    
    db_manager = ctx.obj['db_manager']
    
    # Safety check
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed", err=True)
        sys.exit(1)
    
    # Create backup before migration
    if click.confirm("Create backup before generating migration?"):
        backup_path = f"backup_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        if db_manager.backup_database(backup_path):
            click.echo(f"✅ Backup created: {backup_path}")
        else:
            click.echo("❌ Backup failed", err=True)
            if not click.confirm("Continue without backup?"):
                sys.exit(1)
    
    # Generate migration
    try:
        cmd = [
            sys.executable, '-m', 'flask', 'db', 'migrate',
            '-m', message
        ]
        
        if autogenerate:
            cmd.append('--rev-id')
            cmd.append(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.lower().replace(' ', '_')}")
        
        env = os.environ.copy()
        env['FLASK_APP'] = 'migrations/migration_app.py'
        
        result = subprocess.run(
            cmd,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..'),
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            click.echo("✅ Migration created successfully")
            click.echo(result.stdout)
        else:
            click.echo(f"❌ Migration creation failed: {result.stderr}", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ Migration creation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--revision', help='Target revision (default: latest)')
@click.option('--backup/--no-backup', default=True, help='Create backup before upgrade')
@click.pass_context
def upgrade(ctx, revision, backup):
    """Upgrade database to latest or specified revision"""
    click.echo("⬆️ Upgrading database...")
    
    db_manager = ctx.obj['db_manager']
    
    # Safety checks
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed", err=True)
        sys.exit(1)
    
    if backup:
        backup_path = f"backup_pre_upgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        click.echo(f"📦 Creating backup: {backup_path}")
        if not db_manager.backup_database(backup_path):
            click.echo("❌ Backup failed", err=True)
            if not click.confirm("Continue without backup?"):
                sys.exit(1)
    
    if not _run_migrations(revision):
        click.echo("❌ Database upgrade failed", err=True)
        sys.exit(1)
    
    click.echo("✅ Database upgrade completed successfully")


@cli.command()
@click.option('--revision', help='Target revision')
@click.option('--backup/--no-backup', default=True, help='Create backup before downgrade')
@click.pass_context
def downgrade(ctx, revision, backup):
    """Downgrade database to specified revision"""
    if not revision:
        click.echo("❌ Revision is required for downgrade", err=True)
        sys.exit(1)
    
    click.echo(f"⬇️ Downgrading database to revision: {revision}")
    
    if not click.confirm("⚠️ This operation may cause data loss. Continue?"):
        click.echo("Operation cancelled")
        return
    
    db_manager = ctx.obj['db_manager']
    
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed", err=True)
        sys.exit(1)
    
    if backup:
        backup_path = f"backup_pre_downgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        click.echo(f"📦 Creating backup: {backup_path}")
        if not db_manager.backup_database(backup_path):
            click.echo("❌ Backup failed", err=True)
            sys.exit(1)
    
    try:
        env = os.environ.copy()
        env['FLASK_APP'] = 'migrations/migration_app.py'
        
        result = subprocess.run([
            sys.executable, '-m', 'flask', 'db', 'downgrade', revision
        ], cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..'),
           env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Database downgrade completed successfully")
        else:
            click.echo(f"❌ Downgrade failed: {result.stderr}", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ Downgrade failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def optimize(ctx):
    """Run comprehensive database optimization"""
    click.echo("🔧 Optimizing database...")
    
    db_manager = ctx.obj['db_manager']
    
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed", err=True)
        sys.exit(1)
    
    _run_optimization(db_manager)


@cli.command()
@click.argument('backup_path', type=click.Path())
@click.option('--compress/--no-compress', default=True, help='Compress backup')
@click.pass_context
def backup(ctx, backup_path, compress):
    """Create database backup"""
    click.echo(f"📦 Creating database backup: {backup_path}")
    
    db_manager = ctx.obj['db_manager']
    
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed", err=True)
        sys.exit(1)
    
    if db_manager.backup_database(backup_path, compression=compress):
        click.echo("✅ Backup created successfully")
    else:
        click.echo("❌ Backup failed", err=True)
        sys.exit(1)


def _run_migrations(revision: Optional[str] = None) -> bool:
    """Run database migrations"""
    try:
        env = os.environ.copy()
        env['FLASK_APP'] = 'migrations/migration_app.py'
        
        cmd = [sys.executable, '-m', 'flask', 'db', 'upgrade']
        if revision:
            cmd.append(revision)
        
        result = subprocess.run(
            cmd,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..'),
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            click.echo("✅ Migrations applied successfully")
            return True
        else:
            click.echo(f"❌ Migration failed: {result.stderr}", err=True)
            return False
    
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)
        return False


def _run_optimization(db_manager: DatabaseManager) -> None:
    """Run database optimization tasks"""
    click.echo("Running optimization tasks...")
    
    results = db_manager.optimize_database()
    
    for task, success in results.items():
        status = "✅" if success else "❌"
        click.echo(f"  {status} {task.replace('_', ' ').title()}")
    
    # Final health check
    click.echo("\nPost-optimization health check:")
    health = db_manager.check_database_health()
    _display_health_status(health)


def _display_health_status(health: DatabaseHealth, detailed: bool = False) -> None:
    """Display database health status"""
    status_icon = "✅" if health.is_healthy else "❌"
    click.echo(f"  {status_icon} Overall health: {'Healthy' if health.is_healthy else 'Issues detected'}")
    click.echo(f"  📊 Connections: {health.active_connections}/{health.connection_count}")
    click.echo(f"  📈 Index usage: {health.index_usage}%")
    click.echo(f"  🐌 Slow queries: {health.slow_queries}")
    
    if detailed and health.table_bloat:
        click.echo("  📊 Table bloat:")
        for table, bloat in health.table_bloat.items():
            if bloat > 10:  # Only show significant bloat
                click.echo(f"    - {table}: {bloat}%")
    
    if health.issues:
        click.echo("  ⚠️ Issues:")
        for issue in health.issues:
            click.echo(f"    - {issue}")
    
    if health.recommendations:
        click.echo("  💡 Recommendations:")
        for rec in health.recommendations:
            click.echo(f"    - {rec}")


if __name__ == "__main__":
    cli()
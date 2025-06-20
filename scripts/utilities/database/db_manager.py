#!/usr/bin/env python3
"""
Core Database Management Utilities for SearXNG-Cool
Production-grade database utilities with retry logic, monitoring, and safety checks
"""

import os
import sys
import time
import logging
import psycopg2
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from orchestrator.config_loader import load_config, get_database_uri, validate_config

logger = logging.getLogger(__name__)


@dataclass
class DatabaseHealth:
    """Database health check result"""
    is_healthy: bool
    connection_count: int
    active_connections: int
    slow_queries: int
    index_usage: float
    table_bloat: Dict[str, float]
    issues: List[str]
    recommendations: List[str]


@dataclass
class MigrationStatus:
    """Migration status information"""
    current_revision: Optional[str]
    pending_migrations: List[str]
    is_up_to_date: bool
    last_migration_date: Optional[datetime]


class DatabaseManager:
    """
    Production database management with safety checks and monitoring.
    
    Provides secure database operations with:
    - Connection retry logic
    - Transaction safety
    - Performance monitoring
    - Backup verification
    - Migration safety
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, max_retries: int = 3):
        """
        Initialize database manager.
        
        Args:
            config: Configuration dictionary. If None, loads from orchestrator.yml
            max_retries: Maximum connection retry attempts
        """
        self.config = config or load_config()
        self.database_uri = get_database_uri(self.config)
        self.max_retries = max_retries
        self._connection_pool = None
        
        # Parse database URI for connection parameters
        self._parse_database_uri()
    
    def _parse_database_uri(self) -> None:
        """Parse database URI to extract connection parameters"""
        import urllib.parse as urlparse
        
        parsed = urlparse.urlparse(self.database_uri)
        self.db_params = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password
        }
    
    @contextmanager
    def get_connection(self, autocommit: bool = False):
        """
        Get database connection with retry logic and proper cleanup.
        
        Args:
            autocommit: Whether to use autocommit mode
            
        Yields:
            psycopg2.connection: Database connection
            
        Raises:
            psycopg2.Error: If connection fails after retries
        """
        connection = None
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                connection = psycopg2.connect(**self.db_params)
                connection.autocommit = autocommit
                
                logger.debug(f"✅ Database connection established (attempt {retry_count + 1})")
                yield connection
                return
                
            except psycopg2.Error as e:
                retry_count += 1
                if connection:
                    connection.close()
                
                if retry_count >= self.max_retries:
                    logger.error(f"❌ Database connection failed after {self.max_retries} attempts: {e}")
                    raise
                
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"⚠️ Database connection attempt {retry_count} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            
            finally:
                if connection and not connection.closed:
                    connection.close()
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            bool: True if connection successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_migration_status(self) -> MigrationStatus:
        """
        Get current migration status.
        
        Returns:
            MigrationStatus: Current migration information
        """
        try:
            # Use flask db commands to get migration status
            result = subprocess.run(
                [sys.executable, '-c', '''
import sys, os
sys.path.insert(0, os.getcwd())
os.environ["FLASK_APP"] = "migrations/migration_app.py"
from flask_migrate import current as get_current
from migrations.migration_app import app
with app.app_context():
    current_rev = get_current()
    print(current_rev if current_rev else "None")
                '''],
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..')
            )
            
            current_revision = result.stdout.strip() if result.stdout.strip() != "None" else None
            
            # Get pending migrations
            pending_result = subprocess.run(
                [sys.executable, '-c', '''
import sys, os
sys.path.insert(0, os.getcwd())
os.environ["FLASK_APP"] = "migrations/migration_app.py"
from alembic import command
from flask_migrate import upgrade
from migrations.migration_app import app
with app.app_context():
    from flask_migrate import _get_config
    config = _get_config()
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    print(",".join(heads) if heads else "")
                '''],
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..')
            )
            
            heads = pending_result.stdout.strip().split(',') if pending_result.stdout.strip() else []
            is_up_to_date = current_revision in heads if heads else True
            
            return MigrationStatus(
                current_revision=current_revision,
                pending_migrations=[],
                is_up_to_date=is_up_to_date,
                last_migration_date=None
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get migration status: {e}")
            return MigrationStatus(
                current_revision=None,
                pending_migrations=[],
                is_up_to_date=False,
                last_migration_date=None
            )
    
    def check_database_health(self) -> DatabaseHealth:
        """
        Perform comprehensive database health check.
        
        Returns:
            DatabaseHealth: Health check results with recommendations
        """
        issues = []
        recommendations = []
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check connection statistics
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_connections,
                            COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                            COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                    """)
                    conn_stats = cursor.fetchone()
                    
                    # Check for slow queries
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM pg_stat_statements 
                            WHERE mean_exec_time > 1000
                        """)
                        slow_query_count = cursor.fetchone()[0]
                    except psycopg2.ProgrammingError:
                        slow_query_count = 0
                        recommendations.append("Install pg_stat_statements extension for query analysis")
                    
                    # Check index usage
                    cursor.execute("""
                        SELECT 
                            ROUND(
                                100.0 * SUM(idx_scan) / NULLIF(SUM(seq_scan + idx_scan), 0), 
                                2
                            ) as index_usage_percent
                        FROM pg_stat_user_tables
                    """)
                    index_usage_result = cursor.fetchone()
                    index_usage = index_usage_result[0] if index_usage_result[0] else 0
                    
                    # Check table bloat
                    cursor.execute("""
                        SELECT 
                            relname as table_name,
                            CASE 
                                WHEN n_live_tup > 0 
                                THEN ROUND(100.0 * n_dead_tup / n_live_tup, 2)
                                ELSE 0 
                            END as dead_tuple_percent
                        FROM pg_stat_user_tables
                        WHERE n_dead_tup > 0
                        ORDER BY dead_tuple_percent DESC
                    """)
                    table_bloat = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # Analyze results and generate recommendations
                    if conn_stats[0] > 100:
                        issues.append(f"High connection count: {conn_stats[0]}")
                        recommendations.append("Consider connection pooling")
                    
                    if index_usage < 90:
                        issues.append(f"Low index usage: {index_usage}%")
                        recommendations.append("Review and optimize queries")
                    
                    for table, bloat in table_bloat.items():
                        if bloat > 20:
                            issues.append(f"High table bloat in {table}: {bloat}%")
                            recommendations.append(f"Run VACUUM ANALYZE on {table}")
                    
                    is_healthy = len(issues) == 0
                    
                    return DatabaseHealth(
                        is_healthy=is_healthy,
                        connection_count=conn_stats[0],
                        active_connections=conn_stats[1],
                        slow_queries=slow_query_count,
                        index_usage=index_usage,
                        table_bloat=table_bloat,
                        issues=issues,
                        recommendations=recommendations
                    )
        
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return DatabaseHealth(
                is_healthy=False,
                connection_count=0,
                active_connections=0,
                slow_queries=0,
                index_usage=0,
                table_bloat={},
                issues=[f"Health check failed: {str(e)}"],
                recommendations=["Fix database connectivity issues"]
            )
    
    def backup_database(self, backup_path: str, compression: bool = True) -> bool:
        """
        Create database backup using pg_dump.
        
        Args:
            backup_path: Path for backup file
            compression: Whether to compress backup
            
        Returns:
            bool: True if backup successful
        """
        try:
            cmd = [
                'pg_dump',
                '--host', str(self.db_params['host']),
                '--port', str(self.db_params['port']),
                '--username', self.db_params['user'],
                '--dbname', self.db_params['database'],
                '--verbose',
                '--clean',
                '--no-owner',
                '--no-privileges'
            ]
            
            if compression:
                cmd.extend(['--compress', '9'])
                if not backup_path.endswith('.gz'):
                    backup_path += '.gz'
            
            cmd.extend(['--file', backup_path])
            
            # Set password via environment
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_params['password']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Database backup created: {backup_path}")
                return True
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Backup operation failed: {e}")
            return False
    
    def vacuum_analyze_all(self) -> bool:
        """
        Run VACUUM ANALYZE on all user tables.
        
        Returns:
            bool: True if operation successful
        """
        try:
            with self.get_connection(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # Get all user tables
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in tables:
                        logger.info(f"Running VACUUM ANALYZE on {table}")
                        cursor.execute(f"VACUUM ANALYZE {table}")
                    
                    logger.info(f"✅ VACUUM ANALYZE completed on {len(tables)} tables")
                    return True
        
        except Exception as e:
            logger.error(f"❌ VACUUM ANALYZE failed: {e}")
            return False
    
    def optimize_database(self) -> Dict[str, bool]:
        """
        Run database optimization tasks.
        
        Returns:
            Dict[str, bool]: Results of optimization tasks
        """
        results = {}
        
        # Run VACUUM ANALYZE
        results['vacuum_analyze'] = self.vacuum_analyze_all()
        
        # Update table statistics
        try:
            with self.get_connection(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("ANALYZE")
                    results['analyze'] = True
                    logger.info("✅ Database statistics updated")
        except Exception as e:
            logger.error(f"❌ ANALYZE failed: {e}")
            results['analyze'] = False
        
        # Refresh materialized views
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = 'public'
                    """)
                    views = [row[0] for row in cursor.fetchall()]
                    
                    for view in views:
                        try:
                            cursor.execute(f"REFRESH MATERIALIZED VIEW {view}")
                            logger.info(f"✅ Refreshed materialized view: {view}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to refresh {view}: {e}")
                    
                    conn.commit()
                    results['refresh_views'] = True
        except Exception as e:
            logger.error(f"❌ Materialized view refresh failed: {e}")
            results['refresh_views'] = False
        
        return results


if __name__ == "__main__":
    # Test database manager
    logging.basicConfig(level=logging.INFO)
    
    try:
        db_manager = DatabaseManager()
        
        print("Testing database connection...")
        if db_manager.test_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            sys.exit(1)
        
        print("\nChecking migration status...")
        migration_status = db_manager.get_migration_status()
        print(f"Current revision: {migration_status.current_revision}")
        print(f"Up to date: {migration_status.is_up_to_date}")
        
        print("\nPerforming health check...")
        health = db_manager.check_database_health()
        print(f"Database healthy: {health.is_healthy}")
        print(f"Active connections: {health.active_connections}")
        print(f"Index usage: {health.index_usage}%")
        
        if health.issues:
            print("\nIssues found:")
            for issue in health.issues:
                print(f"  - {issue}")
        
        if health.recommendations:
            print("\nRecommendations:")
            for rec in health.recommendations:
                print(f"  - {rec}")
        
        print("\n✅ Database manager test completed")
        
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        sys.exit(1)
#!/usr/bin/env python3
"""
Production Database Management Script
Provides comprehensive database management capabilities for SearXNG-Cool
"""
import os
import sys
import click
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database connection string from environment
import os
from urllib.parse import quote_plus

# Build database URL from environment or use default
if db_url := os.environ.get('DATABASE_URL'):
    DATABASE_URL = db_url
else:
    user = os.environ.get('DB_USER', 'searxng_user')
    password = os.environ.get('DB_PASSWORD', '')
    if not password:
        raise ValueError("DB_PASSWORD environment variable must be set")
    password = quote_plus(password)
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    database = os.environ.get('DB_NAME', 'searxng_cool_music')
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"


class DatabaseManager:
    """Production database management utilities"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
    
    def analyze_indexes(self) -> List[Dict[str, Any]]:
        """Analyze index usage and effectiveness"""
        query = """
        SELECT 
            schemaname,
            relname as tablename,
            indexrelname as indexname,
            idx_scan as index_scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
            CASE 
                WHEN idx_scan = 0 THEN 'UNUSED'
                WHEN idx_scan < 100 THEN 'RARELY_USED'
                WHEN idx_scan < 1000 THEN 'MODERATELY_USED'
                ELSE 'FREQUENTLY_USED'
            END as usage_category
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def analyze_queries(self) -> List[Dict[str, Any]]:
        """Analyze slow queries (requires pg_stat_statements)"""
        query = """
        SELECT 
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            stddev_exec_time,
            rows
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat_statements%'
        ORDER BY mean_exec_time DESC
        LIMIT 20;
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except psycopg2.ProgrammingError:
            return [{"error": "pg_stat_statements extension not installed"}]
    
    def analyze_table_stats(self) -> List[Dict[str, Any]]:
        """Get comprehensive table statistics"""
        query = """
        SELECT 
            t.schemaname,
            t.relname as tablename,
            pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.relname)) as total_size,
            pg_size_pretty(pg_relation_size(t.schemaname||'.'||t.relname)) as table_size,
            pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.relname) - 
                          pg_relation_size(t.schemaname||'.'||t.relname)) as indexes_size,
            t.n_live_tup as live_tuples,
            t.n_dead_tup as dead_tuples,
            CASE 
                WHEN t.n_live_tup > 0 
                THEN ROUND(100.0 * t.n_dead_tup / t.n_live_tup, 2)
                ELSE 0 
            END as dead_tuple_percent,
            t.last_vacuum,
            t.last_autovacuum,
            t.last_analyze,
            t.last_autoanalyze
        FROM pg_stat_user_tables t
        WHERE t.schemaname = 'public'
        ORDER BY pg_total_relation_size(t.schemaname||'.'||t.relname) DESC;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def check_missing_indexes(self) -> List[Dict[str, Any]]:
        """Identify potentially missing indexes"""
        query = """
        SELECT 
            schemaname,
            tablename,
            attname as column_name,
            n_distinct,
            correlation
        FROM pg_stats
        WHERE schemaname = 'public'
        AND n_distinct > 100
        AND correlation < 0.1
        AND attname NOT IN (
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid 
                              AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = (schemaname||'.'||tablename)::regclass
        )
        ORDER BY n_distinct DESC;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def refresh_materialized_view(self, view_name: str, concurrently: bool = True) -> bool:
        """Refresh a materialized view"""
        try:
            concurrent_clause = "CONCURRENTLY " if concurrently else ""
            self.cursor.execute(f"REFRESH MATERIALIZED VIEW {concurrent_clause}{view_name}")
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            if "concurrently" in str(e).lower() and concurrently:
                # Try without CONCURRENTLY
                click.echo("Concurrent refresh failed, trying regular refresh...", err=True)
                return self.refresh_materialized_view(view_name, concurrently=False)
            click.echo(f"Error refreshing view: {e}", err=True)
            return False
    
    def vacuum_analyze_table(self, table_name: str) -> bool:
        """Run VACUUM ANALYZE on a specific table"""
        try:
            old_isolation_level = self.conn.isolation_level
            self.conn.set_isolation_level(0)
            self.cursor.execute(f"VACUUM ANALYZE {table_name}")
            self.conn.set_isolation_level(old_isolation_level)
            return True
        except Exception as e:
            click.echo(f"Error vacuuming table: {e}", err=True)
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get database connection statistics"""
        query = """
        SELECT 
            COUNT(*) as total_connections,
            COUNT(*) FILTER (WHERE state = 'active') as active_connections,
            COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
            COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
            MAX(EXTRACT(epoch FROM (now() - query_start))) as longest_query_seconds
        FROM pg_stat_activity
        WHERE datname = current_database();
        """
        self.cursor.execute(query)
        return self.cursor.fetchone()
    
    def get_lock_info(self) -> List[Dict[str, Any]]:
        """Get information about current locks"""
        query = """
        SELECT 
            locktype,
            relation::regclass as table_name,
            mode,
            granted,
            pid,
            query
        FROM pg_locks
        JOIN pg_stat_activity USING (pid)
        WHERE relation IS NOT NULL
        AND query NOT LIKE '%pg_locks%'
        ORDER BY granted, relation;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()


@click.group()
def cli():
    """SearXNG-Cool Database Manager"""
    pass


@cli.command()
def analyze_indexes():
    """Analyze index usage and effectiveness"""
    with DatabaseManager() as db:
        results = db.analyze_indexes()
        headers = ['Table', 'Index', 'Scans', 'Size', 'Usage']
        table_data = [
            [
                r['tablename'],
                r['indexname'],
                r['index_scans'],
                r['index_size'],
                r['usage_category']
            ]
            for r in results
        ]
        click.echo("\nIndex Usage Analysis:")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@cli.command()
def analyze_queries():
    """Analyze slow queries"""
    with DatabaseManager() as db:
        results = db.analyze_queries()
        if results and 'error' in results[0]:
            click.echo(f"Error: {results[0]['error']}")
            click.echo("To enable query analysis, run:")
            click.echo("  sudo -u postgres psql -d searxng_cool_music -c 'CREATE EXTENSION pg_stat_statements;'")
            return
        
        headers = ['Query', 'Calls', 'Avg Time (ms)', 'Total Time (ms)']
        table_data = [
            [
                r['query'][:50] + '...' if len(r['query']) > 50 else r['query'],
                r['calls'],
                f"{r['mean_exec_time']:.2f}",
                f"{r['total_exec_time']:.2f}"
            ]
            for r in results[:10]
        ]
        click.echo("\nTop 10 Slowest Queries:")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@cli.command()
def table_stats():
    """Show comprehensive table statistics"""
    with DatabaseManager() as db:
        results = db.analyze_table_stats()
        headers = ['Table', 'Total Size', 'Table Size', 'Index Size', 'Live Rows', 'Dead %', 'Last Vacuum']
        table_data = [
            [
                r['tablename'],
                r['total_size'],
                r['table_size'],
                r['indexes_size'],
                r['live_tuples'],
                f"{r['dead_tuple_percent']}%",
                r['last_autovacuum'] or r['last_vacuum'] or 'Never'
            ]
            for r in results
        ]
        click.echo("\nTable Statistics:")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@cli.command()
def missing_indexes():
    """Identify potentially missing indexes"""
    with DatabaseManager() as db:
        results = db.check_missing_indexes()
        if results:
            headers = ['Table', 'Column', 'Distinct Values', 'Correlation']
            table_data = [
                [
                    r['tablename'],
                    r['column_name'],
                    r['n_distinct'],
                    f"{r['correlation']:.3f}"
                ]
                for r in results
            ]
            click.echo("\nPotential Missing Indexes:")
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            click.echo("No obviously missing indexes found.")


@cli.command()
@click.argument('view_name')
def refresh_view(view_name):
    """Refresh a materialized view"""
    with DatabaseManager() as db:
        if db.refresh_materialized_view(view_name):
            click.echo(f"Successfully refreshed {view_name}")
        else:
            click.echo(f"Failed to refresh {view_name}", err=True)


@cli.command()
@click.argument('table_name')
def vacuum_table(table_name):
    """Run VACUUM ANALYZE on a table"""
    with DatabaseManager() as db:
        if db.vacuum_analyze_table(table_name):
            click.echo(f"Successfully vacuumed {table_name}")
        else:
            click.echo(f"Failed to vacuum {table_name}", err=True)


@cli.command()
def connection_stats():
    """Show database connection statistics"""
    with DatabaseManager() as db:
        stats = db.get_connection_stats()
        click.echo("\nConnection Statistics:")
        click.echo(f"Total connections: {stats['total_connections']}")
        click.echo(f"Active connections: {stats['active_connections']}")
        click.echo(f"Idle connections: {stats['idle_connections']}")
        click.echo(f"Idle in transaction: {stats['idle_in_transaction']}")
        if stats['longest_query_seconds']:
            click.echo(f"Longest running query: {stats['longest_query_seconds']:.2f} seconds")


@cli.command()
def lock_info():
    """Show current database locks"""
    with DatabaseManager() as db:
        results = db.get_lock_info()
        if results:
            headers = ['Table', 'Lock Type', 'Mode', 'Granted', 'PID', 'Query']
            table_data = [
                [
                    r['table_name'],
                    r['locktype'],
                    r['mode'],
                    r['granted'],
                    r['pid'],
                    r['query'][:40] + '...' if len(r['query']) > 40 else r['query']
                ]
                for r in results
            ]
            click.echo("\nCurrent Locks:")
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            click.echo("No locks currently held.")


@cli.command()
def health_check():
    """Run a comprehensive health check"""
    with DatabaseManager() as db:
        click.echo("=== Database Health Check ===\n")
        
        # Connection stats
        conn_stats = db.get_connection_stats()
        click.echo("Connection Health:")
        click.echo(f"  Total connections: {conn_stats['total_connections']}")
        click.echo(f"  Active queries: {conn_stats['active_connections']}")
        
        # Table stats
        table_results = db.analyze_table_stats()
        high_bloat = [t for t in table_results if t['dead_tuple_percent'] > 20]
        if high_bloat:
            click.echo("\n⚠️  Tables with high bloat:")
            for t in high_bloat:
                click.echo(f"  - {t['tablename']}: {t['dead_tuple_percent']}% dead tuples")
        
        # Unused indexes
        index_results = db.analyze_indexes()
        unused = [i for i in index_results if i['usage_category'] == 'UNUSED']
        if unused:
            click.echo("\n⚠️  Unused indexes:")
            for i in unused:
                click.echo(f"  - {i['indexname']} on {i['tablename']} ({i['index_size']})")
        
        click.echo("\n✅ Health check complete")


if __name__ == "__main__":
    cli()
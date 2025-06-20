#!/usr/bin/env python3
"""
Database Validation Suite for SearXNG-Cool
Comprehensive validation for model integrity, migrations, and performance
"""

import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from db_manager import DatabaseManager
from orchestrator.config_loader import load_config

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validation result for a specific check"""
    name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


@dataclass
class ValidationSuite:
    """Complete validation suite results"""
    overall_passed: bool
    results: List[ValidationResult]
    total_duration_ms: float
    summary: Dict[str, int]


class DatabaseValidator:
    """
    Comprehensive database validation suite.
    
    Validates:
    - Model integrity and relationships
    - Migration consistency
    - Performance benchmarks
    - Data consistency
    - Index effectiveness
    - Constraint enforcement
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize database validator.
        
        Args:
            config: Configuration dictionary. If None, loads from orchestrator.yml
        """
        self.config = config or load_config()
        self.db_manager = DatabaseManager(self.config)
        self.results: List[ValidationResult] = []
    
    def run_all_validations(self) -> ValidationSuite:
        """
        Run complete validation suite.
        
        Returns:
            ValidationSuite: Complete validation results
        """
        start_time = time.time()
        self.results = []
        
        logger.info("🔍 Starting comprehensive database validation...")
        
        # Core validation checks
        validation_checks = [
            self._validate_connection,
            self._validate_schema_integrity,
            self._validate_foreign_key_constraints,
            self._validate_index_existence,
            self._validate_model_relationships,
            self._validate_jsonb_fields,
            self._validate_triggers_and_functions,
            self._validate_materialized_views,
            self._validate_performance_benchmarks,
            self._validate_data_consistency,
            self._validate_migration_history
        ]
        
        for check in validation_checks:
            try:
                result = check()
                self.results.append(result)
                
                status = "✅" if result.passed else "❌"
                logger.info(f"{status} {result.name}: {result.message}")
                
            except Exception as e:
                error_result = ValidationResult(
                    name=check.__name__.replace('_validate_', '').replace('_', ' ').title(),
                    passed=False,
                    message=f"Validation failed with error: {str(e)}",
                    details={'error': str(e)}
                )
                self.results.append(error_result)
                logger.error(f"❌ {error_result.name}: {error_result.message}")
        
        # Calculate summary
        total_duration = (time.time() - start_time) * 1000
        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = len(self.results) - passed_count
        overall_passed = failed_count == 0
        
        summary = {
            'total': len(self.results),
            'passed': passed_count,
            'failed': failed_count
        }
        
        return ValidationSuite(
            overall_passed=overall_passed,
            results=self.results,
            total_duration_ms=total_duration,
            summary=summary
        )
    
    def _timed_check(self, check_func):
        """Decorator to time validation checks"""
        def wrapper(*args, **kwargs):
            start = time.time()
            result = check_func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            result.duration_ms = duration
            return result
        return wrapper
    
    def _validate_connection(self) -> ValidationResult:
        """Validate database connectivity"""
        start = time.time()
        
        if self.db_manager.test_connection():
            return ValidationResult(
                name="Database Connection",
                passed=True,
                message="Database connection successful",
                duration_ms=(time.time() - start) * 1000
            )
        else:
            return ValidationResult(
                name="Database Connection",
                passed=False,
                message="Database connection failed",
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_schema_integrity(self) -> ValidationResult:
        """Validate database schema matches expected structure"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Expected core tables for music platform
                    expected_tables = [
                        'users', 'artists', 'albums', 'tracks', 'playlists',
                        'user_interactions', 'user_library', 'playlist_tracks',
                        'track_sources', 'artist_sources', 'album_sources',
                        'discovery_sessions', 'discovery_session_tracks',
                        'user_music_profiles', 'playlist_collaborators',
                        'playlist_activities', 'user_artist_follows',
                        'user_album_collections', 'playlist_follows',
                        'playlist_track_votes'
                    ]
                    
                    # Check if all expected tables exist
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    existing_tables = {row[0] for row in cursor.fetchall()}
                    
                    missing_tables = set(expected_tables) - existing_tables
                    
                    if missing_tables:
                        return ValidationResult(
                            name="Schema Integrity",
                            passed=False,
                            message=f"Missing tables: {', '.join(missing_tables)}",
                            details={'missing_tables': list(missing_tables)},
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return ValidationResult(
                        name="Schema Integrity",
                        passed=True,
                        message=f"All {len(expected_tables)} expected tables present",
                        details={'table_count': len(existing_tables)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Schema Integrity",
                passed=False,
                message=f"Schema validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_foreign_key_constraints(self) -> ValidationResult:
        """Validate foreign key constraints are properly defined"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for foreign key constraints
                    cursor.execute("""
                        SELECT 
                            tc.table_name,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_schema = 'public'
                    """)
                    
                    fk_constraints = cursor.fetchall()
                    
                    # Expected minimum number of FK constraints for music platform
                    expected_min_fks = 15  # Rough estimate based on schema
                    
                    if len(fk_constraints) >= expected_min_fks:
                        return ValidationResult(
                            name="Foreign Key Constraints",
                            passed=True,
                            message=f"Found {len(fk_constraints)} foreign key constraints",
                            details={'constraint_count': len(fk_constraints)},
                            duration_ms=(time.time() - start) * 1000
                        )
                    else:
                        return ValidationResult(
                            name="Foreign Key Constraints",
                            passed=False,
                            message=f"Only {len(fk_constraints)} foreign key constraints found (expected ≥{expected_min_fks})",
                            details={'constraint_count': len(fk_constraints)},
                            duration_ms=(time.time() - start) * 1000
                        )
        
        except Exception as e:
            return ValidationResult(
                name="Foreign Key Constraints",
                passed=False,
                message=f"FK constraint validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_index_existence(self) -> ValidationResult:
        """Validate critical indexes exist"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for indexes
                    cursor.execute("""
                        SELECT indexname, tablename
                        FROM pg_indexes
                        WHERE schemaname = 'public'
                    """)
                    
                    indexes = cursor.fetchall()
                    index_names = {idx[0] for idx in indexes}
                    
                    # Critical indexes that should exist
                    critical_indexes = [
                        'idx_tracks_artist_id',
                        'idx_user_interactions_user_id',
                        'idx_playlist_tracks_playlist_id',
                        'idx_tracks_audio_features',  # JSONB index
                        'idx_tracks_search'           # Full-text search
                    ]
                    
                    missing_indexes = [idx for idx in critical_indexes if idx not in index_names]
                    
                    if missing_indexes:
                        return ValidationResult(
                            name="Critical Indexes",
                            passed=False,
                            message=f"Missing critical indexes: {', '.join(missing_indexes)}",
                            details={
                                'missing_indexes': missing_indexes,
                                'total_indexes': len(indexes)
                            },
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return ValidationResult(
                        name="Critical Indexes",
                        passed=True,
                        message=f"All critical indexes present ({len(indexes)} total indexes)",
                        details={'total_indexes': len(indexes)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Critical Indexes",
                passed=False,
                message=f"Index validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_model_relationships(self) -> ValidationResult:
        """Validate model relationships work correctly"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test basic JOIN operations to verify relationships
                    test_queries = [
                        # Track-Artist relationship
                        "SELECT COUNT(*) FROM tracks t LEFT JOIN artists a ON t.artist_id = a.id",
                        # Track-Album relationship
                        "SELECT COUNT(*) FROM tracks t LEFT JOIN albums al ON t.album_id = al.id",
                        # User-Interactions relationship
                        "SELECT COUNT(*) FROM user_interactions ui LEFT JOIN users u ON ui.user_id = u.id",
                        # Playlist-Track relationship
                        "SELECT COUNT(*) FROM playlist_tracks pt LEFT JOIN tracks t ON pt.track_id = t.id"
                    ]
                    
                    for query in test_queries:
                        cursor.execute(query)
                        cursor.fetchone()  # Just verify the query executes
                    
                    return ValidationResult(
                        name="Model Relationships",
                        passed=True,
                        message="All relationship queries executed successfully",
                        details={'queries_tested': len(test_queries)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Model Relationships",
                passed=False,
                message=f"Relationship validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_jsonb_fields(self) -> ValidationResult:
        """Validate JSONB fields and operations"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test JSONB operations on key tables
                    jsonb_tests = [
                        # Tracks audio_features
                        "SELECT COUNT(*) FROM tracks WHERE audio_features IS NOT NULL",
                        # Artists genres
                        "SELECT COUNT(*) FROM artists WHERE genres IS NOT NULL",
                        # Test JSONB query operator
                        "SELECT COUNT(*) FROM tracks WHERE audio_features->>'energy' IS NOT NULL"
                    ]
                    
                    for query in jsonb_tests:
                        cursor.execute(query)
                        cursor.fetchone()
                    
                    return ValidationResult(
                        name="JSONB Operations",
                        passed=True,
                        message="JSONB fields and operations working correctly",
                        details={'tests_passed': len(jsonb_tests)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="JSONB Operations",
                passed=False,
                message=f"JSONB validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_triggers_and_functions(self) -> ValidationResult:
        """Validate database triggers and functions"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for update triggers
                    cursor.execute("""
                        SELECT trigger_name, event_object_table
                        FROM information_schema.triggers
                        WHERE trigger_schema = 'public'
                          AND trigger_name LIKE 'update_%_updated_at'
                    """)
                    
                    triggers = cursor.fetchall()
                    
                    # Check for functions
                    cursor.execute("""
                        SELECT proname 
                        FROM pg_proc 
                        WHERE pronamespace = (
                            SELECT oid FROM pg_namespace WHERE nspname = 'public'
                        )
                    """)
                    
                    functions = cursor.fetchall()
                    function_names = {func[0] for func in functions}
                    
                    expected_function = 'update_updated_at_column'
                    
                    if expected_function in function_names and len(triggers) > 0:
                        return ValidationResult(
                            name="Triggers and Functions",
                            passed=True,
                            message=f"Found {len(triggers)} triggers and {len(functions)} functions",
                            details={
                                'trigger_count': len(triggers),
                                'function_count': len(functions)
                            },
                            duration_ms=(time.time() - start) * 1000
                        )
                    else:
                        return ValidationResult(
                            name="Triggers and Functions",
                            passed=False,
                            message=f"Missing expected triggers or functions",
                            details={
                                'trigger_count': len(triggers),
                                'function_count': len(functions),
                                'expected_function_present': expected_function in function_names
                            },
                            duration_ms=(time.time() - start) * 1000
                        )
        
        except Exception as e:
            return ValidationResult(
                name="Triggers and Functions",
                passed=False,
                message=f"Trigger/function validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_materialized_views(self) -> ValidationResult:
        """Validate materialized views"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for materialized views
                    cursor.execute("""
                        SELECT matviewname, ispopulated
                        FROM pg_matviews
                        WHERE schemaname = 'public'
                    """)
                    
                    views = cursor.fetchall()
                    
                    if not views:
                        return ValidationResult(
                            name="Materialized Views",
                            passed=True,  # Not critical if none exist
                            message="No materialized views found (acceptable)",
                            details={'view_count': 0},
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    unpopulated_views = [view[0] for view in views if not view[1]]
                    
                    if unpopulated_views:
                        return ValidationResult(
                            name="Materialized Views",
                            passed=False,
                            message=f"Unpopulated materialized views: {', '.join(unpopulated_views)}",
                            details={
                                'view_count': len(views),
                                'unpopulated_views': unpopulated_views
                            },
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return ValidationResult(
                        name="Materialized Views",
                        passed=True,
                        message=f"All {len(views)} materialized views are populated",
                        details={'view_count': len(views)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Materialized Views",
                passed=False,
                message=f"Materialized view validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_performance_benchmarks(self) -> ValidationResult:
        """Run basic performance benchmarks"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Simple query performance tests
                    test_queries = [
                        # Index usage test
                        ("SELECT * FROM tracks WHERE artist_id = 1", 50),  # 50ms max
                        # JSONB query test
                        ("SELECT COUNT(*) FROM tracks WHERE audio_features IS NOT NULL", 100),  # 100ms max
                        # JOIN performance test
                        ("SELECT t.title, a.name FROM tracks t JOIN artists a ON t.artist_id = a.id LIMIT 10", 100)
                    ]
                    
                    slow_queries = []
                    
                    for query, max_time_ms in test_queries:
                        query_start = time.time()
                        cursor.execute(query)
                        cursor.fetchall()
                        query_time_ms = (time.time() - query_start) * 1000
                        
                        if query_time_ms > max_time_ms:
                            slow_queries.append((query[:50] + "...", query_time_ms, max_time_ms))
                    
                    if slow_queries:
                        return ValidationResult(
                            name="Performance Benchmarks",
                            passed=False,
                            message=f"{len(slow_queries)} queries exceeded performance thresholds",
                            details={'slow_queries': slow_queries},
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return ValidationResult(
                        name="Performance Benchmarks",
                        passed=True,
                        message=f"All {len(test_queries)} performance tests passed",
                        details={'tests_passed': len(test_queries)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Performance Benchmarks",
                passed=False,
                message=f"Performance validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_data_consistency(self) -> ValidationResult:
        """Validate data consistency"""
        start = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for orphaned records
                    consistency_checks = [
                        # Tracks without artists
                        ("SELECT COUNT(*) FROM tracks WHERE artist_id NOT IN (SELECT id FROM artists)", "Orphaned tracks"),
                        # User interactions without users
                        ("SELECT COUNT(*) FROM user_interactions WHERE user_id NOT IN (SELECT id FROM users)", "Orphaned user interactions"),
                        # Playlist tracks without playlists
                        ("SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id NOT IN (SELECT id FROM playlists)", "Orphaned playlist tracks")
                    ]
                    
                    consistency_issues = []
                    
                    for query, description in consistency_checks:
                        cursor.execute(query)
                        count = cursor.fetchone()[0]
                        if count > 0:
                            consistency_issues.append((description, count))
                    
                    if consistency_issues:
                        return ValidationResult(
                            name="Data Consistency",
                            passed=False,
                            message=f"Data consistency issues found: {len(consistency_issues)}",
                            details={'issues': consistency_issues},
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return ValidationResult(
                        name="Data Consistency",
                        passed=True,
                        message="No data consistency issues found",
                        details={'checks_passed': len(consistency_checks)},
                        duration_ms=(time.time() - start) * 1000
                    )
        
        except Exception as e:
            return ValidationResult(
                name="Data Consistency",
                passed=False,
                message=f"Consistency validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_migration_history(self) -> ValidationResult:
        """Validate migration history"""
        start = time.time()
        
        try:
            migration_status = self.db_manager.get_migration_status()
            
            if migration_status.current_revision:
                return ValidationResult(
                    name="Migration History",
                    passed=True,
                    message=f"Migration system functional, current: {migration_status.current_revision}",
                    details={
                        'current_revision': migration_status.current_revision,
                        'is_up_to_date': migration_status.is_up_to_date
                    },
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return ValidationResult(
                    name="Migration History",
                    passed=False,
                    message="No migration history found",
                    details={'current_revision': None},
                    duration_ms=(time.time() - start) * 1000
                )
        
        except Exception as e:
            return ValidationResult(
                name="Migration History",
                passed=False,
                message=f"Migration validation failed: {str(e)}",
                details={'error': str(e)},
                duration_ms=(time.time() - start) * 1000
            )


if __name__ == "__main__":
    # Run validation suite
    logging.basicConfig(level=logging.INFO)
    
    try:
        validator = DatabaseValidator()
        suite_results = validator.run_all_validations()
        
        print(f"\n{'='*60}")
        print("DATABASE VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Overall Status: {'✅ PASSED' if suite_results.overall_passed else '❌ FAILED'}")
        print(f"Total Tests: {suite_results.summary['total']}")
        print(f"Passed: {suite_results.summary['passed']}")
        print(f"Failed: {suite_results.summary['failed']}")
        print(f"Duration: {suite_results.total_duration_ms:.2f}ms")
        print(f"{'='*60}")
        
        # Detailed results
        for result in suite_results.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration = f" ({result.duration_ms:.1f}ms)" if result.duration_ms else ""
            print(f"{status} - {result.name}: {result.message}{duration}")
        
        print(f"{'='*60}")
        
        # Exit with appropriate code
        sys.exit(0 if suite_results.overall_passed else 1)
        
    except Exception as e:
        print(f"❌ Validation suite failed: {e}")
        sys.exit(1)
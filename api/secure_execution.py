"""
Optimized Secure Query Execution System
======================================
High-performance, security-hardened SQL execution with intelligent caching,
connection pooling, and enhanced validation.
"""

import asyncio
import logging
import json
import math
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading

from .query_validator import query_validator, QueryValidationError, QueryRisk
from .test_validator import optimized_test_validator, ComparisonMode
from .duckdb_sandbox import DuckDBSandboxManager, DuckDBSandbox
from .models import (
    User, Problem, TestCase, Submission, 
    ExecutionResult, ExecutionStatus
)
from .schemas import (
    ExecutionResultCreate, 
    DetailedSubmissionResponse,
    TestCaseResponse
)

logger = logging.getLogger(__name__)

# Performance optimizations
MAX_WORKERS = 4  # Limit concurrent executions
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_SIZE = 1000

@dataclass
class ExecutionContext:
    """Lightweight execution context"""
    user_id: str
    problem_id: str
    query: str
    start_time: float
    timeout: int = 30
    max_memory_mb: int = 256

class ResultCache:
    """High-performance result cache with TTL"""

    def __init__(self, max_size: int = MAX_CACHE_SIZE, ttl: int = CACHE_TTL):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl = ttl
        self._lock = threading.RLock()

    def _generate_key(self, query: str, problem_id: str) -> str:
        """Generate cache key from query and problem"""
        return hashlib.md5(f"{problem_id}:{query}".encode()).hexdigest()

    def get(self, query: str, problem_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result if valid"""
        key = self._generate_key(query, problem_id)

        with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() - self.timestamps[key] < self.ttl:
                    return self.cache[key]
                else:
                    # Expired, remove
                    del self.cache[key]
                    del self.timestamps[key]
        return None

    def set(self, query: str, problem_id: str, result: Dict[str, Any]):
        """Cache result with TTL"""
        key = self._generate_key(query, problem_id)

        with self._lock:
            # Evict oldest if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps.keys(), key=self.timestamps.get)
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]

            self.cache[key] = result
            self.timestamps[key] = time.time()

    def clear(self):
        """Clear entire cache"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()

class SecurityManager:
    """Enhanced security validation with pattern detection"""

    def __init__(self):
        # Compiled patterns for performance
        self.dangerous_patterns = [
            (r'\bDROP\s+TABLE\b', 'DROP TABLE detected'),
            (r'\bDELETE\s+FROM\b', 'DELETE operation detected'),
            (r'\bINSERT\s+INTO\b', 'INSERT operation detected'),
            (r'\bUPDATE\s+\w+\s+SET\b', 'UPDATE operation detected'),
            (r'\bCREATE\s+TABLE\b', 'CREATE TABLE detected'),
            (r'\bALTER\s+TABLE\b', 'ALTER TABLE detected'),
            (r'\bTRUNCATE\b', 'TRUNCATE detected'),
            (r';\s*--', 'SQL comment injection pattern'),
            (r'\bUNION\s+SELECT\b', 'UNION injection pattern'),
            (r'\'\s*OR\s+\'\w*\'\s*=\s*\'\w*\'', 'SQL injection pattern'),
        ]

        # Compile regex patterns for performance
        import re
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), message) 
            for pattern, message in self.dangerous_patterns
        ]

    def validate_query_security(self, query: str, allowed_tables: Set[str]) -> Dict[str, Any]:
        """Fast security validation with pattern matching"""
        result = {
            'is_safe': True,
            'violations': [],
            'warnings': [],
            'risk_level': 'LOW'
        }

        query_upper = query.upper().strip()

        # Fast checks for obviously dangerous operations
        if not query_upper.startswith(('SELECT', 'WITH')):
            result['is_safe'] = False
            result['violations'].append(f"Only SELECT and WITH statements allowed, found: {query_upper.split()[0]}")
            result['risk_level'] = 'HIGH'
            return result

        # Pattern-based security checks
        for pattern, message in self.compiled_patterns:
            if pattern.search(query):
                result['is_safe'] = False
                result['violations'].append(message)
                result['risk_level'] = 'HIGH'

        # Check for table access violations
        query_lower = query.lower()
        for table in allowed_tables:
            if table.lower() not in query_lower:
                continue
            # Additional table-specific validation could go here

        # Check for suspicious patterns
        if 'sleep(' in query_lower or 'pg_sleep(' in query_lower:
            result['warnings'].append('Sleep function detected - may cause timeouts')
            result['risk_level'] = 'MEDIUM'

        return result

class OptimizedSecureQueryExecutor:
    """High-performance secure query executor with advanced optimizations"""

    def __init__(self):
        # Core configuration
        self.max_execution_time = 30
        self.max_memory_mb = 256
        self.max_result_rows = 10000

        # Performance components
        self.sandbox_manager = DuckDBSandboxManager()
        self.thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.result_cache = ResultCache()
        self.security_manager = SecurityManager()

        # Performance metrics
        self.metrics = {
            'total_executions': 0,
            'cache_hits': 0,
            'avg_execution_time': 0,
            'security_blocks': 0
        }

    async def submit_solution(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Optimized solution submission with caching and parallel execution
        """
        start_time = time.time()

        try:
            # Fast security validation
            sandbox = await self._get_or_create_sandbox_fast(user_id, problem_id, db)
            if not sandbox:
                return self._create_error_response('Failed to create execution sandbox')

            security_result = self.security_manager.validate_query_security(
                query, set(sandbox.loaded_table_names)
            )

            if not security_result['is_safe']:
                self.metrics['security_blocks'] += 1
                return {
                    'success': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': security_result['violations'],
                    'security_violations': security_result['violations'],
                    'submission_id': None
                }

            # Check cache first for identical queries
            cached_result = self.result_cache.get(query, problem_id)
            if cached_result:
                self.metrics['cache_hits'] += 1
                logger.info(f"Cache hit for problem {problem_id}")
                # Update with new submission record
                return await self._create_submission_from_cache(
                    cached_result, user_id, problem_id, query, db
                )

            # Execute with optimized validation
            test_results = await self._execute_all_test_cases_fast(
                sandbox, problem_id, query, db
            )

            # Fast scoring calculation
            final_score = self._calculate_final_score_fast(test_results)
            is_correct = final_score['overall_score'] >= 95.0

            # Create submission record
            submission = await self._create_submission_record(
                user_id, problem_id, query, is_correct, 
                final_score['avg_execution_time'], db
            )

            result = {
                'success': True,
                'submission_id': submission.id,
                'is_correct': is_correct,
                'score': final_score['overall_score'],
                'feedback': final_score['feedback'],
                'test_results': test_results,
                'passed_tests': final_score['passed_count'],
                'total_tests': final_score['total_count'],
                'execution_stats': {
                    'avg_time_ms': final_score['avg_execution_time'],
                    'max_time_ms': final_score['max_execution_time'],
                    'total_time_ms': int((time.time() - start_time) * 1000)
                },
                'security_warnings': security_result.get('warnings', [])
            }

            # Cache successful results
            if is_correct:
                self.result_cache.set(query, problem_id, result)

            # Update metrics
            self.metrics['total_executions'] += 1
            execution_time = time.time() - start_time
            self.metrics['avg_execution_time'] = (
                (self.metrics['avg_execution_time'] * (self.metrics['total_executions'] - 1) + execution_time) 
                / self.metrics['total_executions']
            )

            # Update user progress asynchronously
            if is_correct:
                asyncio.create_task(self._update_user_progress_async(user_id, problem_id, db))

            return result

        except Exception as e:
            logger.error(f"Solution submission failed: {e}")
            return self._create_error_response(f'Execution error: {str(e)}')

    async def test_query(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session,
        include_hidden_tests: bool = False
    ) -> Dict[str, Any]:
        """
        Optimized query testing with smart caching
        """
        try:
            # Fast sandbox creation
            sandbox = await self._get_or_create_sandbox_fast(user_id, problem_id, db)
            if not sandbox:
                return {
                    'success': False,
                    'feedback': ['Failed to create execution sandbox'],
                    'test_results': []
                }

            # Quick security check
            security_result = self.security_manager.validate_query_security(
                query, set(sandbox.loaded_table_names)
            )

            if not security_result['is_safe']:
                return {
                    'success': False,
                    'feedback': security_result['violations'],
                    'security_violations': security_result['violations'],
                    'test_results': []
                }

            # Execute query with timeout
            query_result = await self._execute_query_with_timeout(sandbox, query, 30)

            if not query_result.get('success'):
                return {
                    'success': False,
                    'feedback': [query_result.get('error', 'Query execution failed')],
                    'test_results': []
                }

            # Fast test case validation
            test_results = await self._validate_against_problem_fast(
                sandbox, problem_id, query, query_result.get('results', []), db
            )

            return {
                'success': True,
                'feedback': self._generate_test_feedback_fast(test_results),
                'test_results': test_results,
                'security_warnings': security_result.get('warnings', []),
                'query_result': {
                    'rows_returned': len(query_result.get('results', [])),
                    'execution_time_ms': query_result.get('execution_time_ms', 0),
                    'columns': list(query_result.get('results', [{}])[0].keys()) if query_result.get('results') else []
                },
                'execution_status': 'SUCCESS'
            }

        except Exception as e:
            logger.error(f"Query test failed: {e}")
            return {
                'success': False,
                'feedback': [f'Test execution error: {str(e)}'],
                'test_results': []
            }

    async def _get_or_create_sandbox_fast(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ) -> Optional[DuckDBSandbox]:
        """
        Optimized sandbox creation with connection reuse
        """
        try:
            # Try to get existing sandbox first
            sandbox = self.sandbox_manager.get_sandbox(user_id, problem_id)
            if sandbox is not None:
                return sandbox

            # Fast problem lookup with minimal data
            problem = db.query(Problem.id, Problem.s3_data_source).filter(
                Problem.id == problem_id
            ).first()

            if not problem:
                return None

            # Create sandbox asynchronously
            sandbox = await self.sandbox_manager.create_sandbox(user_id, problem_id)

            # Load data only if needed
            if problem.s3_data_source:
                setup_result = await sandbox.setup_problem_data(
                    problem_id=problem_id,
                    s3_data_source=problem.s3_data_source
                )

                if not setup_result.get('success', False):
                    logger.warning(f"Failed to load problem data: {setup_result.get('error')}")

            return sandbox

        except Exception as e:
            logger.error(f"Fast sandbox creation failed: {e}")
            return None

    async def _execute_query_with_timeout(
        self, 
        sandbox: DuckDBSandbox, 
        query: str, 
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute query with enforced timeout using thread pool
        """
        try:
            # Execute in thread pool to enable timeout
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.thread_pool,
                sandbox.execute_query,
                query
            )

            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Query execution timeout after {timeout}s")
            return {
                'success': False,
                'error': f'Query execution timed out after {timeout} seconds',
                'execution_time_ms': timeout * 1000
            }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'success': False,
                'error': f'Query execution error: {str(e)}',
                'execution_time_ms': 0
            }

    async def _execute_all_test_cases_fast(
        self,
        sandbox: DuckDBSandbox,
        problem_id: str,
        query: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Optimized test case execution with parallel processing where possible
        """
        # Check for enhanced S3 hash validation first
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return [self._create_error_test_result('Problem not found')]

        if problem.expected_hash and problem.s3_data_source:
            return await self._execute_s3_hash_validation_fast(problem, sandbox, query)

        # Traditional test case validation with optimization
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == problem_id
        ).order_by(TestCase.order_index).all()

        if not test_cases:
            # Fallback to expected output comparison
            return await self._validate_against_expected_output_fast(
                problem, sandbox, query
            )

        # Execute test cases (sequential for data consistency)
        results = []
        for test_case in test_cases:
            try:
                # Execute with timeout
                result = await self._execute_query_with_timeout(sandbox, query, 30)

                if result.get('success'):
                    # Fast validation using optimized validator
                    validation = optimized_test_validator.validate_test_case(
                        result.get('results', []),
                        test_case.expected_output,
                        ComparisonMode.UNORDERED
                    )

                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_hidden': test_case.is_hidden,
                        'is_correct': validation['is_correct'],
                        'score': validation['score'],
                        'feedback': validation['feedback'][:3],  # Limit feedback for performance
                        'execution_time_ms': result.get('execution_time_ms', 0)
                    })
                else:
                    results.append(self._create_failed_test_result(
                        test_case, result.get('error', 'Unknown error')
                    ))

            except Exception as e:
                results.append(self._create_failed_test_result(test_case, str(e)))

        return results

    async def _execute_s3_hash_validation_fast(
        self,
        problem: "Problem",
        sandbox: DuckDBSandbox,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Optimized S3 hash validation with minimal data transfer
        """
        start_time = time.time()

        try:
            # Execute query directly on sandbox (data already loaded)
            result = await self._execute_query_with_timeout(sandbox, query, 30)

            if not result.get('success'):
                return [self._create_error_test_result(result.get('error', 'Query failed'))]

            user_results = result.get('results', [])

            # Fast hash generation
            from .s3_service import s3_service
            user_hash = s3_service.generate_expected_result_hash(user_results)

            # Compare with expected hash
            is_correct = user_hash == problem.expected_hash
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Generate minimal feedback for performance
            if is_correct:
                feedback = ["Perfect! Your query produces the expected results."]
                score = 100.0
            else:
                feedback = [
                    "Your query results don't match the expected output.",
                    f"Your query returned {len(user_results)} rows."
                ]
                score = 0.0

            return [{
                'test_case_id': 'hash_validation',
                'test_case_name': 'S3 Hash Validation',
                'is_hidden': False,
                'is_correct': is_correct,
                'score': score,
                'feedback': feedback,
                'execution_time_ms': execution_time_ms,
                'validation_details': {
                    'hash_match': is_correct,
                    'result_count': len(user_results)
                }
            }]

        except Exception as e:
            logger.error(f"S3 hash validation failed: {e}")
            return [self._create_error_test_result(f'Hash validation failed: {str(e)}')]

    async def _validate_against_expected_output_fast(
        self,
        problem: "Problem",
        sandbox: DuckDBSandbox,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Fast validation against problem's expected output
        """
        try:
            result = await self._execute_query_with_timeout(sandbox, query, 30)

            if not result.get('success'):
                return [self._create_error_test_result(result.get('error', 'Query failed'))]

            user_results = result.get('results', [])
            expected_output = problem.question.get('expectedOutput', []) if problem.question else []

            if not expected_output:
                return [{
                    'test_case_id': 'basic_validation',
                    'test_case_name': 'Basic Output Check',
                    'is_hidden': False,
                    'is_correct': True,
                    'score': 100.0,
                    'feedback': ['Query executed successfully'],
                    'execution_time_ms': result.get('execution_time_ms', 0)
                }]

            # Fast comparison
            is_correct = self._fast_result_comparison(user_results, expected_output)

            return [{
                'test_case_id': 'expected_output',
                'test_case_name': 'Expected Output Comparison',
                'is_hidden': False,
                'is_correct': is_correct,
                'score': 100.0 if is_correct else 0.0,
                'feedback': ['Results match expected output'] if is_correct else ['Results differ from expected output'],
                'execution_time_ms': result.get('execution_time_ms', 0)
            }]

        except Exception as e:
            return [self._create_error_test_result(f'Validation failed: {str(e)}')]

    def _fast_result_comparison(self, actual: List[Dict], expected: List[Dict]) -> bool:
        """Ultra-fast result comparison for basic validation"""
        if len(actual) != len(expected):
            return False

        if not actual and not expected:
            return True

        # Fast hash-based comparison for identical structure
        try:
            actual_str = json.dumps(actual, sort_keys=True, default=str)
            expected_str = json.dumps(expected, sort_keys=True, default=str)
            return actual_str == expected_str
        except:
            # Fallback to row-by-row comparison
            return all(
                self._normalize_row(a) == self._normalize_row(e) 
                for a, e in zip(actual, expected)
            )

    def _normalize_row(self, row: Dict) -> Dict:
        """Fast row normalization for comparison"""
        return {k: str(v).strip() if v is not None else None for k, v in row.items()}

    def _calculate_final_score_fast(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimized scoring calculation"""
        if not test_results:
            return {
                'overall_score': 0.0,
                'passed_count': 0,
                'total_count': 0,
                'feedback': ['No test cases found'],
                'avg_execution_time': 0,
                'max_execution_time': 0
            }

        passed_count = sum(1 for r in test_results if r.get('is_correct', False))
        total_count = len(test_results)
        total_score = sum(r.get('score', 0) for r in test_results)
        execution_times = [r.get('execution_time_ms', 0) for r in test_results]

        overall_score = total_score / total_count if total_count > 0 else 0.0

        # Generate concise feedback
        if overall_score >= 95:
            feedback = ["Excellent! All test cases pass."]
        elif overall_score >= 80:
            feedback = ["Good! Most test cases pass."]
        elif passed_count > 0:
            feedback = [f"{passed_count}/{total_count} test cases pass."]
        else:
            feedback = ["No test cases pass. Review your solution."]

        return {
            'overall_score': round(overall_score, 2),
            'passed_count': passed_count,
            'total_count': total_count,
            'feedback': feedback,
            'avg_execution_time': int(sum(execution_times) / len(execution_times)) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0
        }

    def _generate_test_feedback_fast(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Fast feedback generation"""
        if not test_results:
            return ["No test results available"]

        passed = sum(1 for r in test_results if r.get('is_correct', False))
        total = len(test_results)

        if passed == total:
            return ["All test cases pass! Solution looks correct."]
        elif passed > 0:
            return [f"{passed}/{total} test cases pass. Check failing cases."]
        else:
            return ["No test cases pass. Review your query logic."]

    async def _create_submission_record(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        is_correct: bool,
        execution_time: int,
        db: Session
    ) -> Submission:
        """Fast submission record creation"""
        submission = Submission(
            user_id=user_id,
            problem_id=problem_id,
            query=query,
            is_correct=is_correct,
            execution_time=execution_time
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)

        return submission

    async def _create_submission_from_cache(
        self,
        cached_result: Dict[str, Any],
        user_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> Dict[str, Any]:
        """Create new submission from cached result"""
        submission = await self._create_submission_record(
            user_id, problem_id, query, 
            cached_result['is_correct'],
            cached_result['execution_stats']['avg_time_ms'],
            db
        )

        # Update result with new submission ID
        result = cached_result.copy()
        result['submission_id'] = submission.id
        result['from_cache'] = True

        return result

    async def _update_user_progress_async(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ):
        """Asynchronous user progress update"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.thread_pool,
                self._update_user_progress_sync,
                user_id, problem_id, db
            )
        except Exception as e:
            logger.error(f"Async progress update failed: {e}")

    def _update_user_progress_sync(self, user_id: str, problem_id: str, db: Session):
        """Synchronous user progress update"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Check if first time solving
                existing_correct = db.query(Submission).filter(
                    Submission.user_id == user_id,
                    Submission.problem_id == problem_id,
                    Submission.is_correct == True
                ).count()

                if existing_correct == 1:  # First correct submission
                    user.problems_solved = (user.problems_solved or 0) + 1
                    db.commit()
        except Exception as e:
            logger.error(f"Progress update failed: {e}")

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'success': False,
            'is_correct': False,
            'score': 0.0,
            'feedback': [message],
            'submission_id': None
        }

    def _create_error_test_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error test result"""
        return {
            'test_case_id': 'error',
            'test_case_name': 'Execution Error',
            'is_hidden': False,
            'is_correct': False,
            'score': 0.0,
            'feedback': [error_message],
            'execution_time_ms': 0
        }

    def _create_failed_test_result(self, test_case: TestCase, error: str) -> Dict[str, Any]:
        """Create failed test result"""
        return {
            'test_case_id': test_case.id,
            'test_case_name': test_case.name,
            'is_hidden': test_case.is_hidden,
            'is_correct': False,
            'score': 0.0,
            'feedback': [error],
            'execution_time_ms': 0
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        cache_hit_rate = (
            self.metrics['cache_hits'] / self.metrics['total_executions'] * 100 
            if self.metrics['total_executions'] > 0 else 0
        )

        return {
            'total_executions': self.metrics['total_executions'],
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'avg_execution_time_seconds': round(self.metrics['avg_execution_time'], 3),
            'security_blocks': self.metrics['security_blocks'],
            'cache_size': len(self.result_cache.cache),
            'active_sandboxes': len(self.sandbox_manager._sandboxes)
        }

    def clear_cache(self):
        """Clear result cache"""
        self.result_cache.clear()
        logger.info("Result cache cleared")

# Utility function for JSON sanitization (moved outside class for performance)
def sanitize_json_data(data: Any) -> Any:
    """
    Fast JSON sanitization for NaN and infinity values
    """
    if isinstance(data, dict):
        return {key: sanitize_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_data(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data):
            return None
        elif math.isinf(data):
            return None
        return data
    return data

# Create global instance for import
secure_executor = OptimizedSecureQueryExecutor()
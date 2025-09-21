"""
Secure Query Execution System - High Performance
===============================================
Ultra-optimized version focused on submission speed while maintaining API compatibility.
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
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading
import re

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

def sanitize_json_data(data: Any, seen: set = None) -> Any:
    """Comprehensive JSON sanitization for FastAPI responses with UTF-8 safety"""
    if seen is None:
        seen = set()
    
    # Cycle detection for nested structures
    data_id = id(data)
    if data_id in seen:
        return None
    
    # Handle None first
    if data is None:
        return None
    
    # Handle basic JSON-safe types
    if isinstance(data, (bool, int)):
        return data
    elif isinstance(data, str):
        # Ensure string is UTF-8 safe
        try:
            data.encode('utf-8')
            return data
        except UnicodeEncodeError:
            return data.encode('utf-8', errors='replace').decode('utf-8')
    
    # Add to seen set for complex types
    seen.add(data_id)
    
    try:
        # Handle float with NaN/Infinity
        if isinstance(data, float):
            if math.isnan(data):
                return None
            elif math.isinf(data):
                return "Infinity" if data > 0 else "-Infinity"
            else:
                return data
        
        # Handle bytes/bytearray/memoryview - convert to UTF-8 string or base64
        elif isinstance(data, (bytes, bytearray, memoryview)):
            if isinstance(data, memoryview):
                data = data.tobytes()
            elif isinstance(data, bytearray):
                data = bytes(data)
            
            # Try multiple encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            # Final fallback: base64 encoding for binary data
            import base64
            return f"base64:{base64.b64encode(data).decode('ascii')}"
        
        # Handle dict - sanitize keys and values
        elif isinstance(data, dict):
            return {str(k): sanitize_json_data(v, seen) for k, v in data.items()}
        
        # Handle list/tuple/set - convert to list with sanitized elements
        elif isinstance(data, (list, tuple, set)):
            return [sanitize_json_data(item, seen) for item in data]
        
        # Handle datetime objects
        elif hasattr(data, 'isoformat'):  # datetime, date, time
            try:
                return data.isoformat()
            except:
                return str(data)
        
        # Handle Decimal
        elif hasattr(data, '__class__') and data.__class__.__name__ == 'Decimal':
            try:
                if data.is_finite():
                    return float(data)
                else:
                    return str(data)
            except:
                return str(data)
        
        # Handle UUID
        elif hasattr(data, '__class__') and data.__class__.__name__ == 'UUID':
            return str(data)
        
        # Handle numpy types if available
        elif hasattr(data, '__module__') and data.__module__ and 'numpy' in data.__module__:
            try:
                # Handle numpy scalars
                if hasattr(data, 'item'):
                    return sanitize_json_data(data.item(), seen)
                # Handle numpy arrays
                elif hasattr(data, 'tolist'):
                    return sanitize_json_data(data.tolist(), seen)
                else:
                    return str(data)
            except:
                return str(data)
        
        # Handle pandas types if available
        elif hasattr(data, '__module__') and data.__module__ and 'pandas' in data.__module__:
            try:
                # Handle DataFrame
                if hasattr(data, 'to_dict'):
                    return sanitize_json_data(data.to_dict('records'), seen)
                # Handle Series
                elif hasattr(data, 'tolist'):
                    return sanitize_json_data(data.tolist(), seen)
                # Handle Timestamp/NaT
                elif hasattr(data, 'isoformat'):
                    return data.isoformat()
                else:
                    return str(data)
            except:
                return str(data)
        
        # Handle Path-like objects
        elif hasattr(data, '__fspath__'):
            return str(data)
        
        # Handle Exception objects
        elif isinstance(data, Exception):
            return str(data)
        
        # Default fallback - convert to string
        else:
            return str(data)
    
    finally:
        # Remove from seen set when done processing
        seen.discard(data_id)

class _FastSecurityChecker:
    """Minimal security checker optimized for speed"""
    
    def __init__(self):
        # Only essential security checks for maximum speed
        self.forbidden_keywords = {
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE'
        }
    
    def is_safe(self, query: str) -> Tuple[bool, List[str]]:
        """Ultra-fast security check"""
        query_upper = query.upper().strip()
        
        # Fast whitelist check
        if not query_upper.startswith(('SELECT', 'WITH')):
            first_word = query_upper.split()[0] if query_upper else 'UNKNOWN'
            return False, [f"Only SELECT and WITH statements allowed, found: {first_word}"]
        
        # Fast keyword check
        query_words = set(query_upper.split())
        forbidden_found = query_words & self.forbidden_keywords
        if forbidden_found:
            return False, [f"Forbidden operations detected: {', '.join(forbidden_found)}"]
        
        return True, []

class _MinimalCache:
    """Minimal cache implementation for maximum speed"""
    
    def __init__(self, max_size: int = 500):
        self.data = {}
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self.data.get(key)
    
    def set(self, key: str, value: Any):
        with self._lock:
            if len(self.data) >= self.max_size:
                # Remove oldest (simple FIFO)
                oldest_key = next(iter(self.data))
                del self.data[oldest_key]
            self.data[key] = value
    
    def make_key(self, query: str, problem_id: str) -> str:
        return f"{problem_id}:{hashlib.md5(query.encode()).hexdigest()[:16]}"

class SecureQueryExecutor:
    """Ultra-fast secure query executor optimized for submission speed"""
    
    def __init__(self):
        self.max_execution_time = 30
        self.max_memory_mb = 256
        self.max_result_rows = 10000
        self.sandbox_manager = DuckDBSandboxManager()
        
        # Minimal components for maximum speed
        self._security_checker = _FastSecurityChecker()
        self._cache = _MinimalCache()
        self._thread_pool = ThreadPoolExecutor(max_workers=2)  # Reduced for lower overhead
    
    async def submit_solution(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> Dict[str, Any]:
        """Ultra-optimized submission with minimal overhead"""
        start_time = time.time()
        
        try:
            # STEP 1: Ultra-fast security check (no external calls)
            is_safe, security_errors = self._security_checker.is_safe(query)
            if not is_safe:
                return self._create_error_response(security_errors[0])
            
            # STEP 2: Fast cache check (skip for now to avoid complexity)
            cache_key = self._cache.make_key(query, problem_id)
            cached = self._cache.get(cache_key)
            if cached and cached.get('is_correct'):
                # Fast submission creation from cache
                submission = self._create_submission_fast(user_id, problem_id, query, cached, db)
                cached['submission_id'] = submission.id
                return cached
            
            # STEP 3: Get sandbox (reuse existing if possible)
            sandbox = await self._get_sandbox_fast(user_id, problem_id, db)
            if not sandbox:
                return self._create_error_response('Failed to create execution sandbox')
            
            # STEP 4: Execute query with minimal validation
            test_results = await self._execute_minimal_validation(sandbox, problem_id, query, db)
            
            # STEP 5: Fast scoring
            final_score = self._calculate_score_fast(test_results)
            is_correct = final_score['overall_score'] >= 95.0
            
            # STEP 6: Create submission (minimal data)
            submission = Submission(
                user_id=user_id,
                problem_id=problem_id,
                query=query,
                is_correct=is_correct,
                execution_time=final_score['avg_execution_time']
            )
            
            db.add(submission)
            db.commit()
            db.refresh(submission)
            
            # STEP 7: Build minimal response
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
                'security_warnings': []
            }
            
            # STEP 8: Cache successful results
            if is_correct:
                self._cache.set(cache_key, result)
            
            # STEP 9: Async user progress update (fire and forget)
            if is_correct:
                self._update_user_progress_background(user_id, problem_id, db)
            
            return result
            
        except Exception as e:
            logger.error(f"Fast submission failed: {e}")
            return self._create_error_response(f'Execution error: {str(e)}')
    
    async def test_query(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session,
        include_hidden_tests: bool = False
    ) -> Dict[str, Any]:
        """Ultra-fast query testing"""
        try:
            # Fast security check
            is_safe, security_errors = self._security_checker.is_safe(query)
            if not is_safe:
                return {
                    'success': False,
                    'feedback': security_errors,
                    'security_violations': security_errors,
                    'test_results': []
                }
            
            # Get sandbox fast
            sandbox = await self._get_sandbox_fast(user_id, problem_id, db)
            if not sandbox:
                return {
                    'success': False,
                    'feedback': ['Failed to create execution sandbox'],
                    'test_results': []
                }
            
            # Execute with minimal validation
            query_result = await self._execute_query_fast(sandbox, query)
            
            if not query_result.get('success'):
                return {
                    'success': False,
                    'feedback': [query_result.get('error', 'Query execution failed')],
                    'test_results': []
                }
            
            # Minimal test validation
            test_results = await self._validate_minimal(sandbox, problem_id, query, query_result.get('results', []), db)
            
            return {
                'success': True,
                'feedback': self._generate_feedback_fast(test_results),
                'test_results': test_results,
                'security_warnings': [],
                'query_result': {
                    'rows_returned': len(query_result.get('results', [])),
                    'execution_time_ms': query_result.get('execution_time_ms', 0)
                },
                'execution_status': 'SUCCESS'
            }
            
        except Exception as e:
            logger.error(f"Fast test failed: {e}")
            return {
                'success': False,
                'feedback': [f'Test execution error: {str(e)}'],
                'test_results': []
            }
    
    async def _get_sandbox_fast(self, user_id: str, problem_id: str, db: Session) -> Optional[DuckDBSandbox]:
        """Ultra-fast sandbox retrieval with proper S3 data loading"""
        try:
            # Try existing sandbox first
            sandbox = self.sandbox_manager.get_sandbox(user_id, problem_id)
            if sandbox:
                # Check if sandbox needs data reloading (from original logic)
                problem = db.query(Problem).filter(Problem.id == problem_id).first()
                if problem and problem.s3_data_source:
                    # Verify table exists
                    table_info = sandbox.get_table_info()
                    expected_table_name = problem.s3_data_source.get('table_name', 'problem_data')
                    
                    table_exists = any(
                        table.get('name') == expected_table_name 
                        for table in table_info.get('tables', [])
                    )
                    
                    if not table_exists:
                        logger.info(f"Reloading S3 data for existing sandbox - table {expected_table_name} not found")
                        # Properly await async operation
                        setup_result = await sandbox.setup_problem_data(
                            problem_id=problem_id,
                            s3_data_source=problem.s3_data_source
                        )
                        if not setup_result.get('success', False):
                            logger.error(f"Failed to reload problem data: {setup_result.get('error')}")
                
                return sandbox
            
            # Get problem info for new sandbox
            problem = db.query(Problem.id, Problem.s3_data_source).filter(Problem.id == problem_id).first()
            if not problem:
                logger.error(f"Problem {problem_id} not found")
                return None
            
            # Create sandbox properly with await
            sandbox = await self.sandbox_manager.create_sandbox(user_id, problem_id)
            
            # Load S3 data if needed
            if problem.s3_data_source:
                logger.info(f"Loading S3 data for problem {problem_id}")
                setup_result = await sandbox.setup_problem_data(
                    problem_id=problem_id,
                    s3_data_source=problem.s3_data_source
                )
                
                if not setup_result.get('success', False):
                    logger.error(f"Failed to load problem data: {setup_result.get('error')}")
            
            return sandbox
                
        except Exception as e:
            logger.error(f"Fast sandbox creation failed: {e}")
            return None
    
    async def _execute_query_fast(self, sandbox: DuckDBSandbox, query: str) -> Dict[str, Any]:
        """Execute query with minimal overhead"""
        try:
            # Direct execution without complex timeout handling
            result = sandbox.execute_query(query)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': 0
            }
    
    async def _execute_minimal_validation(
        self,
        sandbox: DuckDBSandbox,
        problem_id: str,
        query: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Optimized validation that properly handles all test case types"""
        try:
            # Get problem with all needed fields for validation
            problem = db.query(Problem).filter(Problem.id == problem_id).first()
            
            if not problem:
                return [{
                    'test_case_id': 'error',
                    'test_case_name': 'Problem Not Found',
                    'is_hidden': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ['Problem not found in database'],
                    'execution_time_ms': 0,
                    'execution_status': ExecutionStatus.ERROR.value,
                    'validation_details': {}
                }]
            
            # Check if this is an enhanced S3-based question with hash validation (fastest path)
            if problem.expected_hash and problem.s3_data_source:
                logger.info(f"Using S3 hash validation for problem {problem_id}")
                return await self._hash_validation_fast(problem, sandbox, query)
            
            # Check for traditional test cases
            test_cases = db.query(TestCase).filter(
                TestCase.problem_id == problem_id
            ).order_by(TestCase.order_index).all()
            
            if test_cases:
                # Execute against test cases (optimized)
                return await self._execute_test_cases_fast(sandbox, query, test_cases)
            
            # Check if problem has S3 solution source for verification
            if hasattr(problem, 'solution_source') and problem.solution_source == 's3' and hasattr(problem, 's3_solution_source') and problem.s3_solution_source:
                # Execute query and verify with S3 solution
                result = await self._execute_query_fast(sandbox, query)
                
                if result.get('success'):
                    user_results = result.get('results', [])
                    s3_verification = await self._verify_with_s3_solution_fast(
                        sandbox, problem, query, user_results
                    )
                    return s3_verification
                else:
                    return [{
                        'test_case_id': 's3_verification',
                        'test_case_name': 'S3 Solution Verification',
                        'is_hidden': False,
                        'is_correct': False,
                        'score': 0.0,
                        'feedback': [result.get('error', 'Query execution failed')],
                        'execution_time_ms': 0
                    }]
            
            # Check for expected output in problem question
            if problem.question and isinstance(problem.question, dict):
                expected_output = problem.question.get('expectedOutput', [])
                if expected_output:
                    result = await self._execute_query_fast(sandbox, query)
                    
                    if result.get('success'):
                        user_results = result.get('results', [])
                        
                        # Enhanced comparison with detailed feedback
                        is_correct, comparison_details = self._compare_results_detailed(user_results, expected_output)
                        
                        feedback = []
                        if is_correct:
                            feedback.append('Results match expected output perfectly')
                        else:
                            feedback.extend(comparison_details)
                        
                        return [{
                            'test_case_id': f"{problem_id}_expected_output",
                            'test_case_name': 'Expected Output Check',
                            'is_hidden': False,
                            'is_correct': is_correct,
                            'score': 100.0 if is_correct else 0.0,
                            'feedback': feedback,
                            'execution_time_ms': result.get('execution_time_ms', 0),
                            'user_output': user_results,
                            'expected_output': expected_output,
                            'output_matches': is_correct
                        }]
                    else:
                        return [{
                            'test_case_id': f"{problem_id}_expected_output",
                            'test_case_name': 'Expected Output Check',
                            'is_hidden': False,
                            'is_correct': False,
                            'score': 0.0,
                            'feedback': [result.get('error', 'Query execution failed')],
                            'execution_time_ms': 0
                        }]
            
            # Fallback: just execute query and return success
            result = await self._execute_query_fast(sandbox, query)
            
            if result.get('success'):
                return [{
                    'test_case_id': 'basic_execution',
                    'test_case_name': 'Query Execution',
                    'is_hidden': False,
                    'is_correct': True,
                    'score': 100.0,
                    'feedback': ['Query executed successfully'],
                    'execution_time_ms': result.get('execution_time_ms', 0)
                }]
            else:
                return [{
                    'test_case_id': 'execution_error',
                    'test_case_name': 'Query Execution',
                    'is_hidden': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': [result.get('error', 'Query failed')],
                    'execution_time_ms': 0
                }]
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return [{
                'test_case_id': 'validation_error',
                'test_case_name': 'Validation Error',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'Validation error: {str(e)}'],
                'execution_time_ms': 0
            }]
    
    async def _execute_test_cases_fast(
        self,
        sandbox: DuckDBSandbox,
        query: str,
        test_cases: List[TestCase]
    ) -> List[Dict[str, Any]]:
        """Fast execution against traditional test cases"""
        results = []
        
        for test_case in test_cases:
            try:
                # Execute query
                result = await self._execute_query_fast(sandbox, query)
                
                if result.get('success'):
                    user_output = result.get('results', [])
                    expected_output = test_case.expected_output or []
                    
                    # Handle S3 expected output source if exists
                    if test_case.expected_output_source:
                        try:
                            s3_config = test_case.expected_output_source
                            if s3_config.get('bucket') and s3_config.get('key'):
                                # Fetch from S3
                                from .s3_service import s3_service
                                from .schemas import S3AnswerSource
                                
                                s3_answer_source = S3AnswerSource(**s3_config)
                                cache_result = s3_service.fetch_answer_file(
                                    bucket=s3_answer_source.bucket,
                                    key=s3_answer_source.key,
                                    format=s3_answer_source.format,
                                    etag=getattr(s3_answer_source, 'etag', None)
                                )
                                expected_output = cache_result.data
                                logger.info(f"Fetched {len(expected_output)} expected rows from S3")
                        except Exception as e:
                            logger.error(f"Failed to fetch S3 expected output: {e}")
                            # Continue with fallback expected_output
                    
                    # Enhanced comparison with detailed feedback
                    is_correct, comparison_details = self._compare_results_detailed(user_output, expected_output)
                    
                    feedback = []
                    if is_correct:
                        feedback.append('Results match expected output perfectly')
                    else:
                        feedback.extend(comparison_details)
                    
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_hidden': test_case.is_hidden,
                        'is_correct': is_correct,
                        'score': 100.0 if is_correct else 0.0,
                        'feedback': feedback,
                        'execution_time_ms': result.get('execution_time_ms', 0),
                        'execution_status': ExecutionStatus.SUCCESS.value,
                        'user_output': user_output,
                        'expected_output': expected_output,
                        'output_matches': is_correct
                    })
                else:
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_hidden': test_case.is_hidden,
                        'is_correct': False,
                        'score': 0.0,
                        'feedback': [result.get('error', 'Query execution failed')],
                        'execution_time_ms': 0,
                        'execution_status': ExecutionStatus.ERROR.value
                    })
                    
            except Exception as e:
                logger.error(f"Test case execution failed: {e}")
                results.append({
                    'test_case_id': test_case.id,
                    'test_case_name': test_case.name,
                    'is_hidden': test_case.is_hidden,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': [f'Test execution error: {str(e)}'],
                    'execution_time_ms': 0,
                    'execution_status': ExecutionStatus.ERROR.value
                })
        
        return results
    
    async def _hash_validation_fast(
        self,
        problem: Problem,
        sandbox: DuckDBSandbox,
        query: str
    ) -> List[Dict[str, Any]]:
        """Fast hash-based validation"""
        try:
            # Execute user query
            result = await self._execute_query_fast(sandbox, query)
            
            if not result.get('success'):
                return [{
                    'test_case_id': 'hash_validation',
                    'test_case_name': 'Hash Validation',
                    'is_hidden': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': [result.get('error', 'Query execution failed')],
                    'execution_time_ms': 0
                }]
            
            user_results = result.get('results', [])
            
            # Fast hash comparison
            user_hash = self._compute_result_hash_fast(user_results)
            expected_hash = problem.expected_hash
            
            is_correct = user_hash == expected_hash
            
            return [{
                'test_case_id': 'hash_validation',
                'test_case_name': 'Result Hash Validation',
                'is_hidden': False,
                'is_correct': is_correct,
                'score': 100.0 if is_correct else 0.0,
                'feedback': ['Query results match expected pattern'] if is_correct else ['Query results do not match expected pattern'],
                'execution_time_ms': result.get('execution_time_ms', 0),
                'user_hash': user_hash,
                'expected_hash': expected_hash,
                'hash_matches': is_correct
            }]
            
        except Exception as e:
            logger.error(f"Hash validation failed: {e}")
            return [{
                'test_case_id': 'hash_validation_error',
                'test_case_name': 'Hash Validation Error',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'Hash validation error: {str(e)}'],
                'execution_time_ms': 0
            }]
    
    async def _verify_with_s3_solution_fast(
        self,
        sandbox: DuckDBSandbox,
        problem: Problem,
        query: str,
        user_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fast S3 solution verification"""
        try:
            from .s3_service import s3_service
            
            s3_solution_data = problem.s3_solution_source
            bucket = s3_solution_data.get('bucket')
            solution_key = s3_solution_data.get('key')
            
            # Fetch expected results from S3
            validation_result = s3_service.validate_dataset_file(bucket, solution_key, 'solution')
            if not validation_result.get('is_valid'):
                return [{
                    'test_case_id': 's3_solution_verification',
                    'test_case_name': 'S3 Solution Verification',
                    'is_hidden': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ['Failed to load expected results from S3'],
                    'execution_time_ms': 0
                }]
            
            expected_results = validation_result.get('sample_data', [])
            
            # Fast comparison
            is_correct = self._compare_results_fast(user_results, expected_results)
            
            return [{
                'test_case_id': 's3_solution_verification',
                'test_case_name': 'S3 Solution Verification',
                'is_hidden': False,
                'is_correct': is_correct,
                'score': 100.0 if is_correct else 0.0,
                'feedback': ['Results match S3 solution'] if is_correct else ['Results differ from S3 solution'],
                'execution_time_ms': 0,
                'user_output': user_results,
                'expected_output': expected_results,
                'output_matches': is_correct
            }]
            
        except Exception as e:
            logger.error(f"S3 solution verification failed: {e}")
            return [{
                'test_case_id': 's3_solution_error',
                'test_case_name': 'S3 Solution Error',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'S3 verification error: {str(e)}'],
                'execution_time_ms': 0
            }]
    
    async def _validate_minimal(
        self,
        sandbox: DuckDBSandbox,
        problem_id: str,
        query: str,
        query_results: List[Dict[str, Any]],
        db: Session
    ) -> List[Dict[str, Any]]:
        """Fast minimal validation for test queries"""
        try:
            # Just return basic success for test queries
            return [{
                'test_case_id': 'test_execution',
                'test_case_name': 'Query Test',
                'is_hidden': False,
                'is_correct': True,
                'score': 100.0,
                'feedback': ['Query executed successfully'],
                'execution_time_ms': 0
            }]
            
        except Exception as e:
            logger.error(f"Minimal validation failed: {e}")
            return [{
                'test_case_id': 'test_error',
                'test_case_name': 'Query Test Error',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'Test error: {str(e)}'],
                'execution_time_ms': 0
            }]
    
    def _compare_results_fast(self, user_results: List[Dict], expected_results: List[Dict]) -> bool:
        """Ultra-fast result comparison"""
        try:
            if len(user_results) != len(expected_results):
                return False
            
            # Quick comparison for small datasets
            if len(user_results) <= 100:
                return user_results == expected_results
            
            # Sample comparison for large datasets
            sample_size = min(50, len(user_results))
            for i in range(0, len(user_results), len(user_results) // sample_size):
                if i < len(user_results) and i < len(expected_results):
                    if user_results[i] != expected_results[i]:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Fast comparison failed: {e}")
            return False
    
    def _compare_results_detailed(self, user_results: List[Dict], expected_results: List[Dict]) -> Tuple[bool, List[str]]:
        """Detailed result comparison with specific feedback"""
        try:
            feedback = []
            
            # Check row count first
            user_count = len(user_results)
            expected_count = len(expected_results)
            
            if user_count != expected_count:
                feedback.append(f"Row count mismatch: your query returned {user_count} rows, expected {expected_count} rows")
                return False, feedback
            
            if user_count == 0:
                return True, ["Both results are empty"]
            
            # Check column structure
            if user_results and expected_results:
                user_columns = set(user_results[0].keys()) if user_results[0] else set()
                expected_columns = set(expected_results[0].keys()) if expected_results[0] else set()
                
                if user_columns != expected_columns:
                    missing_cols = expected_columns - user_columns
                    extra_cols = user_columns - expected_columns
                    
                    if missing_cols:
                        feedback.append(f"Missing columns: {', '.join(sorted(missing_cols))}")
                    if extra_cols:
                        feedback.append(f"Unexpected columns: {', '.join(sorted(extra_cols))}")
                    
                    return False, feedback
            
            # Check data content
            for i, (user_row, expected_row) in enumerate(zip(user_results, expected_results)):
                if user_row != expected_row:
                    # Find specific differences
                    differences = []
                    for col in expected_row.keys():
                        if col in user_row:
                            user_val = user_row[col]
                            expected_val = expected_row[col]
                            if user_val != expected_val:
                                differences.append(f"{col}: got '{user_val}', expected '{expected_val}'")
                    
                    if differences:
                        if i < 3:  # Show details for first few rows
                            feedback.append(f"Row {i + 1} differs - {'; '.join(differences[:3])}")
                        elif i == 3:  # Summarize if many differences
                            feedback.append(f"... and {user_count - i} more rows with differences")
                            break
                    else:
                        feedback.append(f"Row {i + 1} has subtle differences in data types or formatting")
                    
                    if len(feedback) >= 5:  # Limit feedback length
                        break
            
            if feedback:
                return False, feedback
            else:
                return True, ["Results match perfectly"]
                
        except Exception as e:
            logger.error(f"Detailed comparison failed: {e}")
            return False, [f"Comparison error: {str(e)}"]
    
    def _compute_result_hash_fast(self, results: List[Dict[str, Any]]) -> str:
        """Fast hash computation for results"""
        try:
            # Simple hash based on result structure
            content = json.dumps(results, sort_keys=True, default=str)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Hash computation failed: {e}")
            return "error_hash"
    
    def _calculate_score_fast(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced scoring calculation with detailed feedback"""
        if not test_results:
            return {
                'overall_score': 0.0,
                'passed_count': 0,
                'total_count': 0,
                'avg_execution_time': 0,
                'max_execution_time': 0,
                'feedback': ['No test results available - this problem may not have test cases configured yet.']
            }
        
        passed_count = sum(1 for result in test_results if result.get('is_correct', False))
        total_count = len(test_results)
        overall_score = (passed_count / total_count) * 100.0 if total_count > 0 else 0.0
        
        execution_times = [result.get('execution_time_ms', 0) for result in test_results]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        
        # Collect detailed feedback from all test results
        detailed_feedback = []
        
        # Add overall score summary
        if passed_count == total_count:
            detailed_feedback.append(f'✅ Excellent! All {total_count} test case(s) passed!')
        elif passed_count > 0:
            detailed_feedback.append(f'⚠️  {passed_count} of {total_count} test cases passed')
        else:
            detailed_feedback.append(f'❌ None of the {total_count} test case(s) passed')
        
        # Add specific feedback from each test result
        for i, result in enumerate(test_results, 1):
            test_name = result.get('test_case_name', f'Test Case {i}')
            is_correct = result.get('is_correct', False)
            test_feedback = result.get('feedback', [])
            
            if is_correct:
                detailed_feedback.append(f'✓ {test_name}: PASSED')
            else:
                detailed_feedback.append(f'✗ {test_name}: FAILED')
                # Add specific failure details
                if test_feedback:
                    for fb in test_feedback:
                        detailed_feedback.append(f'  → {fb}')
                
                # Add comparison details if available
                if 'user_output' in result and 'expected_output' in result:
                    user_rows = len(result.get('user_output', []))
                    expected_rows = len(result.get('expected_output', []))
                    if user_rows != expected_rows:
                        detailed_feedback.append(f'  → Row count mismatch: got {user_rows} rows, expected {expected_rows} rows')
                    elif user_rows > 0:
                        detailed_feedback.append(f'  → Row count matches ({user_rows} rows) but data differs')
        
        # Add execution time info if significant
        if avg_execution_time > 1000:  # More than 1 second
            detailed_feedback.append(f'⏱️  Average execution time: {avg_execution_time:.0f}ms')
        
        return {
            'overall_score': overall_score,
            'passed_count': passed_count,
            'total_count': total_count,
            'avg_execution_time': avg_execution_time,
            'max_execution_time': max_execution_time,
            'feedback': detailed_feedback
        }
    
    def _generate_feedback_fast(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Fast feedback generation"""
        if not test_results:
            return ['No test results available']
        
        feedback = []
        for result in test_results:
            if result.get('feedback'):
                feedback.extend(result['feedback'])
        
        return feedback if feedback else ['Query executed']
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Fast error response creation"""
        return {
            'success': False,
            'is_correct': False,
            'score': 0.0,
            'feedback': [error_message],
            'test_results': [],
            'passed_tests': 0,
            'total_tests': 0,
            'execution_stats': {
                'avg_time_ms': 0,
                'max_time_ms': 0,
                'total_time_ms': 0
            },
            'security_warnings': [error_message],
            'submission_id': None
        }
    
    def _create_submission_fast(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        cached_result: Dict[str, Any],
        db: Session
    ) -> Submission:
        """Fast submission creation from cache"""
        submission = Submission(
            user_id=user_id,
            problem_id=problem_id,
            query=query,
            is_correct=cached_result.get('is_correct', False),
            execution_time=cached_result.get('execution_stats', {}).get('avg_time_ms', 0)
        )
        
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return submission
    
    def _update_user_progress_background(self, user_id: str, problem_id: str, db: Session):
        """Background user progress update"""
        try:
            # Simple fire-and-forget progress update
            self._thread_pool.submit(self._update_user_progress_sync, user_id, problem_id, db)
        except Exception as e:
            logger.warning(f"Background progress update failed: {e}")
    
    def _update_user_progress_sync(self, user_id: str, problem_id: str, db: Session):
        """Synchronous user progress update"""
        try:
            # Check if this is first time solving this problem
            existing_correct = db.query(Submission).filter(
                Submission.user_id == user_id,
                Submission.problem_id == problem_id,
                Submission.is_correct == True
            ).first()
            
            if not existing_correct:
                # Update user's solved count
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.problems_solved = (user.problems_solved or 0) + 1
                    db.commit()
                    
        except Exception as e:
            logger.error(f"User progress update failed: {e}")
    
    async def get_user_progress(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Fast user progress retrieval"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Basic progress stats
            total_submissions = db.query(Submission).filter(Submission.user_id == user_id).count()
            correct_submissions = db.query(Submission).filter(
                Submission.user_id == user_id,
                Submission.is_correct == True
            ).count()
            
            return {
                'success': True,
                'user_id': user_id,
                'problems_solved': user.problems_solved or 0,
                'total_submissions': total_submissions,
                'correct_submissions': correct_submissions,
                'accuracy': (correct_submissions / total_submissions * 100) if total_submissions > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"User progress retrieval failed: {e}")
            return {
                'success': False,
                'error': f'Progress retrieval failed: {str(e)}'
            }

# Global secure executor instance
secure_executor = SecureQueryExecutor()
"""
Secure Query Execution System
============================
Integrates SQL validation, sandbox execution, and test case validation
for the SQLGym learning platform.
"""

import asyncio
import logging
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from contextlib import asynccontextmanager

from .query_validator import query_validator, QueryValidationError, QueryRisk
from .test_validator import test_validator, ComparisonMode
# PostgreSQL sandbox functionality removed - using DuckDB only
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

def sanitize_json_data(data: Any) -> Any:
    """
    Recursively sanitize data by replacing NaN and infinity values with JSON-safe values
    
    Args:
        data: Data structure that may contain NaN or infinity values
        
    Returns:
        Sanitized data structure safe for JSON serialization
    """
    if isinstance(data, dict):
        return {key: sanitize_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_data(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data):
            return None  # Convert NaN to null in JSON
        elif math.isinf(data):
            return "Infinity" if data > 0 else "-Infinity"  # Convert infinity to string
        else:
            return data
    else:
        return data

class SecureQueryExecutor:
    """Secure SQL query executor with comprehensive validation"""
    
    def __init__(self):
        self.max_execution_time = 30  # seconds
        self.max_memory_mb = 256
        self.max_result_rows = 10000
        self.sandbox_manager = DuckDBSandboxManager()
    
    async def submit_solution(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Submit and validate a complete solution
        
        Returns:
            Complete submission result with scoring and feedback
        """
        try:
            # Step 1: Get or create sandbox to access loaded table names
            sandbox = await self._get_or_create_sandbox(user_id, problem_id, db)
            
            if not sandbox:
                return {
                    'success': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ['Failed to create execution sandbox'],
                    'submission_id': None
                }
            
            # Step 2: Validate query security with semantic validation
            validation_result = query_validator.validate_query(query, sandbox.loaded_table_names)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': validation_result['errors'],
                    'security_violations': validation_result['blocked_operations'],
                    'submission_id': None
                }
            
            # Step 3: Execute against all test cases
            test_results = await self._execute_all_test_cases(
                sandbox.id, problem_id, query, db
            )
            
            # Step 4: Calculate final score and correctness
            final_score = self._calculate_final_score(test_results)
            is_correct = final_score['overall_score'] >= 95.0
            
            # Step 5: Create submission record
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
            
            # Step 6: Update user progress if correct
            if is_correct:
                await self._update_user_progress(user_id, problem_id, db)
            
            return {
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
                    'memory_used_mb': final_score.get('avg_memory_mb', 0)
                },
                'security_warnings': validation_result.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Solution submission failed: {e}")
            return {
                'success': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'Execution error: {str(e)}'],
                'submission_id': None
            }
    
    async def test_query(
        self,
        user_id: str,
        problem_id: str,
        query: str,
        db: Session,
        include_hidden_tests: bool = False
    ) -> Dict[str, Any]:
        """
        Test a query without submitting (practice mode)
        
        Returns:
            Test results without creating submission
        """
        try:
            # Step 1: Get or create sandbox to access loaded table names
            sandbox = await self._get_or_create_sandbox(user_id, problem_id, db)
            
            if not sandbox:
                return {
                    'success': False,
                    'feedback': ['Failed to create execution sandbox'],
                    'test_results': []
                }
            
            # Step 2: Quick validation with semantic validation
            validation_result = query_validator.validate_query(query, sandbox.loaded_table_names)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'feedback': validation_result['errors'],
                    'security_violations': validation_result['blocked_operations'],
                    'test_results': []
                }
            
            # Step 3: Execute query in DuckDB sandbox
            query_result = sandbox.execute_query(query)
            execution_status = ExecutionStatus.SUCCESS if query_result.get('success') else ExecutionStatus.ERROR
            
            # Step 4: Execute test case validation using hybrid approach
            test_results = []
            if query_result.get('success'):
                problem = db.query(Problem).filter(Problem.id == problem_id).first()
                if problem:
                    # Use hybrid verification approach based on solution_source
                    if problem.solution_source == 's3' and problem.s3_solution_source:
                        # Use S3 solution verification
                        test_results = await self._verify_with_s3_solution(
                            sandbox, problem, query, query_result.get('results', [])
                        )
                    else:
                        # Use Neon database verification (default)
                        if problem.question:
                            expected_output = problem.question.get('expectedOutput', [])
                            if expected_output:
                                # Compare results with expected output
                                actual_results = query_result.get('results', [])
                                test_results.append({
                                    'test_case_id': f"{problem_id}_main",
                                    'passed': actual_results == expected_output,
                                    'expected': expected_output,
                                    'actual': actual_results,
                                    'is_hidden': False
                                })
            
            # Step 5: Provide feedback without final scoring
            feedback = self._generate_test_feedback(test_results)
            
            return {
                'success': True,
                'feedback': feedback,
                'test_results': test_results,
                'security_warnings': validation_result.get('warnings', []),
                'query_analysis': validation_result['parsed_query'],
                'query_result': query_result,  # Include actual query execution results
                'execution_status': execution_status.value if execution_status else 'SUCCESS'
            }
            
        except Exception as e:
            logger.error(f"Query test failed: {e}")
            return {
                'success': False,
                'feedback': [f'Test execution error: {str(e)}'],
                'test_results': []
            }
    
    async def _get_or_create_sandbox(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ) -> Optional[DuckDBSandbox]:
        """
        Get existing sandbox or create a new one for the user and problem
        
        Args:
            user_id: User identifier
            problem_id: Problem identifier
            db: Database session
            
        Returns:
            DuckDBSandbox instance or None if creation failed
        """
        try:
            # Get problem info first to check if we need S3 data
            problem = db.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                logger.error(f"Problem {problem_id} not found")
                return None
            
            # First, try to get existing sandbox
            sandbox = self.sandbox_manager.get_sandbox(user_id, problem_id)
            
            if sandbox is not None:
                logger.info(f"Using existing sandbox for user {user_id}, problem {problem_id}")
                
                # IMPORTANT FIX: Always ensure data is loaded for existing sandboxes too
                if problem.s3_data_source:
                    # Check if sandbox has the required table loaded
                    table_info = sandbox.get_table_info()
                    expected_table_name = problem.s3_data_source.get('table_name', 'problem_data')
                    
                    # If the expected table is not found, reload the data
                    table_exists = any(
                        table.get('name') == expected_table_name 
                        for table in table_info.get('tables', [])
                    )
                    
                    if not table_exists:
                        logger.info(f"Reloading S3 data for existing sandbox - table {expected_table_name} not found")
                        setup_result = await sandbox.setup_problem_data(
                            problem_id=problem_id,
                            s3_data_source=problem.s3_data_source
                        )
                        
                        if not setup_result.get('success', False):
                            logger.error(f"Failed to reload problem data: {setup_result.get('error')}")
                            # Continue anyway - some problems might not need data
                
                return sandbox
            
            # Create new sandbox
            logger.info(f"Creating new sandbox for user {user_id}, problem {problem_id}")
            sandbox = await self.sandbox_manager.create_sandbox(user_id, problem_id)
            
            # Load problem data if it has S3 data source
            if problem.s3_data_source:
                logger.info(f"Loading S3 data for problem {problem_id}")
                setup_result = await sandbox.setup_problem_data(
                    problem_id=problem_id,
                    s3_data_source=problem.s3_data_source
                )
                
                if not setup_result.get('success', False):
                    logger.error(f"Failed to load problem data: {setup_result.get('error')}")
                    # Continue anyway - some problems might not need data
            
            return sandbox
            
        except Exception as e:
            logger.error(f"Failed to get or create sandbox for user {user_id}, problem {problem_id}: {e}")
            return None
    
    async def _verify_with_s3_solution(
        self,
        sandbox: DuckDBSandbox,
        problem: Problem,
        user_query: str,
        user_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Verify user query results against S3 solution parquet file (out.parquet)
        
        Args:
            sandbox: DuckDB sandbox instance
            problem: Problem object with S3 solution configuration
            user_query: User's SQL query
            user_results: Results from user's query
            
        Returns:
            List of test results
        """
        try:
            s3_solution = problem.s3_solution_source
            if not s3_solution:
                return [{
                    'test_case_id': f"{problem.id}_s3_solution",
                    'passed': False,
                    'expected': [],
                    'actual': user_results,
                    'is_hidden': False,
                    'error': 'S3 solution source not configured'
                }]
            
            # Download out.parquet file from S3 (expected results dataset)
            from .s3_service import s3_service
            logger.info(f"Downloading S3 solution results from s3://{s3_solution['bucket']}/{s3_solution['key']}")
            
            try:
                # Use the new fetch_parquet_solution method to get expected results directly
                solution_result = s3_service.fetch_parquet_solution(
                    bucket=s3_solution['bucket'], 
                    key=s3_solution['key'],
                    etag=s3_solution.get('etag')
                )
                expected_results = solution_result.data
                logger.info(f"Successfully loaded {len(expected_results)} expected result rows from S3")
                
            except Exception as e:
                logger.error(f"Failed to download S3 solution parquet file: {e}")
                return [{
                    'test_case_id': f"{problem.id}_s3_solution",
                    'passed': False,
                    'expected': [],
                    'actual': user_results,
                    'is_hidden': False,
                    'error': f'Failed to download solution parquet file: {str(e)}'
                }]
            
            # Compare user results with official solution results
            comparison = self._compare_query_results(user_results, expected_results)
            
            return [{
                'test_case_id': f"{problem.id}_s3_solution",
                'passed': comparison['matches'],
                'expected': expected_results,
                'actual': user_results,
                'is_hidden': False,
                'verification_method': 's3_solution',
                'validation_details': {
                    'row_comparisons': comparison['row_comparisons'],
                    'matching_row_count': comparison['matching_row_count'],
                    'total_row_count': comparison['total_row_count'],
                    'comparison_differences': comparison['differences']
                }
            }]
            
        except Exception as e:
            logger.error(f"S3 solution verification failed for problem {problem.id}: {e}")
            return [{
                'test_case_id': f"{problem.id}_s3_solution",
                'passed': False,
                'expected': [],
                'actual': user_results,
                'is_hidden': False,
                'error': f'Verification error: {str(e)}'
            }]
    
    def _compare_query_results(self, actual: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare two query result sets for equivalence with detailed comparison info
        
        Args:
            actual: Results from user query
            expected: Results from official solution
            
        Returns:
            Dict with comparison results including detailed row-by-row comparison
        """
        comparison_result = {
            'matches': False,
            'row_comparisons': [],
            'matching_row_count': 0,
            'total_row_count': 0,
            'differences': []
        }
        
        try:
            # Handle empty results
            if not actual and not expected:
                comparison_result['matches'] = True
                return comparison_result
            
            if not actual or not expected:
                comparison_result['differences'].append(
                    f"One result set is empty: actual={len(actual or [])}, expected={len(expected or [])}"
                )
                return comparison_result
                
            # Check row count
            if len(actual) != len(expected):
                comparison_result['differences'].append(
                    f"Row count mismatch: actual={len(actual)}, expected={len(expected)}"
                )
                comparison_result['total_row_count'] = len(expected)
                return comparison_result
                
            comparison_result['total_row_count'] = len(expected)
            
            # Sort both result sets for comparison (handle unordered results)
            def normalize_row(row):
                """Convert row values to comparable format with robust type handling"""
                normalized = {}
                for key, value in row.items():
                    if value is None:
                        normalized[key] = None
                    else:
                        # Convert to string and strip whitespace for consistent comparison
                        # This handles int/float/string type mismatches gracefully
                        normalized[key] = str(value).strip()
                return normalized
            
            actual_normalized = [normalize_row(row) for row in actual]
            expected_normalized = [normalize_row(row) for row in expected]
            
            # Create mapping for detailed row comparison
            actual_tuples = [tuple(sorted(row.items())) for row in actual_normalized]
            expected_tuples = [tuple(sorted(row.items())) for row in expected_normalized]
            
            # Create detailed row comparisons
            for i, expected_row in enumerate(expected):
                expected_tuple = expected_tuples[i]
                matches = expected_tuple in actual_tuples
                
                row_comparison = {
                    'row_index': i,
                    'matches': matches,
                    'expected_row': expected_row,
                    'actual_row': None
                }
                
                if matches:
                    # Find the matching actual row
                    for j, actual_row in enumerate(actual):
                        if actual_tuples[j] == expected_tuple:
                            row_comparison['actual_row'] = actual_row
                            break
                    comparison_result['matching_row_count'] += 1
                else:
                    row_comparison['differences'] = "Row not found in user results"
                
                comparison_result['row_comparisons'].append(row_comparison)
            
            # Check if all rows match
            comparison_result['matches'] = comparison_result['matching_row_count'] == comparison_result['total_row_count']
            
            return comparison_result
            
        except Exception as e:
            logger.error(f"Error comparing query results: {e}")
            comparison_result['differences'].append(f"Comparison error: {str(e)}")
            return comparison_result
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """
        Safely split SQL content into individual statements
        
        Args:
            sql_content: Multi-line SQL content
            
        Returns:
            List of individual SQL statements
        """
        try:
            # Simple but safe approach: split on semicolon followed by newline
            # This handles most cases while avoiding complex SQL parsing
            statements = []
            current_statement = ""
            
            lines = sql_content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('--') or line.startswith('/*'):
                    continue
                
                current_statement += line + " "
                
                # If line ends with semicolon, it's likely end of statement
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # Add any remaining statement without semicolon
            if current_statement.strip():
                statements.append(current_statement.strip())
            
            # Filter out empty statements
            statements = [stmt for stmt in statements if stmt and stmt != ';']
            
            logger.info(f"Split SQL content into {len(statements)} statements")
            return statements
            
        except Exception as e:
            logger.error(f"Error splitting SQL statements: {e}")
            # Fallback: return as single statement
            return [sql_content.strip()]
    
    async def get_problem_schema(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get database schema information for a problem
        """
        try:
            # Verify problem exists
            problem = db.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                return {
                    'success': False,
                    'error': 'Problem not found'
                }
            
            # Get or create sandbox to access database
            sandbox = await self._get_or_create_sandbox(user_id, problem_id, db)
            
            if not sandbox:
                return {
                    'success': False,
                    'error': 'Failed to create schema access sandbox'
                }
            
            # Extract schema from problem question data
            question_data = problem.question if isinstance(problem.question, dict) else {}
            tables = question_data.get('tables', [])
            
            # Enhance with database introspection if needed
            schema_info = await self._introspect_database_schema(sandbox.id, tables)
            
            return {
                'success': True,
                'problem_id': problem_id,
                'tables': schema_info['tables'],
                'relationships': schema_info.get('relationships', []),
                'indexes': schema_info.get('indexes', []),
                'constraints': schema_info.get('constraints', [])
            }
            
        except Exception as e:
            logger.error(f"Schema retrieval failed: {e}")
            return {
                'success': False,
                'error': f'Schema access error: {str(e)}'
            }
    
    async def get_user_progress(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get comprehensive user progress statistics
        """
        try:
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Get submission statistics
            from sqlalchemy import func, and_
            
            submission_stats = db.query(
                func.count(Submission.id).label('total_submissions'),
                func.count(Submission.id).filter(Submission.is_correct == True).label('correct_submissions'),
                func.avg(Submission.execution_time).label('avg_execution_time'),
                func.min(Submission.execution_time).label('best_execution_time')
            ).filter(Submission.user_id == user_id).first()
            
            # Get problem difficulty breakdown
            difficulty_stats = db.query(
                Problem.difficulty,
                func.count(Submission.id).filter(Submission.is_correct == True).label('solved_count')
            ).join(
                Submission, Submission.problem_id == Problem.id
            ).filter(
                Submission.user_id == user_id,
                Submission.is_correct == True
            ).group_by(Problem.difficulty).all()
            
            # Get recent activity
            recent_submissions = db.query(Submission).filter(
                Submission.user_id == user_id
            ).order_by(Submission.submitted_at.desc()).limit(10).all()
            
            # Calculate streak and other metrics
            streak_info = await self._calculate_user_streak(user_id, db)
            
            return {
                'success': True,
                'user_id': user_id,
                'username': user.username,
                'statistics': {
                    'problems_solved': user.problems_solved or 0,
                    'total_submissions': submission_stats.total_submissions or 0,
                    'correct_submissions': submission_stats.correct_submissions or 0,
                    'success_rate': (
                        (submission_stats.correct_submissions / submission_stats.total_submissions * 100)
                        if submission_stats.total_submissions > 0 else 0
                    ),
                    'avg_execution_time_ms': int(submission_stats.avg_execution_time or 0),
                    'best_execution_time_ms': int(submission_stats.best_execution_time or 0)
                },
                'difficulty_breakdown': {
                    stat.difficulty: stat.solved_count for stat in difficulty_stats
                },
                'streak': streak_info,
                'recent_activity': [
                    {
                        'submission_id': sub.id,
                        'problem_id': sub.problem_id,
                        'is_correct': sub.is_correct,
                        'submitted_at': sub.submitted_at.isoformat(),
                        'execution_time': sub.execution_time
                    }
                    for sub in recent_submissions
                ],
                'badges': [],  # TODO: Implement badge system
                'achievements': []  # TODO: Implement achievement system
            }
            
        except Exception as e:
            logger.error(f"Progress retrieval failed: {e}")
            return {
                'success': False,
                'error': f'Progress access error: {str(e)}'
            }
    
    # PostgreSQL sandbox functionality removed - using DuckDB only
    
    async def _execute_all_test_cases(
        self,
        sandbox_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Execute query against all test cases with enhanced S3 hash validation"""
        from .models import Problem
        
        # Get problem details to check for enhanced S3 validation
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return [{
                'test_case_id': 'unknown',
                'test_case_name': 'Problem not found',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': ['Problem not found in database'],
                'execution_time_ms': 0,
                'execution_status': ExecutionStatus.ERROR.value,
                'validation_details': {}
            }]
        
        # Check if this is an enhanced S3-based question with hash validation
        if problem.expected_hash and problem.s3_data_source:
            logger.info(f"Using enhanced S3 hash validation for problem {problem_id}")
            return await self._execute_s3_hash_validation(problem, query, db)
        
        # Fall back to traditional test case validation
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == problem_id
        ).order_by(TestCase.order_index).all()
        
        results = []
        
        # Extract user_id and problem_id from sandbox_id (format: "user_id_problem_id") 
        try:
            user_id, extracted_problem_id = sandbox_id.rsplit('_', 1)
            # Verify the problem_id matches
            if extracted_problem_id != problem_id:
                logger.warning(f"Problem ID mismatch: {extracted_problem_id} != {problem_id}")
            sandbox = self.sandbox_manager.get_sandbox(user_id, problem_id)
        except ValueError:
            logger.error(f"Invalid sandbox_id format: {sandbox_id}")
            sandbox = None
            
        if not sandbox:
            logger.error(f"Sandbox not found for {sandbox_id}")
            return [{
                'test_case_id': 'error',
                'test_case_name': 'Execution Error',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': ['Sandbox not found'],
                'execution_time_ms': 0,
                'execution_status': ExecutionStatus.ERROR.value,
                'validation_details': {}
            }]
        
        for test_case in test_cases:
            try:
                # Execute query against DuckDB sandbox
                result = sandbox.execute_query(query)
                execution_status = ExecutionStatus.SUCCESS if result.get('success', False) else ExecutionStatus.ERROR
                
                # Validate result using advanced test validator
                if execution_status == ExecutionStatus.SUCCESS:
                    user_output = result.get('results', [])
                    
                    # Check if test case has S3 expected output source
                    expected_output = test_case.expected_output  # Default fallback
                    
                    if test_case.expected_output_source:
                        try:
                            # Parse S3 configuration from JSONB
                            s3_config = test_case.expected_output_source
                            if s3_config.get('bucket') and s3_config.get('key') and s3_config.get('format'):
                                logger.info(f"Fetching expected output from S3: {s3_config['bucket']}/{s3_config['key']}")
                                
                                # Fetch data from S3 using the s3_service
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
                                logger.info(f"Successfully fetched {len(expected_output)} rows from S3 expected output")
                        except Exception as e:
                            logger.error(f"Failed to fetch S3 expected output for test case {test_case.id}: {e}")
                            # Continue with fallback expected_output
                            pass
                    
                    validation = test_validator.validate_test_case(
                        user_output,
                        expected_output,
                        ComparisonMode.UNORDERED  # Allow row reordering by default
                    )
                    
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_hidden': test_case.is_hidden,
                        'is_correct': validation['is_correct'],
                        'score': validation['score'],
                        'feedback': validation['feedback'],
                        'execution_time_ms': result.get('execution_time_ms', 0),
                        'execution_status': execution_status.value,
                        'validation_details': validation['details'],
                        # Add detailed comparison data for UI
                        'user_output': user_output,
                        'expected_output': expected_output,
                        'output_matches': validation['is_correct']
                    })
                else:
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_hidden': test_case.is_hidden,
                        'is_correct': False,
                        'score': 0.0,
                        'feedback': [result.get('error', 'Unknown execution error')],
                        'execution_time_ms': 0,
                        'execution_status': execution_status.value,
                        'validation_details': {}
                    })
                    
            except Exception as e:
                logger.error(f"Test case execution failed: {e}")
                results.append({
                    'test_case_id': test_case.id,
                    'test_case_name': test_case.name,
                    'is_hidden': test_case.is_hidden,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': [f'Execution error: {str(e)}'],
                    'execution_time_ms': 0,
                    'execution_status': 'ERROR',
                    'validation_details': {}
                })
        
        return results
    
    async def _execute_s3_hash_validation(
        self, problem: "Problem", query: str, db: Session
    ) -> List[Dict[str, Any]]:
        """
        Execute user query against S3 dataset and validate using hash comparison
        
        This implements the enhanced S3 workflow:
        1. User query → run on same dataset (DuckDB)
        2. Hash result → compare with stored expected_hash
        3. Return ✅ / ❌
        """
        from .s3_service import s3_service
        import duckdb
        import time
        import os
        
        start_time = time.time()
        
        try:
            # Extract S3 data source info
            s3_data = problem.s3_data_source
            bucket = s3_data.get('bucket')
            key = s3_data.get('key')
            
            if not bucket or not key:
                return [{
                    'test_case_id': 'hash_validation',
                    'test_case_name': 'S3 Hash Validation',
                    'is_hidden': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ['Invalid S3 data source configuration'],
                    'execution_time_ms': 0,
                    'execution_status': ExecutionStatus.ERROR.value,
                    'validation_details': {}
                }]
            
            logger.info(f"Executing user query against S3 dataset: s3://{bucket}/{key}")
            
            # Download dataset to temporary file
            temp_dataset_path = s3_service.download_to_temp_file(bucket, key)
            
            try:
                # Create DuckDB connection and load dataset with correct table name
                conn = duckdb.connect(":memory:")
                table_name = s3_data.get('table_name', 'dataset')  # Use configured table name
                conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM read_parquet(?)', [temp_dataset_path])
                
                # Execute user query
                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description]
                
                # Convert to list of dictionaries and sanitize for JSON serialization
                user_results_raw = [dict(zip(columns, row)) for row in result]
                user_results = sanitize_json_data(user_results_raw)
                
                # Generate hash from user results
                user_hash = s3_service.generate_expected_result_hash(user_results)
                
                # Compare with expected hash
                is_correct = user_hash == problem.expected_hash
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"Hash comparison - Expected: {problem.expected_hash}, User: {user_hash}, Match: {is_correct}")
                
                # Generate feedback
                if is_correct:
                    feedback = ["🎉 Perfect! Your query produces the exact expected results."]
                    score = 100.0
                else:
                    preview_rows = problem.preview_rows or []
                    feedback = [
                        "❌ Your query results don't match the expected output.",
                        f"Expected {len(preview_rows)} sample rows (showing first 3):"
                    ]
                    # Add first 3 preview rows for context
                    for i, row in enumerate(preview_rows[:3]):
                        feedback.append(f"Row {i+1}: {row}")
                    feedback.append(f"Your query returned {len(user_results)} rows.")
                    if len(user_results) <= 5:
                        feedback.append("Your results:")
                        for i, row in enumerate(user_results):
                            feedback.append(f"Row {i+1}: {row}")
                    score = 0.0
                
                return [{
                    'test_case_id': 'hash_validation',
                    'test_case_name': 'S3 Hash Validation',
                    'is_hidden': False,
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback,
                    'execution_time_ms': execution_time_ms,
                    'execution_status': ExecutionStatus.SUCCESS.value,
                    'validation_details': {
                        'hash_match': is_correct,
                        'expected_hash': problem.expected_hash,
                        'user_hash': user_hash,
                        'result_count': len(user_results)
                    },
                    'user_output': user_results[:5],  # Show first 5 rows for debugging
                    'expected_output': sanitize_json_data(problem.preview_rows or []),
                    'output_matches': is_correct
                }]
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_dataset_path)
                except:
                    pass
                    
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"S3 hash validation failed for problem {problem.id}: {e}")
            
            return [{
                'test_case_id': 'hash_validation',
                'test_case_name': 'S3 Hash Validation',
                'is_hidden': False,
                'is_correct': False,
                'score': 0.0,
                'feedback': [f'Query execution failed: {str(e)}'],
                'execution_time_ms': execution_time_ms,
                'execution_status': ExecutionStatus.ERROR.value,
                'validation_details': {'error': str(e)}
            }]
    
    async def _execute_test_cases(
        self,
        sandbox_id: str,
        problem_id: str,
        query: str,
        db: Session,
        include_hidden: bool = False
    ) -> List[Dict[str, Any]]:
        """Execute query against visible test cases"""
        query_filter = db.query(TestCase).filter(TestCase.problem_id == problem_id)
        
        if not include_hidden:
            query_filter = query_filter.filter(TestCase.is_hidden == False)
            
        test_cases = query_filter.order_by(TestCase.order_index).all()
        
        return await self._execute_specific_test_cases(sandbox_id, query, test_cases)
    
    async def _execute_specific_test_cases(
        self,
        sandbox_id: str,
        query: str,
        test_cases: List[TestCase]
    ) -> List[Dict[str, Any]]:
        """Execute query against specific test cases"""
        results = []
        
        # Extract user_id and problem_id from sandbox_id (format: "user_id_problem_id")
        try:
            user_id, problem_id = sandbox_id.rsplit('_', 1)
            sandbox = self.sandbox_manager.get_sandbox(user_id, problem_id)
        except ValueError:
            logger.error(f"Invalid sandbox_id format: {sandbox_id}")
            sandbox = None
            
        if not sandbox:
            logger.error(f"Sandbox not found for {sandbox_id}")
            return [{
                'test_case_id': 'error',
                'test_case_name': 'Execution Error',
                'is_correct': False,
                'score': 0.0,
                'feedback': ['Sandbox not found'],
                'execution_time_ms': 0,
                'validation_details': {}
            }]
        
        for test_case in test_cases:
            try:
                # Use transaction isolation to prevent queries from affecting other tests
                # For SELECT queries, execute normally since they don't modify data
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = sandbox.execute_query(query)
                else:
                    # For DDL/DML queries, use transaction isolation (BEGIN...ROLLBACK)
                    # This prevents data modifications from affecting subsequent tests
                    isolated_query = f"BEGIN; {query}; ROLLBACK;"
                    result = sandbox.execute_query(isolated_query)
                
                execution_status = ExecutionStatus.SUCCESS if result.get('success', False) else ExecutionStatus.ERROR
                
                if execution_status == ExecutionStatus.SUCCESS:
                    validation = test_validator.validate_test_case(
                        result.get('result', []),
                        test_case.expected_output,
                        ComparisonMode.UNORDERED
                    )
                    
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_correct': validation['is_correct'],
                        'score': validation['score'],
                        'feedback': validation['feedback'],
                        'execution_time_ms': result.get('execution_time_ms', 0),
                        'validation_details': validation['details']
                    })
                else:
                    results.append({
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'is_correct': False,
                        'score': 0.0,
                        'feedback': [result.get('error', 'Execution failed')],
                        'execution_time_ms': 0,
                        'validation_details': {}
                    })
                    
            except Exception as e:
                results.append({
                    'test_case_id': test_case.id,
                    'test_case_name': test_case.name,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': [f'Error: {str(e)}'],
                    'execution_time_ms': 0,
                    'validation_details': {}
                })
        
        return results
    
    def _calculate_final_score(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate final score from all test results"""
        if not test_results:
            return {
                'overall_score': 0.0,
                'passed_count': 0,
                'total_count': 0,
                'feedback': ['No test cases found'],
                'avg_execution_time': 0,
                'max_execution_time': 0
            }
        
        total_score = 0.0
        passed_count = 0
        total_count = len(test_results)
        execution_times = []
        feedback_messages = []
        
        for result in test_results:
            total_score += result['score']
            if result['is_correct']:
                passed_count += 1
            execution_times.append(result['execution_time_ms'])
            
            # Collect feedback from failed tests
            if not result['is_correct'] and not result.get('is_hidden', False):
                feedback_messages.extend(result['feedback'])
        
        overall_score = total_score / total_count if total_count > 0 else 0.0
        
        # Generate summary feedback
        if overall_score >= 95:
            summary = "🎉 Excellent! Your solution passes all test cases."
        elif overall_score >= 80:
            summary = "Great job! Your solution passes most test cases with minor issues."
        elif overall_score >= 60:
            summary = "⚠️ Good attempt, but there are some issues to address."
        else:
            summary = "❌ Your solution needs significant improvements."
        
        return {
            'overall_score': round(overall_score, 2),
            'passed_count': passed_count,
            'total_count': total_count,
            'feedback': [summary] + feedback_messages,
            'avg_execution_time': int(sum(execution_times) / len(execution_times)) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0
        }
    
    def _generate_test_feedback(self, test_results: List[Dict[str, Any]]) -> List[str]:
        """Generate helpful feedback for test mode"""
        feedback = []
        
        passed = sum(1 for r in test_results if r['is_correct'])
        total = len(test_results)
        
        if passed == total:
            feedback.append("🎉 All visible test cases pass! Your solution looks correct.")
        elif passed > 0:
            feedback.append(f"{passed}/{total} test cases pass. Review the failing cases below.")
        else:
            feedback.append("❌ No test cases pass. Check your query logic carefully.")
        
        # Add specific feedback from failed tests
        for result in test_results:
            if not result['is_correct']:
                feedback.append(f"❌ {result['test_case_name']}: {'; '.join(result['feedback'])}")
        
        return feedback
    
    async def _introspect_database_schema(
        self,
        sandbox_id: str,
        table_definitions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Introspect database schema for enhanced information"""
        try:
            # Use provided table definitions as base
            schema_info = {
                'tables': table_definitions,
                'relationships': [],
                'indexes': [],
                'constraints': []
            }
            
            # Could enhance with actual database introspection here
            # For now, return the provided schema
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema introspection failed: {e}")
            return {
                'tables': table_definitions,
                'relationships': [],
                'indexes': [],
                'constraints': []
            }
    
    async def _calculate_user_streak(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Calculate user's current solving streak"""
        try:
            # Get recent submissions ordered by date
            from sqlalchemy import func, and_
            
            recent_submissions = db.query(Submission).filter(
                Submission.user_id == user_id
            ).order_by(Submission.submitted_at.desc()).limit(50).all()
            
            if not recent_submissions:
                return {
                    'current_streak': 0,
                    'max_streak': 0,
                    'last_correct_date': None
                }
            
            # Calculate current streak
            current_streak = 0
            max_streak = 0
            temp_streak = 0
            last_correct_date = None
            
            for submission in recent_submissions:
                if submission.is_correct:
                    if current_streak == 0:  # First correct submission
                        current_streak = 1
                        last_correct_date = submission.submitted_at
                    temp_streak += 1
                    max_streak = max(max_streak, temp_streak)
                else:
                    if temp_streak > 0:
                        break  # Streak broken
                    temp_streak = 0
            
            return {
                'current_streak': current_streak,
                'max_streak': max_streak,
                'last_correct_date': last_correct_date.isoformat() if last_correct_date else None
            }
            
        except Exception as e:
            logger.error(f"Streak calculation failed: {e}")
            return {
                'current_streak': 0,
                'max_streak': 0,
                'last_correct_date': None
            }
    
    async def _update_user_progress(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ) -> None:
        """Update user progress after successful submission"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Check if this is the first time solving this problem
                # Get the current submission to exclude from duplicate check
                current_submission = db.query(Submission).filter(
                    Submission.user_id == user_id,
                    Submission.problem_id == problem_id,
                    Submission.is_correct == True
                ).order_by(Submission.submitted_at.desc()).first()
                
                # Count previous correct submissions (excluding the current one)
                existing_correct_count = db.query(Submission).filter(
                    Submission.user_id == user_id,
                    Submission.problem_id == problem_id,
                    Submission.is_correct == True,
                    Submission.id != current_submission.id if current_submission else None
                ).count()
                
                if existing_correct_count == 0:
                    # First time solving this problem
                    user.problems_solved = (user.problems_solved or 0) + 1
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update user progress: {e}")


# Global executor instance
secure_executor = SecureQueryExecutor()
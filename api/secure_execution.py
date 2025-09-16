"""
Secure Query Execution System
============================
Integrates SQL validation, sandbox execution, and test case validation
for the SQLGym learning platform.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from contextlib import asynccontextmanager

from .query_validator import query_validator, QueryValidationError, QueryRisk
from .test_validator import test_validator, ComparisonMode
from .sandbox_manager import sandbox_manager, execute_sandbox_query
from .models import (
    User, Problem, TestCase, UserSandbox, Submission, 
    ExecutionResult, ExecutionStatus, SandboxStatus
)
from .schemas import (
    ExecutionResultCreate, 
    DetailedSubmissionResponse,
    TestCaseResponse
)

logger = logging.getLogger(__name__)

class SecureQueryExecutor:
    """Secure SQL query executor with comprehensive validation"""
    
    def __init__(self):
        self.max_execution_time = 30  # seconds
        self.max_memory_mb = 256
        self.max_result_rows = 10000
    
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
            # Step 1: Validate query security
            validation_result = query_validator.validate_query(query)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': validation_result['errors'],
                    'security_violations': validation_result['blocked_operations'],
                    'submission_id': None
                }
            
            # Step 2: Get or create sandbox
            sandbox = await self._get_or_create_sandbox(user_id, problem_id, db)
            
            if not sandbox:
                return {
                    'success': False,
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ['Failed to create execution sandbox'],
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
            # Step 1: Quick validation
            validation_result = query_validator.validate_query(query)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'feedback': validation_result['errors'],
                    'security_violations': validation_result['blocked_operations'],
                    'test_results': []
                }
            
            # Step 2: Get or create sandbox
            sandbox = await self._get_or_create_sandbox(user_id, problem_id, db)
            
            if not sandbox:
                return {
                    'success': False,
                    'feedback': ['Failed to create test sandbox'],
                    'test_results': []
                }
            
            # Step 3: Execute the query to get actual results
            query_result, execution_status = await execute_sandbox_query(
                sandbox.id, query, 30
            )
            
            # Step 4: Execute against visible test cases only (unless admin)
            test_results = await self._execute_test_cases(
                sandbox.id, problem_id, query, db, include_hidden_tests
            )
            
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
    
    async def _get_or_create_sandbox(
        self,
        user_id: str,
        problem_id: str,
        db: Session
    ) -> Optional[UserSandbox]:
        """Get existing active sandbox or create new one"""
        try:
            # Check for existing active sandbox
            existing_sandbox = db.query(UserSandbox).filter(
                UserSandbox.user_id == user_id,
                UserSandbox.problem_id == problem_id,
                UserSandbox.status == SandboxStatus.ACTIVE.value,
                UserSandbox.expires_at > datetime.utcnow()
            ).first()
            
            if existing_sandbox:
                # Update last accessed
                existing_sandbox.last_accessed_at = datetime.utcnow()
                db.commit()
                return existing_sandbox
            
            # Create new sandbox
            from .sandbox_manager import create_user_sandbox
            sandbox = await create_user_sandbox(user_id, problem_id)
            return sandbox
            
        except Exception as e:
            logger.error(f"Failed to get/create sandbox: {e}")
            return None
    
    async def _execute_all_test_cases(
        self,
        sandbox_id: str,
        problem_id: str,
        query: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Execute query against all test cases"""
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == problem_id
        ).order_by(TestCase.order_index).all()
        
        results = []
        
        for test_case in test_cases:
            try:
                # Execute query
                result, execution_status = await execute_sandbox_query(
                    sandbox_id,
                    query,
                    test_case.timeout_seconds
                )
                
                # Validate result using advanced test validator
                if execution_status == ExecutionStatus.SUCCESS:
                    user_output = result.get('result', [])
                    expected_output = test_case.expected_output
                    
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
        
        for test_case in test_cases:
            try:
                result, execution_status = await execute_sandbox_query(
                    sandbox_id,
                    query,
                    test_case.timeout_seconds
                )
                
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
                existing_correct = db.query(Submission).filter(
                    Submission.user_id == user_id,
                    Submission.problem_id == problem_id,
                    Submission.is_correct == True
                ).first()
                
                if not existing_correct:
                    # First time solving this problem
                    user.problems_solved = (user.problems_solved or 0) + 1
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update user progress: {e}")


# Global executor instance
secure_executor = SecureQueryExecutor()
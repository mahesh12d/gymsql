"""
Optimized SQL Test Case Validator
================================
High-performance validator with smart feedback and minimal overhead.
Focuses on essential improvements while maintaining speed.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from datetime import datetime, date
from decimal import Decimal
import re
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


class ComparisonMode(Enum):
    """Different modes for comparing query results"""
    EXACT = "exact"
    UNORDERED = "unordered"
    SUBSET = "subset"
    FUZZY = "fuzzy"


class ErrorCategory(Enum):
    """Categories of common SQL errors for targeted feedback"""
    SYNTAX = "syntax"
    LOGIC = "logic"
    JOIN = "join"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"


@dataclass
class FeedbackContext:
    """Lightweight context for personalized feedback"""
    user_level: str = "intermediate"  # beginner, intermediate, advanced
    previous_attempts: int = 0


class OptimizedTestCaseValidator:
    """Performance-optimized validator with essential smart features"""

    def __init__(self):
        self.numeric_tolerance = 0.001

        # Cached patterns for performance
        self._error_keywords = {
            'join_issues': ['cartesian', 'missing', 'duplicate'],
            'aggregation_issues': ['sum', 'count', 'avg', 'group'],
            'filter_issues': ['where', 'condition', 'missing']
        }

        # Pre-compiled regex patterns
        self._sql_patterns = {
            'select_star': re.compile(r'select\s+\*', re.IGNORECASE),
            'missing_semicolon': re.compile(r'[^;]\s*$'),
            'cartesian_join': re.compile(r'from\s+\w+\s*,\s*\w+',
                                         re.IGNORECASE)
        }

    def validate_test_case(
            self,
            actual_result: List[Dict[str, Any]],
            expected_result: List[Dict[str, Any]],
            student_query: Optional[str] = None,
            comparison_mode: ComparisonMode = ComparisonMode.EXACT,
            context: Optional[FeedbackContext] = None) -> Dict[str, Any]:
        """
        Optimized validation with smart feedback

        Performance optimizations:
        - Lazy evaluation of expensive operations
        - Early returns for obvious cases
        - Minimal object creation
        - Cached computations
        """
        if context is None:
            context = FeedbackContext()

        result = self._create_base_result()

        try:
            # Fast path for empty results
            if not expected_result and not actual_result:
                result.update({
                    'is_correct': True,
                    'score': 100.0,
                    'feedback': ["Perfect! Both results are empty."]
                })
                return result

            # Fast path for obvious mismatches
            if not expected_result or not actual_result:
                return self._handle_missing_results(result,
                                                    bool(expected_result),
                                                    context)

            # Quick structure validation (most performance critical)
            structure_score = self._validate_structure_fast(
                actual_result, expected_result, result)

            # Only do expensive content validation if structure looks reasonable
            if structure_score > 30:  # Skip expensive validation for obviously wrong queries
                content_score = self._validate_content_fast(
                    actual_result, expected_result, comparison_mode, result)
            else:
                content_score = 0.0

            # Quick scoring calculation
            final_score = self._calculate_final_score(structure_score,
                                                      content_score, context)
            result['score'] = round(final_score, 2)
            result['is_correct'] = final_score >= 100.0

            # Lazy smart feedback generation (only if needed)
            if student_query and final_score < 100:
                self._add_quick_query_feedback(student_query, result, context)

            self._add_contextual_feedback(result, context)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result['errors'].append(f"Validation error: {str(e)}")

        return result

    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure quickly"""
        return {
            'is_correct': False,
            'score': 0.0,
            'max_score': 100.0,
            'feedback': [],
            'errors': [],
            'warnings': [],
            'details': {
                'row_count_match': False,
                'column_count_match': False,
                'column_names_match': False,
                'data_matches': False
            }
        }

    def _handle_missing_results(self, result: Dict[str,
                                                   Any], has_expected: bool,
                                context: FeedbackContext) -> Dict[str, Any]:
        """Fast handling of missing results"""
        if not has_expected:
            result['errors'].append("No expected result provided")
        else:
            result['errors'].append("Query returned no results")
            if context.user_level == "beginner":
                result['feedback'].append(
                    "💡 Your query didn't return any data. Check your FROM and WHERE clauses."
                )
            else:
                result['feedback'].append(
                    "Query returned empty result set. Verify your conditions.")
        return result

    def _validate_structure_fast(self, actual: List[Dict[str, Any]],
                                 expected: List[Dict[str, Any]],
                                 result: Dict[str, Any]) -> float:
        """Optimized structure validation with early exits"""
        score = 0.0

        # Row count (fastest check)
        actual_rows, expected_rows = len(actual), len(expected)
        if actual_rows == expected_rows:
            result['details']['row_count_match'] = True
            score += 40.0
        else:
            # Quick ratio calculation for partial credit
            ratio = min(actual_rows, expected_rows) / max(
                actual_rows, expected_rows) if max(actual_rows,
                                                   expected_rows) > 0 else 0
            score += 40.0 * ratio

            # Fast feedback generation
            diff = actual_rows - expected_rows
            if diff > 0:
                result['feedback'].append(
                    f"Too many rows: got {actual_rows}, expected {expected_rows}"
                )
            else:
                result['feedback'].append(
                    f"Too few rows: got {actual_rows}, expected {expected_rows}"
                )

        # Column structure (only if we have data)
        if actual and expected:
            actual_cols = set(actual[0].keys())
            expected_cols = set(expected[0].keys())

            # Column count
            if len(actual_cols) == len(expected_cols):
                result['details']['column_count_match'] = True
                score += 30.0
            else:
                ratio = min(len(actual_cols), len(expected_cols)) / max(
                    len(actual_cols), len(expected_cols))
                score += 30.0 * ratio

            # Column names (using set operations for speed)
            if actual_cols == expected_cols:
                result['details']['column_names_match'] = True
                score += 30.0
            else:
                # Fast similarity calculation
                intersection = len(actual_cols & expected_cols)
                union = len(actual_cols | expected_cols)
                similarity = intersection / union if union > 0 else 0
                score += 30.0 * similarity

                # Quick feedback
                missing = expected_cols - actual_cols
                extra = actual_cols - expected_cols
                if missing:
                    result['feedback'].append(
                        f"Missing columns: {', '.join(list(missing)[:3])}{'...' if len(missing) > 3 else ''}"
                    )
                if extra:
                    result['feedback'].append(
                        f"Extra columns: {', '.join(list(extra)[:3])}{'...' if len(extra) > 3 else ''}"
                    )

        return min(score, 100.0)

    def _validate_content_fast(self, actual: List[Dict[str, Any]],
                               expected: List[Dict[str, Any]],
                               comparison_mode: ComparisonMode,
                               result: Dict[str, Any]) -> float:
        """Optimized content validation"""

        if len(actual) != len(expected):
            return 0.0

        # Fast path for small datasets
        if len(expected) <= 10:
            return self._validate_small_dataset(actual, expected,
                                                comparison_mode, result)

        # Optimized validation for larger datasets
        if comparison_mode == ComparisonMode.UNORDERED:
            return self._validate_unordered_fast(actual, expected, result)
        else:
            return self._validate_ordered_fast(actual, expected, result)

    def _validate_small_dataset(self, actual: List[Dict[str, Any]],
                                expected: List[Dict[str, Any]],
                                comparison_mode: ComparisonMode,
                                result: Dict[str, Any]) -> float:
        """Optimized validation for small datasets (≤10 rows)"""

        if comparison_mode == ComparisonMode.UNORDERED:
            # Convert to tuples for set operations (faster than custom comparison)
            actual_tuples = {tuple(sorted(row.items())) for row in actual}
            expected_tuples = {tuple(sorted(row.items())) for row in expected}

            matches = len(actual_tuples & expected_tuples)
            match_ratio = matches / len(
                expected_tuples) if expected_tuples else 0.0
        else:
            # Exact order comparison
            matches = sum(1 for a, e in zip(actual, expected)
                          if self._rows_equal_fast(a, e))
            match_ratio = matches / len(expected) if expected else 0.0

        result['details']['data_matches'] = match_ratio > 0.95

        # Quick feedback for small datasets
        if match_ratio < 1.0:
            mismatches = len(expected) - matches
            result['feedback'].append(
                f"{mismatches} row(s) don't match expected values")

        return match_ratio * 100.0

    def _validate_unordered_fast(self, actual: List[Dict[str, Any]],
                                 expected: List[Dict[str, Any]],
                                 result: Dict[str, Any]) -> float:
        """Fast unordered comparison using hash-based matching"""

        # Create hash signatures for faster comparison
        actual_hashes = [self._row_hash(row) for row in actual]
        expected_hashes = [self._row_hash(row) for row in expected]

        # Count matches using hash comparison
        actual_hash_count = defaultdict(int)
        for h in actual_hashes:
            actual_hash_count[h] += 1

        matches = 0
        for expected_hash in expected_hashes:
            if actual_hash_count[expected_hash] > 0:
                matches += 1
                actual_hash_count[expected_hash] -= 1

        match_ratio = matches / len(expected) if expected else 0.0
        result['details']['data_matches'] = match_ratio > 0.95

        return match_ratio * 100.0

    def _validate_ordered_fast(self, actual: List[Dict[str, Any]],
                               expected: List[Dict[str, Any]],
                               result: Dict[str, Any]) -> float:
        """Fast ordered comparison with early termination"""

        matches = 0
        max_checks = min(len(actual), len(expected),
                         100)  # Limit checks for very large datasets

        for i in range(max_checks):
            if self._rows_equal_fast(actual[i], expected[i]):
                matches += 1
            elif matches == 0 and i > 5:  # Early termination if no matches found
                break

        # Extrapolate for larger datasets
        if len(expected) > max_checks:
            match_ratio = matches / max_checks if max_checks > 0 else 0.0
        else:
            match_ratio = matches / len(expected) if expected else 0.0

        result['details']['data_matches'] = match_ratio > 0.95

        return match_ratio * 100.0

    def _rows_equal_fast(self, row1: Dict[str, Any], row2: Dict[str,
                                                                Any]) -> bool:
        """Fast row comparison with early exits"""

        # Quick key count check
        if len(row1) != len(row2):
            return False

        # Fast value comparison with early exit
        for key in row2:
            if key not in row1:
                return False

            val1, val2 = row1[key], row2[key]

            # Fast None check
            if val1 is None and val2 is None:
                continue
            if val1 is None or val2 is None:
                return False

            # Fast type-specific comparison
            if type(val1) != type(val2):
                # Try string conversion as fallback
                if str(val1).strip() != str(val2).strip():
                    return False
            elif val1 != val2:
                return False

        return True

    def _row_hash(self, row: Dict[str, Any]) -> int:
        """Create a fast hash for row comparison"""
        # Simple hash based on sorted items (faster than deep comparison)
        return hash(
            tuple(
                sorted((k, str(v) if v is not None else None)
                       for k, v in row.items())))

    def _calculate_final_score(self, structure_score: float,
                               content_score: float,
                               context: FeedbackContext) -> float:
        """Fast score calculation"""
        # Simple weighted average (avoid complex calculations)
        if context.user_level == "beginner":
            return structure_score * 0.4 + content_score * 0.6
        else:
            return structure_score * 0.3 + content_score * 0.7

    def _add_quick_query_feedback(self, query: str, result: Dict[str, Any],
                                  context: FeedbackContext):
        """Add quick query-based feedback using pre-compiled patterns"""

        query_lower = query.lower()

        # Fast pattern matching with pre-compiled regex
        if self._sql_patterns['select_star'].search(query):
            if context.user_level != "beginner":
                result['warnings'].append(
                    "Consider selecting specific columns instead of SELECT *")

        if self._sql_patterns['missing_semicolon'].search(query.strip()):
            if context.user_level == "beginner":
                result['warnings'].append(
                    "SQL queries should end with a semicolon (;)")

        if self._sql_patterns['cartesian_join'].search(query):
            result['warnings'].append(
                "Possible Cartesian product - check your JOIN conditions")

        # Fast keyword-based detection
        if 'join' in query_lower and result['score'] < 50:
            result['feedback'].append(
                "💡 JOIN issue detected. Check your ON conditions.")
        elif 'group by' in query_lower and result['score'] < 50:
            result['feedback'].append(
                "💡 GROUP BY issue detected. Verify your grouping columns.")

    def _add_contextual_feedback(self, result: Dict[str, Any],
                                 context: FeedbackContext):
        """Add context-aware feedback quickly"""
        score = result['score']

        # Fast feedback generation based on score bands
        if score >= 100:
            messages = ["🎉 Perfect!", "Excellent work!", "Spot on!"]
        elif score >= 80:
            messages = ["Good job!", "Almost perfect!", "Great work!"]
        elif score >= 60:
            messages = [
                "You're on the right track", "Getting closer!", "Good attempt"
            ]
        else:
            messages = [
                "Needs work", "Review the requirements",
                "Try a different approach"
            ]

        # Add level-specific encouragement
        base_message = messages[min(len(messages) - 1, int(score // 20))]

        if context.user_level == "beginner" and score < 60:
            base_message += " - break down the problem step by step."
        elif context.previous_attempts > 2 and score > 60:
            base_message += " - you're improving with each attempt!"

        if not result['feedback'] or score >= 100:
            result['feedback'].insert(0, base_message)

    # Keep essential methods from original for compatibility
    def _rows_match(self, actual_row: Dict[str, Any],
                    expected_row: Dict[str, Any]) -> bool:
        """Compatibility method"""
        return self._rows_equal_fast(actual_row, expected_row)

    def _get_row_differences(self, actual_row: Dict[str, Any],
                             expected_row: Dict[str, Any]) -> str:
        """Quick difference detection"""
        differences = []
        for key in expected_row:
            if key not in actual_row or actual_row[key] != expected_row[key]:
                actual_val = actual_row.get(key, '<missing>')
                expected_val = expected_row[key]
                differences.append(
                    f"{key}: got '{actual_val}', expected '{expected_val}'")
                if len(differences) >= 3:  # Limit output for performance
                    differences.append("...")
                    break
        return "; ".join(differences)

    def compare_schemas(self, actual_schema: List[Dict],
                        expected_schema: List[Dict]) -> Dict[str, Any]:
        """Fast schema comparison"""
        actual_names = {table['name'] for table in actual_schema}
        expected_names = {table['name'] for table in expected_schema}

        missing = expected_names - actual_names
        extra = actual_names - expected_names

        matches = len(expected_names
                      & actual_names) == len(expected_names) and not extra
        score = 100.0 - (len(missing) * 20) - (len(extra) * 10)

        differences = []
        if missing:
            differences.append(f"Missing tables: {', '.join(missing)}")
        if extra:
            differences.append(f"Extra tables: {', '.join(extra)}")

        return {
            'matches': matches,
            'differences': differences,
            'score': max(0.0, score)
        }


# Performance-optimized global instance
optimized_test_validator = OptimizedTestCaseValidator()

# Compatibility alias for existing code
test_validator = optimized_test_validator

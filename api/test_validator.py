"""
Advanced Test Case Validation System
===================================
Provides intelligent comparison of SQL query results against expected outputs,
handling different data types, null values, and ordering scenarios.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, date
from decimal import Decimal
import re
from enum import Enum

logger = logging.getLogger(__name__)

class ComparisonMode(Enum):
    """Different modes for comparing query results"""
    EXACT = "exact"  # Exact match including order
    UNORDERED = "unordered"  # Content match, ignore order
    SUBSET = "subset"  # Expected is subset of actual
    FUZZY = "fuzzy"  # Approximate match for numeric values

class TestCaseValidator:
    """Advanced validator for comparing SQL query results"""
    
    def __init__(self):
        self.numeric_tolerance = 0.001  # For floating point comparisons
        self.date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f'
        ]
    
    def validate_test_case(
        self,
        actual_result: List[Dict[str, Any]],
        expected_result: List[Dict[str, Any]], 
        comparison_mode: ComparisonMode = ComparisonMode.EXACT,
        scoring_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Validate query results against expected test case
        
        Args:
            actual_result: Query result from student
            expected_result: Expected result from test case
            comparison_mode: How to compare the results
            scoring_weights: Weights for different comparison aspects
            
        Returns:
            Validation result with score and feedback
        """
        result = {
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
                'data_matches': False,
                'type_matches': False
            }
        }
        
        try:
            # Handle empty results
            if not expected_result and not actual_result:
                result['is_correct'] = True
                result['score'] = 100.0
                result['feedback'].append("Both results are empty - correct!")
                return result
            
            if not expected_result:
                result['errors'].append("No expected result provided")
                return result
                
            if not actual_result:
                result['errors'].append("Query returned no results")
                result['feedback'].append("Your query didn't return any rows. Check your WHERE conditions.")
                return result
            
            # Validate structure
            structure_score = self._validate_structure(actual_result, expected_result, result)
            
            # Validate data content
            content_score = self._validate_content(
                actual_result, expected_result, comparison_mode, result
            )
            
            # Calculate final score
            weights = scoring_weights or {'structure': 0.3, 'content': 0.7}
            final_score = (structure_score * weights.get('structure', 0.3) + 
                          content_score * weights.get('content', 0.7))
            
            result['score'] = round(final_score, 2)
            result['is_correct'] = final_score >= 95.0  # 95% threshold for "correct"
            
            # Add summary feedback
            self._add_summary_feedback(result)
            
        except Exception as e:
            logger.error(f"Test validation failed: {e}")
            result['errors'].append(f"Validation error: {str(e)}")
            
        return result
    
    def _validate_structure(
        self, 
        actual: List[Dict[str, Any]], 
        expected: List[Dict[str, Any]], 
        result: Dict[str, Any]
    ) -> float:
        """Validate structural aspects of the result"""
        score = 0.0
        max_points = 100.0
        
        # Check row count
        if len(actual) == len(expected):
            result['details']['row_count_match'] = True
            score += 30.0
        else:
            result['feedback'].append(
                f"Row count mismatch: expected {len(expected)}, got {len(actual)}"
            )
        
        # Check column structure
        if actual and expected:
            actual_cols = set(actual[0].keys())
            expected_cols = set(expected[0].keys())
            
            # Column count
            if len(actual_cols) == len(expected_cols):
                result['details']['column_count_match'] = True
                score += 20.0
            else:
                result['feedback'].append(
                    f"Column count mismatch: expected {len(expected_cols)}, got {len(actual_cols)}"
                )
            
            # Column names
            if actual_cols == expected_cols:
                result['details']['column_names_match'] = True
                score += 30.0
            else:
                missing = expected_cols - actual_cols
                extra = actual_cols - expected_cols
                
                if missing:
                    result['feedback'].append(f"Missing columns: {', '.join(missing)}")
                if extra:
                    result['feedback'].append(f"Extra columns: {', '.join(extra)}")
        
        # Column types validation
        type_score = self._validate_column_types(actual, expected, result)
        score += type_score * 0.2  # 20% weight for types
        
        return min(score, max_points)
    
    def _validate_column_types(
        self, 
        actual: List[Dict[str, Any]], 
        expected: List[Dict[str, Any]], 
        result: Dict[str, Any]
    ) -> float:
        """Validate column data types"""
        if not actual or not expected:
            return 0.0
            
        score = 0.0
        total_columns = len(expected[0].keys())
        
        for col_name in expected[0].keys():
            if col_name in actual[0]:
                expected_type = type(expected[0][col_name])
                actual_type = type(actual[0][col_name])
                
                if self._types_compatible(expected_type, actual_type):
                    score += 1.0
                else:
                    result['warnings'].append(
                        f"Type mismatch in column '{col_name}': expected {expected_type.__name__}, got {actual_type.__name__}"
                    )
        
        if total_columns > 0:
            type_match_ratio = score / total_columns
            result['details']['type_matches'] = type_match_ratio > 0.8
            return type_match_ratio * 100.0
        
        return 0.0
    
    def _types_compatible(self, expected_type: type, actual_type: type) -> bool:
        """Check if two types are compatible for comparison"""
        # Handle None/null values
        if expected_type is type(None) or actual_type is type(None):
            return True
            
        # Numeric compatibility
        numeric_types = (int, float, Decimal)
        if issubclass(expected_type, numeric_types) and issubclass(actual_type, numeric_types):
            return True
            
        # String compatibility
        string_types = (str, )
        if issubclass(expected_type, string_types) and issubclass(actual_type, string_types):
            return True
            
        # Date/datetime compatibility
        date_types = (date, datetime)
        if issubclass(expected_type, date_types) and issubclass(actual_type, date_types):
            return True
            
        # Exact type match
        return expected_type == actual_type
    
    def _validate_content(
        self,
        actual: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
        comparison_mode: ComparisonMode,
        result: Dict[str, Any]
    ) -> float:
        """Validate the actual data content"""
        if comparison_mode == ComparisonMode.EXACT:
            return self._validate_exact_match(actual, expected, result)
        elif comparison_mode == ComparisonMode.UNORDERED:
            return self._validate_unordered_match(actual, expected, result)
        elif comparison_mode == ComparisonMode.SUBSET:
            return self._validate_subset_match(actual, expected, result)
        elif comparison_mode == ComparisonMode.FUZZY:
            return self._validate_fuzzy_match(actual, expected, result)
        else:
            return self._validate_exact_match(actual, expected, result)
    
    def _validate_exact_match(
        self,
        actual: List[Dict[str, Any]], 
        expected: List[Dict[str, Any]], 
        result: Dict[str, Any]
    ) -> float:
        """Validate exact match including order"""
        if len(actual) != len(expected):
            return 0.0
            
        matching_rows = 0
        total_rows = len(expected)
        
        for i, (actual_row, expected_row) in enumerate(zip(actual, expected)):
            if self._rows_match(actual_row, expected_row):
                matching_rows += 1
            else:
                row_diff = self._get_row_differences(actual_row, expected_row)
                result['feedback'].append(f"Row {i+1} mismatch: {row_diff}")
        
        match_ratio = matching_rows / total_rows if total_rows > 0 else 0.0
        result['details']['data_matches'] = match_ratio > 0.95
        
        return match_ratio * 100.0
    
    def _validate_unordered_match(
        self,
        actual: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> float:
        """Validate content match ignoring order"""
        if len(actual) != len(expected):
            return 0.0
        
        # Convert to sets of tuples for comparison
        actual_set = {self._row_to_tuple(row) for row in actual}
        expected_set = {self._row_to_tuple(row) for row in expected}
        
        intersection = actual_set & expected_set
        match_ratio = len(intersection) / len(expected_set) if expected_set else 0.0
        
        result['details']['data_matches'] = match_ratio > 0.95
        
        if match_ratio < 1.0:
            missing = expected_set - actual_set
            extra = actual_set - expected_set
            
            if missing:
                result['feedback'].append(f"Missing {len(missing)} expected rows")
            if extra:
                result['feedback'].append(f"Found {len(extra)} unexpected rows")
        
        return match_ratio * 100.0
    
    def _validate_subset_match(
        self,
        actual: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> float:
        """Validate that expected is a subset of actual"""
        actual_set = {self._row_to_tuple(row) for row in actual}
        expected_set = {self._row_to_tuple(row) for row in expected}
        
        intersection = actual_set & expected_set
        match_ratio = len(intersection) / len(expected_set) if expected_set else 1.0
        
        result['details']['data_matches'] = match_ratio > 0.95
        
        if match_ratio < 1.0:
            missing = expected_set - actual_set
            result['feedback'].append(f"Missing {len(missing)} required rows from expected result")
        
        return match_ratio * 100.0
    
    def _validate_fuzzy_match(
        self,
        actual: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> float:
        """Validate with fuzzy matching for numeric values"""
        if len(actual) != len(expected):
            return 0.0
        
        matching_rows = 0
        for actual_row, expected_row in zip(actual, expected):
            if self._rows_fuzzy_match(actual_row, expected_row):
                matching_rows += 1
        
        match_ratio = matching_rows / len(expected) if expected else 0.0
        result['details']['data_matches'] = match_ratio > 0.95
        
        return match_ratio * 100.0
    
    def _rows_match(self, actual_row: Dict[str, Any], expected_row: Dict[str, Any]) -> bool:
        """Check if two rows match exactly"""
        if set(actual_row.keys()) != set(expected_row.keys()):
            return False
        
        for key in expected_row.keys():
            if not self._values_match(actual_row.get(key), expected_row[key]):
                return False
        
        return True
    
    def _rows_fuzzy_match(self, actual_row: Dict[str, Any], expected_row: Dict[str, Any]) -> bool:
        """Check if two rows match with fuzzy numeric comparison"""
        if set(actual_row.keys()) != set(expected_row.keys()):
            return False
        
        for key in expected_row.keys():
            if not self._values_fuzzy_match(actual_row.get(key), expected_row[key]):
                return False
        
        return True
    
    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match"""
        # Handle None values
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False
        
        # Convert both to strings and compare (handles type mismatches)
        return str(actual).strip() == str(expected).strip()
    
    def _values_fuzzy_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match with fuzzy comparison"""
        # Exact match first
        if self._values_match(actual, expected):
            return True
        
        # Numeric fuzzy matching
        try:
            actual_num = float(actual)
            expected_num = float(expected)
            return abs(actual_num - expected_num) <= self.numeric_tolerance
        except (ValueError, TypeError):
            pass
        
        # String fuzzy matching (case insensitive, whitespace normalized)
        try:
            actual_str = str(actual).strip().lower()
            expected_str = str(expected).strip().lower()
            return actual_str == expected_str
        except:
            return False
    
    def _row_to_tuple(self, row: Dict[str, Any]) -> tuple:
        """Convert row to tuple for set operations"""
        return tuple(sorted(row.items()))
    
    def _get_row_differences(self, actual_row: Dict[str, Any], expected_row: Dict[str, Any]) -> str:
        """Get human-readable differences between two rows"""
        differences = []
        
        all_keys = set(actual_row.keys()) | set(expected_row.keys())
        
        for key in all_keys:
            actual_val = actual_row.get(key, '<missing>')
            expected_val = expected_row.get(key, '<missing>')
            
            if actual_val != expected_val:
                differences.append(f"{key}: got '{actual_val}', expected '{expected_val}'")
        
        return "; ".join(differences)
    
    def _add_summary_feedback(self, result: Dict[str, Any]):
        """Add summary feedback based on validation results"""
        score = result['score']
        
        if score >= 95:
            result['feedback'].insert(0, "🎉 Perfect! Your query matches the expected result exactly.")
        elif score >= 80:
            result['feedback'].insert(0, "Great job! Your query is mostly correct with minor issues.")
        elif score >= 60:
            result['feedback'].insert(0, "⚠️  Good attempt, but there are some significant differences.")
        elif score >= 40:
            result['feedback'].insert(0, "❌ Your query has several issues that need to be addressed.")
        else:
            result['feedback'].insert(0, "💡 Your query needs major corrections. Review the expected output carefully.")
    
    def compare_schemas(
        self, 
        actual_schema: List[Dict[str, Any]], 
        expected_schema: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare database schemas for structure validation"""
        result = {
            'matches': True,
            'differences': [],
            'score': 100.0
        }
        
        # Convert to comparable format
        actual_tables = {table['name']: table for table in actual_schema}
        expected_tables = {table['name']: table for table in expected_schema}
        
        # Check for missing/extra tables
        missing_tables = set(expected_tables.keys()) - set(actual_tables.keys())
        extra_tables = set(actual_tables.keys()) - set(expected_tables.keys())
        
        if missing_tables:
            result['differences'].append(f"Missing tables: {', '.join(missing_tables)}")
            result['matches'] = False
            result['score'] -= 20
        
        if extra_tables:
            result['differences'].append(f"Extra tables: {', '.join(extra_tables)}")
            result['score'] -= 10
        
        # Check table structures
        for table_name in expected_tables.keys():
            if table_name in actual_tables:
                table_diff = self._compare_table_structure(
                    actual_tables[table_name],
                    expected_tables[table_name]
                )
                if table_diff:
                    result['differences'].extend(table_diff)
                    result['matches'] = False
                    result['score'] -= 10
        
        result['score'] = max(0.0, result['score'])
        return result
    
    def _compare_table_structure(self, actual_table: Dict, expected_table: Dict) -> List[str]:
        """Compare structure of two tables"""
        differences = []
        table_name = expected_table['name']
        
        actual_columns = {col['name']: col for col in actual_table.get('columns', [])}
        expected_columns = {col['name']: col for col in expected_table.get('columns', [])}
        
        # Check for missing/extra columns
        missing_cols = set(expected_columns.keys()) - set(actual_columns.keys())
        extra_cols = set(actual_columns.keys()) - set(expected_columns.keys())
        
        if missing_cols:
            differences.append(f"Table {table_name}: Missing columns {', '.join(missing_cols)}")
        
        if extra_cols:
            differences.append(f"Table {table_name}: Extra columns {', '.join(extra_cols)}")
        
        # Check column types
        for col_name in expected_columns.keys():
            if col_name in actual_columns:
                expected_type = expected_columns[col_name].get('type', '')
                actual_type = actual_columns[col_name].get('type', '')
                
                if expected_type != actual_type:
                    differences.append(
                        f"Table {table_name}, column {col_name}: "
                        f"expected type {expected_type}, got {actual_type}"
                    )
        
        return differences


# Global test validator instance
test_validator = TestCaseValidator()
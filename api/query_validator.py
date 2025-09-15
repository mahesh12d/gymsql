"""
Secure SQL Query Validation System
=================================
Provides comprehensive validation for SQL queries including:
- Syntax validation
- Dangerous operation detection  
- Query analysis and security filtering
- Complete token tree walking for security
- Execution limits enforcement
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from enum import Enum
from sqlparse import parse, tokens, sql
from sqlparse.engine import FilterStack
from sqlparse.filters import StripWhitespaceFilter

logger = logging.getLogger(__name__)

class QueryRisk(Enum):
    """Risk levels for SQL queries"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class QueryValidationError(Exception):
    """Raised when query validation fails"""
    pass

class QueryExecutionRequest:
    """Query execution request configuration"""
    def __init__(self, query: str, timeout_seconds: int = 30, max_rows: int = 1000):
        if not query.strip():
            raise ValueError('Query cannot be empty')
        if len(query) > 10000:
            raise ValueError('Query too long (max 10000 characters)')
        if timeout_seconds < 1 or timeout_seconds > 60:
            raise ValueError('Timeout must be between 1 and 60 seconds')
        if max_rows < 1 or max_rows > 10000:
            raise ValueError('Max rows must be between 1 and 10000')
            
        self.query = query.strip()
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

class ExecutionLimits:
    """Execution limits configuration"""
    def __init__(self, max_execution_time_seconds: int = 30, max_memory_mb: int = 256, 
                 max_result_rows: int = 1000, max_query_length: int = 10000):
        self.max_execution_time_seconds = max_execution_time_seconds
        self.max_memory_mb = max_memory_mb
        self.max_result_rows = max_result_rows
        self.max_query_length = max_query_length

class SecureSQLValidator:
    """Comprehensive SQL query validator with security checks"""
    
    def __init__(self):
        # Execution limits
        self.execution_limits = ExecutionLimits()
        
        # Strictly blocked DML/DDL keywords (anywhere in query)
        self.blocked_keywords = {
            # All DML operations that modify data
            'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'UPSERT',
            
            # All DDL operations that modify structure  
            'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME',
            
            # Administrative and control statements
            'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT',
            'SET', 'RESET', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN',
            
            # Database/schema level operations
            'USE', 'ATTACH', 'DETACH'
        }
        
        # Dangerous system functions and commands
        self.dangerous_patterns = {
            # System access functions
            'system_functions': [
                r'\b(?:xp_cmdshell|sp_configure|openrowset|opendatasource)\b',
                r'\b(?:pg_read_file|pg_write_file|copy\s+.*?\bfrom\s+program)\b',
                r'\b(?:load_file|into\s+outfile|into\s+dumpfile)\b',
                r'\b(?:exec|execute|eval)\s*\(',
                r'\b(?:sleep|waitfor|benchmark)\s*\(',
            ],
            
            # File and OS operations
            'file_operations': [
                r'\binto\s+(?:outfile|dumpfile)\b',
                r'\bload\s+data\s+infile\b',
                r'\bselect\s+.*?\binto\s+(?:outfile|dumpfile)\b'
            ],
            
            # Multi-statement injection attempts
            'injection_attempts': [
                r';\s*(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)',
                r"'\s*OR\s*'[^']*'\s*=\s*'[^']*'",  # Classic SQL injection
                r'\bunion\s+(?:all\s+)?select\s+.*?\bfrom\s+(?:information_schema|pg_|sys)'
            ]
        }
        
        # Allowed statement types for learning platform (read-only)
        self.allowed_statements = {
            'SELECT', 'WITH'  # Only read operations allowed
        }
        
        # Allowed read-only operations and functions
        self.allowed_keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET',
            'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'ON', 'USING',
            'UNION', 'INTERSECT', 'EXCEPT', 'ALL', 'DISTINCT',
            'AS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL',
            'WITH', 'RECURSIVE'
        }
        
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Comprehensive query validation
        
        Returns:
            Dict with validation results including:
            - is_valid: bool
            - risk_level: QueryRisk
            - errors: List[str]
            - warnings: List[str]
            - parsed_query: Dict
        """
        result = {
            'is_valid': False,
            'risk_level': QueryRisk.SAFE,
            'errors': [],
            'warnings': [],
            'parsed_query': {},
            'allowed_operations': [],
            'blocked_operations': []
        }
        
        try:
            # Basic sanitization
            cleaned_query = self._sanitize_query(query)
            
            # Syntax validation
            syntax_result = self._validate_syntax(cleaned_query)
            if not syntax_result['valid']:
                result['errors'].extend(syntax_result['errors'])
                result['risk_level'] = QueryRisk.HIGH
                return result
            
            # Parse the query
            parsed = parse(cleaned_query)[0] if parse(cleaned_query) else None
            if not parsed:
                result['errors'].append("Failed to parse SQL query")
                result['risk_level'] = QueryRisk.HIGH
                return result
            
            # Extract query information
            query_info = self._extract_query_info(parsed)
            result['parsed_query'] = query_info
            
            # Security validation
            security_result = self._validate_security(cleaned_query, query_info)
            result['errors'].extend(security_result['errors'])
            result['warnings'].extend(security_result['warnings'])
            result['blocked_operations'] = security_result['blocked_operations']
            result['allowed_operations'] = security_result['allowed_operations']
            
            # Determine final risk level
            if result['errors']:
                result['risk_level'] = QueryRisk.CRITICAL
                result['is_valid'] = False
            elif result['warnings']:
                result['risk_level'] = QueryRisk.MEDIUM
                result['is_valid'] = True
            else:
                result['risk_level'] = QueryRisk.SAFE
                result['is_valid'] = True
                
        except Exception as e:
            logger.error(f"Query validation failed: {e}")
            result['errors'].append(f"Validation error: {str(e)}")
            result['risk_level'] = QueryRisk.CRITICAL
            
        return result
    
    def _sanitize_query(self, query: str) -> str:
        """Basic query sanitization with enhanced security"""
        if not query or not query.strip():
            raise QueryValidationError("Empty query provided")
            
        # Remove leading/trailing whitespace
        cleaned = query.strip()
        
        # Enhanced length check
        if len(cleaned) > self.execution_limits.max_query_length:
            raise QueryValidationError(f"Query too long (max {self.execution_limits.max_query_length} characters)")
            
        # Remove null bytes and other control characters
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\t\n\r')
        
        return cleaned
    
    def _validate_syntax(self, query: str) -> Dict[str, Any]:
        """Validate SQL syntax with enhanced security checks"""
        result = {'valid': False, 'errors': []}
        
        try:
            parsed = parse(query)
            if not parsed:
                result['errors'].append("Invalid SQL syntax")
                return result
                
            # CRITICAL: Enforce single statement only
            if len(parsed) > 1:
                result['errors'].append("Multiple statements not allowed. Only single SELECT or WITH statements permitted.")
                return result
                
            # Walk the complete token tree to find ALL keywords
            all_keywords = set()
            blocked_found = set()
            
            self._walk_token_tree(parsed[0], all_keywords, blocked_found)
            
            # Check if any blocked keywords were found
            if blocked_found:
                result['errors'].append(f"Blocked operations detected: {', '.join(sorted(blocked_found))}")
                return result
                
            # Validate that first meaningful keyword is allowed  
            first_token = None
            # Use flattened tokens to ensure we get the very first keyword in order
            for token in parsed[0].flatten():
                # Check for any keyword type (including DML, DDL, etc.)
                if (token.ttype is tokens.Keyword or 
                    token.ttype is tokens.Keyword.DML or
                    token.ttype is tokens.Keyword.DDL):
                    potential_token = token.value.upper()
                    if potential_token in self.allowed_statements:
                        first_token = potential_token
                        break
                    
            if not first_token:
                result['errors'].append("No valid SQL statement found")
                return result
                
            if first_token not in self.allowed_statements:
                result['errors'].append(f"Statement type '{first_token}' not allowed. Only SELECT and WITH statements permitted.")
                return result
                
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(f"Syntax validation error: {str(e)}")
            
        return result
    
    def _walk_token_tree(self, token, all_keywords: Set[str], blocked_found: Set[str]):
        """Recursively walk the complete SQL token tree to find all keywords"""
        if hasattr(token, 'tokens'):
            for sub_token in token.tokens:
                self._walk_token_tree(sub_token, all_keywords, blocked_found)
        else:
            if token.ttype is tokens.Keyword:
                keyword = token.value.upper()
                all_keywords.add(keyword)
                
                # Check if this keyword is blocked
                if keyword in self.blocked_keywords:
                    blocked_found.add(keyword)
    
    def _extract_query_info(self, parsed_query) -> Dict[str, Any]:
        """Extract information from parsed query"""
        info = {
            'statement_type': None,
            'tables': [],
            'columns': [],
            'functions': [],
            'joins': [],
            'where_clauses': [],
            'subqueries': 0,
            'complexity_score': 0
        }
        
        try:
            # Get statement type
            for token in parsed_query.flatten():
                if token.ttype is tokens.Keyword:
                    info['statement_type'] = token.value.upper()
                    break
            
            # Extract table names, functions, etc.
            self._extract_query_elements(parsed_query, info)
            
            # Calculate complexity score
            info['complexity_score'] = self._calculate_complexity(info)
            
        except Exception as e:
            logger.warning(f"Failed to extract query info: {e}")
            
        return info
    
    def _extract_query_elements(self, token, info: Dict[str, Any], depth: int = 0):
        """Recursively extract query elements"""
        if hasattr(token, 'tokens'):
            for sub_token in token.tokens:
                self._extract_query_elements(sub_token, info, depth + 1)
        else:
            # Extract different elements based on token type
            if token.ttype is tokens.Name:
                # Could be table or column name
                value = token.value.lower()
                if value not in ['select', 'from', 'where', 'and', 'or']:
                    if depth > 0:  # Likely a table or column
                        if '.' not in value and value not in info['tables']:
                            info['tables'].append(value)
            
            elif token.ttype is tokens.Name.Builtin:
                # Built-in functions
                func_name = token.value.lower()
                if func_name not in info['functions']:
                    info['functions'].append(func_name)
            
            elif token.ttype is tokens.Keyword and token.value.upper() in ['JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL']:
                join_type = token.value.upper()
                if join_type not in info['joins']:
                    info['joins'].append(join_type)
    
    def _calculate_complexity(self, info: Dict[str, Any]) -> int:
        """Calculate query complexity score"""
        score = 0
        score += len(info['tables']) * 2
        score += len(info['joins']) * 3
        score += len(info['functions']) * 2
        score += info['subqueries'] * 5
        score += len(info['where_clauses'])
        return score
    
    def _validate_security(self, query: str, query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform enhanced security validation checks"""
        result = {
            'errors': [],
            'warnings': [],
            'blocked_operations': [],
            'allowed_operations': []
        }
        
        query_upper = query.upper()
        
        # Check for dangerous system functions and operations
        for category, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_upper, re.IGNORECASE):
                    result['errors'].append(f"Dangerous operation detected: {category}")
                    result['blocked_operations'].append(category)
        
        # Check for allowed operations
        if query_info.get('statement_type') in self.allowed_statements:
            result['allowed_operations'].append(query_info['statement_type'])
        
        # Enhanced complexity warnings
        complexity_score = query_info.get('complexity_score', 0)
        if complexity_score > 25:
            result['warnings'].append("Very high query complexity detected")
        elif complexity_score > 15:
            result['warnings'].append("High query complexity detected")
        
        # Check for too many tables (potential for cartesian product)
        table_count = len(query_info.get('tables', []))
        if table_count > 6:
            result['warnings'].append(f"Query accesses {table_count} tables - ensure proper JOIN conditions to avoid cartesian products")
        elif table_count > 3:
            result['warnings'].append("Query accesses multiple tables - verify JOIN conditions")
        
        # Check for potential performance issues
        if 'LIKE' in query_upper and '%' in query and query.index('%') == query.index('LIKE') + 5:
            result['warnings'].append("Leading wildcard in LIKE pattern may cause slow performance")
            
        return result
    
    def get_safe_query_suggestions(self, query: str) -> List[str]:
        """Provide suggestions for making query safer"""
        suggestions = []
        
        query_upper = query.upper()
        
        # Check for missing WHERE clauses
        if 'DELETE FROM' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("Add WHERE clause to DELETE statement for safety")
        
        if 'UPDATE' in query_upper and 'SET' in query_upper and 'WHERE' not in query_upper:
            suggestions.append("Add WHERE clause to UPDATE statement for safety")
        
        # Check for SELECT *
        if 'SELECT *' in query_upper:
            suggestions.append("Consider specifying column names instead of using SELECT *")
        
        # Check for potential inefficiencies
        if 'LIKE' in query_upper and '%' in query:
            suggestions.append("LIKE with leading wildcards can be slow - consider alternatives")
        
        return suggestions


class QuerySanitizer:
    """Enhanced query sanitization utilities"""
    
    @staticmethod
    def normalize_whitespace(query: str) -> str:
        """Normalize whitespace in query"""
        return re.sub(r'\s+', ' ', query.strip())
    
    @staticmethod
    def add_execution_limits(query: str, limits: ExecutionLimits) -> str:
        """Add execution limits to query if not present"""
        query = query.rstrip(';').strip()
        
        # Add LIMIT clause if not present for SELECT statements
        if 'SELECT' in query.upper() and 'LIMIT' not in query.upper():
            query += f' LIMIT {limits.max_result_rows}'
            
        return query
    
    @staticmethod 
    def validate_execution_request(request_data: dict) -> QueryExecutionRequest:
        """Validate execution request using Pydantic"""
        try:
            return QueryExecutionRequest(**request_data)
        except Exception as e:
            raise QueryValidationError(f"Invalid request format: {str(e)}")

class ExecutionLimitEnforcer:
    """Enforces execution limits during query execution"""
    
    def __init__(self, limits: ExecutionLimits):
        self.limits = limits
    
    def prepare_query_with_limits(self, query: str) -> str:
        """Prepare query with enforced limits"""
        # Add row limit if not present
        if 'LIMIT' not in query.upper() and 'SELECT' in query.upper():
            query = query.rstrip(';')
            query += f' LIMIT {self.limits.max_result_rows}'
        
        return query
    
    def validate_execution_time(self, start_time: float, current_time: float) -> bool:
        """Check if execution time exceeds limits"""
        return (current_time - start_time) <= self.limits.max_execution_time_seconds


# Global validator instance
query_validator = SecureSQLValidator()
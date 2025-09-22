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

    def __init__(self,
                 query: str,
                 timeout_seconds: int = 30,
                 max_rows: int = 1000):
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

    def __init__(self,
                 max_execution_time_seconds: int = 30,
                 max_memory_mb: int = 256,
                 max_result_rows: int = 1000,
                 max_query_length: int = 10000):
        self.max_execution_time_seconds = max_execution_time_seconds
        self.max_memory_mb = max_memory_mb
        self.max_result_rows = max_result_rows
        self.max_query_length = max_query_length


class SecureSQLValidator:
    """Comprehensive SQL query validator with security checks"""

    def __init__(self, allowed_tables=None, max_subqueries=2, max_joins=3):
        # Execution limits
        self.execution_limits = ExecutionLimits()
        
        # Configurable validation limits
        self.allowed_tables = allowed_tables or set()
        self.max_subqueries = max_subqueries
        self.max_joins = max_joins

        # Strictly blocked DML/DDL keywords (anywhere in query)
        self.blocked_keywords = {
            # All DML operations that modify data
            'INSERT',
            'UPDATE',
            'DELETE',
            'MERGE',
            'UPSERT',

            # All DDL operations that modify structure
            'CREATE',
            'ALTER',
            'DROP',
            'TRUNCATE',
            'RENAME',

            # Administrative and control statements
            'GRANT',
            'REVOKE',
            'COMMIT',
            'ROLLBACK',
            'SAVEPOINT',
            'SET',
            'RESET',
            'SHOW',
            'DESCRIBE',
            'DESC',
            'EXPLAIN',

            # Database/schema level operations
            'USE',
            'ATTACH',
            'DETACH'
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
            'SELECT',
            'WITH'  # Only read operations allowed
        }

        # Allowed read-only operations and functions
        self.allowed_keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT',
            'OFFSET', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'ON',
            'USING', 'UNION', 'INTERSECT', 'EXCEPT', 'ALL', 'DISTINCT', 'AS',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR', 'NOT', 'IN',
            'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'WITH', 'RECURSIVE'
        }

    def validate_query_with_hardcode_detection(self, query: str,
                       loaded_tables: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Enhanced validation with comprehensive anti-hardcode detection
        
        Args:
            query: SQL query string to validate
            loaded_tables: Set of table names available in the sandbox
            
        Returns:
            Dict with validation results including hardcode detection
        """
        result = self.validate_query(query, loaded_tables)
        
        # Add hardcode detection if basic validation passes
        if result.get('is_valid', False):
            query_info = result.get('query_info', {})
            
            # Layer 1: Static Analysis - Detect hardcoded queries
            hardcode_result = self.detect_hardcoded_query(query, query_info)
            
            # Merge hardcode detection results
            if hardcode_result['is_hardcoded']:
                result['is_valid'] = False
                result['errors'].extend(hardcode_result['errors'])
                result['warnings'].extend(hardcode_result['warnings'])
                
            result['hardcode_detection'] = hardcode_result
            
            # Enhanced semantic validation for loaded tables
            if loaded_tables:
                enhanced_semantic = self._enhanced_semantic_validation(query, query_info, loaded_tables)
                if enhanced_semantic['errors']:
                    result['is_valid'] = False
                    result['errors'].extend(enhanced_semantic['errors'])
                result['warnings'].extend(enhanced_semantic['warnings'])
        
        return result
    
    def _enhanced_semantic_validation(self, query: str, query_info: Dict[str, Any], 
                                    loaded_tables: Set[str]) -> Dict[str, Any]:
        """
        Enhanced semantic validation specifically for anti-hardcode detection
        """
        result = {'errors': [], 'warnings': []}
        
        query_tables = query_info.get('tables', [])
        query_upper = query.upper().strip()
        
        # Rule 1: Must reference at least one loaded table
        if not any(table.lower() in {t.lower() for t in loaded_tables} for table in query_tables):
            if 'FROM' in query_upper or 'JOIN' in query_upper:
                result['errors'].append(
                    "Query must reference tables from the loaded dataset. "
                    f"Available tables: {', '.join(sorted(loaded_tables))}"
                )
            else:
                result['errors'].append(
                    "Query must include FROM clause with dataset tables. "
                    "Constant-only queries are not permitted for data analysis problems."
                )
        
        # Rule 2: Must have meaningful column references for data analysis
        column_refs = self._count_column_references(query)
        if query_tables and column_refs == 0:
            # Exception for COUNT(*) which is legitimate
            if not ('COUNT(*)' in query_upper or 'COUNT( * )' in query_upper):
                result['errors'].append(
                    "Query must reference actual table columns for data analysis. "
                    "Queries that only access table structure without column data are not permitted."
                )
        
        # Rule 3: Aggregation queries must have column dependencies
        agg_functions = ['SUM(', 'AVG(', 'MAX(', 'MIN(']
        has_agg = any(func in query_upper for func in agg_functions)
        if has_agg:
            # Check that aggregation functions contain column references, not just literals
            agg_has_columns = False
            for func in agg_functions:
                if func in query_upper:
                    # Find the function call and check its contents
                    start = query_upper.find(func)
                    if start != -1:
                        # Simple check: ensure there's a word character after the function
                        remaining = query_upper[start + len(func):]
                        if re.search(r'[a-zA-Z_]\w*', remaining.split(')')[0]):
                            agg_has_columns = True
                            break
            
            if not agg_has_columns:
                result['errors'].append(
                    "Aggregation functions must operate on actual table columns, not constant values. "
                    "Use column names in SUM(), AVG(), MAX(), MIN() functions."
                )
        
        return result

    def validate_query(
            self,
            query: str,
            loaded_tables: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Comprehensive query validation
        
        Args:
            query: SQL query string to validate
            loaded_tables: Set of table names that are loaded in the sandbox (optional)
        
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
            security_result = self._validate_security(cleaned_query,
                                                      query_info)
            result['errors'].extend(security_result['errors'])
            result['warnings'].extend(security_result['warnings'])
            result['blocked_operations'] = security_result[
                'blocked_operations']
            result['allowed_operations'] = security_result[
                'allowed_operations']

            # Semantic validation (if loaded tables are provided)
            if loaded_tables is not None:
                semantic_result = self._validate_semantics(
                    query_info, loaded_tables)
                result['errors'].extend(semantic_result['errors'])
                result['warnings'].extend(semantic_result['warnings'])

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
            raise QueryValidationError(
                f"Query too long (max {self.execution_limits.max_query_length} characters)"
            )

        # Remove null bytes and other control characters
        cleaned = ''.join(char for char in cleaned
                          if ord(char) >= 32 or char in '\t\n\r')

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
                result['errors'].append(
                    "Multiple statements not allowed. Only single SELECT or WITH statements permitted."
                )
                return result

            # Walk the complete token tree to find ALL keywords
            all_keywords = set()
            blocked_found = set()

            self._walk_token_tree(parsed[0], all_keywords, blocked_found)

            # Check if any blocked keywords were found
            if blocked_found:
                result['errors'].append(
                    f"Blocked operations detected: {', '.join(sorted(blocked_found))}"
                )
                return result

            # Validate that first meaningful keyword is allowed
            first_token = None
            # Use flattened tokens to ensure we get the very first keyword in order
            for token in parsed[0].flatten():
                # Check for any keyword type (including DML, DDL, etc.)
                if (token.ttype is tokens.Keyword
                        or token.ttype is tokens.Keyword.DML
                        or token.ttype is tokens.Keyword.DDL):
                    potential_token = token.value.upper()
                    if potential_token in self.allowed_statements:
                        first_token = potential_token
                        break

            if not first_token:
                result['errors'].append("No valid SQL statement found")
                return result

            if first_token not in self.allowed_statements:
                result['errors'].append(
                    f"Statement type '{first_token}' not allowed. Only SELECT and WITH statements permitted."
                )
                return result

            result['valid'] = True

        except Exception as e:
            result['errors'].append(f"Syntax validation error: {str(e)}")

        return result

    def _walk_token_tree(self, token, all_keywords: Set[str],
                         blocked_found: Set[str]):
        """Recursively walk the complete SQL token tree to find all keywords"""
        if hasattr(token, 'tokens'):
            for sub_token in token.tokens:
                self._walk_token_tree(sub_token, all_keywords, blocked_found)
        else:
            # Check for all types of keywords including DML and DDL
            if (token.ttype is tokens.Keyword
                    or token.ttype is tokens.Keyword.DML
                    or token.ttype is tokens.Keyword.DDL):
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

            # Extract table names, functions, etc. using improved method
            extracted_info = self._extract_query_elements(parsed_query)
            # Merge the extracted info with the existing info structure
            info.update(extracted_info)

            # Calculate complexity score
            info['complexity_score'] = self._calculate_complexity(info)

        except Exception as e:
            logger.warning(f"Failed to extract query info: {e}")

        return info

    def _extract_query_elements(self, stmt):
        """
        Use sqlparse AST to extract tables, functions, joins, subqueries
        This replaces the old hardcoded approach with proper AST parsing
        """
        from sqlparse.sql import Identifier, IdentifierList, Function
        from sqlparse.tokens import Keyword, DML
        
        tables = set()
        functions = set()
        joins = 0
        subqueries = 0

        def extract_tokens(token_list):
            nonlocal joins, subqueries

            for token in token_list:
                # Handle nested statements
                if token.is_group:
                    if hasattr(token, 'tokens'):
                        # Count subqueries by looking for nested SELECT statements
                        token_str = str(token).strip().upper()
                        if token_str.startswith('(') and 'SELECT' in token_str:
                            subqueries += 1
                        extract_tokens(token.tokens)

                # Handle functions
                if isinstance(token, Function):
                    func_name = token.get_name()
                    if func_name:
                        functions.add(func_name.lower())

                # Handle identifiers (tables/columns)
                elif isinstance(token, Identifier):
                    name = token.get_real_name()
                    if name and self._is_likely_table_name(token, token_list):
                        tables.add(name.lower())

                elif isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        if isinstance(identifier, Identifier):
                            name = identifier.get_real_name()
                            if name and self._is_likely_table_name(identifier, token_list):
                                tables.add(name.lower())

                # Count JOINs
                elif hasattr(token, 'ttype') and token.ttype is Keyword and "JOIN" in token.value.upper():
                    joins += 1

        extract_tokens(stmt.tokens)

        return {
            "tables": list(tables),
            "functions": list(functions),
            "subqueries": subqueries,
            "joins": joins,
        }

    def _is_likely_table_name(self, identifier, parent_tokens):
        """
        Determine if an identifier is likely a table name based on context
        """
        # Get the identifier as string
        identifier_str = str(identifier).strip()
        
        # Skip if it contains dots (likely column references like o.id)
        if '.' in identifier_str:
            return False
            
        # Look at the immediate context around this identifier
        context_tokens = []
        for token in parent_tokens:
            if hasattr(token, 'tokens'):
                for sub_token in token.tokens:
                    if hasattr(sub_token, 'value'):
                        context_tokens.append(sub_token.value.upper())
        
        context_str = ' '.join(context_tokens[-10:])  # Last 10 tokens for context
        
        # Look for keywords that typically precede table names
        table_indicators = ['FROM', 'JOIN', 'UPDATE', 'INTO']
        
        # Check if any table indicator appears right before this identifier
        for indicator in table_indicators:
            if indicator in context_str:
                # Find position of indicator
                indicator_pos = context_str.rfind(indicator)
                # Check if our identifier appears after the indicator
                remaining_context = context_str[indicator_pos + len(indicator):].strip()
                if remaining_context.startswith(identifier_str.upper()):
                    return True
                
        return False

    def _calculate_complexity(self, info: Dict[str, Any]) -> int:
        """Calculate query complexity score using improved scoring"""
        score = 0
        score += len(info.get('tables', [])) * 2
        score += info.get('joins', 0) * 3
        score += len(info.get('functions', [])) * 1
        score += info.get('subqueries', 0) * 2
        score += len(info.get('where_clauses', []))
        return score

    def _validate_security(self, query: str,
                           query_info: Dict[str, Any]) -> Dict[str, Any]:
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
                    result['errors'].append(
                        f"Dangerous operation detected: {category}")
                    result['blocked_operations'].append(category)

        # Check for allowed operations
        if query_info.get('statement_type') in self.allowed_statements:
            result['allowed_operations'].append(query_info['statement_type'])

        # NEW: Configurable table validation
        for table in query_info.get('tables', []):
            if self.allowed_tables and table not in self.allowed_tables:
                result['errors'].append(f"Table '{table}' is not part of dataset")

        # NEW: Subquery limit validation
        subquery_count = query_info.get('subqueries', 0)
        if subquery_count > self.max_subqueries:
            result['errors'].append(
                f"Too many subqueries ({subquery_count}). Maximum allowed: {self.max_subqueries}"
            )

        # NEW: JOIN limit validation
        join_count = query_info.get('joins', 0)
        if join_count > self.max_joins:
            result['errors'].append(
                f"Too many joins ({join_count}). Maximum allowed: {self.max_joins}"
            )

        # Enhanced complexity warnings
        complexity_score = query_info.get('complexity_score', 0)
        if complexity_score > 25:
            result['warnings'].append("Very high query complexity detected")
        elif complexity_score > 15:
            result['warnings'].append("High query complexity detected")

        # Check for too many tables (potential for cartesian product)
        tables = query_info.get('tables', [])
        table_count = len(tables) if isinstance(tables, list) else 0
        if table_count > 6:
            result['warnings'].append(
                f"Query accesses {table_count} tables - ensure proper JOIN conditions to avoid cartesian products"
            )
        elif table_count > 3:
            result['warnings'].append(
                "Query accesses multiple tables - verify JOIN conditions")

        # Check for potential performance issues
        if 'LIKE' in query_upper and '%' in query and query.index(
                '%') == query.index('LIKE') + 5:
            result['warnings'].append(
                "Leading wildcard in LIKE pattern may cause slow performance")

        # NEW: SELECT * warning
        if "select *" in query.lower():
            result["warnings"].append("Avoid using SELECT * - specify columns explicitly")

        return result

    def _validate_semantics(self, query_info: Dict[str, Any],
                            loaded_tables: Set[str]) -> Dict[str, Any]:
        """
        Validate semantic correctness of query against loaded dataset
        Enhanced with anti-hardcode detection
        
        Args:
            query_info: Extracted query information
            loaded_tables: Set of table names loaded in the sandbox
            
        Returns:
            Dict with semantic validation results
        """
        result = {'errors': [], 'warnings': []}

        query_tables = query_info.get('tables', [])

        # Check if query has no tables (likely a constant-only query)
        if not query_tables:
            if query_info.get('statement_type') == 'SELECT':
                result['errors'].append(
                    "Query must reference at least one table from the loaded dataset. Constant-only queries are not allowed for dataset problems."
                )
            return result

        # Check if all referenced tables are in the loaded dataset
        missing_tables = []
        for table in query_tables:
            # Convert to lowercase for case-insensitive comparison
            if table.lower() not in {t.lower() for t in loaded_tables}:
                missing_tables.append(table)

        if missing_tables:
            available_tables = ', '.join(sorted(loaded_tables))
            result['errors'].append(
                f"Query references unknown table(s): {', '.join(missing_tables)}. "
                f"Available tables: {available_tables}")

        # Warning for queries that don't use all available tables (optional enhancement)
        unused_tables = set(loaded_tables) - {t.lower() for t in query_tables}
        if len(unused_tables) > 0 and len(loaded_tables) > 1:
            result['warnings'].append(
                f"Query doesn't use all available tables. Unused: {', '.join(sorted(unused_tables))}"
            )

        return result

    def detect_hardcoded_query(self, query: str, query_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Layer 1: Static Analysis - Detect hardcoded queries that don't properly analyze data
        
        Returns:
            Dict with detection results including errors and confidence score
        """
        result = {
            'is_hardcoded': False,
            'confidence': 0.0,
            'errors': [],
            'warnings': [],
            'reasons': []
        }
        
        query_upper = query.upper().strip()
        query_tables = query_info.get('tables', [])
        
        # Pattern 1: Pure constant queries (SELECT 355, SELECT 'hello', etc.)
        if re.match(r'^\s*SELECT\s+[\d\'\"\w\s,\(\)\.]+(\s+AS\s+[\w\"\'\`]+)?\s*;?\s*$', query_upper):
            # Check if it contains any table references
            if not query_tables and 'FROM' not in query_upper:
                result['is_hardcoded'] = True
                result['confidence'] = 1.0
                result['errors'].append("Pure constant query detected - must analyze actual data")
                result['reasons'].append("No table references, only literal values")
                return result
        
        # Pattern 2: SELECT literals FROM table LIMIT 1 (common cheat pattern)
        if 'LIMIT 1' in query_upper or 'LIMIT\s+1' in query_upper:
            # Check if SELECT clause contains only literals/constants
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query_upper)
            if select_match:
                select_clause = select_match.group(1).strip()
                # Check if select clause is primarily numeric literals
                if re.match(r'^[\d\s,\(\)\.]+$', select_clause.replace(' AS ', ' ').replace('"', '').replace("'", '')):
                    result['is_hardcoded'] = True
                    result['confidence'] = 0.9
                    result['errors'].append("Suspected hardcoded query: literal values with LIMIT 1")
                    result['reasons'].append("Selecting literal values with artificial LIMIT")
                    return result
        
        # Pattern 3: Check for minimal column references
        column_refs = self._count_column_references(query)
        if query_tables and column_refs == 0:
            result['is_hardcoded'] = True
            result['confidence'] = 0.8
            result['errors'].append("Query references tables but no actual columns - likely hardcoded")
            result['reasons'].append("Table referenced but no column access detected")
            return result
        
        # Pattern 4: Aggregation functions with no column references
        agg_functions = ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']
        has_agg = any(func in query_upper for func in agg_functions)
        if has_agg and column_refs == 0 and query_tables:
            # Exception: COUNT(*) is legitimate
            if not ('COUNT(*)' in query_upper or 'COUNT( * )' in query_upper):
                result['warnings'].append("Aggregation function found but no column references - verify legitimacy")
                result['confidence'] = 0.6
                result['reasons'].append("Aggregation without clear column access")
        
        # Pattern 5: VALUES clause usage (often used for hardcoding)
        if 'VALUES' in query_upper and query_tables:
            result['warnings'].append("VALUES clause detected - ensure it's for legitimate purpose")
            result['confidence'] = 0.4
            result['reasons'].append("VALUES clause present")
        
        return result
    
    def _count_column_references(self, query: str) -> int:
        """
        Count probable column references in a query
        This is a heuristic approach - not perfect but catches most cases
        """
        # Remove string literals to avoid false positives
        query_clean = re.sub(r"'[^']*'", "", query)
        query_clean = re.sub(r'"[^"]*"', "", query_clean)
        
        # Look for patterns that suggest column access
        column_patterns = [
            r'\b\w+\.\w+\b',  # table.column
            r'\bSUM\s*\(\s*\w+\s*\)',  # SUM(column)
            r'\bCOUNT\s*\(\s*\w+\s*\)',  # COUNT(column)
            r'\bAVG\s*\(\s*\w+\s*\)',  # AVG(column)
            r'\bMAX\s*\(\s*\w+\s*\)',  # MAX(column)
            r'\bMIN\s*\(\s*\w+\s*\)',  # MIN(column)
            r'\bWHERE\s+\w+',  # WHERE column
            r'\bGROUP\s+BY\s+\w+',  # GROUP BY column
            r'\bORDER\s+BY\s+\w+',  # ORDER BY column
        ]
        
        count = 0
        for pattern in column_patterns:
            matches = re.findall(pattern, query_clean, re.IGNORECASE)
            count += len(matches)
        
        return count

    def get_safe_query_suggestions(self, query: str) -> List[str]:
        """Provide suggestions for making query safer"""
        suggestions = []

        query_upper = query.upper()

        # Check for missing WHERE clauses
        if 'DELETE FROM' in query_upper and 'WHERE' not in query_upper:
            suggestions.append(
                "Add WHERE clause to DELETE statement for safety")

        if 'UPDATE' in query_upper and 'SET' in query_upper and 'WHERE' not in query_upper:
            suggestions.append(
                "Add WHERE clause to UPDATE statement for safety")

        # Check for SELECT *
        if 'SELECT *' in query_upper:
            suggestions.append(
                "Consider specifying column names instead of using SELECT *")

        # Check for potential inefficiencies
        if 'LIKE' in query_upper and '%' in query:
            suggestions.append(
                "LIKE with leading wildcards can be slow - consider alternatives"
            )

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
    def validate_execution_request(
            request_data: dict) -> QueryExecutionRequest:
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

    def validate_execution_time(self, start_time: float,
                                current_time: float) -> bool:
        """Check if execution time exceeds limits"""
        return (current_time -
                start_time) <= self.limits.max_execution_time_seconds


# Global validator instance
query_validator = SecureSQLValidator()

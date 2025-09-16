#!/usr/bin/env python3
"""
Test script to verify SQL query validator security fixes
"""

import sys
import os
sys.path.append('/home/runner/workspace')

from api.query_validator import query_validator, QueryValidationError

def test_security_fixes():
    """Comprehensive test of security fixes"""
    
    print("🔒 Testing SQL Query Validator Security Fixes")
    print("=" * 50)
    
    # Test 1: Single statement enforcement
    print("\n1. Testing single statement enforcement...")
    
    # Should pass: Single SELECT
    result = query_validator.validate_query("SELECT * FROM users")
    assert result['is_valid'] == True, "Single SELECT should be valid"
    print("SUCCESS: Single SELECT statement allowed")
    
    # Should fail: Multiple statements
    result = query_validator.validate_query("SELECT * FROM users; DROP TABLE users;")
    assert result['is_valid'] == False, "Multiple statements should be blocked"
    assert any("Multiple statements" in error for error in result['errors']), "Should detect multiple statements"
    print("SUCCESS: Multiple statements blocked")
    
    # Test 2: DML/DDL blocking
    print("\n2. Testing DML/DDL operation blocking...")
    
    # Should fail: INSERT
    result = query_validator.validate_query("INSERT INTO users (name) VALUES ('test')")
    assert result['is_valid'] == False, "INSERT should be blocked"
    print("SUCCESS: INSERT operations blocked")
    
    # Should fail: UPDATE
    result = query_validator.validate_query("UPDATE users SET name = 'test' WHERE id = 1")
    assert result['is_valid'] == False, "UPDATE should be blocked"
    print("SUCCESS: UPDATE operations blocked")
    
    # Should fail: DELETE
    result = query_validator.validate_query("DELETE FROM users WHERE id = 1")
    assert result['is_valid'] == False, "DELETE should be blocked"
    print("SUCCESS: DELETE operations blocked")
    
    # Should fail: CREATE
    result = query_validator.validate_query("CREATE TABLE test (id INT)")
    assert result['is_valid'] == False, "CREATE should be blocked"
    print("SUCCESS: CREATE operations blocked")
    
    # Should fail: DROP
    result = query_validator.validate_query("DROP TABLE users")
    assert result['is_valid'] == False, "DROP should be blocked"
    print("SUCCESS: DROP operations blocked")
    
    # Test 3: UNION operations (should be allowed)
    print("\n3. Testing UNION operations (should be allowed)...")
    
    result = query_validator.validate_query("""
        SELECT name FROM users 
        UNION 
        SELECT name FROM customers
    """)
    assert result['is_valid'] == True, "UNION should be allowed"
    print("SUCCESS: UNION operations allowed")
    
    result = query_validator.validate_query("""
        SELECT id, name FROM users 
        UNION ALL 
        SELECT id, name FROM customers
    """)
    assert result['is_valid'] == True, "UNION ALL should be allowed"
    print("SUCCESS: UNION ALL operations allowed")
    
    # Test 4: INTERSECT/EXCEPT operations
    print("\n4. Testing INTERSECT/EXCEPT operations...")
    
    result = query_validator.validate_query("""
        SELECT name FROM users 
        INTERSECT 
        SELECT name FROM customers
    """)
    assert result['is_valid'] == True, "INTERSECT should be allowed"
    print("SUCCESS: INTERSECT operations allowed")
    
    result = query_validator.validate_query("""
        SELECT name FROM users 
        EXCEPT 
        SELECT name FROM customers
    """)
    assert result['is_valid'] == True, "EXCEPT should be allowed"
    print("SUCCESS: EXCEPT operations allowed")
    
    # Test 5: Comments (should be allowed)
    print("\n5. Testing SQL comments...")
    
    result = query_validator.validate_query("""
        -- This is a comment
        SELECT * FROM users -- Another comment
        WHERE id > 10
    """)
    assert result['is_valid'] == True, "Comments should be allowed"
    print("SUCCESS: SQL comments allowed")
    
    result = query_validator.validate_query("""
        /* Multi-line comment */
        SELECT * FROM users 
        /* Another comment */
    """)
    assert result['is_valid'] == True, "Multi-line comments should be allowed"
    print("SUCCESS: Multi-line comments allowed")
    
    # Test 6: Dangerous functions (should be blocked)
    print("\n6. Testing dangerous function blocking...")
    
    # Should fail: File operations
    result = query_validator.validate_query("SELECT LOAD_FILE('/etc/passwd')")
    assert result['is_valid'] == False, "LOAD_FILE should be blocked"
    print("SUCCESS: LOAD_FILE operations blocked")
    
    result = query_validator.validate_query("SELECT * FROM users INTO OUTFILE '/tmp/test.txt'")
    assert result['is_valid'] == False, "INTO OUTFILE should be blocked"
    print("SUCCESS: INTO OUTFILE operations blocked")
    
    # Test 7: Complex valid queries
    print("\n7. Testing complex valid queries...")
    
    result = query_validator.validate_query("""
        WITH user_stats AS (
            SELECT 
                department,
                COUNT(*) as user_count,
                AVG(salary) as avg_salary
            FROM users u
            JOIN departments d ON u.dept_id = d.id
            WHERE u.active = true
            GROUP BY department
        )
        SELECT 
            department,
            user_count,
            avg_salary,
            CASE 
                WHEN avg_salary > 50000 THEN 'High'
                WHEN avg_salary > 30000 THEN 'Medium'
                ELSE 'Low'
            END as salary_bracket
        FROM user_stats
        ORDER BY avg_salary DESC
        LIMIT 10
    """)
    assert result['is_valid'] == True, "Complex valid query should be allowed"
    print("SUCCESS: Complex valid queries allowed")
    
    # Test 8: Injection attempts (should be blocked)
    print("\n8. Testing injection attempt blocking...")
    
    result = query_validator.validate_query("SELECT * FROM users WHERE name = '' OR '1'='1'")
    assert result['is_valid'] == False, "SQL injection should be blocked"
    print("SUCCESS: SQL injection attempts blocked")
    
    print("\n" + "=" * 50)
    print("🎉 ALL SECURITY TESTS PASSED!")
    print("SUCCESS: Single statement enforcement working")
    print("SUCCESS: Complete DML/DDL blocking working") 
    print("SUCCESS: UNION/INTERSECT/EXCEPT operations allowed")
    print("SUCCESS: SQL comments allowed")
    print("SUCCESS: Dangerous functions blocked")
    print("SUCCESS: Complex valid queries supported")
    print("SUCCESS: Injection attempts blocked")
    print("\n🔒 SQL Query Validator is now SECURE! 🔒")

if __name__ == "__main__":
    try:
        test_security_fixes()
    except Exception as e:
        print(f"\n❌ SECURITY TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
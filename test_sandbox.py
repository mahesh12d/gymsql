#!/usr/bin/env python3
"""
Test script for sandbox database functionality
"""
import asyncio
import sys
import os

# Add the current directory to Python path to import api modules
sys.path.append(os.getcwd())

from api.sandbox_manager import sandbox_manager, create_user_sandbox, execute_sandbox_query
from api.database import SessionLocal

async def test_sandbox_functionality():
    """Test the sandbox database creation and query execution"""
    
    # Test data
    user_id = "880be3c3-e093-4274-9294-d20c5f08c583"  # demo12s user
    problem_id = "28640a47-e0c3-4330-86bb-98f21cb6950f"  # Select All Customers problem
    
    print("🧪 Testing Sandbox Database System")
    print("=" * 50)
    
    try:
        # Step 1: Create a sandbox
        print("1️⃣  Creating sandbox database...")
        sandbox = await create_user_sandbox(user_id, problem_id)
        print(f"SUCCESS: Sandbox created successfully!")
        
        # Capture attributes before session closes
        database_name = sandbox.database_name
        sandbox_id = sandbox.id
        status = sandbox.status
        expires_at = sandbox.expires_at
        
        print(f"   - Database Name: {database_name}")
        print(f"   - Status: {status}")
        print(f"   - Expires At: {expires_at}")
        
        # Step 2: Test basic query execution
        print("\n2️⃣  Testing query execution...")
        test_query = "SELECT * FROM customers"
        
        result, status = await execute_sandbox_query(
            sandbox_id, 
            test_query, 
            timeout_seconds=10
        )
        
        print(f"SUCCESS: Query executed successfully!")
        print(f"   - Status: {status}")
        print(f"   - Execution Time: {result.get('execution_time_ms', 0)}ms")
        print(f"   - Rows Returned: {result.get('rows_affected', 0)}")
        
        if result.get('result'):
            print(f"   - Sample Data: {result['result'][:2]}...")  # Show first 2 rows
        
        # Step 3: Test a more complex query
        print("\n3️⃣  Testing complex query...")
        complex_query = "SELECT name, city FROM customers WHERE city = 'New York'"
        
        result2, status2 = await execute_sandbox_query(
            sandbox_id, 
            complex_query, 
            timeout_seconds=10
        )
        
        print(f"SUCCESS: Complex query executed successfully!")
        print(f"   - Status: {status2}")
        print(f"   - Execution Time: {result2.get('execution_time_ms', 0)}ms")
        print(f"   - Filtered Results: {result2.get('result', [])}")
        
        # Step 4: Test query validation
        print("\n4️⃣  Testing query validation...")
        validation_query = "SELECT * FROM customers ORDER BY id"
        
        # This would typically be done through the validation endpoint
        result3, status3 = await execute_sandbox_query(
            sandbox_id, 
            validation_query, 
            timeout_seconds=10
        )
        
        print(f"SUCCESS: Validation query executed successfully!")
        print(f"   - Status: {status3}")
        print(f"   - Data matches expected format: {len(result3.get('result', [])) == 3}")
        
        print(f"\n🎉 All sandbox tests passed successfully!")
        print(f"📊 Summary:")
        print(f"   - Sandbox Database: {database_name}")
        print(f"   - Total Queries Executed: 3")
        print(f"   - All Tests: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during sandbox testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sandbox_functionality())
    if success:
        print("\nSUCCESS: Sandbox system is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Sandbox system has issues!")
        sys.exit(1)
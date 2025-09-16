#!/usr/bin/env python3
"""
Initialize Enhanced Database Schema
==================================
Creates the new database tables for the enhanced SQL learning platform.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import create_tables, engine
from api.models import Base

def main():
    """Initialize the enhanced database schema"""
    print("🚀 Initializing Enhanced Database Schema...")
    
    try:
        # Create all tables
        create_tables()
        print("SUCCESS: Enhanced database schema initialized successfully!")
        
        # List all tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📊 Database now contains {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  • {table}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
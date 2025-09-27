#!/usr/bin/env python3
"""
Simple script to create chat tables in the database
"""
import sys
import os
sys.path.append('api')

from api.database import create_tables

if __name__ == "__main__":
    print("Creating chat tables...")
    try:
        create_tables()
        print("✅ Chat tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
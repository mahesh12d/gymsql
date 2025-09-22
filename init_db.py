#!/usr/bin/env python3
"""
Initialize the SQLGym database tables
"""
import sys
import os

# Add the api directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from api.database import create_tables

if __name__ == "__main__":
    print("Initializing SQLGym database tables...")
    create_tables()
    print("Database initialization completed successfully!")
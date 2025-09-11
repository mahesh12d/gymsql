import os
import sys
import json
import argparse
from sqlalchemy.orm import Session

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.database import SessionLocal, engine
from api.models import Base, Problem

def seed_data(env: str):
    """
    Populates the database with initial data from a JSON file
    based on the provided environment.
    """
    # This ensures tables are created before trying to seed them
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # Check if problems already exist
        if db.query(Problem).count() > 0:
            print("Database already contains problems. Skipping seeding.")
            return

        # Determine which data file to use
        file_path = os.path.join(os.path.dirname(__file__), 'data', f'{env}_problems.json')
        
        if not os.path.exists(file_path):
            print(f"Error: Data file not found at {file_path}")
            print("Please specify a valid environment: 'demo' or 'production'.")
            return
            
        print(f"Seeding database with data from {file_path}...")

        with open(file_path, 'r') as f:
            problems_data = json.load(f)

        # Create Problem objects from the loaded data
        problems_to_add = [Problem(**p) for p in problems_data]

        db.add_all(problems_to_add)
        db.commit()
        
        print(f"Successfully seeded {len(problems_to_add)} problems from '{env}' environment.")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with a specific problem set.")
    parser.add_argument(
        "env", 
        choices=["demo", "production"], 
        help="The environment to seed (e.g., 'demo' or 'production')."
    )
    args = parser.parse_args()
    
    seed_data(args.env)

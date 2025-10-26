#!/usr/bin/env python3
"""
Backfill users.problems_solved from ProblemSession table

This script counts completed problems (where completed_at IS NOT NULL)
for each user and updates their problems_solved count in the users table.

PostgreSQL is the source of truth; Redis leaderboard is just a cache.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, func, distinct
from sqlalchemy.orm import sessionmaker
from api.models import User, ProblemSession
from api.database import engine

def backfill_problems_solved():
    """
    Recompute problems_solved for all users based on completed ProblemSessions
    """
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("🔄 Starting backfill of users.problems_solved from ProblemSession table...")
        print()
        
        users = db.query(User).all()
        total_users = len(users)
        updated_count = 0
        
        for idx, user in enumerate(users, 1):
            completed_problems = db.query(func.count(distinct(ProblemSession.problem_id))).filter(
                ProblemSession.user_id == user.id,
                ProblemSession.completed_at.isnot(None)
            ).scalar() or 0
            
            old_count = user.problems_solved or 0
            
            if old_count != completed_problems:
                user.problems_solved = completed_problems
                user.updated_at = func.now()
                updated_count += 1
                
                print(f"✅ [{idx}/{total_users}] User {user.username}: {old_count} → {completed_problems} problems solved")
            else:
                print(f"⏭️  [{idx}/{total_users}] User {user.username}: {completed_problems} problems (no change)")
        
        db.commit()
        
        print()
        print("=" * 60)
        print(f"✨ Backfill complete!")
        print(f"   Total users processed: {total_users}")
        print(f"   Users updated: {updated_count}")
        print(f"   Users unchanged: {total_users - updated_count}")
        print("=" * 60)
        print()
        print("📋 Next step: Sync Redis leaderboard from PostgreSQL")
        print("   Run this command via your admin panel:")
        print("   POST /api/admin/sync-leaderboard")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during backfill: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill_problems_solved()

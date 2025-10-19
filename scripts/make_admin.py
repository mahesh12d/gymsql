#!/usr/bin/env python3
"""
Utility script to grant admin privileges to a user.

Usage:
    python scripts/make_admin.py <email_or_username>
    
Example:
    python scripts/make_admin.py admin@example.com
    python scripts/make_admin.py johndoe
"""

import sys
import os

# Add parent directory to path to import from api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.models import User


def make_user_admin(identifier: str):
    """Grant admin privileges to a user by email or username"""
    db = SessionLocal()
    try:
        # Try to find user by email first
        user = db.query(User).filter(User.email == identifier).first()
        
        # If not found by email, try username
        if not user:
            user = db.query(User).filter(User.username == identifier).first()
        
        if not user:
            print(f"❌ Error: User not found with email or username '{identifier}'")
            return False
        
        # Check if already admin
        if user.is_admin:
            print(f"ℹ️  User '{user.username}' ({user.email}) is already an admin")
            return True
        
        # Grant admin privileges
        user.is_admin = True
        db.commit()
        
        print(f"✅ Success! User '{user.username}' ({user.email}) is now an admin")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


def list_admins():
    """List all admin users"""
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.is_admin == True).all()
        
        if not admins:
            print("No admin users found")
            return
        
        print(f"\n📋 Admin Users ({len(admins)}):")
        print("-" * 60)
        for admin in admins:
            print(f"  • {admin.username} ({admin.email})")
        print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_admin.py <email_or_username>")
        print("       python scripts/make_admin.py --list")
        print("\nExamples:")
        print("  python scripts/make_admin.py admin@example.com")
        print("  python scripts/make_admin.py johndoe")
        print("  python scripts/make_admin.py --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_admins()
    else:
        identifier = sys.argv[1]
        success = make_user_admin(identifier)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

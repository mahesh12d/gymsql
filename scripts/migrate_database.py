#!/usr/bin/env python3
"""
Database Migration Script - SQLGym
==================================
This script migrates data from your current Neon database to a local PostgreSQL database.

Usage:
    python scripts/migrate_database.py

Prerequisites:
1. Set up local PostgreSQL server
2. Create a local database
3. Set LOCAL_DATABASE_URL environment variable or update the script

Migration Order (respects foreign key dependencies):
1. Users
2. Problems  
3. Submissions
4. CommunityPosts
5. PostLikes
6. PostComments
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to sys.path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Base, User, Problem, Submission, CommunityPost, PostLike, PostComment
from api.database import DATABASE_URL as SOURCE_DATABASE_URL

# Load environment variables
load_dotenv()

# Configuration
LOCAL_DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "postgresql://username:password@localhost:5432/sqlgym")
BATCH_SIZE = 100  # Process records in batches for memory efficiency

class DatabaseMigrator:
    def __init__(self, source_url: str, destination_url: str):
        """Initialize migrator with source and destination database connections."""
        self.source_url = source_url
        self.destination_url = destination_url
        
        # Create engines
        self.source_engine = create_engine(source_url, echo=False)
        self.destination_engine = create_engine(destination_url, echo=False)
        
        # Create session factories
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.DestinationSession = sessionmaker(bind=self.destination_engine)
        
    def test_connections(self) -> bool:
        """Test both database connections."""
        try:
            print("Testing source database connection...")
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("SUCCESS: Source database connection successful")
            
            print("Testing destination database connection...")
            with self.destination_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("SUCCESS: Destination database connection successful")
            
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def setup_destination_schema(self) -> bool:
        """Create tables in destination database."""
        try:
            print("Creating destination database schema...")
            Base.metadata.create_all(bind=self.destination_engine)
            print("SUCCESS: Schema created successfully")
            return True
        except Exception as e:
            print(f"❌ Schema creation failed: {e}")
            return False
    
    def get_record_counts(self) -> Dict[str, int]:
        """Get record counts from source database."""
        counts = {}
        tables = [
            ('users', User),
            ('problems', Problem),
            ('submissions', Submission),
            ('community_posts', CommunityPost),
            ('post_likes', PostLike),
            ('post_comments', PostComment)
        ]
        
        with self.SourceSession() as session:
            for table_name, model_class in tables:
                try:
                    count = session.query(model_class).count()
                    counts[table_name] = count
                    print(f"📊 {table_name}: {count} records")
                except Exception as e:
                    print(f"⚠️ Could not count {table_name}: {e}")
                    counts[table_name] = 0
        
        return counts
    
    def migrate_users(self) -> bool:
        """Migrate users table."""
        try:
            print("\n🚀 Migrating users...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    # Get total count for progress tracking
                    total_users = source_session.query(User).count()
                    
                    if total_users == 0:
                        print("ℹ️ No users to migrate")
                        return True
                    
                    # Process in batches
                    offset = 0
                    migrated = 0
                    
                    while offset < total_users:
                        users = source_session.query(User).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not users:
                            break
                        
                        # Create new user objects for destination
                        for user in users:
                            new_user = User(
                                id=user.id,
                                username=user.username,
                                email=user.email,
                                password_hash=user.password_hash,
                                first_name=user.first_name,
                                last_name=user.last_name,
                                profile_image_url=user.profile_image_url,
                                google_id=user.google_id,
                                github_id=user.github_id,
                                auth_provider=user.auth_provider,
                                problems_solved=user.problems_solved,
                                created_at=user.created_at,
                                updated_at=user.updated_at
                            )
                            dest_session.add(new_user)
                        
                        dest_session.commit()
                        migrated += len(users)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_users} users")
                    
                    print(f"SUCCESS: Users migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Users migration failed: {e}")
            return False
    
    def migrate_problems(self) -> bool:
        """Migrate problems table."""
        try:
            print("\n🚀 Migrating problems...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    total_problems = source_session.query(Problem).count()
                    
                    if total_problems == 0:
                        print("ℹ️ No problems to migrate")
                        return True
                    
                    offset = 0
                    migrated = 0
                    
                    while offset < total_problems:
                        problems = source_session.query(Problem).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not problems:
                            break
                        
                        for problem in problems:
                            new_problem = Problem(
                                id=problem.id,
                                title=problem.title,
                                difficulty=problem.difficulty,
                                tags=problem.tags,
                                company=problem.company,  # Single company field
                                hints=problem.hints,
                                question=problem.question,
                                created_at=problem.created_at,
                                updated_at=problem.updated_at
                            )
                            dest_session.add(new_problem)
                        
                        dest_session.commit()
                        migrated += len(problems)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_problems} problems")
                    
                    print(f"SUCCESS: Problems migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Problems migration failed: {e}")
            return False
    
    def migrate_submissions(self) -> bool:
        """Migrate submissions table."""
        try:
            print("\n🚀 Migrating submissions...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    total_submissions = source_session.query(Submission).count()
                    
                    if total_submissions == 0:
                        print("ℹ️ No submissions to migrate")
                        return True
                    
                    offset = 0
                    migrated = 0
                    
                    while offset < total_submissions:
                        submissions = source_session.query(Submission).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not submissions:
                            break
                        
                        for submission in submissions:
                            new_submission = Submission(
                                id=submission.id,
                                user_id=submission.user_id,
                                problem_id=submission.problem_id,
                                query=submission.query,
                                is_correct=submission.is_correct,
                                execution_time=submission.execution_time,
                                submitted_at=submission.submitted_at
                            )
                            dest_session.add(new_submission)
                        
                        dest_session.commit()
                        migrated += len(submissions)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_submissions} submissions")
                    
                    print(f"SUCCESS: Submissions migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Submissions migration failed: {e}")
            return False
    
    def migrate_community_posts(self) -> bool:
        """Migrate community posts table."""
        try:
            print("\n🚀 Migrating community posts...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    total_posts = source_session.query(CommunityPost).count()
                    
                    if total_posts == 0:
                        print("ℹ️ No community posts to migrate")
                        return True
                    
                    offset = 0
                    migrated = 0
                    
                    while offset < total_posts:
                        posts = source_session.query(CommunityPost).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not posts:
                            break
                        
                        for post in posts:
                            new_post = CommunityPost(
                                id=post.id,
                                user_id=post.user_id,
                                content=post.content,
                                code_snippet=post.code_snippet,
                                likes=post.likes,
                                comments=post.comments,
                                created_at=post.created_at,
                                updated_at=post.updated_at
                            )
                            dest_session.add(new_post)
                        
                        dest_session.commit()
                        migrated += len(posts)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_posts} community posts")
                    
                    print(f"SUCCESS: Community posts migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Community posts migration failed: {e}")
            return False
    
    def migrate_post_likes(self) -> bool:
        """Migrate post likes table."""
        try:
            print("\n🚀 Migrating post likes...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    total_likes = source_session.query(PostLike).count()
                    
                    if total_likes == 0:
                        print("ℹ️ No post likes to migrate")
                        return True
                    
                    offset = 0
                    migrated = 0
                    
                    while offset < total_likes:
                        likes = source_session.query(PostLike).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not likes:
                            break
                        
                        for like in likes:
                            new_like = PostLike(
                                id=like.id,
                                user_id=like.user_id,
                                post_id=like.post_id,
                                created_at=like.created_at
                            )
                            dest_session.add(new_like)
                        
                        dest_session.commit()
                        migrated += len(likes)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_likes} post likes")
                    
                    print(f"SUCCESS: Post likes migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Post likes migration failed: {e}")
            return False
    
    def migrate_post_comments(self) -> bool:
        """Migrate post comments table."""
        try:
            print("\n🚀 Migrating post comments...")
            
            with self.SourceSession() as source_session:
                with self.DestinationSession() as dest_session:
                    total_comments = source_session.query(PostComment).count()
                    
                    if total_comments == 0:
                        print("ℹ️ No post comments to migrate")
                        return True
                    
                    offset = 0
                    migrated = 0
                    
                    while offset < total_comments:
                        comments = source_session.query(PostComment).offset(offset).limit(BATCH_SIZE).all()
                        
                        if not comments:
                            break
                        
                        for comment in comments:
                            new_comment = PostComment(
                                id=comment.id,
                                user_id=comment.user_id,
                                post_id=comment.post_id,
                                content=comment.content,
                                created_at=comment.created_at
                            )
                            dest_session.add(new_comment)
                        
                        dest_session.commit()
                        migrated += len(comments)
                        offset += BATCH_SIZE
                        
                        print(f"  SUCCESS: Migrated {migrated}/{total_comments} post comments")
                    
                    print(f"SUCCESS: Post comments migration completed: {migrated} records")
                    return True
                    
        except Exception as e:
            print(f"❌ Post comments migration failed: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify migration by comparing record counts."""
        print("\n🔍 Verifying migration...")
        
        try:
            source_counts = {}
            dest_counts = {}
            
            tables = [
                ('users', User),
                ('problems', Problem),
                ('submissions', Submission),
                ('community_posts', CommunityPost),
                ('post_likes', PostLike),
                ('post_comments', PostComment)
            ]
            
            # Get source counts
            with self.SourceSession() as session:
                for table_name, model_class in tables:
                    source_counts[table_name] = session.query(model_class).count()
            
            # Get destination counts
            with self.DestinationSession() as session:
                for table_name, model_class in tables:
                    dest_counts[table_name] = session.query(model_class).count()
            
            # Compare counts
            all_match = True
            print("\n📊 Migration Verification:")
            print("=" * 50)
            print(f"{'Table':<20} {'Source':<10} {'Dest':<10} {'Status':<10}")
            print("-" * 50)
            
            for table_name in source_counts:
                source_count = source_counts[table_name]
                dest_count = dest_counts[table_name]
                status = "OK" if source_count == dest_count else "MISMATCH"
                
                if source_count != dest_count:
                    all_match = False
                
                print(f"{table_name:<20} {source_count:<10} {dest_count:<10} {status:<10}")
            
            print("-" * 50)
            
            if all_match:
                print("SUCCESS: Migration verification successful! All record counts match.")
                return True
            else:
                print("❌ Migration verification failed! Some record counts don't match.")
                return False
                
        except Exception as e:
            print(f"❌ Migration verification failed: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete migration process."""
        print("🚀 SQLGym Database Migration")
        print("=" * 50)
        print(f"Source: {self.source_url[:50]}...")
        print(f"Destination: {self.destination_url[:50]}...")
        print()
        
        # Test connections
        if not self.test_connections():
            return False
        
        # Setup destination schema
        if not self.setup_destination_schema():
            return False
        
        # Show record counts
        print("\n📊 Source database record counts:")
        self.get_record_counts()
        
        # Migrate in dependency order
        migration_steps = [
            self.migrate_users,
            self.migrate_problems,
            self.migrate_submissions,
            self.migrate_community_posts,
            self.migrate_post_likes,
            self.migrate_post_comments
        ]
        
        for step in migration_steps:
            if not step():
                print(f"\n❌ Migration failed at step: {step.__name__}")
                return False
        
        # Verify migration
        if not self.verify_migration():
            return False
        
        print("\n🎉 Database migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your DATABASE_URL environment variable to point to the local database")
        print("2. Restart your application")
        print("3. Test your application thoroughly")
        
        return True


def main():
    """Main function to run the migration."""
    if not SOURCE_DATABASE_URL:
        print("❌ SOURCE_DATABASE_URL not found. Make sure DATABASE_URL is set in your environment.")
        return False
    
    if LOCAL_DATABASE_URL == "postgresql://username:password@localhost:5432/sqlgym":
        print("⚠️ Using default LOCAL_DATABASE_URL. Please set LOCAL_DATABASE_URL environment variable")
        print("   or update the LOCAL_DATABASE_URL in this script.")
        
        response = input("Continue with default URL? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return False
    
    # Run migration
    migrator = DatabaseMigrator(SOURCE_DATABASE_URL, LOCAL_DATABASE_URL)
    return migrator.run_migration()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
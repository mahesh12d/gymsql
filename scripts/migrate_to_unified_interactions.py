#!/usr/bin/env python3
"""
Migration script to merge ProblemBookmark and ProblemLike tables into ProblemInteraction
"""
import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from api.database import get_database_url
from api.models import ProblemBookmark, ProblemLike, ProblemInteraction

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_interactions():
    """
    Migrate data from ProblemBookmark and ProblemLike tables to ProblemInteraction
    """
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    
    try:
        logger.info("Starting migration of bookmark and like data to unified interactions table")
        
        # Create the new table if it doesn't exist
        ProblemInteraction.__table__.create(engine, checkfirst=True)
        logger.info("Created ProblemInteraction table if it didn't exist")
        
        # Get all existing bookmarks and likes
        bookmarks = session.query(ProblemBookmark).all()
        likes = session.query(ProblemLike).all()
        
        logger.info(f"Found {len(bookmarks)} bookmarks and {len(likes)} likes to migrate")
        
        # Create a dictionary to track user-problem combinations
        interactions = {}
        
        # Process bookmarks
        for bookmark in bookmarks:
            key = (bookmark.user_id, bookmark.problem_id)
            if key not in interactions:
                interactions[key] = {
                    'user_id': bookmark.user_id,
                    'problem_id': bookmark.problem_id,
                    'bookmark': True,
                    'upvote': False,
                    'downvote': False,
                    'created_at': bookmark.created_at
                }
            else:
                # If already exists (from a like), just set bookmark = True
                interactions[key]['bookmark'] = True
                # Use earlier timestamp
                if bookmark.created_at < interactions[key]['created_at']:
                    interactions[key]['created_at'] = bookmark.created_at
        
        # Process likes (convert to upvotes)
        for like in likes:
            key = (like.user_id, like.problem_id)
            if key not in interactions:
                interactions[key] = {
                    'user_id': like.user_id,
                    'problem_id': like.problem_id,
                    'bookmark': False,
                    'upvote': True,
                    'downvote': False,
                    'created_at': like.created_at
                }
            else:
                # If already exists (from a bookmark), just set upvote = True
                interactions[key]['upvote'] = True
                # Use earlier timestamp
                if like.created_at < interactions[key]['created_at']:
                    interactions[key]['created_at'] = like.created_at
        
        logger.info(f"Merged into {len(interactions)} unique user-problem interactions")
        
        # Insert into ProblemInteraction table
        migrated_count = 0
        for interaction_data in interactions.values():
            # Check if this interaction already exists
            existing = session.query(ProblemInteraction).filter(
                ProblemInteraction.user_id == interaction_data['user_id'],
                ProblemInteraction.problem_id == interaction_data['problem_id']
            ).first()
            
            if not existing:
                new_interaction = ProblemInteraction(
                    user_id=interaction_data['user_id'],
                    problem_id=interaction_data['problem_id'],
                    bookmark=interaction_data['bookmark'],
                    upvote=interaction_data['upvote'],
                    downvote=interaction_data['downvote'],
                    created_at=interaction_data['created_at']
                )
                session.add(new_interaction)
                migrated_count += 1
            else:
                logger.info(f"Interaction already exists for user {interaction_data['user_id'][:8]}... and problem {interaction_data['problem_id'][:8]}...")
        
        # Commit the changes
        session.commit()
        logger.info(f"Successfully migrated {migrated_count} interactions to the new table")
        
        # Verify migration
        total_interactions = session.query(ProblemInteraction).count()
        bookmark_count = session.query(ProblemInteraction).filter(ProblemInteraction.bookmark == True).count()
        upvote_count = session.query(ProblemInteraction).filter(ProblemInteraction.upvote == True).count()
        
        logger.info(f"Migration verification:")
        logger.info(f"  Total interactions: {total_interactions}")
        logger.info(f"  With bookmarks: {bookmark_count}")
        logger.info(f"  With upvotes: {upvote_count}")
        logger.info(f"  Original bookmarks: {len(bookmarks)}")
        logger.info(f"  Original likes: {len(likes)}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_interactions()
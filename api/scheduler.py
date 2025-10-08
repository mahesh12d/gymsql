"""
Background scheduler for periodic maintenance tasks.
Runs data retention cleanup automatically.
"""
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from .database import SessionLocal
from .data_retention import cleanup_old_execution_results

logger = logging.getLogger(__name__)

# Configuration
CLEANUP_INTERVAL_HOURS = 24  # Run cleanup once per day
RETENTION_DAYS = 180  # 6 months

async def scheduled_cleanup_task():
    """Background task that runs data retention cleanup periodically."""
    while True:
        try:
            # Wait for the specified interval
            await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)
            
            # Run cleanup
            db = SessionLocal()
            try:
                deleted_count = cleanup_old_execution_results(db, RETENTION_DAYS)
                logger.info(f"Scheduled cleanup completed: Deleted {deleted_count} old execution_results")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in scheduled cleanup task: {str(e)}")
            # Continue running even if there's an error

async def run_initial_cleanup():
    """Run cleanup once on startup."""
    try:
        db = SessionLocal()
        try:
            deleted_count = cleanup_old_execution_results(db, RETENTION_DAYS)
            logger.info(f"Initial startup cleanup completed: Deleted {deleted_count} old execution_results")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in initial cleanup: {str(e)}")

@asynccontextmanager
async def lifespan_with_scheduler(app):
    """
    Lifespan context manager that starts the cleanup scheduler.
    Use this with FastAPI's lifespan parameter.
    """
    # Startup: Run initial cleanup and start background task
    await run_initial_cleanup()
    cleanup_task = asyncio.create_task(scheduled_cleanup_task())
    
    logger.info(f"Data retention scheduler started. Cleanup runs every {CLEANUP_INTERVAL_HOURS} hours, retaining {RETENTION_DAYS} days of data.")
    
    yield
    
    # Shutdown: Cancel the background task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    logger.info("Data retention scheduler stopped.")

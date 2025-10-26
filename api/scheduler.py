"""
Background scheduler for periodic maintenance tasks.
Runs data retention cleanup and sandbox cleanup automatically.
"""
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from .database import SessionLocal
from .data_retention import cleanup_old_execution_results
from .duckdb_sandbox import sandbox_manager

logger = logging.getLogger(__name__)

# Configuration
CLEANUP_INTERVAL_HOURS = 24  # Run cleanup once per day
RETENTION_DAYS = 180  # 6 months
SANDBOX_CLEANUP_INTERVAL_MINUTES = 1  # Check for idle sandboxes every minute

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

async def sandbox_cleanup_task():
    """Background task that cleans up idle sandboxes every minute."""
    while True:
        try:
            # Wait for the specified interval
            await asyncio.sleep(SANDBOX_CLEANUP_INTERVAL_MINUTES * 60)
            
            # Run sandbox cleanup
            cleaned_count = sandbox_manager.cleanup_idle_sandboxes()
            
            if cleaned_count > 0:
                logger.info(f"Sandbox cleanup: Removed {cleaned_count} idle sandbox(es)")
                
        except Exception as e:
            logger.error(f"Error in sandbox cleanup task: {str(e)}")
            # Continue running even if there's an error

async def run_initial_cleanup():
    """Run cleanup once on startup with timeout to prevent blocking."""
    try:
        # Add timeout to prevent blocking Cloud Run startup
        async with asyncio.timeout(10):  # 10 second timeout
            db = SessionLocal()
            try:
                deleted_count = cleanup_old_execution_results(db, RETENTION_DAYS)
                logger.info(f"Initial startup cleanup completed: Deleted {deleted_count} old execution_results")
            finally:
                db.close()
    except asyncio.TimeoutError:
        logger.warning(f"Initial cleanup timed out - will retry in next scheduled run")
    except Exception as e:
        logger.error(f"Error in initial cleanup: {str(e)}")

@asynccontextmanager
async def lifespan_with_scheduler(app):
    """
    Lifespan context manager that starts the cleanup scheduler.
    Use this with FastAPI's lifespan parameter.
    """
    # Startup: Run initial cleanup and start background tasks
    # Make cleanup non-blocking to prevent Cloud Run startup timeout
    try:
        await run_initial_cleanup()
    except Exception as e:
        logger.warning(f"Skipping initial cleanup due to error: {e}")
    
    # Start both cleanup tasks
    cleanup_task = asyncio.create_task(scheduled_cleanup_task())
    sandbox_task = asyncio.create_task(sandbox_cleanup_task())
    
    logger.info(f"Data retention scheduler started. Cleanup runs every {CLEANUP_INTERVAL_HOURS} hours, retaining {RETENTION_DAYS} days of data.")
    logger.info(f"Sandbox cleanup scheduler started. Idle sandboxes (>5 min) cleaned up every {SANDBOX_CLEANUP_INTERVAL_MINUTES} minute(s).")
    
    yield
    
    # Shutdown: Cancel both background tasks
    cleanup_task.cancel()
    sandbox_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await sandbox_task
    except asyncio.CancelledError:
        pass
    
    logger.info("Data retention scheduler stopped.")
    logger.info("Sandbox cleanup scheduler stopped.")

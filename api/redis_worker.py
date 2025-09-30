"""
Redis Worker Process - Consumes SQL submission jobs from queue
This worker protects the database from burst traffic by processing submissions asynchronously
"""
import asyncio
import logging
import sys
import signal
from typing import Optional
from sqlalchemy.orm import Session

from .redis_service import redis_service
from .secure_execution import secure_executor
from .database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def process_job(job_data: dict) -> None:
    """
    Process a single job from the queue
    
    Args:
        job_data: Job containing job_id, user_id, problem_id, sql
    """
    job_id = job_data.get('job_id')
    user_id = job_data.get('user_id')
    problem_id = job_data.get('problem_id')
    sql_query = job_data.get('sql')
    
    logger.info(f"Processing job {job_id} for user {user_id}, problem {problem_id}")
    
    # Mark job as processing
    redis_service.mark_job_processing(job_id, user_id, problem_id)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Execute the submission using secure executor
        result = await secure_executor.submit_solution(
            user_id=user_id,
            problem_id=problem_id,
            query=sql_query,
            db=db
        )
        
        # Store result in Redis with 5-minute TTL
        redis_service.store_job_result(job_id, result, ttl_seconds=300)
        
        logger.info(f"Job {job_id} completed successfully. Correct: {result.get('is_correct', False)}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {e}", exc_info=True)
        
        # Store error result
        error_result = {
            'success': False,
            'error': str(e),
            'feedback': [f'Execution failed: {str(e)}']
        }
        redis_service.store_job_result(job_id, error_result, ttl_seconds=300)
        
    finally:
        db.close()


async def worker_loop():
    """
    Main worker loop - continuously processes jobs from Redis queue
    """
    global shutdown_requested
    
    if not redis_service.is_available():
        logger.error("Redis is not available. Worker cannot start.")
        sys.exit(1)
    
    logger.info("🚀 Redis worker started. Waiting for jobs...")
    logger.info("Press Ctrl+C to stop gracefully")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while not shutdown_requested:
        try:
            # Block for up to 5 seconds waiting for a job
            job_data = redis_service.get_job_from_queue(timeout=5)
            
            if job_data:
                # Process the job
                await process_job(job_data)
            else:
                # No job available, continue waiting
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            shutdown_requested = True
            break
            
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            # Wait a bit before retrying
            await asyncio.sleep(1)
    
    logger.info("Worker shutdown complete")


def main():
    """Entry point for the worker process"""
    try:
        asyncio.run(worker_loop())
    except Exception as e:
        logger.error(f"Worker failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

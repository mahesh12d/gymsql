#!/usr/bin/env python3
"""
Redis Worker for Problem Queue Processing
Consumes SQL jobs from Redis queue and processes them using the secure executor
"""
import os
import sys
import json
import time
import signal
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Add the api directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis_config import queue_manager, redis_config
from database import SessionLocal
from models import Problem, ProblemSubmissionQueue
from secure_execution import secure_executor

class RedisWorker:
    """Worker process for handling problem queue jobs"""
    
    def __init__(self):
        self.running = False
        self.db = None
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
    
    def start(self):
        """Start the worker process"""
        print("🚀 Starting Redis worker for problem queue...")
        
        # Test Redis connection
        if not redis_config.test_connection():
            print("❌ Failed to connect to Redis. Exiting.")
            return False
        
        print("✅ Redis connection established")
        
        # Test database connection
        try:
            self.db = SessionLocal()
            self.db.execute("SELECT 1")
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
        
        self.running = True
        print("🔄 Worker started, waiting for jobs...")
        
        # Main processing loop
        try:
            while self.running:
                self._process_job()
        except KeyboardInterrupt:
            print("\n🛑 Worker interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error in worker: {e}")
            traceback.print_exc()
        finally:
            self._cleanup()
        
        return True
    
    def _process_job(self):
        """Process a single job from the queue"""
        try:
            # Get next job from Redis queue (blocking with timeout)
            job = queue_manager.get_next_job(timeout=5)
            
            if not job:
                return  # No job available, continue loop
            
            job_id = job["job_id"]
            print(f"📝 Processing job {job_id}...")
            
            # Update job status in database
            self._update_job_in_db(job_id, {"status": "processing"})
            
            # Execute the SQL query
            result = self._execute_sql_job(job)
            
            # Complete the job in Redis (include user_id for authorization)
            queue_manager.complete_job(job_id, result, job["user_id"], success=result.get("success", False))
            
            # Update final status in database
            final_status = "completed" if result.get("success", False) else "failed"
            update_data = {
                "status": final_status,
                "rows_returned": result.get("rows_returned"),
                "execution_time_ms": result.get("execution_time_ms"),
                "error_message": result.get("error_message"),
                "result_data": result,
                "completed_at": datetime.now().isoformat()
            }
            self._update_job_in_db(job_id, update_data)
            
            status_icon = "✅" if result.get("success", False) else "❌"
            print(f"{status_icon} Job {job_id} completed: {final_status}")
            
        except Exception as e:
            print(f"❌ Error processing job: {e}")
            traceback.print_exc()
            
            # Try to mark job as failed if we have job_id
            if 'job' in locals() and 'job_id' in locals():
                try:
                    error_result = {
                        "success": False,
                        "error_message": f"Worker error: {str(e)}",
                        "execution_time_ms": 0
                    }
                    queue_manager.complete_job(job_id, error_result, success=False)
                    self._update_job_in_db(job_id, {
                        "status": "failed",
                        "error_message": str(e),
                        "completed_at": datetime.now().isoformat()
                    })
                except Exception as cleanup_error:
                    print(f"❌ Failed to mark job as failed: {cleanup_error}")
    
    def _execute_sql_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query for a job"""
        try:
            # Get problem information
            problem = self.db.query(Problem).filter(Problem.id == job["problem_id"]).first()
            if not problem:
                return {
                    "success": False,
                    "error_message": "Problem not found",
                    "execution_time_ms": 0
                }
            
            # Extract SQL query
            sql_query = job["sql_query"]
            
            print(f"🔍 Executing SQL for problem {job['problem_id']}: {sql_query[:100]}...")
            
            # Use the secure executor to run the query
            start_time = time.time()
            execution_result = secure_executor.execute_query(
                query=sql_query,
                problem=problem,
                user_id=job["user_id"]
            )
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Process the result
            if execution_result.get("success", False):
                query_result = execution_result.get("query_result", {})
                result_rows = query_result.get("result", [])
                
                return {
                    "success": True,
                    "result": result_rows,
                    "rows_returned": len(result_rows) if result_rows else 0,
                    "execution_time_ms": execution_time_ms,
                    "query_execution_time_ms": query_result.get("execution_time_ms", 0)
                }
            else:
                return {
                    "success": False,
                    "error_message": execution_result.get("error", "Unknown execution error"),
                    "execution_time_ms": execution_time_ms
                }
                
        except Exception as e:
            print(f"❌ SQL execution error: {e}")
            return {
                "success": False,
                "error_message": f"Execution error: {str(e)}",
                "execution_time_ms": 0
            }
    
    def _update_job_in_db(self, job_id: str, update_data: Dict[str, Any]):
        """Update job status in PostgreSQL database"""
        try:
            submission = self.db.query(ProblemSubmissionQueue).filter(
                ProblemSubmissionQueue.id == job_id
            ).first()
            
            if submission:
                for key, value in update_data.items():
                    if hasattr(submission, key):
                        if key == "completed_at" and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        setattr(submission, key, value)
                self.db.commit()
            else:
                print(f"⚠️ Job {job_id} not found in database")
                
        except Exception as e:
            print(f"❌ Error updating job in database: {e}")
            self.db.rollback()
    
    def _cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up worker resources...")
        if self.db:
            self.db.close()
        print("✅ Worker shutdown complete")

def main():
    """Main entry point for the worker"""
    print("=" * 50)
    print("Redis Problem Queue Worker")
    print("=" * 50)
    
    worker = RedisWorker()
    success = worker.start()
    
    exit_code = 0 if success else 1
    print(f"Worker exited with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
"""
Background sync service for Redis to PostgreSQL persistence
Ensures data durability by periodically syncing Redis data to PostgreSQL
"""
import os
import sys
import time
import json
import signal
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the api directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis_config import chat_manager, queue_manager, redis_config
from database import SessionLocal
from models import Message, ProblemSubmissionQueue

class BackgroundSyncService:
    """Service for syncing Redis data to PostgreSQL"""
    
    def __init__(self):
        self.running = False
        self.sync_interval = 30  # Sync every 30 seconds
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down sync service...")
        self.running = False
    
    def start(self):
        """Start the background sync service"""
        print("🔄 Starting Redis to PostgreSQL sync service...")
        
        # Test connections
        if not redis_config.test_connection():
            print("❌ Failed to connect to Redis. Exiting.")
            return False
        
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            print("✅ Database connection tested successfully")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
        
        print("✅ Redis connection tested successfully")
        print(f"🔄 Sync service started (interval: {self.sync_interval}s)")
        
        self.running = True
        
        try:
            while self.running:
                self._sync_cycle()
                time.sleep(self.sync_interval)
        except KeyboardInterrupt:
            print("\n🛑 Sync service interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error in sync service: {e}")
        finally:
            print("✅ Sync service shutdown complete")
        
        return True
    
    def _sync_cycle(self):
        """Perform one sync cycle"""
        try:
            # Sync chat messages
            messages_synced = self._sync_chat_messages()
            
            # Sync problem submissions (completed jobs)
            submissions_synced = self._sync_problem_submissions()
            
            if messages_synced > 0 or submissions_synced > 0:
                print(f"📊 Synced: {messages_synced} messages, {submissions_synced} submissions")
            
        except Exception as e:
            print(f"❌ Error during sync cycle: {e}")
    
    def _sync_chat_messages(self) -> int:
        """Sync chat messages from Redis to PostgreSQL"""
        db = SessionLocal()
        messages_synced = 0
        
        try:
            # Get all conversation IDs from Redis
            conversation_keys = redis_config.redis_client.keys("chat:*:messages")
            
            for key in conversation_keys:
                try:
                    # Extract conversation_id from key (format: chat:{conv_id}:messages)
                    conversation_id = key.split(":")[1]
                    
                    # Get messages from Redis
                    redis_messages = redis_config.redis_client.lrange(key, 0, -1)
                    
                    for msg_json in redis_messages:
                        try:
                            msg_data = json.loads(msg_json)
                            
                            # Check if message already exists in PostgreSQL
                            existing = db.query(Message).filter(
                                Message.id == msg_data["id"]
                            ).first()
                            
                            if not existing:
                                # Create new message record
                                message = Message(
                                    id=msg_data["id"],
                                    conversation_id=msg_data["conversation_id"],
                                    sender_id=msg_data["sender_id"],
                                    receiver_id=msg_data["receiver_id"],
                                    content=msg_data["content"],
                                    timestamp=datetime.fromisoformat(msg_data["timestamp"])
                                )
                                db.add(message)
                                messages_synced += 1
                        
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            print(f"⚠️ Skipping invalid message in {key}: {e}")
                            continue
                
                except Exception as e:
                    print(f"⚠️ Error processing conversation {key}: {e}")
                    continue
            
            db.commit()
            
        except Exception as e:
            print(f"❌ Error syncing chat messages: {e}")
            db.rollback()
        finally:
            db.close()
        
        return messages_synced
    
    def _sync_problem_submissions(self) -> int:
        """Sync completed problem submissions from Redis to PostgreSQL"""
        db = SessionLocal()
        submissions_synced = 0
        
        try:
            # Get all result keys from Redis
            result_keys = redis_config.redis_client.keys("problems:result:*")
            
            for key in result_keys:
                try:
                    # Extract job_id from key (format: problems:result:{job_id})
                    job_id = key.split(":")[-1]
                    
                    # Check if already synced to PostgreSQL
                    existing = db.query(ProblemSubmissionQueue).filter(
                        ProblemSubmissionQueue.id == job_id,
                        ProblemSubmissionQueue.status.in_(["completed", "failed"])
                    ).first()
                    
                    if existing:
                        continue  # Already synced
                    
                    # Get result data from Redis
                    result_json = redis_config.redis_client.get(key)
                    if not result_json:
                        continue
                    
                    result_data = json.loads(result_json)
                    
                    # Check if we have the submission record
                    submission = db.query(ProblemSubmissionQueue).filter(
                        ProblemSubmissionQueue.id == job_id
                    ).first()
                    
                    if submission:
                        # Update existing submission with results
                        submission.status = "completed" if result_data["success"] else "failed"
                        submission.result_data = result_data.get("result")
                        submission.execution_time_ms = result_data.get("result", {}).get("execution_time_ms")
                        submission.rows_returned = result_data.get("result", {}).get("rows_returned")
                        submission.error_message = result_data.get("result", {}).get("error_message")
                        submission.completed_at = datetime.fromisoformat(result_data["completed_at"])
                        
                        submissions_synced += 1
                
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"⚠️ Skipping invalid result in {key}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ Error processing result {key}: {e}")
                    continue
            
            db.commit()
            
        except Exception as e:
            print(f"❌ Error syncing problem submissions: {e}")
            db.rollback()
        finally:
            db.close()
        
        return submissions_synced
    
    def _cleanup_old_redis_data(self):
        """Clean up old data from Redis to prevent memory bloat"""
        try:
            # Clean up old result keys (older than 1 hour)
            result_keys = redis_config.redis_client.keys("problems:result:*")
            expired_count = 0
            
            for key in result_keys:
                ttl = redis_config.redis_client.ttl(key)
                if ttl == -1:  # No expiry set, set one
                    redis_config.redis_client.expire(key, 3600)  # 1 hour
                elif ttl < -1:  # Expired
                    redis_config.redis_client.delete(key)
                    expired_count += 1
            
            if expired_count > 0:
                print(f"🧹 Cleaned up {expired_count} expired Redis keys")
                
        except Exception as e:
            print(f"⚠️ Error during Redis cleanup: {e}")

def main():
    """Main entry point for the sync service"""
    print("=" * 50)
    print("Redis to PostgreSQL Sync Service")
    print("=" * 50)
    
    sync_service = BackgroundSyncService()
    success = sync_service.start()
    
    exit_code = 0 if success else 1
    print(f"Sync service exited with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
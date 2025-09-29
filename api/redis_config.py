"""
Redis configuration and connection setup for messaging and problem queue
"""
import os
import json
import redis
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import uuid

# Redis connection configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Redis connection pools for different use cases
class RedisConfig:
    def __init__(self):
        # Main Redis connection for general operations
        self.redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30
        )
        
        # Separate connection for pub/sub (doesn't decode responses for better performance)
        self.pubsub_client = redis.from_url(
            REDIS_URL,
            decode_responses=False,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def test_connection(self) -> bool:
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            return True
        except redis.ConnectionError:
            return False

# Global Redis instance
redis_config = RedisConfig()

class ChatRedisManager:
    """
    Redis operations for chat system following the specified schema:
    - chat:{conversation_id}:messages = List
    - user:{user_id}:conversations = Set  
    - user:{user_id}:online = Boolean (expiring key)
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.MESSAGE_LIMIT = 50  # Keep last 50 messages in Redis
        self.ONLINE_EXPIRY = 300  # 5 minutes
    
    def get_conversation_id(self, user1_id: str, user2_id: str) -> str:
        """Generate consistent conversation ID for two users"""
        users = sorted([user1_id, user2_id])
        return f"{users[0]}_{users[1]}"
    
    def add_message(self, sender_id: str, receiver_id: str, content: str) -> Dict[str, Any]:
        """Add message to Redis and return message data"""
        conversation_id = self.get_conversation_id(sender_id, receiver_id)
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": timestamp
        }
        
        # Add to conversation messages list (RPUSH for chronological order)
        chat_key = f"chat:{conversation_id}:messages"
        self.redis.rpush(chat_key, json.dumps(message_data))
        
        # Trim to keep only last 50 messages
        self.redis.ltrim(chat_key, -self.MESSAGE_LIMIT, -1)
        
        # Add conversation to both users' conversation sets
        self.redis.sadd(f"user:{sender_id}:conversations", conversation_id)
        self.redis.sadd(f"user:{receiver_id}:conversations", conversation_id)
        
        return message_data
    
    def get_recent_messages(self, user1_id: str, user2_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages from a conversation"""
        conversation_id = self.get_conversation_id(user1_id, user2_id)
        chat_key = f"chat:{conversation_id}:messages"
        
        # Get messages (most recent first)
        messages = self.redis.lrange(chat_key, -limit, -1)
        return [json.loads(msg) for msg in messages]
    
    def get_user_conversations(self, user_id: str) -> List[str]:
        """Get all conversation IDs for a user"""
        return list(self.redis.smembers(f"user:{user_id}:conversations"))
    
    def set_user_online(self, user_id: str) -> None:
        """Mark user as online with expiring key"""
        self.redis.setex(f"user:{user_id}:online", self.ONLINE_EXPIRY, "true")
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user is online"""
        return self.redis.exists(f"user:{user_id}:online") > 0
    
    def extend_user_online(self, user_id: str) -> None:
        """Extend user online status"""
        self.redis.expire(f"user:{user_id}:online", self.ONLINE_EXPIRY)

class ProblemQueueManager:
    """
    Redis operations for problem queue following the specified schema:
    - problems:queue = List
    - problems:processing:{job_id} = Hash
    - problems:result:{job_id} = String (TTL 5min)
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.RESULT_TTL = 300  # 5 minutes
    
    def submit_problem(self, user_id: str, problem_id: str, sql_query: str) -> str:
        """Submit a problem to the queue and return job_id"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "problem_id": problem_id,
            "sql_query": sql_query,
            "submitted_at": datetime.now().isoformat(),
            "status": "queued"
        }
        
        # Add to processing queue
        self.redis.lpush("problems:queue", json.dumps(job_data))
        
        return job_id
    
    def get_next_job(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get next job from queue (blocking operation for worker)"""
        try:
            # BRPOP for FIFO processing with timeout
            result = self.redis.brpop("problems:queue", timeout=timeout)
            if result:
                _, job_data = result
                job = json.loads(job_data)
                
                # Move to processing
                job_id = job["job_id"]
                job["status"] = "processing"
                job["processing_started_at"] = datetime.now().isoformat()
                
                # Store in processing hash
                self.redis.hset(f"problems:processing:{job_id}", mapping=job)
                
                return job
        except redis.RedisError:
            pass
        return None
    
    def complete_job(self, job_id: str, result: Dict[str, Any], success: bool = True) -> None:
        """Mark job as complete and store result"""
        # Store result with TTL
        result_data = {
            "job_id": job_id,
            "completed_at": datetime.now().isoformat(),
            "success": success,
            "result": result
        }
        
        # Cache result for 5 minutes
        self.redis.setex(
            f"problems:result:{job_id}",
            self.RESULT_TTL,
            json.dumps(result_data)
        )
        
        # Remove from processing
        self.redis.delete(f"problems:processing:{job_id}")
    
    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached job result"""
        result = self.redis.get(f"problems:result:{job_id}")
        return json.loads(result) if result else None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status"""
        # Check if in processing
        processing_data = self.redis.hgetall(f"problems:processing:{job_id}")
        if processing_data:
            return processing_data
        
        # Check if completed (in results)
        result = self.get_job_result(job_id)
        if result:
            return {"status": "completed", "completed_at": result["completed_at"]}
        
        return None

# Global managers
chat_manager = ChatRedisManager(redis_config.redis_client)
queue_manager = ProblemQueueManager(redis_config.redis_client)

# Pub/Sub for real-time messaging
class MessagePublisher:
    """Handle real-time message publishing"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def publish_message(self, receiver_id: str, message_data: Dict[str, Any]) -> None:
        """Publish message to user's channel"""
        channel = f"user:{receiver_id}:messages"
        self.redis.publish(channel, json.dumps(message_data))

# Global publisher
message_publisher = MessagePublisher(redis_config.redis_client)
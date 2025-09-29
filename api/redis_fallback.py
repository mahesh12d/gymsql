"""
Redis fallback system for Replit environment
Provides stub implementations to allow the app to run without Redis
"""
import json
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta


class FallbackRedisClient:
    """Stub Redis client that provides fallback implementations"""
    
    def __init__(self):
        # In-memory storage for basic operations
        self._data = {}
        self._sets = {}
        self._lists = {}
        
    def ping(self) -> bool:
        """Always return successful ping"""
        return True
    
    def get(self, key: str) -> Optional[str]:
        """Get value from memory"""
        return self._data.get(key)
    
    def set(self, key: str, value: str) -> bool:
        """Set value in memory"""
        self._data[key] = value
        return True
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """Set value with expiration (no actual expiration logic in fallback)"""
        self._data[key] = value
        return True
    
    def delete(self, key: str) -> int:
        """Delete key from memory"""
        if key in self._data:
            del self._data[key]
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        """Check if key exists"""
        return 1 if key in self._data else 0
    
    def expire(self, key: str, time: int) -> bool:
        """Stub expiration (no actual expiration in fallback)"""
        return key in self._data
    
    def sadd(self, key: str, *values) -> int:
        """Add to set"""
        if key not in self._sets:
            self._sets[key] = set()
        before_len = len(self._sets[key])
        self._sets[key].update(values)
        return len(self._sets[key]) - before_len
    
    def smembers(self, key: str) -> set:
        """Get set members"""
        return self._sets.get(key, set())
    
    def rpush(self, key: str, *values) -> int:
        """Push to right of list"""
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])
    
    def lpush(self, key: str, *values) -> int:
        """Push to left of list"""
        if key not in self._lists:
            self._lists[key] = []
        for value in reversed(values):
            self._lists[key].insert(0, value)
        return len(self._lists[key])
    
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list"""
        if key not in self._lists:
            return []
        return self._lists[key][start:end+1 if end != -1 else None]
    
    def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list"""
        if key in self._lists:
            if end == -1:
                self._lists[key] = self._lists[key][start:]
            else:
                self._lists[key] = self._lists[key][start:end+1]
        return True
    
    def brpop(self, keys, timeout: int = 0) -> Optional[tuple]:
        """Blocking right pop (non-blocking fallback)"""
        if isinstance(keys, str):
            keys = [keys]
        
        for key in keys:
            if key in self._lists and self._lists[key]:
                value = self._lists[key].pop()
                return (key, value)
        return None
    
    def hset(self, key: str, mapping: Dict[str, Any] = None, **kwargs) -> int:
        """Set hash fields"""
        if key not in self._data:
            self._data[key] = {}
        
        if not isinstance(self._data[key], dict):
            self._data[key] = {}
        
        updates = mapping or kwargs
        for field, value in updates.items():
            self._data[key][field] = value
        
        return len(updates)
    
    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields"""
        value = self._data.get(key, {})
        return value if isinstance(value, dict) else {}
    
    def publish(self, channel: str, message: str) -> int:
        """Publish message (no-op in fallback)"""
        print(f"[FALLBACK] Would publish to {channel}: {message}")
        return 0
    
    def pubsub(self):
        """Return a fallback pubsub instance"""
        return FallbackPubSub()


class FallbackPubSub:
    """Fallback PubSub implementation"""
    
    def __init__(self):
        self._subscriptions = set()
    
    def subscribe(self, *channels):
        """Subscribe to channels"""
        self._subscriptions.update(channels)
    
    def unsubscribe(self, *channels):
        """Unsubscribe from channels"""
        for channel in channels:
            self._subscriptions.discard(channel)
    
    def get_message(self, timeout: float = 0.0):
        """Get message (always returns None in fallback)"""
        return None
    
    def close(self):
        """Close pubsub"""
        pass


class FallbackRedisConfig:
    """Fallback Redis configuration using in-memory storage"""
    
    def __init__(self):
        self.redis_client = FallbackRedisClient()
        self.pubsub_client = FallbackRedisClient()
    
    def test_connection(self) -> bool:
        """Always return successful connection"""
        print("🔄 Using Redis fallback mode (in-memory storage)")
        return True


class FallbackChatRedisManager:
    """Fallback chat manager with database-only persistence"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.MESSAGE_LIMIT = 50
        self.ONLINE_EXPIRY = 300
        # Note: In fallback mode, messages are stored in PostgreSQL only
    
    def get_conversation_id(self, user1_id: str, user2_id: str) -> str:
        """Generate consistent conversation ID for two users"""
        users = sorted([user1_id, user2_id])
        return f"{users[0]}_{users[1]}"
    
    def add_message(self, sender_id: str, receiver_id: str, content: str) -> Dict[str, Any]:
        """Add message (will be persisted to database only)"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        conversation_id = self.get_conversation_id(sender_id, receiver_id)
        
        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": timestamp
        }
        
        print(f"[FALLBACK] Message will be persisted to database: {sender_id} -> {receiver_id}")
        return message_data
    
    def get_recent_messages(self, user1_id: str, user2_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages (fallback returns empty - will use database)"""
        print(f"[FALLBACK] Retrieving messages from database for {user1_id} <-> {user2_id}")
        return []  # Will fall back to database retrieval
    
    def get_user_conversations(self, user_id: str) -> List[str]:
        """Get conversations (fallback returns empty - will use database)"""
        print(f"[FALLBACK] Retrieving conversations from database for {user_id}")
        return []
    
    def set_user_online(self, user_id: str) -> None:
        """Set user online (no-op in fallback)"""
        pass
    
    def is_user_online(self, user_id: str) -> bool:
        """Check online status (always False in fallback)"""
        return False
    
    def extend_user_online(self, user_id: str) -> None:
        """Extend online status (no-op in fallback)"""
        pass


class FallbackProblemQueueManager:
    """Fallback queue manager that processes jobs synchronously"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.RESULT_TTL = 300
        # Store job results temporarily in memory
        self._job_results = {}
    
    def submit_problem(self, user_id: str, problem_id: str, sql_query: str) -> str:
        """Submit problem (returns job_id but processes synchronously)"""
        job_id = str(uuid.uuid4())
        print(f"[FALLBACK] Problem submitted for immediate processing: {job_id}")
        return job_id
    
    def get_next_job(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get next job (no queue in fallback mode)"""
        return None
    
    def complete_job(self, job_id: str, result: Dict[str, Any], user_id: str, success: bool = True) -> None:
        """Store job result in memory"""
        result_data = {
            "job_id": job_id,
            "user_id": user_id,
            "completed_at": datetime.now().isoformat(),
            "success": success,
            "result": result.get("result"),
            "execution_time_ms": result.get("execution_time_ms"),
            "rows_returned": result.get("rows_returned"),
            "error_message": result.get("error_message")
        }
        self._job_results[job_id] = result_data
        print(f"[FALLBACK] Job completed: {job_id}, success: {success}")
    
    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result from memory"""
        return self._job_results.get(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        result = self._job_results.get(job_id)
        if result:
            return {
                "status": "completed", 
                "completed_at": result["completed_at"],
                "user_id": result.get("user_id")
            }
        return None


class FallbackMessagePublisher:
    """Fallback message publisher (no-op)"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def publish_message(self, receiver_id: str, message_data: Dict[str, Any]) -> None:
        """Publish message (no-op in fallback)"""
        print(f"[FALLBACK] Would publish real-time message to {receiver_id}")
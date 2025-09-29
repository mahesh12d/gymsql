"""
Message Persistence Service
Handles syncing messages from Redis to PostgreSQL for data persistence
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import Message, Conversation, User
from .redis_config import chat_manager, redis_config

logger = logging.getLogger(__name__)

class MessagePersistenceService:
    """
    Service to persist messages from Redis to PostgreSQL
    Ensures messages are not lost when Redis data expires
    """
    
    def __init__(self):
        self.batch_size = 100
        self.sync_interval = 30  # seconds
        self.redis_message_ttl = 3600  # 1 hour
        
    async def ensure_conversation_exists(self, session: Session, user1_id: str, user2_id: str) -> str:
        """
        Ensure conversation exists in PostgreSQL, create if not exists
        Returns conversation_id
        """
        # Sort user IDs for consistent conversation ID
        users = sorted([user1_id, user2_id])
        conversation_id = f"{users[0]}_{users[1]}"
        
        # Check if conversation exists
        existing = session.get(Conversation, conversation_id)
        if existing:
            return conversation_id
            
        # Create new conversation
        conversation = Conversation(
            id=conversation_id,
            user1_id=users[0],
            user2_id=users[1],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            session.add(conversation)
            session.commit()
            logger.info(f"Created new conversation: {conversation_id}")
        except IntegrityError:
            # Handle race condition where another process created it
            session.rollback()
            logger.info(f"Conversation {conversation_id} already exists (race condition)")
            
        return conversation_id
    
    async def persist_message_to_postgres(self, message_data: Dict[str, Any]) -> bool:
        """
        Persist a single message from Redis to PostgreSQL
        Returns True if successful, False otherwise
        """
        try:
            session = SessionLocal()
            
            # Ensure conversation exists
            conversation_id = await self.ensure_conversation_exists(
                session, 
                message_data["sender_id"], 
                message_data["receiver_id"]
            )
            
            # Check if message already exists (prevent duplicates)
            existing = session.get(Message, message_data["id"])
            if existing:
                session.close()
                return True
                
            # Create message in PostgreSQL
            message = Message(
                id=message_data["id"],
                conversation_id=conversation_id,
                sender_id=message_data["sender_id"],
                receiver_id=message_data["receiver_id"],
                content=message_data["content"],
                timestamp=datetime.fromisoformat(message_data["timestamp"]),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(message)
            session.commit()
            session.close()
            
            logger.debug(f"Persisted message {message_data['id']} to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist message to PostgreSQL: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False
    
    async def sync_conversation_messages(self, conversation_id: str) -> int:
        """
        Sync all messages from a Redis conversation to PostgreSQL
        Returns number of messages synced
        """
        try:
            # Get all messages from Redis for this conversation
            chat_key = f"chat:{conversation_id}:messages"
            redis_messages = redis_config.redis_client.lrange(chat_key, 0, -1)
            
            synced_count = 0
            
            for message_json in redis_messages:
                try:
                    message_data = json.loads(message_json)
                    success = await self.persist_message_to_postgres(message_data)
                    if success:
                        synced_count += 1
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Redis message: {message_json}")
                    
            logger.info(f"Synced {synced_count} messages from conversation {conversation_id}")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync conversation {conversation_id}: {e}")
            return 0
    
    async def sync_all_redis_messages(self) -> Dict[str, int]:
        """
        Sync all messages from Redis to PostgreSQL
        Returns sync statistics
        """
        try:
            # Get all conversation keys from Redis
            conversation_keys = redis_config.redis_client.keys("chat:*:messages")
            
            stats = {
                "conversations_processed": 0,
                "messages_synced": 0,
                "errors": 0
            }
            
            for key in conversation_keys:
                try:
                    # Extract conversation_id from key format: chat:{conversation_id}:messages
                    conversation_id = key.split(":")[1]
                    synced = await self.sync_conversation_messages(conversation_id)
                    stats["messages_synced"] += synced
                    stats["conversations_processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to process conversation key {key}: {e}")
                    stats["errors"] += 1
                    
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync Redis messages: {e}")
            return {"conversations_processed": 0, "messages_synced": 0, "errors": 1}
    
    async def get_persistent_messages(self, user1_id: str, user2_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get messages from PostgreSQL for fallback when Redis is unavailable
        """
        try:
            session = SessionLocal()
            
            # Generate conversation ID
            users = sorted([user1_id, user2_id])
            conversation_id = f"{users[0]}_{users[1]}"
            
            # Query messages from PostgreSQL
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(desc(Message.timestamp))
                .limit(limit)
            )
            
            result = session.execute(query)
            messages = result.scalars().all()
            session.close()
            
            # Convert to format compatible with Redis messages
            message_list = []
            for msg in reversed(messages):  # Reverse to get chronological order
                message_list.append({
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "sender_id": msg.sender_id,
                    "receiver_id": msg.receiver_id,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                })
                
            return message_list
            
        except Exception as e:
            logger.error(f"Failed to get persistent messages: {e}")
            return []
    
    async def cleanup_old_redis_messages(self, max_age_hours: int = 24) -> int:
        """
        Clean up old messages from Redis (PostgreSQL keeps them permanently)
        Returns number of messages cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            conversation_keys = redis_config.redis_client.keys("chat:*:messages")
            
            cleaned_count = 0
            
            for key in conversation_keys:
                messages = redis_config.redis_client.lrange(key, 0, -1)
                messages_to_keep = []
                
                for message_json in messages:
                    try:
                        message_data = json.loads(message_json)
                        message_time = datetime.fromisoformat(message_data["timestamp"])
                        
                        if message_time > cutoff_time:
                            messages_to_keep.append(message_json)
                        else:
                            cleaned_count += 1
                    except (json.JSONDecodeError, KeyError):
                        # Keep malformed messages for manual review
                        messages_to_keep.append(message_json)
                
                # Replace the list with cleaned messages
                if len(messages_to_keep) != len(messages):
                    redis_config.redis_client.delete(key)
                    if messages_to_keep:
                        redis_config.redis_client.lpush(key, *reversed(messages_to_keep))
                        
            logger.info(f"Cleaned up {cleaned_count} old messages from Redis")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old Redis messages: {e}")
            return 0

# Global persistence service instance
message_persistence = MessagePersistenceService()

async def enhanced_add_message(sender_id: str, receiver_id: str, content: str) -> Dict[str, Any]:
    """
    Enhanced message adding that persists to both Redis and PostgreSQL
    """
    try:
        # Add to Redis (for speed and real-time features)
        message_data = chat_manager.add_message(sender_id, receiver_id, content)
        
        # Persist to PostgreSQL (for durability)
        asyncio.create_task(message_persistence.persist_message_to_postgres(message_data))
        
        return message_data
        
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        # Fallback: try to save directly to PostgreSQL if Redis fails
        message_data = {
            "id": str(uuid.uuid4()),
            "conversation_id": f"{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}",
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        success = await message_persistence.persist_message_to_postgres(message_data)
        if success:
            return message_data
        else:
            raise e

async def enhanced_get_messages(user1_id: str, user2_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Enhanced message retrieval with PostgreSQL fallback
    """
    try:
        # Try Redis first (faster)
        messages = chat_manager.get_recent_messages(user1_id, user2_id, limit)
        
        # If Redis has no messages or few messages, supplement with PostgreSQL
        if len(messages) < min(limit, 10):  # If we have fewer than 10 messages in Redis
            pg_messages = await message_persistence.get_persistent_messages(user1_id, user2_id, limit)
            
            # Merge and deduplicate
            seen_ids = {msg["id"] for msg in messages}
            for pg_msg in pg_messages:
                if pg_msg["id"] not in seen_ids:
                    messages.append(pg_msg)
                    
            # Sort by timestamp and limit
            messages.sort(key=lambda x: x["timestamp"])
            messages = messages[-limit:]  # Keep most recent
            
        return messages
        
    except Exception as e:
        logger.error(f"Failed to get messages from Redis, falling back to PostgreSQL: {e}")
        # Fallback to PostgreSQL only
        return await message_persistence.get_persistent_messages(user1_id, user2_id, limit)
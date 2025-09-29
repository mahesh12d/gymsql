"""
Chat API routes for real-time messaging with Redis backend
"""
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime

from .database import get_db, SessionLocal
from .models import User, Message
from .auth import get_current_user
from .redis_config import chat_manager, message_publisher, redis_config

# Pydantic models for requests/responses
class SendMessageRequest(BaseModel):
    receiver_id: str
    content: str

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    receiver_id: str
    content: str
    timestamp: str
    sender_username: str = None
    receiver_username: str = None

class ConversationResponse(BaseModel):
    conversation_id: str
    other_user_id: str
    other_user_username: str
    last_message: str = None
    last_message_timestamp: str = None
    is_other_user_online: bool = False

# Create router
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

def persist_message_to_db(message_data: Dict[str, Any]):
    """Background task to persist message to PostgreSQL"""
    db = SessionLocal()
    try:
        message = Message(
            id=message_data["id"],
            conversation_id=message_data["conversation_id"],
            sender_id=message_data["sender_id"],
            receiver_id=message_data["receiver_id"],
            content=message_data["content"],
            timestamp=datetime.fromisoformat(message_data["timestamp"])
        )
        db.add(message)
        db.commit()
    except Exception as e:
        print(f"Error persisting message to database: {e}")
        db.rollback()
    finally:
        db.close()

@chat_router.post("/send", response_model=MessageResponse)
def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to another user"""
    # Verify receiver exists
    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    # Add message to Redis
    message_data = chat_manager.add_message(
        sender_id=current_user.id,
        receiver_id=request.receiver_id,
        content=request.content
    )
    
    # Publish message for real-time delivery
    message_publisher.publish_message(request.receiver_id, message_data)
    
    # Schedule background persistence to PostgreSQL
    background_tasks.add_task(persist_message_to_db, message_data)
    
    # Update sender's online status
    chat_manager.set_user_online(current_user.id)
    
    return MessageResponse(
        **message_data,
        sender_username=current_user.username,
        receiver_username=receiver.username
    )

@chat_router.get("/history/{other_user_id}", response_model=List[MessageResponse])
def get_chat_history(
    other_user_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history with another user"""
    # Verify other user exists
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get recent messages from Redis first
    redis_messages = chat_manager.get_recent_messages(
        current_user.id, 
        other_user_id, 
        limit
    )
    
    # If we need more messages or Redis is empty, get from PostgreSQL
    if len(redis_messages) < limit:
        conversation_id = chat_manager.get_conversation_id(current_user.id, other_user_id)
        
        # Calculate how many more messages we need
        needed_count = limit - len(redis_messages)
        
        # Get older messages from PostgreSQL
        db_messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.timestamp)).limit(needed_count).all()
        
        # Convert DB messages to dict format
        db_message_dicts = []
        for msg in db_messages:
            db_message_dicts.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        # Combine and deduplicate by message ID, then sort by timestamp
        all_messages_dict = {}
        for msg in redis_messages + db_message_dicts:
            all_messages_dict[msg["id"]] = msg
        
        all_messages = list(all_messages_dict.values())
        all_messages.sort(key=lambda x: x["timestamp"])
    else:
        all_messages = redis_messages
    
    # Add usernames to response
    messages_with_usernames = []
    for msg in all_messages:
        sender = db.query(User).filter(User.id == msg["sender_id"]).first()
        receiver = db.query(User).filter(User.id == msg["receiver_id"]).first()
        
        messages_with_usernames.append(MessageResponse(
            **msg,
            sender_username=sender.username if sender else "Unknown",
            receiver_username=receiver.username if receiver else "Unknown"
        ))
    
    # Update user's online status
    chat_manager.set_user_online(current_user.id)
    
    return messages_with_usernames

@chat_router.get("/conversations", response_model=List[ConversationResponse])
def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user"""
    conversation_ids = chat_manager.get_user_conversations(current_user.id)
    conversations = []
    
    for conv_id in conversation_ids:
        # Extract other user ID from conversation ID
        user_ids = conv_id.split("_")
        other_user_id = user_ids[1] if user_ids[0] == current_user.id else user_ids[0]
        
        # Get other user info
        other_user = db.query(User).filter(User.id == other_user_id).first()
        if not other_user:
            continue
        
        # Get last message from Redis
        recent_messages = chat_manager.get_recent_messages(current_user.id, other_user_id, 1)
        last_message = None
        last_timestamp = None
        
        if recent_messages:
            last_msg = recent_messages[-1]
            last_message = last_msg["content"]
            last_timestamp = last_msg["timestamp"]
        else:
            # Fallback to database for last message
            last_db_message = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).order_by(desc(Message.timestamp)).first()
            
            if last_db_message:
                last_message = last_db_message.content
                last_timestamp = last_db_message.timestamp.isoformat()
        
        # Check if other user is online
        is_online = chat_manager.is_user_online(other_user_id)
        
        conversations.append(ConversationResponse(
            conversation_id=conv_id,
            other_user_id=other_user_id,
            other_user_username=other_user.username,
            last_message=last_message,
            last_message_timestamp=last_timestamp,
            is_other_user_online=is_online
        ))
    
    # Update user's online status
    chat_manager.set_user_online(current_user.id)
    
    return conversations

@chat_router.get("/online-status/{user_id}")
def get_user_online_status(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check if a user is online"""
    is_online = chat_manager.is_user_online(user_id)
    return {"user_id": user_id, "is_online": is_online}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        # Mark user as online when they connect
        chat_manager.set_user_online(user_id)
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(message)
                return True
            except Exception:
                # Connection is stale, remove it
                self.disconnect(user_id)
                return False
        return False

manager = ConnectionManager()

@chat_router.websocket("/subscribe")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with authentication"""
    user_id = None
    try:
        # Get and validate token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
            return
        
        # Validate JWT token
        try:
            from .auth import verify_token
            token_data = verify_token(token)
            user_id = token_data.user_id
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
            return
        
        await manager.connect(websocket, user_id)
        
        # Subscribe to Redis pub/sub for this user
        pubsub = redis_config.pubsub_client.pubsub()
        pubsub.subscribe(f"user:{user_id}:messages")
        
        try:
            heartbeat_counter = 0
            while True:
                # Check for new messages from Redis
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    # Forward Redis message to WebSocket
                    await websocket.send_text(message['data'].decode('utf-8'))
                
                # Send heartbeat every 30 seconds and extend online status
                heartbeat_counter += 1
                if heartbeat_counter >= 30:  # 30 seconds (1 sec timeout * 30)
                    chat_manager.extend_user_online(user_id)
                    heartbeat_counter = 0
                    
                    # Send heartbeat ping to keep connection alive
                    try:
                        await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
                    except Exception:
                        # Connection is dead, break out
                        break
                
        except WebSocketDisconnect:
            pass
        finally:
            pubsub.unsubscribe(f"user:{user_id}:messages")
            pubsub.close()
            manager.disconnect(user_id)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(user_id)
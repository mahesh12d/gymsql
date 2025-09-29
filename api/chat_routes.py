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
from .models import User, Message, Conversation
from .auth import get_current_user
from .redis_config import chat_manager, message_publisher, redis_config
from .message_persistence import enhanced_add_message, enhanced_get_messages

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

def get_or_create_conversation(user1_id: str, user2_id: str, db: Session) -> str:
    """Get or create a conversation between two users"""
    # Sort user IDs to ensure consistent conversation ID format
    sorted_users = sorted([user1_id, user2_id])
    conversation_id = f"{sorted_users[0]}_{sorted_users[1]}"
    
    # Check if conversation already exists
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            id=conversation_id,
            user1_id=sorted_users[0],
            user2_id=sorted_users[1]
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    return conversation.id

def persist_message_to_db(message_data: Dict[str, Any]):
    """Background task to persist message to PostgreSQL"""
    db = SessionLocal()
    try:
        # Ensure conversation exists before creating message
        conversation_id = get_or_create_conversation(
            message_data["sender_id"], 
            message_data["receiver_id"], 
            db
        )
        
        # Create message with the proper conversation_id
        message = Message(
            id=message_data["id"],
            conversation_id=conversation_id,
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
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to another user with dual Redis/PostgreSQL persistence"""
    # Verify receiver exists
    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    try:
        # Use enhanced message adding with automatic persistence
        message_data = await enhanced_add_message(
            sender_id=current_user.id,
            receiver_id=request.receiver_id,
            content=request.content
        )
        
        # Publish message for real-time delivery
        message_publisher.publish_message(request.receiver_id, message_data)
        
        # Update sender's online status
        chat_manager.set_user_online(current_user.id)
        
        return MessageResponse(
            **message_data,
            sender_username=current_user.username,
            receiver_username=receiver.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@chat_router.get("/history/{other_user_id}", response_model=List[MessageResponse])
async def get_chat_history(
    other_user_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history with another user using enhanced message retrieval"""
    # Verify other user exists
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Use enhanced message retrieval with automatic fallback
        all_messages = await enhanced_get_messages(
            current_user.id, 
            other_user_id, 
            limit
        )
        
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
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )

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
        
        # Validate JWT token with development bypass
        try:
            import os
            
            # TEMPORARY: Development token bypass - only in explicit dev mode  
            if os.getenv("DEV_TOKEN_BYPASS") == "true" and token == 'dev-token-123':
                user_id = 'dev-user-1'
            else:
                # Normal JWT verification for production
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
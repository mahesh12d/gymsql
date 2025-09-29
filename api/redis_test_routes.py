"""
Test routes for Redis integration
"""
from fastapi import APIRouter, HTTPException, status
from .redis_config import redis_config, chat_manager, queue_manager

# Create router
test_router = APIRouter(prefix="/api/redis-test", tags=["redis-test"])

@test_router.get("/connection")
def test_redis_connection():
    """Test Redis connection"""
    try:
        if redis_config.test_connection():
            return {
                "status": "success",
                "message": "Redis connection successful",
                "redis_info": {
                    "ping": "pong"
                }
            }
        else:
            return {
                "status": "error", 
                "message": "Redis connection failed"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Redis test failed: {str(e)}"
        }

@test_router.get("/chat-test")
def test_chat_functions():
    """Test chat Redis functions"""
    try:
        # Test setting user online
        chat_manager.set_user_online("test_user_1")
        is_online = chat_manager.is_user_online("test_user_1")
        
        # Test adding a message
        message_data = chat_manager.add_message(
            sender_id="test_user_1",
            receiver_id="test_user_2", 
            content="Test message from Redis"
        )
        
        # Test getting messages
        messages = chat_manager.get_recent_messages("test_user_1", "test_user_2", 10)
        
        return {
            "status": "success",
            "message": "Chat functions working",
            "tests": {
                "user_online": is_online,
                "message_added": message_data is not None,
                "messages_retrieved": len(messages),
                "last_message": messages[-1] if messages else None
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Chat test failed: {str(e)}"
        }

@test_router.get("/queue-test")
def test_queue_functions():
    """Test problem queue Redis functions"""
    try:
        # Test submitting a job
        job_id = queue_manager.submit_problem(
            user_id="test_user_1",
            problem_id="test_problem_1",
            sql_query="SELECT 1 as test"
        )
        
        # Test getting queue length
        queue_length = queue_manager.redis.llen("problems:queue")
        
        # Test job status
        status_info = queue_manager.get_job_status(job_id)
        
        return {
            "status": "success", 
            "message": "Queue functions working",
            "tests": {
                "job_submitted": job_id is not None,
                "job_id": job_id,
                "queue_length": queue_length,
                "job_status": status_info
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Queue test failed: {str(e)}"
        }

@test_router.get("/cleanup-test-data")
def cleanup_test_data():
    """Clean up test data from Redis"""
    try:
        # Clean up test chat data
        redis_config.redis_client.delete("chat:test_user_1_test_user_2:messages")
        redis_config.redis_client.delete("user:test_user_1:conversations")
        redis_config.redis_client.delete("user:test_user_2:conversations") 
        redis_config.redis_client.delete("user:test_user_1:online")
        
        # Clean up test queue data
        redis_config.redis_client.delete("problems:queue")
        
        return {
            "status": "success",
            "message": "Test data cleaned up"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Cleanup failed: {str(e)}"
        }
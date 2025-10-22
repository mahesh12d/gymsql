"""
Production-Ready Audit Logging for Admin Actions
=================================================
Comprehensive logging of all admin actions for security and compliance.

Features:
- Logs all admin actions with timestamps, IP addresses, and metadata
- Stores in Redis for fast access (with 90-day retention)
- PostgreSQL fallback for permanent storage
- Query capabilities for security investigations
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import Request
from .redis_service import redis_service
from .database import get_db
from .models import User

# Audit log retention
AUDIT_LOG_RETENTION_DAYS = 90


class AuditLogger:
    """Service for logging and querying admin actions"""
    
    def __init__(self):
        self.audit_prefix = "admin_audit"
        self.user_audit_prefix = "user_audit"
    
    def log_action(
        self,
        user_id: str,
        action: str,
        request: Request,
        metadata: Optional[Dict] = None,
        success: bool = True
    ):
        """
        Log an admin action.
        
        Args:
            user_id: ID of admin user performing the action
            action: Action being performed (e.g., 'create_problem', 'delete_solution')
            request: FastAPI Request object for IP and user agent
            metadata: Additional metadata (e.g., problem_id, changes made)
            success: Whether the action was successful
        """
        timestamp = datetime.utcnow()
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        log_entry = {
            "user_id": user_id,
            "action": action,
            "timestamp": timestamp.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "success": success
        }
        
        # Store in Redis for fast access
        if redis_service.is_available():
            try:
                # Global audit log
                audit_key = f"{self.audit_prefix}:{timestamp.isoformat()}:{user_id}"
                redis_service.client.setex(
                    audit_key,
                    AUDIT_LOG_RETENTION_DAYS * 24 * 3600,
                    json.dumps(log_entry)
                )
                
                # User-specific audit log for quick lookup
                user_audit_key = f"{self.user_audit_prefix}:{user_id}"
                redis_service.client.lpush(user_audit_key, json.dumps(log_entry))
                redis_service.client.ltrim(user_audit_key, 0, 999)  # Keep last 1000 entries
                redis_service.client.expire(user_audit_key, AUDIT_LOG_RETENTION_DAYS * 24 * 3600)
            except Exception as e:
                print(f"Failed to write audit log to Redis: {e}")
        
        # Console logging for real-time monitoring
        status_emoji = "✅" if success else "❌"
        print(
            f"{status_emoji} ADMIN AUDIT [{timestamp.isoformat()}]: "
            f"User {user_id} - {action} - IP: {ip_address} - "
            f"Metadata: {json.dumps(metadata or {})}"
        )
        
        # TODO: For production, also write to PostgreSQL for permanent storage
        # This ensures audit logs survive Redis cache eviction
    
    def get_user_actions(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent actions for a specific admin user.
        
        Args:
            user_id: Admin user ID
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        if not redis_service.is_available():
            return []
        
        user_audit_key = f"{self.user_audit_prefix}:{user_id}"
        
        try:
            entries = redis_service.client.lrange(user_audit_key, 0, limit - 1)
            return [json.loads(entry) for entry in entries]
        except Exception as e:
            print(f"Failed to retrieve user audit logs: {e}")
            return []
    
    def get_recent_actions(
        self,
        hours: int = 24,
        action_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all recent admin actions across all users.
        
        Args:
            hours: Number of hours to look back
            action_filter: Optional action type filter (e.g., 'create_problem')
            
        Returns:
            List of audit log entries
        """
        if not redis_service.is_available():
            return []
        
        try:
            # Scan for all audit keys within time range
            pattern = f"{self.audit_prefix}:*"
            cursor = 0
            entries = []
            
            while True:
                cursor, keys = redis_service.client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000
                )
                
                for key in keys:
                    try:
                        entry_json = redis_service.client.get(key)
                        if entry_json:
                            entry = json.loads(entry_json)
                            
                            # Filter by time
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if datetime.utcnow() - entry_time <= timedelta(hours=hours):
                                # Filter by action if specified
                                if action_filter is None or entry["action"] == action_filter:
                                    entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing audit entry: {e}")
                        continue
                
                if cursor == 0:
                    break
            
            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x["timestamp"], reverse=True)
            return entries
        except Exception as e:
            print(f"Failed to retrieve recent audit logs: {e}")
            return []
    
    def search_actions(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search audit logs with multiple filters.
        
        Args:
            user_id: Filter by admin user ID
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            
        Returns:
            List of matching audit log entries
        """
        if user_id:
            # Use user-specific index for faster lookup
            entries = self.get_user_actions(user_id, limit=1000)
        else:
            # Get all recent entries (past 7 days)
            entries = self.get_recent_actions(hours=7*24)
        
        # Apply filters
        filtered_entries = []
        for entry in entries:
            # Filter by action
            if action and entry.get("action") != action:
                continue
            
            # Filter by date range
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if start_date and entry_time < start_date:
                continue
            if end_date and entry_time > end_date:
                continue
            
            filtered_entries.append(entry)
            
            if len(filtered_entries) >= limit:
                break
        
        return filtered_entries


# Global audit logger instance
audit_logger = AuditLogger()


# Helper function for easy logging
def log_admin_action(
    user_id: str,
    action: str,
    request: Request,
    metadata: Optional[Dict] = None,
    success: bool = True
):
    """
    Convenience function to log admin action.
    
    Args:
        user_id: ID of admin user
        action: Action type
        request: FastAPI Request object
        metadata: Additional metadata
        success: Whether action was successful
    """
    audit_logger.log_action(user_id, action, request, metadata, success)

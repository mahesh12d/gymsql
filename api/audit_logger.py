"""
Production-Ready Audit Logging for Admin Actions (PostgreSQL-based)
====================================================================
Comprehensive logging of all admin actions for security and compliance.

Features:
- Logs all admin actions with timestamps, IP addresses, and metadata
- Stores in PostgreSQL for permanent, queryable storage
- 90-day automatic retention (configurable)
- Fast queries with proper indexing
- Graceful degradation when database tables don't exist (development mode)
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, inspect

# Audit log retention
AUDIT_LOG_RETENTION_DAYS = 90


class AuditLogger:
    """PostgreSQL-based audit logging service with graceful degradation"""
    
    def _table_exists(self, db: Session) -> bool:
        """Check if audit log table exists in the database."""
        try:
            inspector = inspect(db.bind)
            return 'admin_audit_logs' in inspector.get_table_names()
        except Exception:
            return False
    
    def log_action(
        self,
        user_id: str,
        action: str,
        request: Request,
        db: Session,
        metadata: Optional[Dict] = None,
        success: bool = True
    ):
        """
        Log an admin action to PostgreSQL.
        
        Args:
            user_id: ID of admin user performing the action
            action: Action being performed (e.g., 'create_problem', 'delete_solution')
            request: FastAPI Request object for IP and user agent
            db: Database session
            metadata: Additional metadata (e.g., problem_id, changes made)
            success: Whether the action was successful
        """
        timestamp = datetime.utcnow()
        ip_address = request.client.host if request.client else "unknown"
        
        # Console logging always happens (even if tables don't exist)
        status_emoji = "✅" if success else "❌"
        print(
            f"{status_emoji} ADMIN AUDIT [{timestamp.isoformat()}]: "
            f"User {user_id} - {action} - IP: {ip_address} - "
            f"Metadata: {json.dumps(metadata or {})}"
        )
        
        # Graceful degradation: if table doesn't exist, only log to console
        if not self._table_exists(db):
            print(f"⚠️  Audit logger: Table not found, audit log not persisted to database (development mode)")
            return
            
        from .models import AdminAuditLog
        import uuid
        
        user_agent = request.headers.get("user-agent", "unknown")
        
        log_entry = AdminAuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            action_metadata=metadata or {},
            success=success,
            created_at=timestamp
        )
        
        try:
            db.add(log_entry)
            db.commit()
            
            # Periodic cleanup of old logs (runs every ~100 logs)
            import random
            if random.randint(1, 100) == 1:
                self._cleanup_old_logs(db)
                
        except Exception as e:
            db.rollback()
            print(f"⚠️  Audit logger: Failed to write audit log to database: {e}")
    
    def get_user_actions(
        self,
        user_id: str,
        db: Session,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent actions for a specific admin user.
        
        Args:
            user_id: Admin user ID
            db: Database session
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        from .models import AdminAuditLog
        
        try:
            logs = db.query(AdminAuditLog).filter(
                AdminAuditLog.user_id == user_id
            ).order_by(desc(AdminAuditLog.created_at)).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": log.action_metadata,
                    "success": log.success,
                    "timestamp": log.created_at.isoformat()
                }
                for log in logs
            ]
        except Exception as e:
            print(f"Failed to retrieve user audit logs: {e}")
            return []
    
    def get_recent_actions(
        self,
        db: Session,
        hours: int = 24,
        action_filter: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get all recent admin actions across all users.
        
        Args:
            db: Database session
            hours: Number of hours to look back
            action_filter: Optional action type filter (e.g., 'create_problem')
            limit: Maximum number of results
            
        Returns:
            List of audit log entries
        """
        from .models import AdminAuditLog
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = db.query(AdminAuditLog).filter(
                AdminAuditLog.created_at >= cutoff_time
            )
            
            if action_filter:
                query = query.filter(AdminAuditLog.action == action_filter)
            
            logs = query.order_by(desc(AdminAuditLog.created_at)).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": log.action_metadata,
                    "success": log.success,
                    "timestamp": log.created_at.isoformat()
                }
                for log in logs
            ]
        except Exception as e:
            print(f"Failed to retrieve recent audit logs: {e}")
            return []
    
    def search_actions(
        self,
        db: Session,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search audit logs with multiple filters.
        
        Args:
            db: Database session
            user_id: Filter by admin user ID
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            
        Returns:
            List of matching audit log entries
        """
        from .models import AdminAuditLog
        
        try:
            query = db.query(AdminAuditLog)
            
            if user_id:
                query = query.filter(AdminAuditLog.user_id == user_id)
            
            if action:
                query = query.filter(AdminAuditLog.action == action)
            
            if start_date:
                query = query.filter(AdminAuditLog.created_at >= start_date)
            
            if end_date:
                query = query.filter(AdminAuditLog.created_at <= end_date)
            
            logs = query.order_by(desc(AdminAuditLog.created_at)).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": log.action_metadata,
                    "success": log.success,
                    "timestamp": log.created_at.isoformat()
                }
                for log in logs
            ]
        except Exception as e:
            print(f"Failed to search audit logs: {e}")
            return []
    
    def _cleanup_old_logs(self, db: Session):
        """Clean up audit logs older than retention period"""
        from .models import AdminAuditLog
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
            deleted_count = db.query(AdminAuditLog).filter(
                AdminAuditLog.created_at < cutoff_date
            ).delete()
            
            if deleted_count > 0:
                db.commit()
                print(f"🧹 Cleaned up {deleted_count} old audit log entries")
        except Exception as e:
            db.rollback()
            print(f"Failed to cleanup old audit logs: {e}")


# Global audit logger instance
audit_logger = AuditLogger()


# Helper function for easy logging (with db session)
def log_admin_action(
    user_id: str,
    action: str,
    request: Request,
    db: Session,
    metadata: Optional[Dict] = None,
    success: bool = True
):
    """
    Convenience function to log admin action.
    
    Args:
        user_id: ID of admin user
        action: Action type
        request: FastAPI Request object
        db: Database session
        metadata: Additional metadata
        success: Whether action was successful
    """
    audit_logger.log_action(user_id, action, request, db, metadata, success)

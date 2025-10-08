"""
Data retention policy for execution_results table.
Deletes execution results older than 6 months while preserving submission records.
"""
from datetime import datetime, timedelta
from sqlalchemy import delete
from sqlalchemy.orm import Session
from .database import get_db
from .models import ExecutionResult
import logging

logger = logging.getLogger(__name__)

def cleanup_old_execution_results(db: Session, retention_days: int = 180) -> int:
    """
    Delete execution_results older than the specified retention period.
    
    Args:
        db: Database session
        retention_days: Number of days to retain (default: 180 days / 6 months)
    
    Returns:
        Number of records deleted
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    try:
        # Delete execution_results older than cutoff date
        result = db.execute(
            delete(ExecutionResult)
            .where(ExecutionResult.created_at < cutoff_date)
        )
        db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Data retention cleanup: Deleted {deleted_count} execution_results older than {cutoff_date}")
        
        return deleted_count
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error during execution_results cleanup: {str(e)}")
        raise

def get_execution_results_stats(db: Session) -> dict:
    """
    Get statistics about execution_results storage.
    
    Returns:
        Dictionary with total count, old count, and estimated space saved
    """
    cutoff_date = datetime.now() - timedelta(days=180)
    
    total_count = db.query(ExecutionResult).count()
    old_count = db.query(ExecutionResult).filter(
        ExecutionResult.created_at < cutoff_date
    ).count()
    
    return {
        "total_execution_results": total_count,
        "execution_results_older_than_6_months": old_count,
        "retention_policy": "6 months",
        "cutoff_date": cutoff_date.isoformat()
    }

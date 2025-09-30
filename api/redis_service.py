"""
Redis service for caching, job queuing, and leaderboards
"""
import os
import json
import redis
from typing import Optional, Dict, List, Any
from datetime import timedelta
import uuid

class RedisService:
    def __init__(self):
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            self.client = None
            print("⚠️  REDIS_URL not configured - Redis features disabled")
            return
            
        try:
            self.client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            self.client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e} - Features disabled")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.client is not None
    
    # ==================== RESULT CACHING ====================
    
    def get_cached_result(self, cache_key: str, namespace: str = "result") -> Optional[Dict]:
        """
        Get cached result using a full cache key.
        Args:
            cache_key: Full cache key (e.g., user:123:problem:456:hash:abc)
            namespace: Namespace prefix (default: result)
        Returns None if not found or Redis unavailable.
        """
        if not self.is_available():
            return None
            
        try:
            key = f"cache:{namespace}:{cache_key}"
            cached = self.client.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            print(f"Redis cache get error: {e}")
            return None
    
    def cache_result(self, cache_key: str, namespace: str, result: Dict, ttl_seconds: int = 600):
        """
        Cache result with TTL using a full cache key.
        Args:
            cache_key: Full cache key (e.g., user:123:problem:456:hash:abc)
            namespace: Namespace prefix
            result: Result data to cache
            ttl_seconds: Time-to-live in seconds (default 10 minutes)
        """
        if not self.is_available():
            return
            
        try:
            key = f"cache:{namespace}:{cache_key}"
            self.client.setex(
                key,
                ttl_seconds,
                json.dumps(result)
            )
        except Exception as e:
            print(f"Redis cache set error: {e}")
    
    def invalidate_cache(self, cache_key: str, namespace: str = "result"):
        """Invalidate cached result using full cache key"""
        if not self.is_available():
            return
            
        try:
            key = f"cache:{namespace}:{cache_key}"
            self.client.delete(key)
        except Exception as e:
            print(f"Redis cache invalidate error: {e}")
    
    # ==================== JOB QUEUE ====================
    
    def enqueue_submission(self, user_id: str, problem_id: str, sql_query: str) -> str:
        """
        Add SQL submission to job queue.
        Returns job_id for tracking.
        """
        if not self.is_available():
            raise Exception("Redis unavailable - cannot queue submission")
            
        try:
            job_id = str(uuid.uuid4())
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "problem_id": problem_id,
                "sql": sql_query
            }
            
            # Push to queue
            self.client.lpush("problems:queue", json.dumps(job_data))
            
            # Mark as queued
            self.client.hset(
                f"problems:job:{job_id}",
                mapping={
                    "status": "queued",
                    "user_id": user_id,
                    "problem_id": problem_id
                }
            )
            self.client.expire(f"problems:job:{job_id}", 3600)  # 1 hour TTL
            
            return job_id
        except Exception as e:
            raise Exception(f"Failed to enqueue submission: {e}")
    
    def get_job_from_queue(self, timeout: int = 5) -> Optional[Dict]:
        """
        Worker: Get next job from queue (blocking).
        Returns job data or None if timeout.
        """
        if not self.is_available():
            return None
            
        try:
            result = self.client.brpop("problems:queue", timeout=timeout)
            if result:
                _, job_json = result
                return json.loads(job_json)
            return None
        except Exception as e:
            print(f"Redis queue get error: {e}")
            return None
    
    def mark_job_processing(self, job_id: str, user_id: str, problem_id: str):
        """Mark job as processing"""
        if not self.is_available():
            return
            
        try:
            self.client.hset(
                f"problems:job:{job_id}",
                mapping={
                    "status": "processing",
                    "user_id": user_id,
                    "problem_id": problem_id
                }
            )
        except Exception as e:
            print(f"Redis job update error: {e}")
    
    def store_job_result(self, job_id: str, result: Dict, ttl_seconds: int = 300):
        """
        Store job result with TTL (default 5 minutes).
        Format: problems:result:{job_id}
        """
        if not self.is_available():
            return
            
        try:
            key = f"problems:result:{job_id}"
            self.client.setex(key, ttl_seconds, json.dumps(result))
            
            # Update job status
            self.client.hset(f"problems:job:{job_id}", "status", "completed")
        except Exception as e:
            print(f"Redis result store error: {e}")
    
    def get_job_result(self, job_id: str) -> Optional[Dict]:
        """Get job result by job_id"""
        if not self.is_available():
            return None
            
        try:
            key = f"problems:result:{job_id}"
            result = self.client.get(key)
            if result:
                return json.loads(result)
            return None
        except Exception as e:
            print(f"Redis result get error: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get current job status"""
        if not self.is_available():
            return None
            
        try:
            return self.client.hget(f"problems:job:{job_id}", "status")
        except Exception as e:
            print(f"Redis job status error: {e}")
            return None
    
    # ==================== LEADERBOARDS ====================
    
    def increment_leaderboard(self, user_id: str, problem_id: str, score: int = 1, topic: Optional[str] = None):
        """
        Increment user score on global and/or topic-specific leaderboard.
        Uses Redis Sorted Sets for O(log N) performance.
        Made idempotent with SADD to prevent race condition double-counts.
        """
        if not self.is_available():
            return
            
        try:
            # Check if this problem was already solved by user (idempotency check)
            solve_key = f"solved:{user_id}"
            was_added = self.client.sadd(solve_key, problem_id)
            
            # Only increment if this is the first time solving this problem
            if was_added:
                # Global leaderboard
                self.client.zincrby("leaderboard:global", score, f"user:{user_id}")
                
                # Topic-specific leaderboard
                if topic:
                    self.client.zincrby(f"leaderboard:topic:{topic}", score, f"user:{user_id}")
                
                return True  # Incremented
            return False  # Already solved, no increment
        except Exception as e:
            print(f"Redis leaderboard increment error: {e}")
            return False
    
    def get_global_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Get top N users from global leaderboard.
        Returns list of {user_id, score} sorted by score descending.
        """
        if not self.is_available():
            return []
            
        try:
            results = self.client.zrevrange(
                "leaderboard:global",
                0,
                limit - 1,
                withscores=True
            )
            
            leaderboard = []
            for member, score in results:
                user_id = member.replace("user:", "")
                leaderboard.append({
                    "user_id": user_id,
                    "score": int(score)
                })
            return leaderboard
        except Exception as e:
            print(f"Redis leaderboard get error: {e}")
            return []
    
    def get_topic_leaderboard(self, topic: str, limit: int = 10) -> List[Dict]:
        """Get top N users for specific topic"""
        if not self.is_available():
            return []
            
        try:
            results = self.client.zrevrange(
                f"leaderboard:topic:{topic}",
                0,
                limit - 1,
                withscores=True
            )
            
            leaderboard = []
            for member, score in results:
                user_id = member.replace("user:", "")
                leaderboard.append({
                    "user_id": user_id,
                    "score": int(score)
                })
            return leaderboard
        except Exception as e:
            print(f"Redis topic leaderboard error: {e}")
            return []
    
    def get_user_rank(self, user_id: str, topic: Optional[str] = None) -> Optional[Dict]:
        """
        Get user's rank and score.
        Returns {rank, score} or None if not found.
        """
        if not self.is_available():
            return None
            
        try:
            key = f"leaderboard:topic:{topic}" if topic else "leaderboard:global"
            member = f"user:{user_id}"
            
            rank = self.client.zrevrank(key, member)
            score = self.client.zscore(key, member)
            
            if rank is not None and score is not None:
                return {
                    "rank": rank + 1,  # Redis rank is 0-indexed
                    "score": int(score)
                }
            return None
        except Exception as e:
            print(f"Redis user rank error: {e}")
            return None
    
    def sync_leaderboard_from_db(self, user_scores: List[Dict]):
        """
        Sync leaderboard from database (for initialization/rebuild).
        user_scores: [{"user_id": "123", "score": 45}, ...]
        """
        if not self.is_available():
            return
            
        try:
            # Clear existing global leaderboard
            self.client.delete("leaderboard:global")
            
            # Rebuild from database
            for user_data in user_scores:
                user_id = user_data["user_id"]
                score = user_data["score"]
                self.client.zadd("leaderboard:global", {f"user:{user_id}": score})
                
            print(f"✅ Leaderboard synced: {len(user_scores)} users")
        except Exception as e:
            print(f"Redis leaderboard sync error: {e}")
    
    def sync_solved_sets(self, solved_problems: List[Dict]):
        """
        Rebuild solved problem sets for idempotency.
        solved_problems: [{"user_id": "123", "problem_id": "456"}, ...]
        """
        if not self.is_available():
            return
            
        try:
            # Clear existing solved sets (optional, for clean rebuild)
            # Could also just add to existing sets
            
            # Rebuild solved sets
            for item in solved_problems:
                user_id = item["user_id"]
                problem_id = item["problem_id"]
                self.client.sadd(f"solved:{user_id}", problem_id)
                
            print(f"✅ Solved sets synced: {len(solved_problems)} submissions")
        except Exception as e:
            print(f"Redis solved sets sync error: {e}")

# Global Redis instance
redis_service = RedisService()

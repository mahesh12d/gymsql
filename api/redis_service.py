"""
Redis service for caching, job queuing, and leaderboards
"""
import os
import json
import redis
import time
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
    
    # ==================== RATE LIMITING ====================
    
    # In-memory fallback rate limiter (when Redis is unavailable)
    _in_memory_rate_limits = {}
    
    def _check_in_memory_rate_limit(self, user_id: str, action: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """Fallback in-memory rate limiter using sliding window"""
        key = f"{action}:{user_id}"
        now = time.time()
        
        if key not in self._in_memory_rate_limits:
            self._in_memory_rate_limits[key] = []
        
        # Clean old entries
        self._in_memory_rate_limits[key] = [
            ts for ts in self._in_memory_rate_limits[key]
            if ts > now - window_seconds
        ]
        
        current_count = len(self._in_memory_rate_limits[key])
        
        if current_count >= limit:
            oldest = min(self._in_memory_rate_limits[key])
            retry_after = int(oldest + window_seconds - now)
            return {
                "allowed": False,
                "retry_after": max(1, retry_after),
                "remaining": 0,
                "limit": limit
            }
        
        # Record this request
        self._in_memory_rate_limits[key].append(now)
        
        return {
            "allowed": True,
            "retry_after": 0,
            "remaining": limit - current_count - 1,
            "limit": limit
        }
    
    def check_rate_limit(self, user_id: str, action: str = "submit", limit: int = 10, window_seconds: int = 60) -> Dict[str, Any]:
        """
        Check if user has exceeded rate limit using sliding window with atomic Lua script.
        Args:
            user_id: User ID to check
            action: Action type (e.g., 'submit')
            limit: Max actions allowed in window
            window_seconds: Time window in seconds
        Returns:
            Dict with 'allowed' (bool) and 'retry_after' (int seconds)
        """
        if not self.is_available():
            # Use in-memory fallback when Redis unavailable
            print(f"⚠️  Redis unavailable - using in-memory rate limiting for {action} user {user_id}")
            return self._check_in_memory_rate_limit(user_id, action, limit, window_seconds)
        
        try:
            key = f"ratelimit:{action}:{user_id}"
            now = time.time()
            window_start = now - window_seconds
            member = str(uuid.uuid4())
            
            # Lua script for atomic rate limit check
            # Only adds the request if under limit
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            local window_seconds = tonumber(ARGV[4])
            local member = ARGV[5]
            
            -- Remove old entries
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
            
            -- Count current entries
            local current_count = redis.call('ZCARD', key)
            
            if current_count >= limit then
                -- Rate limit exceeded - get oldest for retry calculation
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local retry_after = 1
                if oldest[2] then
                    retry_after = math.max(1, math.ceil(tonumber(oldest[2]) + window_seconds - now))
                end
                return {0, retry_after, 0, limit}  -- allowed=false, retry_after, remaining=0
            else
                -- Under limit - record this request
                redis.call('ZADD', key, now, member)
                redis.call('EXPIRE', key, window_seconds)
                return {1, 0, limit - current_count - 1, limit}  -- allowed=true, retry_after=0, remaining
            end
            """
            
            result = self.client.eval(
                lua_script,
                1,  # number of keys
                key,  # KEYS[1]
                now, window_start, limit, window_seconds, member  # ARGV
            )
            
            allowed, retry_after, remaining, limit_val = result
            
            return {
                "allowed": bool(allowed),
                "retry_after": int(retry_after),
                "remaining": int(remaining),
                "limit": int(limit_val)
            }
            
        except Exception as e:
            print(f"Rate limit check error: {e}")
            # On error, use in-memory fallback
            return self._check_in_memory_rate_limit(user_id, action, limit, window_seconds)
    
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
    
    def get_job_from_queue(self, timeout: int = 5) -> Optional[tuple]:
        """
        Worker: Get next job from queue (blocking) using BRPOPLPUSH for reliability.
        Atomically moves job from queue to processing list to prevent job loss on crashes.
        Returns tuple of (job_data, job_json) or None if timeout.
        The job_json is returned to ensure exact match for LREM in complete_job().
        """
        if not self.is_available():
            return None
            
        try:
            # Use BRPOPLPUSH to atomically move job to processing list
            job_json = self.client.brpoplpush(
                "problems:queue", 
                "problems:processing", 
                timeout=timeout
            )
            
            if job_json:
                job_data = json.loads(job_json)
                return (job_data, job_json)  # Return both for exact matching
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
    
    def complete_job(self, job_json: str):
        """
        Remove completed job from processing list.
        Should be called after job is successfully processed.
        """
        if not self.is_available():
            return
            
        try:
            # Remove this specific job from the processing list
            self.client.lrem("problems:processing", 1, job_json)
        except Exception as e:
            print(f"Redis job completion error: {e}")
    
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
    
    def get_job_owner(self, job_id: str) -> Optional[str]:
        """Get job owner user_id for authorization checks"""
        if not self.is_available():
            return None
            
        try:
            user_id = self.client.hget(f"problems:job:{job_id}", "user_id")
            # Handle both str and bytes return types
            if isinstance(user_id, bytes):
                user_id = user_id.decode('utf-8')
            return str(user_id) if user_id else None
        except Exception as e:
            print(f"Redis job owner get error: {e}")
            return None
    
    def recover_orphaned_jobs(self) -> int:
        """
        Recover orphaned jobs from processing list on worker startup.
        These are jobs that were being processed when a worker crashed.
        Uses a lock to prevent race conditions with multiple workers.
        Returns the number of jobs recovered.
        """
        if not self.is_available():
            return 0
            
        try:
            # Acquire lock to prevent multiple workers from recovering at the same time
            lock_key = "lock:orphan_recovery"
            lock_acquired = self.client.set(lock_key, "1", nx=True, ex=30)  # 30 second TTL
            
            if not lock_acquired:
                print("⏳ Another worker is recovering orphaned jobs, skipping...")
                return 0
            
            try:
                # Get all jobs from processing list
                processing_jobs = self.client.lrange("problems:processing", 0, -1)
                
                if not processing_jobs:
                    return 0
                
                recovered_count = 0
                
                for job_json in processing_jobs:
                    try:
                        job_data = json.loads(job_json)
                        job_id = job_data.get('job_id')
                        
                        # Check if job still exists and is marked as processing
                        job_status = self.get_job_status(job_id)
                        
                        if job_status == "processing" or job_status == "queued":
                            # Job was orphaned - move it back to queue
                            # Use atomic operation: remove from processing, add back to queue
                            pipe = self.client.pipeline()
                            pipe.lrem("problems:processing", 1, job_json)
                            pipe.lpush("problems:queue", job_json)
                            
                            # Reset job status to queued
                            pipe.hset(f"problems:job:{job_id}", "status", "queued")
                            pipe.execute()
                            
                            recovered_count += 1
                            print(f"♻️  Recovered orphaned job: {job_id}")
                        elif job_status == "completed" or job_status is None:
                            # Job was completed or expired - just remove from processing list (don't requeue)
                            self.client.lrem("problems:processing", 1, job_json)
                            print(f"🧹 Cleaned completed/expired job from processing list: {job_id}")
                        else:
                            # Unknown status - remove from processing list for safety
                            self.client.lrem("problems:processing", 1, job_json)
                            print(f"⚠️  Removed job with unknown status '{job_status}' from processing list: {job_id}")
                            
                    except json.JSONDecodeError:
                        # Invalid job data - remove it
                        self.client.lrem("problems:processing", 1, job_json)
                        print(f"⚠️  Removed invalid job from processing list")
                
                if recovered_count > 0:
                    print(f"✅ Recovered {recovered_count} orphaned job(s) from processing list")
                
                return recovered_count
            finally:
                # Always release the lock
                self.client.delete(lock_key)
            
        except Exception as e:
            print(f"Job recovery error: {e}")
            return 0
    
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

"""
Production-Ready Security Middleware
====================================
Security headers and middleware for protecting the application.

Features:
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Request logging for admin endpoints
- IP whitelisting capability
"""
from typing import Optional, List, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS for HTTPS (only in production)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy (adjust based on your needs)
        # This is a basic CSP - you may need to customize it
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict access to admin endpoints by IP address.
    Optional - only active if ADMIN_ALLOWED_IPS is set.
    """
    
    def __init__(self, app, allowed_ips: Optional[List[str]] = None):
        super().__init__(app)
        
        # Get allowed IPs from environment variable
        env_ips = os.getenv("ADMIN_ALLOWED_IPS", "").strip()
        
        if env_ips:
            self.allowed_ips: Set[str] = set(env_ips.split(","))
            self.enabled = True
            print(f"🔒 IP Whitelist ENABLED for admin endpoints: {self.allowed_ips}")
        elif allowed_ips:
            self.allowed_ips = set(allowed_ips)
            self.enabled = True
            print(f"🔒 IP Whitelist ENABLED for admin endpoints: {self.allowed_ips}")
        else:
            self.allowed_ips = set()
            self.enabled = False
            print("⚠️  IP Whitelist DISABLED - set ADMIN_ALLOWED_IPS to enable")
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to admin endpoints
        if not request.url.path.startswith("/api/admin"):
            return await call_next(request)
        
        # Skip if whitelist is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Check if IP is allowed
        if client_ip and client_ip not in self.allowed_ips:
            # Also check X-Forwarded-For header (for reverse proxies)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, take the first one
                forwarded_ip = forwarded_for.split(",")[0].strip()
                if forwarded_ip in self.allowed_ips:
                    return await call_next(request)
            
            print(f"🚫 SECURITY: Blocked admin access from unauthorized IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to admin panel is restricted to authorized IP addresses"
            )
        
        return await call_next(request)


class AdminRequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all admin endpoint requests for monitoring.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only log admin endpoints
        if request.url.path.startswith("/api/admin"):
            ip_address = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            print(
                f"📝 ADMIN REQUEST: {request.method} {request.url.path} "
                f"- IP: {ip_address} - User-Agent: {user_agent[:50]}"
            )
        
        response = await call_next(request)
        return response

"""Custom middleware for request handling."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from co.config import get_settings


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = {}
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get user ID from JWT (simplified - implement proper JWT extraction)
        user_id = request.headers.get("X-User-ID", "anonymous")
        
        current_time = time.time()
        window_start = current_time - self.settings.rate_limit_window
        
        # Clean old entries
        if user_id in self.requests:
            self.requests[user_id] = [
                ts for ts in self.requests[user_id] if ts > window_start
            ]
        else:
            self.requests[user_id] = []
        
        # Check rate limit
        if len(self.requests[user_id]) >= self.settings.rate_limit_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests",
                        "details": {
                            "retry_after": self.settings.rate_limit_window
                        }
                    }
                }
            )
        
        # Record request
        self.requests[user_id].append(current_time)
        
        return await call_next(request)
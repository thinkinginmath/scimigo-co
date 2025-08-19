"""Custom middleware for request handling."""

import time
import uuid
from typing import Awaitable, Callable

import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from co.config import get_settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract user ID from JWT and attach to request state."""

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
            try:
                payload = jwt.decode(
                    token,
                    self.settings.jwt_public_key or "secret",
                    algorithms=[self.settings.jwt_algorithm],
                    audience=self.settings.jwt_audience,
                    issuer=self.settings.jwt_issuer,
                )
                user_id = payload.get("sub")
                if not user_id:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid token: missing user ID"},
                    )
                request.state.user_id = user_id
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token has expired"},
                )
            except jwt.InvalidTokenError as exc:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": f"Invalid token: {exc}"},
                )
        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
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

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Get user ID from request state set by AuthMiddleware
        user_id = getattr(request.state, "user_id", "anonymous")

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
                        "details": {"retry_after": self.settings.rate_limit_window},
                    }
                },
            )

        # Record request
        self.requests[user_id].append(current_time)

        return await call_next(request)

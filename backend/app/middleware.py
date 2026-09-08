import time
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            client_ip = request.client.host
            now = time.time()

            # Remove expired timestamps
            self._requests[client_ip] = [
                t for t in self._requests[client_ip]
                if now - t < RATE_LIMIT_WINDOW
            ]

            if len(self._requests[client_ip]) >= RATE_LIMIT_REQUESTS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
                )

            self._requests[client_ip].append(now)

        return await call_next(request)

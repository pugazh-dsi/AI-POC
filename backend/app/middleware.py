import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP request cap, guarding the endpoints that cost money.

    Reading chat history is a local SQLite read, and the sidebar issues one per
    conversation the user opens — counting those would let ordinary browsing
    burn the budget meant for the LLM endpoints. Only GETs are exempt; creating,
    renaming and deleting conversations still counts.
    """

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _is_exempt(self, request: Request) -> bool:
        return request.method == "GET" and request.url.path.startswith("/api/chats")

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and not self._is_exempt(request):
            # request.client is None for some ASGI transports (e.g. test clients)
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()

            # Remove expired timestamps
            recent = [t for t in self._requests[client_ip] if now - t < RATE_LIMIT_WINDOW]

            if len(recent) >= RATE_LIMIT_REQUESTS:
                self._requests[client_ip] = recent
                # Must RETURN a response: an HTTPException raised inside
                # BaseHTTPMiddleware bypasses FastAPI's handlers and surfaces as a 500.
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds."
                    },
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
                )

            recent.append(now)
            self._requests[client_ip] = recent

            # Drop idle clients so the tracking dict doesn't grow without bound
            if len(self._requests) > 1000:
                self._requests = defaultdict(
                    list,
                    {ip: ts for ip, ts in self._requests.items() if ts},
                )

        return await call_next(request)

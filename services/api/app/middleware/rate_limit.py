from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window limiter keyed by API key (or remote IP).

    Good enough for single-process dev. Swap for Redis later.
    """

    def __init__(self, app, per_minute: int = 600) -> None:
        super().__init__(app)
        self.limit = per_minute
        self.window = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("X-GamePulse-Key") or (request.client.host if request.client else "anon")
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse({"detail": "rate_limited"}, status_code=429)
        bucket.append(now)
        return await call_next(request)

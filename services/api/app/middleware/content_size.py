from __future__ import annotations

from gamepulse_core.constants import MAX_PAYLOAD_BYTES
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds MAX_PAYLOAD_BYTES.

    Checked from the header only — no body buffering required.
    Returns HTTP 413 with a human-readable message.
    """

    def __init__(self, app, max_bytes: int = MAX_PAYLOAD_BYTES) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None and int(cl) > self.max_bytes:
            limit_kb = self.max_bytes // 1024
            return JSONResponse(
                {
                    "detail": (
                        f"Payload too large. Maximum request size is {self.max_bytes:,} bytes "
                        f"({limit_kb} KB). Split into smaller batches."
                    )
                },
                status_code=413,
            )
        return await call_next(request)

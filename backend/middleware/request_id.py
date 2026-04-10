"""
middleware/request_id.py
────────────────────────
Stamps every inbound request with a UUID request ID.

Behaviour:
  - Uses X-Request-ID from the incoming request if present (for end-to-end tracing).
  - Generates a UUID4 if the header is absent.
  - Stores the ID in core.logger._request_id (ContextVar) so it appears in all
    log lines emitted during that request.
  - Echoes the ID back in the response X-Request-ID header.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logger import _request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            _request_id.reset(token)

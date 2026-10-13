"""
Security response headers middleware.

Headers applied to every response:
  X-Content-Type-Options   → Prevent MIME-type sniffing (XSS vector)
  X-Frame-Options          → Prevent clickjacking via iframe embedding
  X-XSS-Protection         → Legacy XSS filter for older browsers
  Referrer-Policy          → Limit referrer information leakage
  Permissions-Policy       → Deny access to sensitive browser APIs
  Content-Security-Policy  → Whitelist trusted content sources
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(self), camera=(), payment=()"
        )
        connect_sources = " ".join(settings.cors_origins)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob: https://fonts.googleapis.com https://www.gstatic.com; "
            "worker-src 'self' blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; "
            f"connect-src 'self' {connect_sources} https://www.gstatic.com https://fonts.googleapis.com https://fonts.gstatic.com blob: data:; "
            "base-uri 'self'; form-action 'self';"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

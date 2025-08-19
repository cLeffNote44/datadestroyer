import base64
import os
from typing import Callable

from django.http import HttpRequest, HttpResponse


class CSPNonceMiddleware:
    """Generate a CSP nonce and attach it to the request.

    If the response does not already include a Content-Security-Policy header
    (e.g., when running behind nginx which sets it), this middleware adds a
    conservative header that permits 'self' and a per-request nonce for scripts.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 16 bytes -> 22 char URL-safe base64
        nonce = base64.b64encode(os.urandom(16)).decode("ascii").rstrip("=")
        request.csp_nonce = nonce
        response = self.get_response(request)

        if not response.has_header("Content-Security-Policy"):
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                "img-src 'self' data: blob:; "
                "style-src 'self'; "
                "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
            )
            response["Content-Security-Policy"] = csp
        return response

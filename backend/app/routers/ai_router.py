"""Backwards-compatible shim for the legacy ai_router module.

The actual router now lives in app.ai.router.
"""

from app.ai.router import router  # noqa: F401

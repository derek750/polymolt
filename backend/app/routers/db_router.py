"""
Database router — placeholder for future DB-backed routes.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/health")
def db_health():
    """Placeholder. Replace with real DB connectivity check later."""
    return {"status": "ok", "message": "Database router ready; not connected yet."}

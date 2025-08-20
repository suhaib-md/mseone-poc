from __future__ import annotations

from fastapi import Header, HTTPException, status

# For local dev, accept a fixed token. Replace with AAD in Phase 2.
LOCAL_DEV_TOKEN = "devtoken123"


async def require_bearer(authorization: str = Header(None)) -> None:
    """Reject if missing/invalid. In Phase 2 we validate real AAD JWTs."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != LOCAL_DEV_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

"""
Phase 14 — Authentication Dependency.

FastAPI dependency for extracting and validating JWT tokens from requests.
"""
from typing import Optional
from fastapi import Security, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.auth_service import AuthenticationService
from models.user import User


# HTTPBearer security scheme. With auto_error=False it only annotates the
# OpenAPI docs (Authorize button) without enforcing anything — the actual
# token validation + 401 responses are handled in get_current_user below.
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates the JWT token and returns the current user.

    Extracts bearer token from Authorization header.
    Uses the same request-scoped DB session as the route handler.

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 403: User not found or inactive

    Usage in route:
        @app.get("/api/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Verify token
    user_id = await AuthenticationService.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user
    user = await AuthenticationService.get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or inactive",
        )

    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication dependency. Returns current user if token provided, None otherwise.

    Usage in route:
        @app.get("/api/semi-protected")
        async def semi_protected(current_user: Optional[User] = Depends(get_optional_user)):
            if current_user:
                return {"user_id": current_user.id}
            return {"user_id": "anonymous"}
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix
    user_id = await AuthenticationService.verify_token(token)
    if not user_id:
        return None

    user = await AuthenticationService.get_user_by_id(session, user_id)
    return user if user and user.is_active else None

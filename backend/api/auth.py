"""
Phase 14 — Authentication API Endpoints.

REST API for user registration, login, and current user retrieval.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    AuthenticatedUserResponse,
)
from services.auth_service import AuthenticationService
from models.user import User
from dependencies.auth import get_current_user


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _user_to_response(user: User) -> UserResponse:
    """Convert User ORM model to safe response schema."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        phone=user.phone,
        membership=user.membership.value,
        loyalty_points=user.loyalty_points,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    - Validates email uniqueness
    - Hashes password securely with bcrypt
    - Returns user data (no password hash)

    Returns:
        UserResponse: Created user details
    """
    success, message, user = await AuthenticationService.register_user(
        session,
        email=request.email,
        password=request.password,
        name=request.name,
        phone=request.phone,
    )

    if not success:
        # Determine appropriate status code
        if "already registered" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    await session.commit()
    return _user_to_response(user)


@router.post("/login", response_model=AuthenticatedUserResponse)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access token.

    - Validates email and password
    - Returns JWT token with 24-hour expiration
    - Returns user data in response

    Returns:
        AuthenticatedUserResponse: Token and user data
    """
    success, message, user = await AuthenticationService.login_user(
        session,
        email=request.email,
        password=request.password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    # Generate token
    token, expires_in = AuthenticationService.generate_access_token(user.id)

    return AuthenticatedUserResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=_user_to_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.

    Requires: Valid JWT token in Authorization header

    Returns:
        UserResponse: Current user details (no password hash)
    """
    return _user_to_response(current_user)

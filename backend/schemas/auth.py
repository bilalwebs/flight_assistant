"""
Phase 14 — Authentication Schemas.

Pydantic models for user registration, login, and token responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: str = Field(..., min_length=1, max_length=200, description="User full name")
    phone: Optional[str] = Field(None, description="Phone number (optional)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
                "name": "John Doe",
                "phone": "+1234567890"
            }
        }
    }


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123"
            }
        }
    }


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    }


class UserResponse(BaseModel):
    """Safe user response (no password hash)."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    phone: Optional[str] = Field(None, description="User phone")
    membership: str = Field(..., description="Membership tier")
    loyalty_points: str = Field(..., description="Loyalty points balance")
    is_active: bool = Field(..., description="Account active status")
    created_at: str = Field(..., description="Account creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "John Doe",
                "phone": "+1234567890",
                "membership": "standard",
                "loyalty_points": "0",
                "is_active": True,
                "created_at": "2026-09-06T04:00:00Z"
            }
        }
    }


class AuthenticatedUserResponse(TokenResponse):
    """Login response with user data and token."""
    user: UserResponse = Field(..., description="Authenticated user data")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "phone": "+1234567890",
                    "membership": "standard",
                    "loyalty_points": "0",
                    "is_active": True,
                    "created_at": "2026-09-06T04:00:00Z"
                }
            }
        }
    }

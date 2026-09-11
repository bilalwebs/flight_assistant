"""
Phase 14 — Authentication Service.

Handles user registration, login, password hashing, and JWT token generation.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import hashlib
import secrets

from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from models.user import User


class AuthenticationService:
    """Authentication and authorization operations."""

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using PBKDF2."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${pwd_hash.hex()}"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password."""
        return AuthenticationService._hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a hash."""
        try:
            salt, pwd_hash = hashed_password.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except Exception:
            return False

    @staticmethod
    def generate_access_token(user_id: str, expires_hours: Optional[int] = None) -> tuple[str, int]:
        """Generate a JWT access token for a user.

        Args:
            user_id: User ID to encode in token
            expires_hours: Token expiration in hours (default from config)

        Returns:
            Tuple of (token, expires_in_seconds)
        """
        if expires_hours is None:
            expires_hours = JWT_EXPIRATION_HOURS

        now = datetime.utcnow()
        expires = now + timedelta(hours=expires_hours)
        expires_in_seconds = int(expires_hours * 3600)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires,
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, expires_in_seconds

    @staticmethod
    async def verify_token(token: str) -> Optional[str]:
        """Verify a JWT token and extract the user ID.

        Args:
            token: JWT token string

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            return user_id
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    async def register_user(
        session: AsyncSession,
        email: str,
        password: str,
        name: str,
        phone: Optional[str] = None,
    ) -> tuple[bool, str, Optional[User]]:
        """Register a new user.

        Args:
            session: Database session
            email: User email (must be unique)
            password: Plaintext password
            name: User full name
            phone: Optional phone number

        Returns:
            Tuple of (success, message, user_or_none)
        """
        try:
            # Check if email already exists
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            if result.scalars().first():
                return False, "Email already registered.", None

            # Create new user
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                email=email.lower(),
                name=name,
                phone=phone,
                password_hash=AuthenticationService.hash_password(password),
                is_active=True,
            )
            session.add(user)
            await session.flush()

            return True, "User registered successfully.", user

        except Exception as e:
            await session.rollback()
            return False, f"Registration failed: {str(e)}", None

    @staticmethod
    async def login_user(
        session: AsyncSession,
        email: str,
        password: str,
    ) -> tuple[bool, str, Optional[User]]:
        """Authenticate a user and return their record.

        Args:
            session: Database session
            email: User email
            password: Plaintext password

        Returns:
            Tuple of (success, message, user_or_none)
        """
        try:
            # Fetch user by email
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalars().first()

            if not user:
                return False, "Invalid email or password.", None

            if not user.is_active:
                return False, "Account is disabled.", None

            # Verify password
            if not AuthenticationService.verify_password(password, user.password_hash or ""):
                return False, "Invalid email or password.", None

            return True, "Login successful.", user

        except Exception as e:
            return False, f"Login failed: {str(e)}", None

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
        """Fetch a user by ID.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            User record or None
        """
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

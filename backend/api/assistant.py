"""
Phase 14 — AI Assistant API Endpoints.

REST API for the guarded flight orchestrator agent with session persistence.
"""
import logging
import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from models.user import User
from models.context import FlightAssistantContext
from sessions.session_manager import SessionManager
from schemas.assistant import (
    AssistantMessageRequest,
    AssistantMessageResponse,
)
from dependencies.auth import get_current_user
from config.settings import SESSION_DB_PATH

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# Initialize session manager
session_manager = SessionManager(db_path=SESSION_DB_PATH)


@router.post("/chat", response_model=AssistantMessageResponse)
async def chat_with_assistant(
    request: AssistantMessageRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Chat with the AI Flight Assistant.

    The assistant maintains conversation history per user/conversation pair.
    User ID is enforced from authentication token (cannot be spoofed).
    Context preferences (cabin/origin/destination) are taken from the request
    and combined with the authenticated user's identity.

    Architecture:
    1. Authenticated user → current_user from token
    2. Session ID → conversation_id or auto-generate
    3. Create FlightAssistantContext with user preferences
    4. SessionManager retrieves persistent session
    5. GuardedFlightOrchestrator runs with guardrails
    6. Response returned with new conversation_id if needed

    Args:
        request: User message and optional conversation_id

    Returns:
        AssistantMessageResponse with assistant's response

    Raises:
        401: Unauthenticated
        422: Invalid request body
        500: Assistant execution failure
    """
    try:
        # Use provided conversation_id or generate new one
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # CRITICAL: User ID comes from authentication token, never from request
        user_id = current_user.id

        # Create context with user preferences
        context = FlightAssistantContext(
            user_id=user_id,
            user_name=current_user.name,
            user_email=current_user.email,
            user_phone=current_user.phone,
            origin_preference=request.origin_preference,
            destination_preference=request.destination_preference,
            cabin_preference=request.cabin_preference,
            # Mirror into the established context field so agent instructions work
            preferred_cabin_class=request.cabin_preference,
        )

        # Run conversation with persistent session
        final_output = await session_manager.run_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            user_input=request.message,
            context=context,
        )

        return AssistantMessageResponse(
            conversation_id=conversation_id,
            message=final_output or "No response generated",
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Never leak internals to the client; log the real error server-side.
        logger.exception("Assistant chat failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assistant request failed. Please try again.",
        )

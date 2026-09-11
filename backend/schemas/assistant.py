"""
Phase 14 — Assistant API Schemas.

Pydantic models for AI assistant chat requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional


class AssistantMessageRequest(BaseModel):
    """Chat message request to assistant."""
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID (auto-generated if not provided)")
    origin_preference: Optional[str] = Field(None, description="Preferred origin IATA code")
    destination_preference: Optional[str] = Field(None, description="Preferred destination IATA code")
    cabin_preference: Optional[str] = Field(None, description="Preferred cabin class: economy|business|first")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "I want to book a flight from Karachi to Dubai",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "origin_preference": "KHI",
                "destination_preference": "DXB",
                "cabin_preference": "economy"
            }
        }
    }


class AssistantMessageResponse(BaseModel):
    """Chat response from assistant."""
    conversation_id: str = Field(..., description="Conversation ID (for continuing conversation)")
    message: str = Field(..., description="Assistant's response")
    success: bool = Field(..., description="Whether the request was successful")

    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "I found 3 flights from Karachi to Dubai for you. Here are the best options...",
                "success": True
            }
        }
    }

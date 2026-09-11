"""Phase 11 — Session Manager.

Provides a clean application-facing entry point for running conversations
with persistent session history using the Agents SDK's SQLiteSession.
"""
from pathlib import Path
from agents import SQLiteSession, Runner
from app_agents.guarded_flight_orchestrator_agent import guarded_flight_orchestrator_agent
from models.context import FlightAssistantContext


class SessionManager:
    """Manages conversation sessions with persistence."""

    def __init__(self, db_path: str | Path = "sessions.db"):
        """Initialize session manager.

        Args:
            db_path: Path to SQLite database. Defaults to sessions.db in current directory.
        """
        self.db_path = Path(db_path)

    def get_session(self, user_id: str, conversation_id: str) -> SQLiteSession:
        """Get or create a session for a user/conversation pair.

        Session ID is user_id:conversation_id to ensure isolation.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier

        Returns:
            SQLiteSession ready for use
        """
        session_id = f"{user_id}:{conversation_id}"
        return SQLiteSession(
            session_id=session_id,
            db_path=str(self.db_path),
            sessions_table="agent_sessions",
            messages_table="agent_messages",
        )

    async def run_conversation(
        self,
        user_id: str,
        conversation_id: str,
        user_input: str,
        context: FlightAssistantContext | None = None,
    ) -> str:
        """Run a conversation turn with session history.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            user_input: User's message for this turn
            context: Optional FlightAssistantContext with preferences

        Returns:
            Final output from the orchestrator
        """
        session = self.get_session(user_id, conversation_id)

        try:
            result = await Runner.run(
                starting_agent=guarded_flight_orchestrator_agent,
                input=user_input,
                context=context,
                session=session,
            )

            return result.final_output
        finally:
            session.close()

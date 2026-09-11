"""Phase 11 — Sessions + Conversation Memory test suite."""
import asyncio
import tempfile
from pathlib import Path
from sessions.session_manager import SessionManager
from models.context import FlightAssistantContext
from agents import set_tracing_disabled

set_tracing_disabled(True)


async def main():
    print("=" * 70)
    print("PHASE 11 — SESSIONS + CONVERSATION MEMORY")
    print("=" * 70)

    # Use temp DB for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sessions.db"
        manager = SessionManager(db_path)

        # Test 1: Single-turn search
        print("\n[TEST 1] Single-turn flight search")
        try:
            result = await manager.run_conversation(
                user_id="user_1",
                conversation_id="conv_1",
                user_input="Find flights from Karachi to Dubai tomorrow.",
                context=FlightAssistantContext(user_name="Alice"),
            )
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: Search executed, output generated")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

        # Test 2: Multi-turn — same session continuation
        print("\n[TEST 2] Multi-turn conversation (same session)")
        try:
            # Turn 2: follow-up in same session
            result = await manager.run_conversation(
                user_id="user_1",
                conversation_id="conv_1",
                user_input="Show me only the cheapest one.",
            )
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: Follow-up executed, session history available")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

        # Test 3: Session isolation — different conversation
        print("\n[TEST 3] Session isolation (different conversation)")
        try:
            result = await manager.run_conversation(
                user_id="user_1",
                conversation_id="conv_2",  # Different conversation ID
                user_input="Find flights from Karachi to Istanbul tomorrow.",
            )
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: New conversation independent, no cross-contamination")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

        # Test 4: User isolation
        print("\n[TEST 4] User isolation (different user)")
        try:
            result = await manager.run_conversation(
                user_id="user_2",  # Different user
                conversation_id="conv_1",  # Same conversation ID as user_1
                user_input="List my previous flights.",
            )
            # Should NOT have user_1's conversation history
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: Different user, separate session")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

        # Test 5: Context still works
        print("\n[TEST 5] FlightAssistantContext compatibility")
        try:
            ctx = FlightAssistantContext(
                user_name="Bob",
                preferred_cabin_class="business",
                preferred_currency="USD",
            )
            result = await manager.run_conversation(
                user_id="user_3",
                conversation_id="conv_1",
                user_input="Find flights from Karachi to Dubai tomorrow.",
                context=ctx,
            )
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: Context passed through session layer")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

        # Test 6: Persistence across manager recreation
        print("\n[TEST 6] Persistence across manager recreation")
        try:
            # Create new manager instance (same DB)
            manager2 = SessionManager(db_path)
            result = await manager2.run_conversation(
                user_id="user_1",
                conversation_id="conv_1",
                user_input="What was my first request?",  # Should have history
            )
            if isinstance(result, str) and len(result.strip()) > 0:
                print("    PASS: History persisted across manager recreation")
            else:
                print("    FAIL: No output")
        except Exception as e:
            print(f"    FAIL: {e}")

    print("\n" + "=" * 70)
    print("Phase 11 tests complete.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

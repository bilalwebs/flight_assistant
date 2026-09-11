"""
Phase 13 — Stripe Webhook Endpoint.

FastAPI endpoint for receiving and processing Stripe webhooks.
Verifies webhook signature and processes payment events.
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from config.settings import STRIPE_WEBHOOK_SECRET
from database.database import AsyncSessionLocal
from services.payment_service import PaymentService

router = APIRouter()


@router.post("/api/payments/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint for payment event processing.

    Verifies signature and processes charge.succeeded and charge.failed events.
    Idempotent: handles duplicate deliveries safely.

    When STRIPE_WEBHOOK_SECRET is not configured, the endpoint returns a clear
    503 configuration error — Stripe is an optional future module.
    """
    # Stripe is optional — if the webhook secret is absent, report a clear
    # configuration error rather than attempting signature verification.
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. The webhook endpoint is inactive; "
                   "payments are an optional future module.",
        )

    # 1. Read raw body for signature verification
    body = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 2. Verify Stripe signature
    try:
        event = stripe.Webhook.construct_event(
            body, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    # 3. Get event type
    event_type = event.get("type")

    # 4. Process only supported event types
    if event_type not in ["charge.succeeded", "charge.failed"]:
        # Unknown event — acknowledge but don't process
        return {"status": "received", "event_type": event_type}

    # 5. Process the event with database transaction
    async with AsyncSessionLocal() as session:
        result = await PaymentService.verify_payment_from_webhook(session, event)

        if result:
            await session.commit()
        else:
            await session.rollback()

    # 6. Always return 200 to acknowledge receipt
    # Stripe will retry on any 4xx/5xx response
    return {"status": "received", "event_type": event_type, "result": result}

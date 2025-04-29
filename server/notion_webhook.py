"""
File: notion_webhook.py
Author: Vasu Chukka
Created: 2025-04-29
Last Modified: 2025-04-30
Description:
    Webhook receiver for native Notion events.

    This FastAPI router listens for webhook POST requests sent from Notion.
    It optionally verifies HMAC signatures (if a NOTION_WEBHOOK_SECRET is set)
    and dispatches logic based on the type of event received, such as:

    - page.created
    - page.updated
    - database.updated
    - comment.created

    This serves as the bridge between Notion and FinSense actions,
    enabling real-time updates and automation from your Notion workspace.
"""

from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
import hmac
import hashlib
import os
import json

router = APIRouter()

# Optional: Use HMAC verification if secret is set
NOTION_WEBHOOK_SECRET = os.getenv("NOTION_WEBHOOK_SECRET")

@router.post("/")
async def receive_notion_webhook(
    request: Request,
    x_notion_signature: str = Header(None)
):
    """
    Handles incoming POST requests from Notion's webhook system.

    - Verifies payload signature using HMAC (optional)
    - Parses and logs the JSON payload
    - Dispatches based on event type

    Args:
        request (Request): FastAPI request object
        x_notion_signature (str): Optional HMAC signature from Notion header

    Returns:
        JSONResponse: Confirmation that the event was received and logged
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # ✅ Optional: Verify HMAC signature
    if NOTION_WEBHOOK_SECRET:
        if not x_notion_signature:
            raise HTTPException(status_code=401, detail="Missing Notion signature.")
        expected_sig = hmac.new(
            NOTION_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, x_notion_signature):
            raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    # ✅ Log and inspect the payload
    print("📥 Notion Webhook Event:")
    print(json.dumps(payload, indent=2))

    # ✅ Dispatch on each event
    for event in payload.get("events", []):
        event_type = event.get("type")
        resource = event.get("resource", {})
        page_id = resource.get("id")

        print(f"🔔 Event received: {event_type} for resource ID: {page_id}")

        # In the future: hook into FinSense logic
        if event_type == "page.updated":
            print(f"🔄 You could now fetch and process page {page_id}.")
        elif event_type == "comment.created":
            print(f"💬 A new comment was created.")

    return JSONResponse(content={"status": "ok", "received": True})
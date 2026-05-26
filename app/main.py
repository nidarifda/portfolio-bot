from fastapi import FastAPI, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import uuid
import json
import httpx
from datetime import datetime
import pytz

from app.config import (
    PORT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TIMEZONE, BASE_URL
)
from app.telegram_handler import (
    send_cv_request_notification,
    send_booking_notification,
    send_confirmation,
)
from app.email_service import (
    send_cv_email,
    send_booking_confirmation,
    send_reschedule_email,
    send_decline_email,
)
from app.calendar_service import create_event, get_available_slots

app = FastAPI(title="NRC Labs Bot", version="1.0.0")

# CORS for website form submissions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for pending requests (use Redis in production)
pending_requests: dict = {}

tz = pytz.timezone(TIMEZONE)


# ==================== WEBHOOK ENDPOINTS ====================

@app.post("/webhook/cv-request")
async def handle_cv_request(request: Request):
    """Handle CV request from website form."""
    form = await request.form()
    name = form.get("name", "")
    email = form.get("email", "")
    note = form.get("note", "")
    redirect_url = form.get("_next", "")

    request_id = str(uuid.uuid4())[:8]

    pending_requests[request_id] = {
        "type": "cv",
        "name": name,
        "email": email,
        "note": note,
        "timestamp": datetime.now(tz).isoformat(),
    }

    # Notify via Telegram
    await send_cv_request_notification(request_id, name, email, note)

    # Redirect to thank you page
    if redirect_url:
        return RedirectResponse(url=redirect_url, status_code=303)
    return JSONResponse({"status": "received", "id": request_id})


@app.post("/webhook/book-call")
async def handle_book_call(request: Request):
    """Handle call booking from website form."""
    form = await request.form()
    name = form.get("name", "")
    email = form.get("email", "")
    subject = form.get("subject", "")
    message = form.get("message", "")
    redirect_url = form.get("_next", "")

    request_id = str(uuid.uuid4())[:8]

    pending_requests[request_id] = {
        "type": "booking",
        "name": name,
        "email": email,
        "topic": subject,
        "message": message,
        "timestamp": datetime.now(tz).isoformat(),
    }

    # Notify via Telegram
    await send_booking_notification(request_id, name, email, subject, message)

    # Redirect to thank you page
    if redirect_url:
        return RedirectResponse(url=redirect_url, status_code=303)
    return JSONResponse({"status": "received", "id": request_id})


# ==================== TELEGRAM CALLBACK HANDLER ====================

@app.post("/telegram/callback")
async def handle_telegram_callback(request: Request):
    """Handle Telegram inline button callbacks."""
    data = await request.json()

    if "callback_query" not in data:
        return {"ok": True}

    callback = data["callback_query"]
    callback_data = callback["data"]
    callback_id = callback["id"]

    # Acknowledge the button press
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Processing..."},
        )

    action, request_id = callback_data.split(":", 1)
    req = pending_requests.get(request_id)

    if not req:
        await send_confirmation("⚠️ Request expired or not found.")
        return {"ok": True}

    try:
        if action == "cv_approve":
            send_cv_email(req["email"], req["name"])
            await send_confirmation(
                f"✅ CV sent to {req['name']} ({req['email']})"
            )
            del pending_requests[request_id]

        elif action == "cv_decline":
            send_decline_email(req["email"], req["name"], "cv")
            await send_confirmation(
                f"❌ CV request from {req['name']} declined."
            )
            del pending_requests[request_id]

        elif action == "book_accept":
            # Create calendar event
            now = datetime.now(tz)
            # Find next available slot
            slots = get_available_slots(days_ahead=7)
            if slots:
                slot = slots[0]
                event = create_event(
                    summary=f"NRC Labs Call — {req['name']}",
                    description=f"Topic: {req.get('topic', 'General')}\nEmail: {req['email']}",
                    start_dt=slot["start"],
                    attendee_email=req["email"],
                )
                send_booking_confirmation(
                    req["email"], req["name"],
                    slot["start"].strftime("%A, %B %d"),
                    slot["start"].strftime("%I:%M %p MYT"),
                )
                await send_confirmation(
                    f"✅ Call booked with {req['name']}\n"
                    f"📅 {slot['display']}\n"
                    f"📧 Invite sent to {req['email']}"
                )
            else:
                send_booking_confirmation(
                    req["email"], req["name"], "TBD", "TBD"
                )
                await send_confirmation(
                    f"✅ Booking confirmed with {req['name']}\n"
                    f"⚠️ No calendar slots found — manual scheduling needed."
                )
            del pending_requests[request_id]

        elif action == "book_resched":
            slots = get_available_slots(days_ahead=7)
            if slots:
                slot_strings = [s["display"] for s in slots]
                send_reschedule_email(req["email"], req["name"], slot_strings)
                await send_confirmation(
                    f"📅 Reschedule options sent to {req['name']}\n"
                    f"Offered {len(slot_strings)} time slots."
                )
            else:
                await send_confirmation(
                    "⚠️ No available slots found in the next 7 days."
                )

        elif action == "book_decline":
            send_decline_email(req["email"], req["name"], "booking")
            await send_confirmation(
                f"❌ Booking from {req['name']} declined."
            )
            del pending_requests[request_id]

    except Exception as e:
        await send_confirmation(f"⚠️ Error: {str(e)}")

    return {"ok": True}


# ==================== UTILITY ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "app": "NRC Labs Bot",
        "status": "running",
        "endpoints": {
            "cv_request": "/webhook/cv-request",
            "book_call": "/webhook/book-call",
            "telegram_callback": "/telegram/callback",
            "available_slots": "/slots",
        },
    }


@app.get("/slots")
async def available_slots():
    """Get available booking slots (public endpoint)."""
    slots = get_available_slots()
    return {"slots": [s["display"] for s in slots]}


@app.get("/health")
async def health():
    return {"status": "ok", "telegram": bool(TELEGRAM_BOT_TOKEN)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)

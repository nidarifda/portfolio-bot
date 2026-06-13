from fastapi import FastAPI, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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

    return _thank_you_page("CV Request Sent!", "Your request has been received. I'll review it and send my CV to your inbox shortly.")


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

    return _thank_you_page("Inquiry Sent!", "Your booking request has been received. I'll get back to you within 24 hours.")


@app.post("/webhook/cal")
async def handle_cal_webhook(request: Request):
    """Handle Cal.com booking webhook — sends Telegram notification."""
    try:
        payload = await request.json()
        event_type = payload.get("triggerEvent", "")
        booking = payload.get("payload", {})

        # Extract booking details
        name = ""
        email = ""
        attendees = booking.get("attendees", [])
        if attendees:
            name = attendees[0].get("name", "Unknown")
            email = attendees[0].get("email", "")

        title = booking.get("title", "Free Consultation")
        start_raw = booking.get("startTime", "")
        end_raw = booking.get("endTime", "")
        meet_url = booking.get("metadata", {}).get("videoCallUrl", "")

        # If no meet URL in metadata, check conferenceData
        if not meet_url:
            conference = booking.get("conferenceData", {})
            if conference:
                meet_url = conference.get("uri", "") or conference.get("url", "")

        # Format date/time
        date_str = ""
        time_str = ""
        if start_raw:
            try:
                start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                start_local = start_dt.astimezone(tz)
                date_str = start_local.strftime("%A, %B %d, %Y")
                time_str = start_local.strftime("%I:%M %p")
            except Exception:
                date_str = start_raw

        # Build Telegram message based on event type
        if event_type == "BOOKING_CREATED":
            emoji = "📅"
            header = "New Booking!"
        elif event_type == "BOOKING_RESCHEDULED":
            emoji = "🔄"
            header = "Booking Rescheduled"
        elif event_type == "BOOKING_CANCELLED":
            emoji = "❌"
            header = "Booking Cancelled"
        else:
            emoji = "📅"
            header = "Booking Update"

        message = (
            f"{emoji} <b>{header}</b>\n\n"
            f"👤 <b>{name}</b>\n"
            f"📧 {email}\n"
            f"📌 {title}\n"
            f"📆 {date_str}\n"
            f"🕐 {time_str}\n"
        )
        if meet_url:
            message += f"🔗 <a href=\"{meet_url}\">Join Meeting</a>\n"

        # Send to Telegram
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )

        return {"status": "ok"}
    except Exception as e:
        print(f"Cal webhook error: {e}")
        return {"status": "error", "detail": str(e)}


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


def _thank_you_page(title: str, message: str) -> HTMLResponse:
    """Return a styled thank you page matching NRC Labs branding."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — NRC Labs</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family:'Inter',system-ui,sans-serif;
            background:#08080f; color:#f1f5f9;
            min-height:100vh; display:flex; align-items:center; justify-content:center;
            overflow:hidden;
        }}
        .card {{
            text-align:center; max-width:480px; padding:48px 40px;
            background:rgba(15,15,30,0.9); border:1px solid rgba(168,85,247,0.2);
            border-radius:20px; box-shadow:0 0 60px rgba(168,85,247,0.15);
            animation:fadeUp .5s ease;
        }}
        @keyframes fadeUp {{
            from {{ opacity:0; transform:translateY(20px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
        .icon {{
            width:72px; height:72px; margin:0 auto 24px;
            background:linear-gradient(135deg,#a855f7,#6d28d9);
            border-radius:50%; display:flex; align-items:center; justify-content:center;
            font-size:2rem; box-shadow:0 0 30px rgba(168,85,247,0.4);
        }}
        h1 {{
            font-size:1.8rem; font-weight:900; margin-bottom:12px;
            background:linear-gradient(135deg,#a855f7,#00d4ff);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        }}
        p {{ color:#8892a8; font-size:1rem; line-height:1.7; margin-bottom:28px; }}
        .btn {{
            display:inline-block; padding:14px 32px; border-radius:999px;
            font-weight:700; font-size:.9rem; text-decoration:none;
            background:linear-gradient(135deg,#a855f7,#6d28d9); color:#fff;
            box-shadow:0 8px 28px rgba(168,85,247,0.35); transition:all .2s;
        }}
        .btn:hover {{ transform:translateY(-2px); box-shadow:0 12px 36px rgba(168,85,247,0.45); }}
        .glow {{
            position:fixed; width:300px; height:300px; border-radius:50%;
            background:radial-gradient(circle,rgba(168,85,247,0.15),transparent 70%);
            pointer-events:none;
        }}
        .glow-1 {{ top:-100px; left:-100px; }}
        .glow-2 {{ bottom:-100px; right:-100px; }}
    </style>
</head>
<body>
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="card">
        <div class="icon">✓</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <a href="https://nidalabs.vercel.app/" class="btn">← Back to Portfolio</a>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)

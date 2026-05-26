import httpx
import json
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_cv_request_notification(
    request_id: str, name: str, email: str, note: str = ""
):
    """Send CV request notification with approve/decline buttons."""
    note_line = f"\n📝 Note: {note}" if note else ""
    text = (
        f"📄 *New CV Request*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {_escape(name)}\n"
        f"📧 Email: {_escape(email)}"
        f"{note_line}\n\n"
        f"_Tap a button to respond:_"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Send CV", "callback_data": f"cv_approve:{request_id}"},
                {"text": "❌ Decline", "callback_data": f"cv_decline:{request_id}"},
            ]
        ]
    }

    await _send_message(text, keyboard)


async def send_booking_notification(
    request_id: str, name: str, email: str, topic: str, preferred_time: str = ""
):
    """Send booking notification with accept/reschedule/decline buttons."""
    time_line = f"\n🕐 Preferred: {_escape(preferred_time)}" if preferred_time else ""
    text = (
        f"📞 *New Call Booking*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {_escape(name)}\n"
        f"📧 Email: {_escape(email)}\n"
        f"💡 Topic: {_escape(topic)}"
        f"{time_line}\n\n"
        f"_Tap a button to respond:_"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept", "callback_data": f"book_accept:{request_id}"},
                {"text": "📅 Reschedule", "callback_data": f"book_resched:{request_id}"},
                {"text": "❌ Decline", "callback_data": f"book_decline:{request_id}"},
            ]
        ]
    }

    await _send_message(text, keyboard)


async def send_confirmation(text: str):
    """Send a simple confirmation message."""
    await _send_message(text)


async def _send_message(text: str, reply_markup: dict = None):
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram disabled] Would send: {text}")
        return

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json=payload)


def _escape(text: str) -> str:
    """Escape special Markdown characters."""
    for char in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
        text = text.replace(char, f"\\{char}")
    return text

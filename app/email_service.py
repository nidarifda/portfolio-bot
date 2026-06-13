"""Email service using Gmail API (OAuth2) instead of SMTP.
This works on Render's free tier where SMTP ports are blocked.
"""
import base64
import json
import os
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.config import (
    GMAIL_ADDRESS, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
    GMAIL_REFRESH_TOKEN, SENDER_NAME, CV_FILE_PATH,
)

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _get_access_token() -> str:
    """Get a fresh access token using the refresh token."""
    data = urllib.parse.urlencode({
        "client_id": GMAIL_CLIENT_ID,
        "client_secret": GMAIL_CLIENT_SECRET,
        "refresh_token": GMAIL_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data)
    resp = urllib.request.urlopen(req)
    tokens = json.loads(resp.read())
    return tokens["access_token"]


def _send_via_gmail_api(msg: MIMEMultipart, to_email: str):
    """Send email via Gmail API (HTTP POST, not SMTP)."""
    # Encode the email as base64url
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    # Get fresh access token
    access_token = _get_access_token()

    # Send via Gmail API
    body = json.dumps({"raw": raw_message}).encode("utf-8")
    req = urllib.request.Request(
        GMAIL_SEND_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Email sent to {to_email} | Message ID: {result.get('id', 'unknown')}")
    return result


def send_cv_email(to_email: str, to_name: str):
    """Send CV as PDF attachment with a professional email."""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = f"CV from {SENDER_NAME}"

    body = f"""Hi {to_name},

Thank you for your interest in working together! As requested, please find my CV attached.

I'd love to discuss how I can help with your project. Feel free to book a free consultation at:
https://cal.com/nidalabs/free-consultation

Looking forward to connecting!

Best regards,
Nida Rifda Chairuli
NRC Labs | AI Automation & Data Intelligence
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach CV
    if os.path.exists(CV_FILE_PATH):
        with open(CV_FILE_PATH, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="Nida_Rifda_Chairuli_CV.pdf"',
            )
            msg.attach(part)

    _send_via_gmail_api(msg, to_email)
    return True


def send_booking_confirmation(to_email: str, to_name: str, date_str: str, time_str: str):
    """Send booking confirmation email to client."""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = f"Call Confirmed | {date_str} at {time_str} — NRC Labs"

    body = f"""Hi {to_name},

Your consultation call has been confirmed! Here are the details:

Date: {date_str}
Time: {time_str} (Malaysian Time / GMT+8)
Platform: Google Meet (link will be in the calendar invite)

What to expect:
- A focused 30-minute discussion about your project
- Actionable insights on how AI can help your business
- No pressure, no obligations

If you need to reschedule, simply reply to this email.

See you soon!

Best regards,
Nida Rifda Chairuli
NRC Labs | AI Automation & Data Intelligence
"""
    msg.attach(MIMEText(body, "plain"))
    _send_via_gmail_api(msg, to_email)
    return True


def send_reschedule_email(to_email: str, to_name: str, slots: list[str]):
    """Send available time slots to client for rescheduling."""
    slots_text = "\n".join([f"  - {slot}" for slot in slots])

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = "Let's find a better time — NRC Labs"

    body = f"""Hi {to_name},

I'd like to reschedule our call. Here are my available slots:

{slots_text}

Simply reply with the slot number or time that works best for you, and I'll confirm it right away.

Best regards,
Nida Rifda Chairuli
NRC Labs | AI Automation & Data Intelligence
"""
    msg.attach(MIMEText(body, "plain"))
    _send_via_gmail_api(msg, to_email)
    return True


def send_decline_email(to_email: str, to_name: str, request_type: str = "cv"):
    """Send a polite decline email."""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email

    if request_type == "cv":
        msg["Subject"] = "Thank you for your interest — NRC Labs"
        body = f"""Hi {to_name},

Thank you for reaching out! Unfortunately, I'm unable to share my CV at this time.

Feel free to check out my portfolio and projects at:
https://nidalabs.vercel.app/

Best regards,
Nida Rifda Chairuli
NRC Labs
"""
    else:
        msg["Subject"] = "Regarding your booking request — NRC Labs"
        body = f"""Hi {to_name},

Thank you for your interest in booking a consultation. Unfortunately, I'm not available at this time.

I'll reach out when my schedule opens up. In the meantime, feel free to explore my work at:
https://nidalabs.vercel.app/

Best regards,
Nida Rifda Chairuli
NRC Labs
"""
    msg.attach(MIMEText(body, "plain"))
    _send_via_gmail_api(msg, to_email)
    return True

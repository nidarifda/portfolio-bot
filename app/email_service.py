import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from app.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, SENDER_NAME, CV_FILE_PATH


def send_cv_email(to_email: str, to_name: str):
    """Send CV as PDF attachment with a professional email."""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = f"CV from {SENDER_NAME}"

    body = f"""Hi {to_name},

Thank you for your interest in working together! As requested, please find my CV attached.

I'd love to discuss how I can help with your project. Feel free to book a free consultation at:
https://nidarifda.github.io/Portofolio/#contact

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

    _send(msg, to_email)
    return True


def send_booking_confirmation(to_email: str, to_name: str, date_str: str, time_str: str):
    """Send booking confirmation email to client."""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = f"Call Confirmed | {date_str} at {time_str} — NRC Labs"

    body = f"""Hi {to_name},

Your consultation call has been confirmed! Here are the details:

📅 Date: {date_str}
🕐 Time: {time_str} (Malaysian Time / GMT+8)
📍 Platform: Google Meet (link will be in the calendar invite)

What to expect:
• A focused 30-minute discussion about your project
• Actionable insights on how AI can help your business
• No pressure, no obligations

If you need to reschedule, simply reply to this email.

See you soon!

Best regards,
Nida Rifda Chairuli
NRC Labs | AI Automation & Data Intelligence
"""
    msg.attach(MIMEText(body, "plain"))
    _send(msg, to_email)
    return True


def send_reschedule_email(to_email: str, to_name: str, slots: list[str]):
    """Send available time slots to client for rescheduling."""
    slots_text = "\n".join([f"  • {slot}" for slot in slots])

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
    _send(msg, to_email)
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
https://nidarifda.github.io/Portofolio/

Best regards,
Nida Rifda Chairuli
NRC Labs
"""
    else:
        msg["Subject"] = "Regarding your booking request — NRC Labs"
        body = f"""Hi {to_name},

Thank you for your interest in booking a consultation. Unfortunately, I'm not available at this time.

I'll reach out when my schedule opens up. In the meantime, feel free to explore my work at:
https://nidarifda.github.io/Portofolio/

Best regards,
Nida Rifda Chairuli
NRC Labs
"""
    msg.attach(MIMEText(body, "plain"))
    _send(msg, to_email)
    return True


def _send(msg: MIMEMultipart, to_email: str):
    """Send email via Gmail SMTP."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import pytz
from app.config import (
    GOOGLE_CREDENTIALS_JSON,
    CALENDAR_ID,
    TIMEZONE,
    AVAILABLE_DAYS,
    AVAILABLE_START_HOUR,
    AVAILABLE_END_HOUR,
    SLOT_DURATION_MINUTES,
)

tz = pytz.timezone(TIMEZONE)


def _get_service():
    """Build Google Calendar API service."""
    if not GOOGLE_CREDENTIALS_JSON:
        return None
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return build("calendar", "v3", credentials=creds)


def create_event(
    summary: str,
    description: str,
    start_dt: datetime,
    attendee_email: str,
    duration_minutes: int = SLOT_DURATION_MINUTES,
) -> dict | None:
    """Create a calendar event and send invite to attendee."""
    service = _get_service()
    if not service:
        return None

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
        "attendees": [{"email": attendee_email}],
        "conferenceData": {
            "createRequest": {"requestId": f"nrc-{int(start_dt.timestamp())}"}
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        },
    }

    result = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event,
        sendUpdates="all",
        conferenceDataVersion=1,
    ).execute()

    return result


def get_available_slots(days_ahead: int = 7) -> list[dict]:
    """Get available 30-min slots for the next N days."""
    service = _get_service()
    now = datetime.now(tz)
    slots = []

    for day_offset in range(1, days_ahead + 1):
        check_date = now + timedelta(days=day_offset)

        # Skip weekends
        if check_date.weekday() not in AVAILABLE_DAYS:
            continue

        # Get busy times for this day
        busy_times = _get_busy_times(service, check_date) if service else []

        # Generate slots
        for hour in range(AVAILABLE_START_HOUR, AVAILABLE_END_HOUR):
            for minute in [0, 30]:
                slot_start = check_date.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)

                # Skip past slots
                if slot_start <= now:
                    continue

                # Skip if conflicts with existing event
                if not _is_conflicting(slot_start, slot_end, busy_times):
                    slots.append({
                        "start": slot_start,
                        "end": slot_end,
                        "display": slot_start.strftime("%A, %b %d at %I:%M %p MYT"),
                    })

    return slots[:8]  # Return max 8 slots


def _get_busy_times(service, date: datetime) -> list[tuple]:
    """Get busy times from calendar for a specific date."""
    if not service:
        return []

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=23, minute=59, second=59, microsecond=0)

    try:
        body = {
            "timeMin": day_start.isoformat(),
            "timeMax": day_end.isoformat(),
            "timeZone": TIMEZONE,
            "items": [{"id": CALENDAR_ID}],
        }
        result = service.freebusy().query(body=body).execute()
        busy = result["calendars"][CALENDAR_ID]["busy"]
        return [
            (
                datetime.fromisoformat(b["start"]),
                datetime.fromisoformat(b["end"]),
            )
            for b in busy
        ]
    except Exception:
        return []


def _is_conflicting(start: datetime, end: datetime, busy: list[tuple]) -> bool:
    """Check if a slot conflicts with any busy period."""
    for busy_start, busy_end in busy:
        if start < busy_end and end > busy_start:
            return True
    return False

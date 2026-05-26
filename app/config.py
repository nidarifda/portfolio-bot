import os
from dotenv import load_dotenv

load_dotenv()

# === Server ===
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Gmail SMTP ===
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "nidarifda14@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# === Google Calendar ===
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
CALENDAR_ID = os.getenv("CALENDAR_ID", GMAIL_ADDRESS)

# === Availability (Malaysian Time / GMT+8) ===
TIMEZONE = "Asia/Kuala_Lumpur"
AVAILABLE_DAYS = [0, 1, 2, 3, 4]  # Mon-Fri
AVAILABLE_START_HOUR = 13  # 1 PM
AVAILABLE_END_HOUR = 17    # 5 PM
SLOT_DURATION_MINUTES = 30

# === CV File ===
CV_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "cv.pdf")
SENDER_NAME = "Nida Rifda Chairuli | NRC Labs"

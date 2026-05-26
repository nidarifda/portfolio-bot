# NRC Labs Bot

Automation bot for the NRC Labs portfolio website.

## Features
- **CV Request Approval** — Get notified on Telegram, approve with one tap, CV auto-sent via email
- **Call Booking** — Accept bookings, auto-create Google Calendar events, send confirmations
- **Reschedule** — Bot checks your calendar and offers available slots to clients

## Setup

### 1. Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create an app password for "Mail"
5. Copy the 16-character password → set as `GMAIL_APP_PASSWORD`

### 2. Telegram Bot
1. Open Telegram → search [@BotFather](https://t.me/BotFather)
2. Send `/newbot` → follow prompts
3. Copy the bot token → set as `TELEGRAM_BOT_TOKEN`
4. Send a message to your bot, then visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Find your `chat_id` → set as `TELEGRAM_CHAT_ID`

### 3. Google Calendar (optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable Calendar API
3. Create Service Account → Download JSON key
4. Share your calendar with the service account email
5. Paste the JSON as `GOOGLE_CREDENTIALS_JSON`

### 4. Deploy to Render
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo → set environment variables
4. Deploy!

### 5. Set Telegram Webhook
After deployment, run:
```
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<RENDER_URL>/telegram/callback"
```

## Environment Variables
See `.env.example` for all required variables.

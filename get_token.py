"""One-time script to generate Gmail OAuth2 refresh token.
Run locally ONLY - not deployed to server.

Usage:
  Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env first, then run:
  python get_token.py
"""
import json
import os
import urllib.parse
import urllib.request
import http.server
import webbrowser
import sys
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8888"
SCOPES = "https://www.googleapis.com/auth/gmail.send"

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env first!")
    sys.exit(1)

auth_code = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>Go back to terminal.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error = params.get("error", ["unknown"])[0]
            self.wfile.write(f"<h1>Error: {error}</h1>".encode())
    def log_message(self, format, *args):
        pass

print("\n=== Gmail OAuth2 Setup ===")
print("Starting local server on port 8888...")
server = http.server.HTTPServer(("127.0.0.1", 8888), Handler)

auth_url = (
    f"https://accounts.google.com/o/oauth2/auth?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"response_type=code&"
    f"scope={SCOPES}&"
    f"access_type=offline&"
    f"prompt=consent"
)

print(f"\nOpening browser... Sign in and click Allow.")
sys.stdout.flush()
webbrowser.open(auth_url)

print("Waiting for Google callback...")
sys.stdout.flush()
server.handle_request()

if not auth_code:
    print("ERROR: No auth code received!")
    sys.exit(1)

print(f"Got auth code! Exchanging for tokens...")
sys.stdout.flush()

token_data = urllib.parse.urlencode({
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data)
resp = urllib.request.urlopen(req)
tokens = json.loads(resp.read())

print("\n" + "="*50)
print("SUCCESS! Add this to .env and Render:")
print("="*50)
print(f"\nGMAIL_REFRESH_TOKEN={tokens['refresh_token']}")
sys.stdout.flush()

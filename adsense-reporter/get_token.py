#!/Users/alfred/.local/pipx/venvs/hermes-agent/bin/python3
"""
One-shot script to mint a Google OAuth refresh token for the longweekend.my
reporting stack. Re-authorizes both AdSense + Search Console in a single
browser flow.

Run this ONCE on your machine. It opens a browser, you sign in with the Gmail
that owns the AdSense account + Search Console property, grant permission, and
the script prints 3 values:
  - Refresh token
  - Client ID
  - Client secret

Send those 3 values to Alfred (or paste into .env yourself) and the AdSense
reporter cron + Search Console queries can start pulling data.

Usage:
  pip install google-auth-oauthlib
  python3 get_token.py

Required file: client_secret.json (downloaded from GCP Console)

Scopes:
  - adsense.readonly: AdSense Management API for daily revenue reports
  - webmasters.readonly: Search Console API for clicks/impressions/CTR
  - console.audit: harmless audit log scope requested by Google
"""
from google_auth_oauthlib.flow import InstalledAppFlow
import json
import sys
from pathlib import Path

# Two APIs needed for the longweekend.my reporting stack. Both are read-only.
# Adding both scopes means one browser flow covers both — no need to re-auth
# in two separate sessions.
SCOPES = [
    "https://www.googleapis.com/auth/adsense.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/console.audit",
]
CLIENT_SECRET_PATH = Path(__file__).parent / "client_secret.json"


def main():
    if not CLIENT_SECRET_PATH.exists():
        print(f"ERROR: {CLIENT_SECRET_PATH} not found.", file=sys.stderr)
        print("Download the OAuth client JSON from GCP Console → Credentials", file=sys.stderr)
        print("and save it as client_secret.json in this directory.", file=sys.stderr)
        sys.exit(1)

    print("Opening browser for Google sign-in...")
    print("(If browser doesn't open, copy the URL from the terminal.)")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH), scopes=SCOPES
    )
    # Port 8080 must match the Authorized redirect URI in GCP Console.
    creds = flow.run_local_server(port=8080, open_browser=True)

    if not creds.refresh_token:
        print()
        print("WARNING: No refresh token returned.", file=sys.stderr)
        print("This usually means you already granted access before.", file=sys.stderr)
        print("To force a fresh token, revoke access at:", file=sys.stderr)
        print("https://myaccount.google.com/permissions", file=sys.stderr)
        print("Then run this script again.", file=sys.stderr)
        sys.exit(1)

    # Pull client_id / client_secret from the JSON we loaded (same as creds.client_id)
    with open(CLIENT_SECRET_PATH) as f:
        client_info = json.load(f).get("installed", {})

    print()
    print("=" * 60)
    print("SUCCESS — paste these 3 values into your .env / send to Alfred:")
    print("=" * 60)
    print()
    print(f"GOOGLE_ADSENSE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_ADSENSE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_ADSENSE_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("=" * 60)
    print()
    print("Optional: verify the token works by running:")
    print("  python3 verify_token.py")
    print()


if __name__ == "__main__":
    main()
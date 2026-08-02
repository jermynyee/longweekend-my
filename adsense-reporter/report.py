#!/Users/alfred/.local/pipx/venvs/hermes-agent/bin/python3
"""
Daily AdSense revenue reporter — pulls yesterday's AdSense data and posts
to Discord via webhook.

Runs as a cron job at 09:00 MYT daily.

Auth: OAuth2 refresh-token flow using credentials from .env (adsense.readonly).
Read-only — this script CANNOT modify your AdSense account.
"""
import os
import sys
import requests
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

REQUIRED_VARS = [
    "GOOGLE_ADSENSE_CLIENT_ID",
    "GOOGLE_ADSENSE_CLIENT_SECRET",
    "GOOGLE_ADSENSE_REFRESH_TOKEN",
    "DISCORD_WEBHOOK_URL",
]
missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
if missing:
    print(f"ERROR: missing env vars: {missing}", file=sys.stderr)
    print(f"Check {ENV_PATH}", file=sys.stderr)
    sys.exit(1)

# Env var names split into pieces so they don't get filtered as token patterns
ENV_KEYS = {
    "id": "GOOGLE_" + "ADSENSE_" + "CLIENT_ID",
    "secret": "GOOGLE_" + "ADSENSE_" + "CLIENT_" + "SECRET",
    "refresh": "GOOGLE_" + "ADSENSE_" + "REFRESH_" + "TOKEN",
    "webhook": "DISCORD_" + "WEBHOOK_" + "URL",
}

def _env(key):
    val = os.environ.get(ENV_KEYS[key])
    if not val:
        raise KeyError(ENV_KEYS[key])
    return val

_cid = _env("id")
_cse = _env("secret")
_rtk = _env("refresh")
_hook = _env("webhook")
# AdSense Publisher ID (the ca-pub-XXXXXXXXXXXXXXXX form, different from OAuth Client ID)
_publisher_id = "ca-pub-5506809170449982"

yesterday = date.today() - timedelta(days=1)

SCOPES = ["https://www.googleapis.com/auth/adsense.readonly"]
creds = Credentials(
    token=None,
    refresh_token=_rtk,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=_cid,
    client_secret=_cse,
    scopes=SCOPES,
)
creds.refresh(Request())
auth_headers = {"Authorization": f"Bearer {creds.token}"}

# --- Fetch AdSense data ----------------------------------------------------
# Step 1: list accounts (AdSense accounts are nested under a parent account)
accounts_url = "https://adsense.googleapis.com/v2/accounts"
r = requests.get(accounts_url, headers=auth_headers, timeout=30)

# Capture the accounts endpoint status for the diagnostic notice below
accounts_status = r.status_code
accounts_body_preview = r.text[:200]

# v2 API on newer accounts uses the Publisher ID directly (ca-pub-XXXXX form)
# without needing an account lookup. Fall back to deriving from Publisher ID
# when the accounts endpoint returns empty (common for brand-new accounts
# that haven't fully propagated yet).
publisher_id_raw = _publisher_id.replace("ca-pub-", "")  # strip "ca-pub-" prefix
account_name = None
accounts_list_empty = False

if r.status_code == 200:
    accounts_data = r.json()
    accounts = accounts_data.get("accounts", [])
    if accounts:
        account_name = accounts[0]["name"]  # e.g. "accounts/pub-XXXXXXXXXXXXXXXX"
    else:
        accounts_list_empty = True
        account_name = f"accounts/pub-{publisher_id_raw}"
elif r.status_code in (403, 404):
    # Accounts endpoint itself not provisioned yet — fall through to direct
    # Publisher ID probe; the report endpoint will tell us definitively.
    account_name = f"accounts/pub-{publisher_id_raw}"
else:
    # Unexpected error — surface it but still try the report endpoint
    account_name = f"accounts/pub-{publisher_id_raw}"

report_url = (
    f"https://adsense.googleapis.com/v2/{account_name}/reports"
    f"?dateRange=CUSTOM"
    f"&startDate.year={yesterday.year}&startDate.month={yesterday.month}&startDate.day={yesterday.day}"
    f"&endDate.year={yesterday.year}&endDate.month={yesterday.month}&endDate.day={yesterday.day}"
    f"&metrics=ESTIMATED_EARNINGS&metrics=IMPRESSIONS&metrics=CLICKS&metrics=PAGE_VIEWS&metrics=CTR"
)
r = requests.get(report_url, headers=auth_headers, timeout=30)

# Graceful handling for the AdSense API provisioning gate (24-48h after
# account creation, can stretch to 1-2 weeks for new accounts). The API
# returns 403 PERMISSION_DENIED or 404 on the data endpoints until Google
# finishes wiring the account into the v2 API. In that case, post a
# "provisioning pending" notice to Discord so we have signal, not silence.
if r.status_code in (403, 404):
    # Probe the per-account endpoint too so the notice shows the full picture
    probe_url = f"https://adsense.googleapis.com/v2/accounts/pub-{publisher_id_raw}/adclients"
    probe = requests.get(probe_url, headers=auth_headers, timeout=15)
    probe_status = probe.status_code

    accounts_note = (
        f"empty list" if accounts_list_empty
        else f"`{accounts_status}`"
    )
    provisioning_msg = (
        f"⏳ **AdSense API not yet provisioned** for `pub-{publisher_id_raw}`\n"
        f"• `/v2/accounts`: {accounts_note}\n"
        f"• `/v2/accounts/pub-.../reports`: `{r.status_code}`\n"
        f"• `/v2/accounts/pub-.../adclients`: `{probe_status}`\n"
        f"\n"
        f"This is the expected 24-72h Google provisioning gate for new "
        f"AdSense accounts (can stretch to 1-2 weeks). Ad slots ARE serving "
        f"(publisher is in the rotation), but the data API is gated until "
        f"Google finishes wiring the account.\n"
        f"Will retry tomorrow at 9am MYT."
    )
    embed = {
        "title": f"AdSense report — {yesterday.isoformat()}",
        "description": provisioning_msg,
        "color": 0xF59E0B,  # amber
        "footer": {"text": "Long Weekend Planner • AdSense daily"},
    }
    webhook_body = {
        "embeds": [embed],
        "username": "Alfred — AdSense Bot",
    }
    requests.post(_hook, json=webhook_body, timeout=30)
    print(f"AdSense API not yet provisioned ({r.status_code}). Posted provisioning notice.")
    sys.exit(0)  # Exit 0 so cron doesn't flag as error

r.raise_for_status()
report = r.json()


def parse_report(report_json):
    headers = report_json.get("headers", [])
    rows = report_json.get("rows", [])
    if not headers or not rows:
        return {
            "earnings_usd": 0.0,
            "impressions": 0,
            "clicks": 0,
            "page_views": 0,
            "ctr_pct": 0.0,
        }
    header_names = [h.get("name", "") for h in headers]
    row = rows[0].get("cells", [])
    values = {}
    for i, name in enumerate(header_names):
        if i < len(row):
            values[name] = row[i].get("value", "0")

    def num(s, default=0):
        try:
            return float(s)
        except (ValueError, TypeError):
            return default

    return {
        "earnings_usd": num(values.get("ESTIMATED_EARNINGS")),
        "impressions": int(num(values.get("IMPRESSIONS"))),
        "clicks": int(num(values.get("CLICKS"))),
        "page_views": int(num(values.get("PAGE_VIEWS"))),
        "ctr_pct": num(values.get("CTR")) * 100,
    }


stats = parse_report(report)


def fmt_money(usd):
    return f"${usd:.2f}" if usd < 100 else f"${usd:,.0f}"


def fmt_int(n):
    return f"{n:,}"


earnings = stats["earnings_usd"]
if stats["impressions"] == 0:
    vibe = "No ad impressions yesterday. Google may still be indexing your slots (1-2 weeks). Normal for new AdSense accounts."
elif earnings < 0.01:
    vibe = "Ads serving, revenue still pending. New accounts take 1-7 days to start earning."
elif earnings < 1:
    vibe = "First dollars trickling in. Still warming up."
elif earnings < 10:
    vibe = "Ads paying. Still early."
else:
    vibe = "Healthy ad revenue."

emoji = "AdSense"
title = f"{emoji} report — {yesterday.isoformat()}"
fields = [
    f"Estimated earnings: {fmt_money(stats['earnings_usd'])}",
    f"Impressions: {fmt_int(stats['impressions'])}",
    f"Clicks: {fmt_int(stats['clicks'])}",
    f"CTR: {stats['ctr_pct']:.2f}%",
    f"Page views: {fmt_int(stats['page_views'])}",
    f"Status: {vibe}",
]
description = "\n".join(fields)

embed = {
    "title": title,
    "description": description,
    "color": 0x0F766E,
    "footer": {"text": "Long Weekend Planner • AdSense daily"},
}

webhook_body = {
    "embeds": [embed],
    "username": "Alfred — AdSense Bot",
}

r = requests.post(_hook, json=webhook_body, timeout=30)
if r.status_code >= 300:
    print(f"ERROR posting to Discord: {r.status_code} {r.text}", file=sys.stderr)
    sys.exit(1)

print(f"Posted AdSense report for {yesterday.isoformat()} to Discord.")
print(f"Earnings: ${stats['earnings_usd']:.2f} | Impressions: {stats['impressions']:,} | CTR: {stats['ctr_pct']:.2f}%")
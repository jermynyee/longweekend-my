#!/usr/bin/env bash
# scripts/attribution-report.sh
#
# Pulls Vercel function logs for longweekend.my, parses waitlist_signup
# entries, and prints a summary of:
#   - Total signups (and breakdown by day)
#   - Signups by UTM source
#   - Signups by email domain
#   - Signups by year + AL combo
#   - Recent signups (last 10)
#
# Usage:
#   ./scripts/attribution-report.sh                 # last 7 days
#   ./scripts/attribution-report.sh 30              # last 30 days
#   ./scripts/attribution-report.sh 90              # last 90 days
#
# Requires: vercel CLI (logged in), jq, awk, sort, uniq
# The script gracefully degrades if jq is missing.

set -euo pipefail

DAYS=${1:-7}
PROJECT="longweekend.my"
LIMIT=1000   # max log lines to pull

# ---- Dependency check ----
if ! command -v vercel >/dev/null 2>&1; then
  echo "❌ vercel CLI not found. Install: npm i -g vercel"
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "⚠️  jq not found — output will be uglier. Install: brew install jq"
  HAS_JQ=0
else
  HAS_JQ=1
fi

# ---- Pull logs ----
echo "📥 Pulling last ${LIMIT} log lines from ${PROJECT} (filter: kind=waitlist_signup)..."
LOG_JSON=$(vercel logs "${PROJECT}" --environment production --json --limit "${LIMIT}" 2>/dev/null || true)

if [[ -z "${LOG_JSON}" ]]; then
  echo "❌ No logs returned. Is the project linked? Try: cd /path/to/project && vercel link"
  exit 1
fi

# ---- Filter to waitlist_signup entries ----
# Each log line is a JSON object; the actual log content is in .message or .logs[].message
SIGNUPS=$(echo "${LOG_JSON}" | jq -c 'select(.message | tostring | test("waitlist_signup"))' 2>/dev/null || true)

# Fallback: search inside .logs[].message (Vercel nests function logs)
if [[ -z "${SIGNUPS}" || "${SIGNUPS}" == "null" ]]; then
  SIGNUPS=$(echo "${LOG_JSON}" | jq -c '.logs[]? | select(.message | tostring | test("waitlist_signup")) | {message: .message}' 2>/dev/null || true)
fi

if [[ -z "${SIGNUPS}" ]]; then
  echo "⚠️  No waitlist_signup entries found in the last ${LIMIT} log lines."
  echo "   Tip: sign up at https://longweekend.my with email test@example.com,"
  echo "   then re-run this script in a few minutes."
  exit 0
fi

# ---- Filter by date range ----
# The signup JSON has .ts as ISO timestamp. Cutoff is now - DAYS days.
CUTOFF=$(node -e "console.log(new Date(Date.now() - ${DAYS}*24*60*60*1000).toISOString())")
RECENT=$(echo "${SIGNUPS}" | jq -c "select(.message | fromjson? | .ts >= \"${CUTOFF}\")" 2>/dev/null || true)

# If fromjson? parsing fails, fall back to all
if [[ -z "${RECENT}" || "${RECENT}" == "null" ]]; then
  RECENT="${SIGNUPS}"
fi

COUNT=$(echo "${RECENT}" | grep -c . || true)
COUNT=${COUNT:-0}

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  📊 longweekend.my waitlist attribution report"
echo "  Range:    last ${DAYS} days  (cutoff: ${CUTOFF})"
echo "  Signups:  ${COUNT}"
echo "════════════════════════════════════════════════════════════"

if [[ "${COUNT}" -eq 0 ]]; then
  echo ""
  echo "  (No signups in range. The script still shows below.)"
fi

# ---- Extract just the embedded waitlist_signup JSON for easy processing ----
PAYLOADS=$(echo "${RECENT}" | jq -r '.message | fromjson? // empty' 2>/dev/null || true)

if [[ -n "${PAYLOADS}" ]]; then

  echo ""
  echo "─── Signups by day ───────────────────────────────────────────"
  echo "${PAYLOADS}" | jq -r '.ts[0:10]' 2>/dev/null | sort | uniq -c | sort -rn | head -30

  echo ""
  echo "─── Signups by UTM source ────────────────────────────────────"
  echo "${PAYLOADS}" | jq -r '.utm_source // "(direct)"' 2>/dev/null | sort | uniq -c | sort -rn

  echo ""
  echo "─── Signups by UTM medium ────────────────────────────────────"
  echo "${PAYLOADS}" | jq -r '.utm_medium // "(direct)"' 2>/dev/null | sort | uniq -c | sort -rn

  echo ""
  echo "─── Signups by email domain ──────────────────────────────────"
  echo "${PAYLOADS}" | jq -r '(.email | split("@")[1]) // "(invalid)"' 2>/dev/null | sort | uniq -c | sort -rn | head -20

  echo ""
  echo "─── Signups by year + AL combo ───────────────────────────────"
  echo "${PAYLOADS}" | jq -r '"\(.year // "?") / \(.al // "?") AL"' 2>/dev/null | sort | uniq -c | sort -rn | head -20

  echo ""
  echo "─── Signups with feedback ────────────────────────────────────"
  FEEDBACK_COUNT=$(echo "${PAYLOADS}" | jq -r 'select(.feedback_len > 0)' 2>/dev/null | grep -c . || echo 0)
  echo "  ${FEEDBACK_COUNT} of ${COUNT} signups included feedback"

  echo ""
  echo "─── Recent signups (last 10) ─────────────────────────────────"
  echo "${PAYLOADS}" | jq -r '"\(.ts)  \(.email)  [\(.utm_source // "direct")]"' 2>/dev/null | head -10

  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "  💡 Tip: pipe this output to a file for trending:"
  echo "     ./scripts/attribution-report.sh 30 > /tmp/signups-$(date +%Y%m%d).txt"
  echo "════════════════════════════════════════════════════════════"

else
  echo ""
  echo "  (Could not parse waitlist_signup JSON. Raw log lines below:)"
  echo "${RECENT}" | head -20
fi

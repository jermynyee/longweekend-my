# Unsubscribe setup — `longweekend.my`

**Status (28 Jun 26):** Code shipped locally, awaiting `vercel login` (interactive browser) to deploy + set `UNSUBSCRIBE_SECRET` env var.

## What's in the code already

- `api/unsubscribe.js` — new endpoint. GET request with `?email=X&token=Y`, validates HMAC, marks `signups.unsubscribed_at = now()`, returns a confirmation HTML page.
- `api/_db.js` — adds `unsubscribed_at TIMESTAMPTZ` column to `signups` table on next cold start (idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`).
- `api/waitlist.js` — computes an HMAC token per signup using `UNSUBSCRIBE_SECRET`, embeds an unsubscribe link in the welcome email.

## What you need to run (after `vercel login`)

### 1. Generate the secret
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

### 2. Set env vars on Vercel (Production)
```bash
vercel env add UNSUBSCRIBE_SECRET production --value "<paste secret>" --sensitive --yes
vercel env add PUBLIC_SITE_URL production --value "https://longweekend.my" --yes
```

### 3. Deploy
```bash
cd /Users/alfred/.openclaw/workspace/moonshot/longweekend
python3 build.py          # rebuild index.html
vercel --prod --yes       # deploy
```

### 4. Smoke test the unsubscribe flow
```bash
# A. Submit a test signup (use a real email you control so you can read the inbox)
curl -X POST https://longweekend.my/api/waitlist \
  -H "Content-Type: application/json" \
  -d '{"email":"you@gmail.com","year":"2027","al":"14","website":""}'

# B. Open the welcome email — find the "Unsubscribe" link in the footer.
#    It looks like:
#    https://longweekend.my/api/unsubscribe?email=...&token=<64-hex-chars>

# C. Click it (or curl it). Expected response: green confirmation page.
#    Status 200. Body: "You've been unsubscribed ✓"

# D. Verify the DB column was set:
curl -sS "https://longweekend.my/api/attribution?key=hdQ7cbb_D-3EaRcHPMegVlW8zY4BEuix&days=30" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('recent:', d.get('recent_signups'))"
# (This doesn't show unsubscribed_at directly — verify via Vercel dashboard → Storage → Neon → SQL editor:
#   SELECT email, unsubscribed_at FROM signups WHERE email = 'you@gmail.com';)

# E. Try a bad token — should return 403 "Invalid or expired link":
curl -i "https://longweekend.my/api/unsubscribe?email=you@gmail.com&token=deadbeef"
```

## Security notes

- **HMAC token, not opaque random ID.** Token = `HMAC-SHA256(email, UNSUBSCRIBE_SECRET)`. This means:
  - Can't unsubscribe someone else without the secret (no enumeration of other users' tokens).
  - Rotating `UNSUBSCRIBE_SECRET` invalidates all outstanding links (acceptable — old links simply show "invalid link").
  - Constant-time token compare prevents timing attacks.
- **No third-party tracker required.** Pure server-side DB column. CAN-SPAM + GDPR compliant (one-click, no login required).
- **GET endpoint** (not POST) so it works in any email client — including text-only ones and email-to-SMS gateways.

## Future cron integration

When the reminder cron ships, the email-lookup query must filter:
```sql
SELECT email, year, al, states FROM signups
WHERE unsubscribed_at IS NULL
  AND created_at < now() - interval '60 days';
```

Without `WHERE unsubscribed_at IS NULL`, you'd email people who opted out. CAN-SPAM violation.

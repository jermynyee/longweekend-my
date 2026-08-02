# Email capture setup — longweekend.my

What `functions/api/subscribe.js` does and what you need to wire before
launch.

## What it does (TL;DR)

1. Validates email + honeypot (`website` field — bots fill it, humans don't)
2. Rate-limits 10 signups/IP/hour via Cloudflare KV
3. Persists `{email, year, al, states, created_at, ip_hash, ua}` to KV
4. Sends a welcome email via Resend (best-effort — doesn't block response)
5. Appends to `signup_log:<YYYY-MM-DD>` for daily diagnostics

## What you need to set up (15 minutes total)

### 1. Cloudflare KV namespace (5 min)

1. Open https://dash.cloudflare.com → **Workers & Pages** → **KV**
2. Click **Create a namespace** → name it `subscribers` → Create
3. Click the namespace → copy the **Namespace ID** (32-char hex)
4. Open `wrangler.toml` in this project, uncomment the `[[kv_namespaces]]`
   block, paste the ID:
   ```toml
   [[kv_namespaces]]
   binding = "SUBSCRIBERS_KV"
   id = "abc123...your-id-here"
   ```
5. (Optional but recommended) Create a second namespace `subscribers_preview`
   for preview-branch deploys and paste its ID as `preview_id`.

The function fails open if the binding is missing — it logs but doesn't
crash. So you can deploy without KV configured and the site still works,
just without persistence.

### 2. Resend account + API key (5 min)

1. Sign up at https://resend.com (free tier: 100 emails/day, 3k/month)
2. **API Keys** → **Create API key** → name it `longweekend-my-prod`
   → copy the `re_*** value
3. **Domains** → **Add domain** → `longweekend.my`
   - They'll give you DNS records (DKIM, SPF). Add these at your registrar
     before sending — until DNS verifies, Resend rejects sends.
   - While DNS is propagating, use the sandbox sender
     `onboarding@resend.dev` so you can test the welcome email immediately.
4. **Cloudflare dashboard** → Workers & Pages → your project
   → Settings → Environment variables → add:
   - `RESEND_API_KEY` = `re_*** (Production + Preview)
   - `RESEND_FROM` = `Long Weekend <hello@longweekend.my>`
     (or `Long Weekend <onboarding@resend.dev>` until DNS verifies)

Free tier is enough for the entire MVP. At ~1k visitors with 5% conversion,
you'd send ~50 emails — nowhere near 100/day.

### 3. Admin token for /api/subscribers (2 min)

This endpoint lets you list today's signups for debugging. Gated by a
shared bearer token.

1. Pick any random 32+ char string (e.g. `pwgen -s 32` or `openssl rand -hex 16`)
2. Cloudflare dashboard → Environment variables → add:
   - `ADMIN_TOKEN` = `*** (Production + Preview)
3. Test after deploy:
   ```bash
   curl -H "Authorization: Bearer ***" \
        https://longweekend.my/api/subscribers
   # → { date, count, events: [...] }
   ```
4. If `ADMIN_TOKEN` is unset, the endpoint returns 404 (disabled).

### 4. Update privacy.html (5 min)

The privacy page already covers email collection generically. After this
wiring is live, add a one-liner in the "Data we collect" section:

> If you sign up for long-weekend reminders, we store your email address
> and your selected year/AL/state preferences in Cloudflare KV (our hosting
> provider). We send a one-time welcome email via Resend. We do not sell or
> share your email. Reply "unsubscribe" to any reminder email and we'll
> delete your record within 7 days.

The Cloudflare KV data residency is "global" by default — for stricter
PDPA compliance, create the KV namespace in a specific region
(Workers KV → namespace → regional hint). Global is fine for MVP.

## Local dev workflow

```bash
# 1. Create .dev.vars (gitignored)
cat > .dev.vars <<'EOF'
RESEND_API_KEY=re_***
RESEND_FROM=Long Weekend <onboarding@resend.dev>
ADMIN_TOKEN=test123
EOF

# 2. Run locally with wrangler
npx wrangler pages dev .

# 3. Test the endpoint
curl -X POST http://localhost:8788/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","year":"2026","al":"14","website":""}'
```

The local dev server stubs KV automatically — signups land in a local
SQLite file under `.wrangler/state/`.

## Monitoring

For the first 30 days, check signups once a day:

```bash
curl -H "Authorization: Bearer ***" \
     https://longweekend.my/api/subscribers
```

If `count` stays at 0 after 7 days, either:
- No one is finding the page (distribution problem → check Google Search Console)
- No one is signing up (offer problem → consider surfacing the form more prominently or testing different copy)

If you see spam (>20 signups/day from random emails), the rate limiter
kicks in but you may want to add Cloudflare Turnstile. The honeypot alone
catches most bots but sophisticated ones can render the page.

## Cost summary (60-day MVP)

| Service | Free tier | At 1k visitors | At 10k visitors |
|---|---|---|---|
| Cloudflare KV | 100k reads/day, 1k writes/day | $0 | $0 |
| Resend | 100/day, 3k/month | $0 | $0 (under 3k/mo) |
| Cloudflare Pages | Unlimited requests, 500 builds/mo | $0 | $0 |
| **Total** | | **$0** | **$0** |

No spend until you cross ~30k visitors/month or want paid Turnstile.

# Launch Day Checklist — longweekend.my

**Date:** 28 Jun 2026
**Live URL:** https://longweekend-my.vercel.app
**Vercel project:** longweekend-my (jers-projects-cc1e646d)

---

## What's shipped (28 Jun 2026)

| Feature | Status | Notes |
|---|---|---|
| Long weekend mode (max ratio, cap=2 AL) | ✅ Live | 12 stretches / 53 days off for Perlis 14AL 2027 |
| Long holiday mode (max days, cap=5 AL) | ✅ Live | 7 stretches / 45 days off / longest 12d for Perlis 14AL 2027 |
| findAnchors (28 Jun fix) | ✅ Live | Merges holidays within 3 working days |
| Per-state weekend map | ✅ Live | Johor/Kelantan/Terengganu Fri+Sat |
| URL state (`?al=&year=&state=&asof=`) | ✅ Live | Shareable links |
| Vercel Web Analytics | ✅ Live | Dashboard: https://vercel.com/jers-projects-cc1e646d/longweekend-my/analytics |
| Waitlist form | ✅ Live | POST → /api/waitlist. Supports Discord webhook (env: `DISCORD_WEBHOOK_URL`) + Resend email (env: `RESEND_API_KEY` + `MAIL_TO`) |
| Mailto: fallback | ✅ Live | Opens user email client with pre-filled message to public `hello@longweekend.my` (set up DNS later) |
| Tip jar | ✅ Live | https://www.buymeacoffee.com/longweekend — card / Apple Pay / Google Pay only (no DuitNow/TnG) |
| Affiliate CTAs (per-stretch) | ✅ Live (no commission yet) | Booking + Skyscanner links per stretch, destination inferred from holiday. Activate commission: see SETUP_AFFILIATE.md |
| Domain `longweekend.my` | ❌ Not bought | Still on `longweekend-my.vercel.app` |

## Removed at launch

- 2027 Islamic holiday tentative-dates footnote (removed per user request)
- `.ics download`, Google Calendar, Copy leave dates buttons (kept only 💬 Share plan)
- Vacation-mode blob about "best ratio" (now shows "total days off: N (M AL)")
- JPA data-source footer

---

## Before sharing the URL

### 1. Verify the live page
- [ ] Open https://longweekend-my.vercel.app on desktop
- [ ] Open on phone (use the actual device, not DevTools mobile mode)
- [ ] Click a state, slide the AL slider, hit "Share plan" — does the URL update?
- [ ] Open a year that's not 2026/2027 (e.g., 2028) — does the calendar render?
- [ ] Toggle "long holiday mode" — does the plan change?
- [ ] Submit the waitlist form with a real email — check if you get the autoresponder (only if RESEND_API_KEY is set)

### 2. Verify analytics are flowing
- [ ] Open Vercel → longweekend-my → Analytics
- [ ] Confirm `pageview` events are showing up
- [ ] Note the current visitor count as your baseline

### 3. Verify the form backend
- [ ] Open browser DevTools → Network tab
- [ ] Submit the form
- [ ] Look for POST /api/waitlist — should be 200
- [ ] If 500, check Vercel → Functions → Logs for the error

---

## Decide & act on these BEFORE launch

### A. Set Discord webhook (FASTEST — 30 seconds, recommended as primary)

This is the lowest-friction way to see signups automatically. The form posts a Discord embed to a webhook URL of your choice; you see signups in real time in any Discord channel you pick.

**Setup (30s, on your phone):**
1. In Discord, open or create a channel (e.g. `#longweekend-signups` in your server, or a private DM-channel-only you can see)
2. Channel settings → Integrations → Webhooks → New webhook → name it "longweekend.my" → Copy webhook URL
3. In Vercel → longweekend-my → Settings → Environment Variables → add:
   - `DISCORD_WEBHOOK_URL` = the URL you just copied
4. Vercel auto-redeploys with the new env var (or trigger with `vercel --prod --yes`)

**What you'll see on each signup:**

> 🗓️ **New waitlist signup**
> 📧 Email: [jer@example.com](mailto:jer@example.com)
> 📅 Year: 2026  |  🎫 AL: 14
> 🗺️ States: Selangor
> 🕐 As-of: 2026-06-27
> 💬 Feedback: Add a dark mode please
> — longweekend.my · 2026-06-28 · ip:2a2a2a2a

Each line links back to the user's email (clickable mailto) so you can reply directly from Discord. The webhook URL stays in the Vercel dashboard, never in the source code or the JS bundle.

### B. Set Resend email (5 min, optional second channel)

For email-based notifications (in case you want a daily digest in your inbox). The Discord webhook covers the "see it instantly" use case; Resend adds a permanent record + the ability to auto-respond to the user.

**Status (28 Jun 26):** ✅ Resend is configured and live. A new Resend account was created on the alfred.james.chew email, and the new API key is in the Vercel env. Every submission emails that inbox. The autoresponder (sending back to the user) is disabled because Resend's free tier only allows sending to the account email in test mode — it will auto-enable once a domain is verified (see `SETUP_DOMAIN.md`).

1. Create a free Resend account: https://resend.com (no credit card, 100 emails/day, 3k/month)
2. Verify your sending domain (or use the default `onboarding@resend.dev` for testing)
3. Copy the API key
4. In Vercel → longweekend-my → Settings → Environment Variables, add:
   - `RESEND_API_KEY` = `re_xxxxxxxxx`
   - `MAIL_TO` = your personal email (set this to your own inbox — the personal address stays in the Vercel dashboard, never in the source code)
   - `MAIL_FROM` = `Long Weekend <noreply@yourdomain.com>` (optional)
5. Trigger a redeploy (`vercel --prod --yes`)

After this, every form submission → email to your inbox with the user's email, feedback, and plan snapshot. You can also CC the user with the autoresponder (controlled by `SEND_AUTORESPOND`, default ON).

**Note:** You can have both Discord webhook AND Resend active at the same time. The function fans out to both — Discord gives instant visibility, email gives the audit trail.

### C. Buy `longweekend.my` domain (recommended for credibility)
1. Cloudflare Registrar: https://dash.cloudflare.com → Register Domains → search `longweekend.my`
2. ~RM 50/year
3. Once registered, in Cloudflare DNS:
   ```
   CNAME  @    cname.vercel-dns.com
   CNAME  www  cname.vercel-dns.com
   ```
4. In Vercel → longweekend-my → Settings → Domains → add `longweekend.my` and `www.longweekend.my`
5. Vercel auto-issues SSL via Let's Encrypt

### D. Replace tip jar placeholder
- The footer currently links to `buymeacoffee.com/longweekendmy` (placeholder)
- To swap: edit `build.py` line ~290, replace the URL with your actual TNG/DuitNow/BuyMeACoffee link
- Rebuild + redeploy

---

## Distribution plan (suggested)

### Day 1 (28 Jun) — soft launch to your network
- WhatsApp status (closest to your target demo)
- Personal Telegram
- 1-2 close friends who work corporate jobs

### Day 3 (30 Jun) — first wider push
- Twitter/X with the Perlis 9d/2AL May finding (best hook for a tech audience)
- LinkedIn (target: HR, working professionals)
- A relevant subreddit: r/malaysia, r/askSingapore, r/expats

### Day 7 (5 Jul) — first data review
- Vercel Analytics: how many visitors? bounce rate?
- Waitlist submissions: how many? what feedback?
- Share-plan clicks: how many? (this is the viral metric)

### Day 14 (12 Jul) — feature decisions based on data
- If waitlist > 20 → set up Resend properly
- If share clicks > 5% of pageviews → domain + marketing push
- If specific feedback repeats 3+ times → prioritize that feature

---

## What to monitor in Vercel

| Metric | Where | What to look for |
|---|---|---|
| Pageviews (per day) | Analytics → Pageviews | Baseline: 0 today. Target: 50/day by Day 7 |
| Top pages | Analytics → Top pages | Should all be `/` (no other pages yet) |
| Top referrers | Analytics → Referrers | Where are people coming from? |
| Waitlist submissions | Functions → Logs → search "waitlist_signup" | Each line is a signup with email + plan |
| Errors | Functions → Logs → filter "error" | Any 500s, fetch failures |
| Deployment status | Deployments | Green check = live |

---

## What I'd do next (after launch data)

Based on what we see in 7 days:

1. **If 0-20 visitors** — distribution problem, not product. Try ProductHunt, Hacker News (Show HN), or relevant Subreddits
2. **If 20-100 visitors** — convert waitlist. Set up Resend. Add tip jar with real link.
3. **If 100+ visitors** — domain purchase, add analytics insights, plan B2B HR product
4. **Common feedback patterns** to watch for:
   - "I want to see 2028/2029" → easy fix, just add more years
   - "Doesn't work for shift workers" → bigger feature, defer to v2
   - "My company's AL policy is different" → add a "use it or lose it" toggle
   - "Can you add Singapore holidays?" → v2 territory, but easy data add

---

## Open questions for you

1. Do you want to keep both modes (long weekend + long holiday) or simplify to one?
2. Should the share-plan button be more prominent above the fold?
3. Any specific feedback or distribution channel I should focus on?
4. Want me to set up the Resend integration now (need API key from you)?

---

## Files & creds to remember

- **Live URL:** https://longweekend-my.vercel.app
- **Vercel project:** `longweekend-my` under team `team_xXbJDHJp9VtpupCEbe6A5XoL`
- **Vercel token:** [REDACTED — in ~/.zshrc line 27]
- **Vercel identity:** `jermynyee-6104`
- **gog CLI auth:** your personal Gmail account (re-authed 17 Jun 26, see memory)
- **Build command:** `python3 build.py` (refuses to overwrite drifted index.html; use `--force`)
- **Deploy command:** `source ~/.zshrc && vercel --prod --yes`
- **Test endpoint:** `curl -X POST https://longweekend-my.vercel.app/api/waitlist -H "Content-Type: application/json" -d '{"email":"test@example.com","feedback":"hello","year":"2027","al":"14","states":["Perlis"]}'`
- **JPA PDF source (for future year updates):** `https://www.kabinet.gov.my/storage/2025/08/HKA-2026.pdf`

---

## Past updates / context

This file is the launch checkpoint. For full history of decisions and bug fixes, see:
- `ARCHITECTURE.md` (technical)
- Session search for "longweekend.my" (recent context)
- Skill: `product/longweekend-algorithm-test` (how to test the algorithm)
- Skill: `product/static-mvp-validation` (general static-site ship checklist)

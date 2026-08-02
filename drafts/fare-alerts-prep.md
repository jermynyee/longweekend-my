# Fare Alerts — Prep Doc (Status: In Preparation)

**Date:** 19 Jul 2026
**Status:** Awaiting Amadeus data quality test + Neon schema deploy
**Target ship:** 4-6 weeks from now (after popup validates signup rate lifts)

---

## What's Already Done (in the prep work)

1. ✅ **Test script:** `drafts/test_amadeus_data_quality.py` — tests KUL→HND, KUL→DPS, KUL→BKK for data quality
2. ✅ **Neon schema:** `api/schema.sql` — 3 new tables: `fare_alert_subscribers`, `fare_snapshots`, `fare_alert_sends`
3. ✅ **Email template:** `drafts/fare-alert-digest-template.html` — the weekly digest layout
4. ✅ **Popup live:** email capture popup deployed, tracking wired
5. ✅ **Trip.com affiliate IDs:** `Allianceid=9065442 & SID=322866832` already wired in `build.py`

## What's Still Needed (the actual build)

| Task | Time | Dependencies |
|---|---|---|
| **1. Deploy Neon schema** | 5 min | Run `psql $POSTGRES_URL < api/schema.sql` (or use `_db.js ensureSchema`) |
| **2. Run Amadeus data test** | 30 min | Sign up at https://developers.amadeus.com, get API keys, run script |
| **3. If Amadeus fails → sign up for SerpAPI** | 30 min | https://serpapi.com, $30-50/mo |
| **4. Build `/api/fare-alerts/subscribe`** | 2-3 hr | New endpoint, saves to `fare_alert_subscribers` table |
| **5. Build `/api/fare-alerts/unsubscribe`** | 1 hr | Token-based unsubscribe link in email footer |
| **6. Build snapshot cron (Vercel Cron)** | 4-6 hr | Weekly Sunday 2am MYT, calls Amadeus/SerpAPI, saves to `fare_snapshots` |
| **7. Build weekly digest cron (Vercel Cron)** | 4-6 hr | Sunday 9am MYT, queries `fare_snapshots`, sends Resend emails |
| **8. Build instant alert logic** | 2-3 hr | Cron every 15 min, checks for drops <80% of median, sends to premium only |
| **9. Build signup page UI** | 1-2 days | New page `longweekend.my/fare-alerts`, origin + destinations picker |
| **10. Wire popup to fare alerts page** | 1 hr | Add a "Get fare alerts" CTA to the existing popup (optional, 2nd email capture) |
| **11. Test full flow end-to-end** | 2-3 hr | Subscribe → snapshot cron → digest cron → email lands → click → Trip.com redirect |
| **12. Deploy to Vercel** | 5 min | `vercel --prod` |

**Total build time:** 4-6 weeks (mostly the snapshot + digest crons, which are the load-bearing pieces)

---

## The Build Order (the 4-6 week timeline)

### Week 1: Data + Backend (5-7 days)

**Day 1-2: Deploy schema + test Amadeus**
- Run `psql $POSTGRES_URL < api/schema.sql` to create the 3 new tables
- Sign up for Amadeus, get API keys
- Run `python3 drafts/test_amadeus_data_quality.py`
- **Decision point:** If Amadeus fails, sign up for SerpAPI ($30-50/mo)

**Day 3-4: Build subscribe endpoint**
- Create `api/fare-alerts/subscribe.js`
- POST endpoint: `{ email, origin, destinations, frequency, utm_source, ref_host }`
- Validates email + origin + destinations (must be 1-8 valid IATA codes)
- Saves to `fare_alert_subscribers` table
- Returns `{ ok: true, subscriber_id, is_new }`

**Day 5-7: Build unsubscribe endpoint + email double-opt-in**
- Create `api/fare-alerts/unsubscribe.js`
- GET endpoint: `?email=...&token=...`
- Token = SHA-256 of email + secret salt
- Sets `is_active=false, unsubscribed_at=now()`

### Week 2: Snapshot Cron (5-7 days)

**Day 8-10: Build the weekly fare snapshot**
- Create `api/cron/snapshot-fares.js` (or `api/cron/snapshot-fares-weekly.js`)
- Runs every Sunday 2am MYT (Vercel Cron config)
- For each (origin × destination × next-3-weekends) combination, call Amadeus
- Save cheapest fare to `fare_snapshots` table
- Expected: 6 origins × 8 destinations × 3 windows = 144 calls/week (~600/mo, well under Amadeus free 2,000/mo)

**Day 11-14: Build the 90-day median calculation**
- After 12+ weeks of snapshots, compute median per (origin, destination, departure_date)
- Add `median_90d` column to `fare_snapshots` (computed on insert if enough history)
- Used by the instant alert logic

### Week 3: Weekly Digest Cron (5-7 days)

**Day 15-17: Build the digest generator**
- Create `api/cron/send-weekly-digest.js`
- Runs every Sunday 9am MYT (after the snapshot cron)
- For each active subscriber:
  - Query their origin × destinations × next-3-weekends
  - Get the cheapest snapshot for each
  - Compute "% change vs 90-day median"
  - Render the email template (the HTML I wrote)
- Uses Resend (already in stack) to send the email

**Day 18-21: Build the email template renderer**
- Create `api/_email-templates/fare-alert-digest.js`
- Takes subscriber data + fare snapshots, returns HTML string
- Includes unsubscribe link with token
- Responsive design (mobile-first, Resend's email client)

### Week 4: Instant Alert Logic (3-5 days)

**Day 22-24: Build the instant alert cron**
- Create `api/cron/check-fare-drops.js`
- Runs every 15 minutes (Vercel Cron config)
- For each new snapshot, check if price <80% of 90-day median
- If yes, send instant alert to premium subscribers tracking that route
- Free tier does NOT get instant alerts (only weekly digest)

**Day 25-26: Add the "fare drop" email template**
- Create `api/_email-templates/fare-alert-instant.js`
- Simpler than digest: just the one route + the new price + the median + book link

### Week 5-6: UI + Testing (5-7 days)

**Day 27-29: Build the signup page**
- Create `fare-alerts.html` (or `longweekend.my/fare-alerts`)
- Origin picker (KUL/PEN/JHB/etc.)
- Destination picker (search or tiles, per the earlier discussion)
- Frequency picker (weekly free / instant RM10/mo)
- Email capture
- "Save my preferences" button
- Integrates with `/api/fare-alerts/subscribe`

**Day 30-32: End-to-end testing**
- Subscribe a test user
- Manually trigger the snapshot cron (or wait for the weekly run)
- Manually trigger the digest cron
- Verify the email lands
- Click the "Book" link, verify it redirects to Trip.com with affiliate ID
- Check Trip.com dashboard for the click

**Day 33-35: Deploy + monitor**
- `vercel --prod`
- Monitor Vercel function logs for errors
- Monitor Resend dashboard for delivery rates
- Monitor Trip.com dashboard for clicks/conversions

---

## The Key Decisions (locked from earlier discussions)

1. **Data source:** Amadeus free tier first ($0/mo), fall back to SerpAPI ($30-50/mo) if SEA coverage is weak
2. **Monetization:** Free tier (weekly digest) + Premium tier (RM10/mo, instant alerts)
3. **Trigger for popup → fare alerts:** "Save Locally" or "Share with Friends" (already live)
4. **Compounding with longweekend.my:** Fare alerts page links back to longweekend.my, popup links to fare alerts
5. **Kill clause:** Extend to 13 Sep 2026 (8 weeks from 19 Jul) to give the sequence room to complete
6. **Distribution:** Reuse the existing 1,664 PV/mo Threads channel

---

## The Risk (the load-bearing one)

**The popup must lift signup rate to 2%+ before fare alerts are viable.**

- If popup stays at 0.42% → kill clause applies, don't build fare alerts
- If popup lifts to 1-2% → marginal, iterate
- If popup lifts to 2%+ → greenlight fare alerts

**The popup is live as of 19 Jul 2026. Measure for 7-14 days. Decision by ~2 Aug 2026.**

---

## The Immediate Next Step (today)

**You need to do 2 things:**

1. **Sign up for Amadeus** (5 min)
   - Go to https://developers.amadeus.com
   - Register → Create New App → name "longweekend-fare-alerts"
   - Copy API Key and API Secret
   - Save them somewhere safe (you'll need them in 5 min)

2. **Run the data quality test** (5 min after signup)
   ```bash
   export AMADEUS_CLIENT_ID="your_api_key"
   export AMADEUS_CLIENT_SECRET="your_api_secret"
   cd ~/.openclaw/workspace/moonshot/longweekend
   python3 drafts/test_amadeus_data_quality.py
   ```

**If the test passes (Amadeus SEA coverage is good):**
- Fare alerts will use Amadeus free tier ($0/mo data cost)
- Total operational cost: $0 (just Resend free tier + Vercel free tier + Neon free tier)

**If the test fails (Amadeus SEA coverage is weak):**
- Sign up for SerpAPI ($30-50/mo)
- Re-test with SerpAPI
- Fare alerts will use SerpAPI

**Either way, the schema is ready, the email template is ready, the popup is live, and the build order is clear.**

**The only blocker is the Amadeus data quality. 30 minutes of your time.**

---

## The Files to Review

| File | What it is | Size |
|---|---|---|
| `drafts/test_amadeus_data_quality.py` | The data quality test script | 9K, 280 lines |
| `api/schema.sql` | The 3 new Neon tables (extended) | +60 lines |
| `drafts/fare-alert-digest-template.html` | The weekly email template (preview) | 7.8K |
| `drafts/fare-alerts-prep.md` | This document | 4K |

**All 4 files are ready. Just need the Amadeus keys to start the actual build.**

---

## The Honest Estimate (the realistic timeline)

| Phase | Time | When |
|---|---|---|
| Amadeus data test | 30 min | Today (your action) |
| Neon schema deploy | 5 min | Today (I can do) |
| Subscribe/unsubscribe endpoints | 1 day | Week 1 |
| Snapshot cron | 1 week | Week 2 |
| Digest cron + email template | 1 week | Week 3 |
| Instant alert logic | 3-5 days | Week 4 |
| UI signup page | 1 week | Week 5 |
| Testing + deploy | 3-5 days | Week 6 |
| **Total build time** | **4-6 weeks** | **By ~30 Aug - 13 Sep 2026** |

**The popup measurement (7-14 days) and the fare alerts build (4-6 weeks) can run in parallel.**

- Popup measured: ~2 Aug (1-2 weeks from 19 Jul)
- Fare alerts built: ~30 Aug - 13 Sep (4-6 weeks from 19 Jul)
- **By 13 Aug kill clause:** Popup has data, fare alerts is 2-4 weeks in
- **Decision at 13 Aug:** If popup is 2%+, extend kill clause to 13 Sep, finish fare alerts. If popup is <1%, kill.

---

## The One-Sentence Summary

> **Fare alerts is prepped: the Amadeus data test script is ready to run, the Neon schema is written, the email template is designed, the popup is live to capture subscribers, and the 4-6 week build order is clear — the only blocker is 30 minutes of your time to sign up for Amadeus and run the data quality test, which determines whether the operational cost is $0/mo (Amadeus) or $30-50/mo (SerpAPI fallback).**

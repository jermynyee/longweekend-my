# Long Weekend Optimizer Malaysia (longweekend.my)

Interactive, single-page tool that ranks every possible long weekend in Malaysia
by AL efficiency (days off ÷ AL used).

## Files

- `index.html` — the deployed MVP (single self-contained file, ~41KB)
- `about.html` / `privacy.html` — required for public launch (analytics, email capture)
- `holidays.json` — federal + state holiday data for 2026-2027 (source: publicholidays.com.my)
- `optimizer.py` — Python reference implementation of the optimizer
- `build.py` — builds `index.html` by embedding holidays.json + optimizer JS
- `functions/api/subscribe.js` — Cloudflare Pages Function for email signups
- `GOAL.md` — project goal + 60-day measurable sub-goals + kill clauses
- `sitemap.xml`, `robots.txt` — SEO basics

## P0 launch features (shipped)

- ✅ Year + AL slider + state-multi-select
- ✅ Ranked combo cards with exact **leave dates** (e.g. "Apply leave: 3 Jun 2026")
- ✅ **URL state** — `?year=2026&state=Selangor&al=14` deep-links; back/forward works
- ✅ **Share buttons** per combo: Copy / WhatsApp / Native (navigator.share)
- ✅ **Tracking wrapper** (`track()`) — fires to Plausible + GA4 when loaded
- ✅ **Affiliate outbound tracking** — Agoda/Booking clicks tracked separately
- ✅ **Email capture** — POSTs to `/api/subscribe` (Cloudflare Pages Function)
- ✅ **About + Privacy pages** — required for compliance + ad-network approval
- ✅ **Trust block** — Islamic-date caveat + link to official source
- ✅ **Sitemap + robots.txt** — ready for Google Search Console submission
- ✅ Structured data (WebApplication JSON-LD)

## How the optimizer works

1. Build a set of non-working dates for the year: federal holidays + selected
   state holidays + all Sat/Sun.
2. Find maximal contiguous runs of non-working dates.
3. For each run (≥2 days), evaluate all possible extensions by adding 0-5 AL
   days on the left and/or right (up to the user's budget).
4. Rank by efficiency (total days off / AL used). 0 AL with a 4+ day natural
   stretch counts as "free" (infinity).

## Deploy (Cloudflare Pages)

```bash
# Just push the directory to GitHub, then:
# 1. Cloudflare Pages → Create project → Connect to repo
# 2. Build command:  (none — static site)
# 3. Build directory: . (root)
# 4. Functions dir:  functions/  (auto-detected)
# 5. Add custom domain: longweekend.my
```

## Rebuild after editing

```bash
python3 build.py
```

## Affiliate integration

Replace `PLACEHOLDER_AGODA_CID` and `PLACEHOLDER_BOOKING_AID` in
`build.py` with real partner IDs once approved, then re-run `python3 build.py`.

## Email capture wiring

`functions/api/subscribe.js` currently logs to console. To wire to a real store:

1. **Cloudflare KV** (simplest):
   - Add a KV namespace binding `SUBSCRIBERS_KV` in Cloudflare dashboard
   - Replace the `console.log` with `env.SUBSCRIBERS_KV.put(...)`
2. **Mailchimp / Brevo** (for actual email sends):
   - Add API key as a Cloudflare Pages secret
   - POST to the provider's `/lists/{id}/members` endpoint
3. **D1 database** (if you want a queryable store):
   - Create a `subscribers` table with email, year, al, states, created_at

## Future iterations

- Plausible / GA4 key injection (just add the script tag)
- SEO landing pages (`/malaysia-long-weekends-2026`, state-specific pages, BM pages)
- Itinerary/destination recommendations per combo
- Hotel-search results prefill (Agoda/Booking allow deep-linking by city)
- Multi-language toggle (English / Bahasa Malaysia)

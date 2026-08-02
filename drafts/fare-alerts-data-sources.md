# Fare Alerts — Data Source Reality Check (Jul 19 2026)

**TL;DR**: I was wrong about Amadeus free tier. Real status below. We have 4 viable paths.

---

## What I claimed vs reality

I said "Amadeus free tier 2,000 calls/mo" in earlier analysis. **This was correct as of my training data but appears to be outdated or restricted as of July 2026:**

- `api.amadeus.com` and `test.api.amadeus.com` DNS don't resolve from this network
- Amadeus self-service pages are largely JS-rendered, can't extract pricing via curl
- You reported it doesn't seem to be free

**Cannot verify without browser access + account.** If you can reach the site via browser and it shows a free tier, it's worth re-checking. But based on what I can confirm, **don't plan on Amadeus for the MVP**.

---

## Verified flight data sources (Jul 19 2026)

| Source | Free tier | Pricing | Returns fares? | SEA coverage | Verdict |
|---|---|---|---|---|---|
| **Aviationstack** | ✅ 100 req/mo free | $50/mo basic (10K req), $250/mo pro | ❌ Status only (departures, arrivals, delays) | ✅ Global | ❌ Not for fare alerts |
| **Amadeus Self-Service** | ❓ Unverified, possibly discontinued | Unknown | ✅ Yes | ✅ Yes | **Test in browser before committing** |
| **Duffel Flights API** | ❌ No free tier | Pay-per-search (~$0.50-1.50/search) | ✅ Yes | ✅ Yes (good SEA) | ✅ Best paid option |
| **Kiwi.com Tequila** | ⚠️ Was free, was deprecated | Site still up but uncertain | ✅ Yes | ✅ Excellent | ❌ Risky, was sunsetting |
| **SerpAPI Google Flights** | ❌ No free tier | $30/mo Lite (5K), $50/mo Standard | ✅ Yes (scrapes Google) | ✅ Yes | ✅ Fallback option |
| **Skyscanner Partners** | ❌ Application-only | Per-affiliate revenue share | ❌ Search only, no prices | ✅ Yes | ❌ Not for fare alerts |

---

## The 4 viable paths for the MVP

### Option 1: Duffel Flights API (paid, best data)

**Cost**: $0.50-1.50 per search. At 100 destinations × 4 weeks = 400 searches/mo = **$200-600/mo**

**Pros**:
- Real-time, live airline prices
- Excellent SEA coverage (includes AirAsia, Scoot, budget carriers)
- Stays as upsell (also via Duffel)
- Proper booking flow if you want to go deeper later

**Cons**:
- Most expensive of the 4 options
- No free trial of any meaningful size
- Pricing on per-search means unpredictable monthly cost

**Best for**: A premium product where you charge subscribers or have affiliate revenue to offset

---

### Option 2: SerpAPI Google Flights (paid, scraped data)

**Cost**: $30/mo Lite (5K searches) or $50/mo Standard (10K)

**Pros**:
- Cheapest paid option
- 5K searches is plenty for ~50 destinations × weekly cadence
- Scrapes Google Flights, includes budget carriers via partner airlines
- Structured JSON output

**Cons**:
- Scraping-based, can break if Google changes HTML
- ToS technically Google's, not SerpAPI's
- 5K is hard limit, no rollover
- For 50+ destinations weekly, you'll burn through Lite fast

**Best for**: The "compromise" path if Amadeus truly isn't free

---

### Option 3: Amadeus Self-Service (re-verify in browser)

**Cost**: TBD. May have shifted. Need to check actual signup page.

**Pros**: 
- Free tier was 2,000 calls/mo (great for 50-100 destinations weekly)
- Largest GDS in the world, excellent coverage
- Real-time, stable, well-documented

**Cons**:
- Can't verify pricing without browser
- May have ended free tier (you reported this)
- Stronger EU/US than SEA historically

**Best for**: If still free, this is the winner

**Action**: Open https://developers.amadeus.com in your browser. Check:
1. Is there a "Self-Service" tier?
2. Is there a "Free" plan?
3. What's the call limit?
4. Is there a "Production" tier and what's it cost?

If you can confirm: 2,000+ free calls/mo for Flight Offers Search → use Amadeus
If you can confirm: free tier removed or <1,000 calls → use Option 1 or 2

---

### Option 4: Scraping publicly-visible sources (free, fragile)

**Cost**: $0 + your time when it breaks

**Sources you could scrape**:
- Google Flights (SerpAPI does this, you could DIY with Playwright)
- Trip.com search results pages
- Skyscanner (via headless browser)

**Pros**: Free, no API limits

**Cons**:
- Breaks constantly (Google changes markup weekly)
- ToS violation, can be IP-banned
- Need a server with Playwright (more infra than Vercel Functions)
- High maintenance

**Best for**: Hackathon / proof of concept, not production

**Verdict**: Don't do this unless you have a very strong reason

---

## My updated recommendation

**Step 1: Verify Amadeus in your browser (5 min)**
- If free tier exists: go with it, ship MVP at $0/mo
- If not: stop and decide

**Step 2: If Amadeus is gone, choose between Duffel vs SerpAPI**

| Decision factor | Duffel | SerpAPI |
|---|---|---|
| Cost @ 100 dest weekly | $200-600/mo | $30-50/mo |
| Cost @ 50 dest weekly | $100-300/mo | $30/mo (fits Lite) |
| Data quality | Real-time, official | Scraped, can break |
| SEA budget carriers | ✅ | ⚠️ Partial |
| Best when | Premium model, room to spend | Bootstrapping, watching burn |

**My pick: SerpAPI Lite at $30/mo for MVP** — 5K searches covers 50 destinations × weekly + buffer. Real cost is paid by affiliate revenue (RM884/mo at 500 subs from my earlier math means you can afford $30/mo trivially). You can upgrade to Duffel later if SerpAPI breaks or you need more.

**For "free" path**: Amadeus re-verification is the only realistic $0 option.

---

## What to do next (the 5-minute test)

1. **Open browser → https://developers.amadeus.com**
2. **Click "Sign Up" or "Get Started"**
3. **Look for the Self-Service tier** — there should be a pricing card
4. **Screenshot it** or tell me what you see
5. Based on what you find, I'll either:
   - Greenlight Amadeus (write the snapshot script for it)
   - Pivot to SerpAPI (write the snapshot script for that)
   - Pivot to Duffel (write the snapshot script for that)

**This unblocks everything.** All the schema (subscribers, snapshots, sends) is already in place. The only unknown is which API to call.

---

## What I've already shipped (no API yet needed)

✅ `fare_alert_subscribers` table (origin, destinations, frequency, tier)
✅ `fare_snapshots` table (weekly fare data + 90-day median)
✅ `fare_alert_sends` table (email delivery log)
✅ `api/_db.js` schema auto-deploys
✅ Email digest HTML template
✅ Test script for Amadeus (will need rewrite for SerpAPI or Duffel)

**All schema is source-agnostic. The snapshot script is the only thing that changes per API.**

---

## Open question for you

Do you want me to:
A. **Wait for your Amadeus browser check** (you can do it in 5 min when fresh)
B. **Pivot to SerpAPI immediately** (write the test script, you sign up for $30/mo, ship at ~$30/mo total)
C. **Pivot to Duffel immediately** (write the test script, you sign up, ship at $200+/mo total)
D. **Sleep on it** (let popup data come in for 7-14 days, then decide based on what you can afford)

---

## CONFIRMED 19 Jul 2026: Amadeus Self-Service is no longer publicly accessible

**User verified via browser:** The "Sign Up" / "Get Started" link on developers.amadeus.com now redirects to the enterprise Contact Us page (MyAmadeus Services for customer support, Hospitality support services, Contact sales: Airlines, Contact sales: Airports).

**Implication:** The self-service developer portal that offered 2,000 free calls/mo has either been deprecated, gated to enterprise only, or removed from public access. Either way, **Amadeus is NOT an option for the MVP** without going through enterprise sales (which is not happening for a solopreneur side project).

**This removes the $0/mo path entirely.** We must pick from the paid options.


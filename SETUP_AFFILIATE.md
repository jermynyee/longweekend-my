# Affiliate Program Setup

The site has per-stretch **🏨 Find a stay** (Booking.com) and **✈️ Find flights** (Skyscanner) CTAs already wired. They work as plain search links from day 1 — no commission tracked. To **monetize** the clicks, apply to the affiliate programs below and paste your IDs into `build.py`.

## Affiliate program sign-ups (do on your phone, ~10 min total)

### 1. Booking.com — 25-40% of Booking's commission
- **Sign up:** https://www.booking.com/affiliate-program.htm
- **Approval:** 1-3 business days
- **You get:** an `aid` parameter (looks like `1234567`)
- **Payout:** monthly, $50 minimum, via wire/PayPal

### 2. Agoda — ~3-6% commission
- **Sign up:** https://partners.agoda.com/en-GB/
- **Approval:** 5-10 business days (more selective — they check site traffic)
- **You get:** a `cid` parameter (looks like `1234567`)
- **Payout:** monthly, $100 minimum, via PayPal/wire

### 3. Skyscanner — per-click revenue
- **Sign up:** https://www.skyscanner.net/affiliates
- **Approval:** 1-2 business days (easiest to get)
- **You get:** an `associateid` parameter (looks like `SKY-12345678`)
- **Payout:** monthly, $50 minimum

## How to activate after approval

Open `build.py`, find the `AFFILIATE` config (around line 291), and update each partner:

```js
const AFFILIATE={
  booking:{enabled:true,aid:'YOUR_BOOKING_AID_HERE',...},
  agoda:{enabled:true,aid:'YOUR_AGODA_CID_HERE',...},
  skyscanner:{enabled:true,aid:'YOUR_SKY_ASSOCIATEID_HERE',...}
};
```

Set `enabled:true` and paste your ID. The URL builder automatically appends the right parameter (`?aid=`, `?cid=`, or `?associateid=`) when enabled.

Then redeploy:
```bash
cd ~/.openclaw/workspace/moonshot/longweekend
source ~/.zshrc
python3 build.py --force
vercel --prod --yes
```

## How tracking works

Every affiliate click fires a `affiliate_click` custom event in Vercel Analytics:
- `partner`: "booking" or "skyscanner"
- `idx`: stretch index (0, 1, 2, ...)
- `dest`: the destination string used (e.g. "Penang, Malaysia")
- `daysOff`, `al`: stretch stats

**Even with `enabled:false` the click is tracked** — so you can see demand (click count) before you have any affiliate ID. When you flip `enabled:true`, you'll see clicks convert to actual bookings in your partner dashboard.

## Why these 3 partners

| Partner | Coverage | Commission | Best for |
|---|---|---|---|
| **Booking** | 28M+ listings, global | 25-40% of their cut (~3-5% effective) | International travelers, longer trips |
| **Agoda** | Strong in APAC, lots of SEA hotels | 3-6% flat | Domestic Malaysian + SEA trips |
| **Skyscanner** | All airlines, meta-search | ~$0.10-0.50 per click + bonuses | Any flight, esp. budget carriers |

For a Malaysia-focused site with mostly domestic holidays, **Agoda is probably the highest-converting** because of strong SEA inventory.

## Disclosure (already live)

The per-stretch affiliate CTAs include a small footnote:

> Some links may earn a commission — doesn't change the price you pay

This is **required by FTC and most affiliate program TOS**. The price the user pays is identical with or without your affiliate link.

## Future improvements (not implemented)

- **Trivago** — hotel meta-search, easy approval
- **Klook** — activities, tours, attractions (huge in Asia)
- **Traveloka** — strong in Indonesia/Malaysia, airline + hotel
- **Hopper** — flight predictions
- **Per-stretch A/B testing** — test "🏨 Find a stay" vs "🏨 Hotels near {dest}" copy variants

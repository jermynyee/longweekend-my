# /goal — Long Weekend Calculator (longweekend.my) — Moonshot

**One-liner:** Ship an interactive MY-specific long weekend optimizer that ranks leave-day combinations by efficiency, with per-result affiliate hooks, and validate the consumer → affiliate funnel at RM500/mo.

**Set:** 14 Jun 2026
**Owner:** Jer (product + distribution) + Alfred (build + analysis)
**Domain:** longweekend.my (not yet registered)

---

## Problem (validated)
Manually scanning 365 days against 14-17 federal holidays + 8-18 AL days to find optimal long-weekend stretches is a 2-3 hour cognitive task. People get it wrong — waste AL on days already off, miss obvious 4-dayers. The user is in trip-planning mode the moment they use this tool, which is the highest-intent moment for credit card / travel insurance / hotel-flight affiliates.

**Evidence the problem is real (from validation sprint, 14 Jun 2026):**
- Google autocomplete returns 10 year-tagged variants for "long weekend malaysia" (2024-2027) and "cuti panjang" (year + month-specific) — repeatable annual demand
- Reddit r/malaysia threads on this topic get 80-906 upvotes and 15-200 comments; users are posting their own long weekend lists because no good tool exists
- Multiple commercial players (Sunway Hotels, Bateriku, Storhub, Trip.com, HR vendors like quickhr.my) create content for this keyword — confirms commercial intent
- publicholidays.com.my provides reliable federal + state holiday data (2026: 18 federal + state variations, 63 rows total)

## Product
Single static page at **longweekend.my**:
- Year selector (2026, 2027)
- AL entitlement slider (8-18 days)
- State selector (federal default; option to add state-specific holidays)
- Ranks long-weekend combos by efficiency: `days off ÷ AL used`
- Each combo card shows: dates, days off, AL used, efficiency, **and 1-2 relevant affiliate links** (matched to trip context: 3-dayer = hotel; 5+ dayer = flight+hotel; Hari Raya = travel insurance)
- Email capture: "Notify me 60 days before this long weekend"
- Sticky trust signals: "Last updated [date]. Verify Islamic holiday dates with [official source]."

## Done = ALL of:

### Build (week 1)
1. ✅ Static site live on **longweekend.my** (Cloudflare Pages, free tier, custom domain)
2. ✅ Core feature working: year + AL slider → ranked long-weekend combos
3. ✅ Each combo card shows 1-2 monetization hooks (start with: Agoda search + Booking search with affiliate tags; no credit card partner in MVP)
4. ✅ JSON-LD structured data (schema.org Event for each holiday) + sitemap.xml
5. ✅ Page loads <1s, single HTML file <200KB

### Affiliate setup (week 1-2)
6. ✅ Agoda Affiliate Partner account approved + tag live
7. ✅ Booking.com Affiliate Partner account approved + tag live
8. ✅ (Stretch) One credit card or insurance partner: e.g. Involve Asia, Accesstrade, or direct with Maybank/CIMB travel cards

### Distribution (week 2-4)
9. ✅ Post on r/malaysia as **engagement, not promotion**: reply to 5-10 high-engagement threads (1ru50b3, 1ruihv2, 1m5cjre, 1t47di5, etc.) with value-add (a better visual table, a state-specific view) and a single soft mention of longweekend.my in the post body
10. ✅ One Twitter/X thread: "I built a long weekend calculator for Malaysia 2026 — here's the optimal way to use 14 days of AL" with screenshots
11. ✅ One LinkedIn post: productivity framing for working professionals

### Measurable sub-goals (60-day measurement window)
12. ✅ **Traffic:** ≥1,000 unique visitors in 60 days
13. ✅ **SEO ranking:** appear on page 1 of Google MY for at least one of:
    - "long weekend malaysia 2026"
    - "cuti panjang 2026"
    - "kalendar cuti umum malaysia 2026"
    - "public holiday malaysia 2026"
14. ✅ **Reddit signal:** the r/malaysia distribution post gets ≥50 upvotes (proves the topic + the tool both resonate)
15. ✅ **Conversion signal:** ≥1 confirmed affiliate click-through that lands a booking, OR ≥50 email captures, OR ≥500 unique visitors with ≥1% click-through on any affiliate link
16. ✅ **Revenue signal:** RM0-RM500 cumulative affiliate revenue (any non-zero number proves the funnel works)

### Kill clauses (30-day and 60-day)
17. ❌ **30-day kill:** if <200 unique visitors AND <20 upvotes on the Reddit distribution post, the convenience-to-distribution funnel is broken. Pause distribution, document learnings, consider Plan B (B2B/HR pivot)
18. ❌ **60-day kill:** if <500 unique visitors AND no page-1 ranking AND zero affiliate clicks, kill the project and document why
19. ❌ **6-month kill:** if cumulative revenue <RM50 after 6 months, retire the project

## What this goal tests (the real bet)
The unproven assumption we're validating with money and time: **a MY-specific interactive long weekend tool can capture enough organic + distribution traffic to monetize via per-result affiliate links at RM500/mo scale.**

If the goal fails, we learn one of three things:
- A: Demand exists but our distribution is too weak (Reddit, Twitter didn't drive traffic) → fix distribution
- B: Demand exists, traffic flows, but users don't click affiliate links → fix the offer/monetization
- C: Demand is thinner than the autocomplete + Reddit signals suggested → kill, document, move on

## Plan B (not a sub-goal, but a documented fallback)
If the consumer play fails at 60 days, the validated holiday data + state-specific knowledge + a working interactive tool is potentially sellable / partnerable to:
- HR vendors (quickhr.my, Kakitangan.com, Beng HR) as embeddable content
- Travel agencies / travel insurance companies as a lead-gen widget
- Government tourism (Tourism Malaysia) as a public-facing utility

## Target outcome
**RM500/month passive revenue from affiliate conversions within 6 months of launch.** Realistic ceiling, not aspirational.

## Estimated timeline
- Week 1: Build + deploy MVP, set up affiliates
- Week 2-4: Distribution sprint (3 platforms)
- Week 4-12: Measure, iterate, double down on what works
- Month 6: Re-evaluate against 6-month kill clause

---

## Validation log

**14 Jun 2026:** Problem validation sprint completed.
- ✅ Reddit r/malaysia: real engagement (80-906 upvotes on the topic, multiple high-engagement threads in 2025-2026)
- ✅ Google autocomplete: 10 year-tagged variants for both EN and BM queries
- ✅ Competitive landscape: gap exists — no interactive MY-specific optimizer, only static lists and content articles
- ✅ Holiday data: publicholidays.com.my is reliable, 4/5 stars, 2026 (18 federal + state variations) and 2027 lists extracted

**Decision:** Green light to build.

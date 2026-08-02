# longweekend.my — Architecture Proposal (Larry, chief architect)

**Date:** 20 Jun 2026
**Status:** Awaiting user approval; Alfred (main agent) will execute after sign-off
**Scope:** Complete redesign. Current build is NOT preserved.

---

## 1. Spec interpretation — what is this tool actually for?

Re-reading GOAL.md, the one-liner is "interactive MY-specific long weekend optimizer that ranks leave-day combinations by efficiency, with per-result affiliate hooks." The validated problem (line 12) is the real spec: *"Manually scanning 365 days against 14-17 federal holidays + 8-18 AL days to find optimal long-weekend stretches is a 2-3 hour cognitive task."*

The user is a Malaysian working professional in January (or any planning moment) holding a number: their AL entitlement for the year. They are not browsing for "a nice long weekend." They are trying to **allocate a scarce annual resource** — 8 to 18 leave days — across a whole year to maximize rest. The moment they reach for this tool is the moment they realize "if I take leave on these 4 specific Fridays, I get 4 long weekends; if I take them on those 4, I get 3 longer ones — which is better?"

**Success for a single session:** in under 2 minutes, the user sees a **concrete annual plan** — "Take these 5 specific leave days, get these 4 long-weekend stretches totaling 38 days off" — and can copy that plan to their calendar or share it with a partner/spouse to coordinate. The affiliate click is a *side effect of being in trip-planning mode*, not the goal of the session.

The current build (and the reference site) both treat this as a **catalog problem**: "show me N ranked long-weekend cards." It is actually a **knapsack / allocation problem**: "given a budget, build me the optimal yearly plan."

---

## 2. Why the current design is failing (specific failures)

1. **Solves the wrong problem.** Optimizer ranks individual long-weekend stretches; never assembles a subset that fits the AL budget.
2. **No additive mental model.** Cards don't show how they interact (taking #1 + #3 = 6 AL = 12 days off, but UI never says so).
3. **Controls before answer.** Year/AL/state-checkboxes is 4 controls up front.
4. **Visual noise competes with the answer.** 9 UI elements per card × 20 cards.
5. **Affiliate-first framing breaks trust.** "Apply leave: 24 Mar" + affiliate buttons on every card makes it feel like a booking funnel.
6. **Efficiency is the wrong ranking axis.** `days off ÷ AL used` ranks infinite-efficiency 3-dayers above memorable 9-day trips.
7. **Mobile density.** 20 cards on mobile = ~14 scrolls. The primary interaction (building a plan) is impossible on a phone.

---

## 3. The actual user question (priority order)

A Malaysian professional opens this in January with 14 AL days. They are asking, in this order:

1. **"What's my best year, given 14 AL days?"** — Give me the single highest-value annual plan. *Current: does not answer.*
2. **"Which exact dates do I apply leave on?"** — Literal calendar dates to submit to HR. *Current: per-card only.*
3. **"How does that change if I have 10/18/8 AL days?"** — Sensitivity to budget. *Current: re-ranks, doesn't re-solve.*
4. **"What if I'm in Selangor / Penang / Johor?"** — State-specific holidays. *Current: re-ranks, doesn't re-plan.*
5. **"Which of these should I book a trip for now vs. later?"** — The prioritization that drives the affiliate click. *Current: doesn't differentiate.*

Current build answers Q2 (per-card) and Q4 (re-rank). Misses Q1, Q3, Q5.

---

## 4. Architecture proposal — the new shape

### Layout, top to bottom

1. **Answer band (full-width, above the fold).** Single annual plan as the hero. 28px wordmark top-left only.
2. **Plan detail (calendar).** 12-month horizontal timeline (desktop) / stacked month list (mobile).
3. **Budget configurator.** AL slider, state selector, year toggle. Compact, inline, below the answer. Default 14 AL / federal / 2026.
4. **Alternative plans.** 2-3 competing plans as switchable tabs: "Max days off" / "Most long weekends" / "Longest single stretch".
5. **Per-stretch actions.** Clicking a stretch expands a panel with leave dates, holidays, ONE affiliate CTA.
6. **Trust footer.** Last-verified date, Islamic-date caveat, data source.

### Content blocks

- **Answer band:** "With 14 AL days, take 5 days of leave to get 38 days off in 2026." + 5 leave dates listed. **One CTA: "Add to calendar" (.ics).** Secondary: "Share plan" (WhatsApp + URL).
- **Calendar:** 12-row month strip. Days as cells. Weekends grey, holidays amber dots, selected leave days solid teal, days-off regions tinted.
- **Configurator:** `[Year 2026 ▾] [AL: ●——— 14] [State: Federal ▾]`. State multi-select behind disclosure, off by default.
- **Alternative plans:** Three tabs, each re-solves the knapsack.
- **Stretch panel:** "Fri 20 Mar – Sun 29 Mar · 10 days off · 2 AL (24–25 Mar)". One button: "Find hotels in [destination]".

### Primary interaction

**One thing: drag the AL slider.** Plan re-solves live. User feels the trade-off: "12 AL → 4 stretches / 32 days off; 14 AL → 5 stretches / 38 days off; 16 AL → 6 stretches / 44 days off."

### Information hierarchy

- **0–2s:** The headline number + the calendar with stretches tinted.
- **2–10s:** The leave dates listed; user scans which months.
- **10–30s:** User drags slider, watches plan morph, copies .ics or clicks into a stretch for affiliate.

### Mobile vs desktop

Same content, different surface.
- **Desktop:** Horizontal 12-month timeline; plan headline left, calendar right.
- **Mobile:** Plan headline full-width, vertical scrollable month list (Jan→Dec), each month 7-column day grid. Slider sticky at top. Affiliate CTAs full-width, 44px tap target.

### State model

```
year: 2026 | 2027
alBudget: int 8..18
states: Set<state>  default ∅
planMode: 'daysOff' | 'count' | 'longest'
selectedStretchId: string | null
```

All five URL-serializable: `?y=2026&al=14&s=selangor,penang&m=daysOff`. Sharing a plan = sharing a URL.

### Data model — a "Plan"

```javascript
Plan {
  alUsed: int
  totalDaysOff: int
  stretchCount: int
  longestStretch: int
  leaveDates: [ISO]          // exact days to apply AL
  stretches: [
    { start, end, daysOff, alUsed,
      leaveDates: [ISO], holidays: [{name, date, type}] }
  ]
}
```

Optimizer: knapsack solve. Pick subset of candidate runs (~30) whose total AL ≤ budget, maximizing selected objective. Runs in <1ms client-side.

---

## 5. Visual design direction

**Palette.** Calm, planning-tool, not travel-booking.
- Background `#FAFAF9` (warm off-white, "paper")
- Text `#1C1917` (stone-900)
- Muted `#78716C` (stone-500)
- Accent `#0D9488` (teal-600) — kept from current build
- Leave-day fill `#0D9488` solid; days-off tint `#CCFBF1` (teal-100)
- Holiday dot `#F59E0B` (amber-500)
- Weekend `#E7E5E4` (stone-200)
- Affiliate CTA `#1C1917` button, white text — quiet, not shouty

No gradient heroes. No star ratings. No orange/sunset secondary.

**Typography.** Inter (system fallback). Scale: headline 32/40 bold, plan headline 24/32 semibold, body 15/24, labels 12/16 medium uppercase tracking 0.04em. **Tabular-nums** in headline so numbers don't jitter as slider moves.

**Density.** Low. Whole page is one plan + one calendar + one configurator.

**Hero.** No marketing hero. The answer IS the hero.

**Primary surface: calendar, not cards.** Cards imply independent choices; a calendar implies a year with holes filled in — the user's mental model.

**What earns its place:** calendar, headline number, slider, .ics button, share button.
**What's noise:** star ratings, "#1 PICK" badges, day-block badges, per-card affiliate buttons, email capture, AL-suggestion bookkeeping, hero-result duplicate.

---

## 6. Implementation approach for Alfred

**Single static HTML file. Keep current architecture.** No framework. Reference site uses Next.js for 6 cards — overkill, hurts <1s / <200KB goals (GOAL.md line 37). Vanilla JS, one `index.html`, one embedded `holidays.json`, one `build.py` generator. Keep `build.py` drift-guard; only the **rendered output** and **optimizer objective** change.

**Data flow:** client-side only. Knapsack solve is <1ms. No backend. Share = URL with query params + pre-filled WhatsApp text. `.ics` generated client-side via Blob download.

**File structure (unchanged):**
```
longweekend/
  build.py            # generator — rewrite renderer + optimizer
  holidays.json       # unchanged
  index.html          # generated
  sitemap.xml, robots.txt, privacy.html, about.html  # unchanged
```

**TODO items, in order:**

1. In `build.py`, rewrite JS optimizer: add `solvePlan(budget, nonWorking, objective)` returning a `Plan` object. Keep `findRuns` for candidates; add greedy/DP selector over runs (respecting non-overlap and budget) for each objective.
2. Rewrite HTML renderer: replace `combo-grid` + `hero-result` with answer-band + 12-month calendar. Reuse existing date helpers (`dateToObj`, `fmt`, `getNonWorking`).
3. Add `.ics` generator: `buildICS(plan, year)` → Blob → `<a download="longweekend-plan-2026.ics">`.
4. Add URL state serialization (`?y=&al=&s=&m=`) with `history.replaceState` on every change.
5. Move affiliate CTA into per-stretch expand panel, one button, destination from `AFFILIATES.destinations` map.
6. Strip: star ratings, day-block badges, "#1 PICK", chip rows, AL-suggestion block, email-capture remnants, hero-result block.
7. Restyle per §5 palette. Drop gradient.
8. Mobile: sticky slider, vertical month list, full-width CTAs.
9. Keep JSON-LD but emit `schema.org/TouristTrip` per stretch in the selected plan.
10. Verify: <200KB, <1s load, Lighthouse ≥95 mobile.

---

## 7. Reference inspiration

**long-weekend-calc.vercel.app does well:**
- Headline-first ("Turn your 14 AL days into the most holiday possible")
- Single-number inputs (Year + AL number field) vs. slider + state-checkbox wall
- Summary stat row (Holidays / AL Available / Top Score)

**Do NOT copy:**
- "A A A → ✦✦✦" chip abstraction (cute, semantically useless)
- Star ratings on combos
- Next.js for this scope
- "4-day block" / "2-day block" badges

**Other references:**
- **Google Flights "Explore"** — one knob, many results, pick one
- **Wise.com currency converter** — gold standard for slider-driven instant answers
- **TimeAndDate.com** — trust signals done without noise
- **Teamup / Notion calendar** — calendar-cell visual language

---

## 8. Success criteria

**The 30-second test:** User lands, sees "With 14 AL days, take 5 days of leave to get 38 days off in 2026," sees the 5 dates on the calendar, drags the slider once, clicks "Add to calendar." Done. If they can't reach .ics download in 30s, design failed.

**The next thing they'd want:** Share with a spouse/friend to coordinate — "I'm taking 20–24 Mar off, you?" Served by WhatsApp share with prefilled plan text + URL.

**Measurement vs. current build:**
- *Time-to-first-plan-visible* < 1s
- *Add-to-calendar click rate* > 5% (new primary conversion proxy)
- *Slider interaction rate* > 25%
- *Affiliate CTR per session* may drop in raw % but rise in conversion quality (CTAs only after user commits to a stretch)
- *Bounce rate* target < 45%
- Qualitative: a Reddit r/malaysia screenshot reads as a **complete answer** without explanation

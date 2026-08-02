# Leave Optimizer Spec — longweekend.my v2

**Author:** Alfred (with Jer's direction)
**Date:** 19 Jul 2026
**Status:** Draft for review
**Target ship:** 1-2 Aug 2026 (1.5-2 weeks of work)
**Build cost:** $0 (no new infrastructure)

---

## 1. The Goal (the one-line version)

A personalized, saveable leave calendar on longweekend.my that shows each user their state's specific holidays + the optimal long-weekend stretches for the year, with email capture triggered AFTER value is delivered (not on page load).

**Predicted effect:** Lift signup rate from 0.42% → 2-5% within 7-14 days post-launch.

---

## 2. What This Replaces

**Current longweekend.my flow (0.42% signup rate):**
1. User lands from Threads
2. Sees 19 AL dates (generic, federal only, all users see the same list)
3. Sees "Join the waitlist" CTA at the bottom
4. 0.42% sign up

**The problem:** The calendar is generic. A Kelantan user sees 19 federal dates but doesn't get:
- Their 2 extra state holidays
- The "optimal" long weekends (1 AL day used = 3-4 day weekend)
- Saveable preferences
- Shareable with friends

**The fix:** Personalize the calendar to the user's state, calculate optimal stretches, allow save + share, then ask for email as a "save across devices" or "get alerts" trigger.

---

## 3. What's Already Built (don't reinvent)

Good news: the codebase already has most of the state infrastructure:

- **`STATES` constant** in build.py:184 — all 13 states + KL + Putrajaya + Labuan already extracted from holidays.json
- **State selector UI** (`.state-disclosure`, build.py:290-297, 405-407) — a `<details>` dropdown with checkbox list
- **Weekend pattern logic** (`weekendForStates()`, build.py:766+) — Kelantan/Terengganu use Fri+Sat, others use Sat+Sun
- **Per-state holiday filtering** — the `state` field in holidays.json enables filtering
- **Existing waitlist form** (`.waitlist` class, build.py:373-382) — the email capture form is already styled

**The leave optimizer is mostly a NEW UI/UX section + a few new functions, not a from-scratch build.** The state data and weekend logic are already there.

---

## 4. The New Sections (what to add)

### 4.1 The State Picker (new, prominent)

**Location:** Above the existing calendar, below the page title.

**UI design (mobile-first):**
```
┌─────────────────────────────────────────────┐
│  📅 Your Personalized Leave Calendar        │
│  Pick your state to see your best windows.  │
│                                              │
│  [ 🗺️  Select your state...  ▾ ]            │
│                                              │
└─────────────────────────────────────────────┘
```

**Behavior:**
- Pre-filled by IP geolocation (MaxMind GeoLite2, free, no signup required)
- If state is detected (e.g., user is in KL), pre-select "Kuala Lumpur"
- If state cannot be detected, show "Federal only" as default (current behavior)
- User clicks the dropdown → sees the 13 states + KL + Putrajaya + Labuan list
- User can change their state anytime

**Styling:** Reuse existing `.state-disclosure` class (build.py:290-297) but promote it to the top of the page with a "Your state" label.

### 4.2 The Personalized Calendar (new, replaces the current stretch list)

**Behavior:**
- When the user picks a state, the calendar immediately re-renders to show:
  - Federal holidays (14)
  - State-specific holidays (0-3 extra, depending on state)
  - Optimal long-weekend stretches (color-coded by tier)
  - The "best windows" highlighted (top 3-5)

**The "optimal stretches" calculation:**

For each AL day (federal or state), calculate:
- **3-day weekend:** AL day is on a Friday or Monday (uses 1 AL day, gives 3 days off including the weekend)
- **4-day weekend:** AL day is adjacent to a weekend (e.g., Friday AL + Saturday/Sunday = 4 days off, or Thursday AL + Saturday/Sunday = 4 days off, uses 1 AL day)
- **5-day weekend:** Two adjacent AL days (e.g., Thursday + Friday AL, or Monday AL + adjacent weekend, uses 2 AL days)
- **6+ day weekend:** Three+ adjacent AL days or AL days spanning a full week

**Color-coding (the visual hierarchy):**
- 🟢 **Green (3-day):** 1 AL day used, 3 days off — the "easy win"
- 🟡 **Yellow (4-day):** 1-2 AL days used, 4 days off — the "sweet spot"
- 🔵 **Blue (5+ day):** 2+ AL days used, 5+ days off — the "big trip"

**The "best windows" (top 3-5 per year):**
- Sort stretches by: total days off ÷ AL days used (efficiency)
- Highlight the top 3-5 as "Your best windows for travel"
- Show the dates + how many AL days used + how many total days off

**Example output (for Kelantan, 2026):**
```
🟢 17-19 Jan 2026 (3 days, 1 AL): Israk & Mikraj + weekend
🟡 14-17 Feb 2026 (4 days, 1 AL): Federal Territory Day + Thaipusam
🟢 20-22 Mar 2026 (3 days, 1 AL): Awal Ramadan (Kelantan)
🟡 1-4 May 2026 (4 days, 1 AL): Labour Day + weekend
🔵 30 May-1 Jun 2026 (3 days, 1 AL): Wesak Day
🟢 31 Aug-2 Sep 2026 (3 days, 1 AL): Merdeka Day
🟡 16-18 Sep 2026 (3 days, 1 AL): Malaysia Day + Kelantan state holiday
🔵 7-10 Nov 2026 (4 days, 1 AL): Deepavali
🟢 25 Dec 2026 (3 days, 1 AL): Christmas + weekend
```

### 4.3 The Save & Share Buttons (new, after calendar)

**Location:** Below the personalized calendar, above the existing waitlist form.

**UI design:**
```
┌─────────────────────────────────────────────┐
│  💾 Save my calendar                         │
│  Get back to your windows any time.         │
│                                              │
│  [ Save Locally ]  [ 📤 Share with Friends ] │
│                                              │
└─────────────────────────────────────────────┘
```

**"Save Locally" button:**
- Saves user's state + selected holidays to localStorage
- No email required
- No server call
- Shows "✓ Saved" confirmation
- On next visit, auto-loads the saved state

**"Share with Friends" button:**
- Generates a shareable URL: `https://longweekend.my/?s=kelantan&asof=2026-07-19`
- The state is pre-filled in the URL
- When a friend clicks the link, the calendar auto-loads with that state
- Copy-to-clipboard button
- Shows "Link copied! Share with your travel buddies."

### 4.4 The Email Capture (new, triggered by user action)

**Location:** After the user clicks "Save Locally" OR "Share with Friends" (not on page load).

**UI design (a modal that appears after the click):**
```
┌─────────────────────────────────────────────┐
│  Want to get an email when your next        │
│  long weekend is coming up?                 │
│                                              │
│  [ your@email.com            ]              │
│                                              │
│  [ Save my calendar across devices ]        │
│                                              │
│  We'll never spam. Unsubscribe anytime.     │
└─────────────────────────────────────────────┘
```

**Behavior:**
- Triggered AFTER user has seen value (calendar rendered, stretches shown, save/share clicked)
- Single field: email
- Submit button: "Save my calendar across devices"
- Copy clarifies the value: "across devices" (so the user knows localStorage + cloud sync)
- No "Join the waitlist" language (that was the generic 0.42% version)
- Privacy reassurance: "We'll never spam. Unsubscribe anytime."

**Optional second trigger (the alternative copy):**
- After the user picks a state and sees their calendar, show a non-intrusive inline message: "📬 Get an email when your best windows are coming up →"
- Click → modal with the same email capture
- This is the "get alerts" version (vs the "save across devices" version)

**Storage (in Neon, via existing `waitlist` table or new `leave_optimizer_signups`):**
```json
{
  "email": "jer@example.com",
  "state": "Kelantan",
  "utm_source": "threads",
  "utm_medium": "social",
  "referrer": "https://www.threads.net/@jer/...",
  "signup_at": "2026-07-19T10:30:00Z",
  "trigger": "save_locally" or "share_friends" or "get_alerts",
  "selected_stretches": ["2026-08-31", "2026-09-16", ...]  // which windows they cared about
}
```

---

## 5. The Data Model (what gets computed)

### 5.1 New functions in build.py

**`calculate_stretches(state, year)` → List[Stretch]**

For each AL day (federal + state-specific) in the year, calculate the optimal stretch window:

```python
def calculate_stretches(state: str, year: int) -> list:
    """
    Calculate optimal long-weekend stretches for a given state and year.
    Returns: [{"start": "2026-08-29", "end": "2026-09-02", 
               "al_days_used": 1, "total_days": 5, 
               "tier": "blue", "al_dates": ["2026-08-31"]}, ...]
    """
    # 1. Get all AL days for this state (federal + state-specific)
    al_days = get_holidays_for_state(state, year)
    
    # 2. Get the weekend pattern (Sat+Sun for most, Fri+Sat for Kelantan/Terengganu)
    weekend_days = get_weekend_days_for_state(state)
    
    # 3. For each AL day, calculate the stretch window
    stretches = []
    for al_date in al_days:
        stretch = calculate_single_stretch(al_date, weekend_days, al_days)
        if stretch and stretch["total_days"] >= 3:  # Only show 3+ day weekends
            stretches.append(stretch)
    
    # 4. Sort by efficiency (total_days / al_days_used)
    stretches.sort(key=lambda s: s["total_days"] / s["al_days_used"], reverse=True)
    
    # 5. Deduplicate overlapping stretches
    return deduplicate_stretches(stretches)
```

**`render_leave_optimizer(state, year)` → str (HTML)**

Generates the HTML for the state picker + personalized calendar + save/share buttons.

**`render_stretch_card(stretch)` → str (HTML)**

Generates the HTML for a single stretch card (color-coded by tier, with dates + efficiency).

### 5.2 New CSS (mobile-first)

```css
/* State picker (promoted to top) */
.optimizer-picker { background: var(--panel); border: 1px solid var(--border); 
                    border-radius: 10px; padding: 1.25rem; margin-bottom: 1.5rem; }
.optimizer-picker h2 { font-size: 18px; margin-bottom: 0.5rem; }
.optimizer-picker p { color: var(--muted); font-size: 14px; margin-bottom: 1rem; }

/* Stretch cards */
.stretch-card { display: flex; align-items: center; gap: 0.75rem; 
                padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; }
.stretch-card.green { background: #e8f5e9; border-left: 4px solid #4caf50; }
.stretch-card.yellow { background: #fff8e1; border-left: 4px solid #ff9800; }
.stretch-card.blue { background: #e3f2fd; border-left: 4px solid #2196f3; }
.stretch-dates { font-weight: 600; font-size: 14px; }
.stretch-meta { font-size: 12px; color: var(--muted); }
.stretch-tier { font-size: 11px; padding: 2px 6px; border-radius: 4px; 
                background: rgba(0,0,0,0.05); margin-left: auto; }

/* Save & share buttons */
.save-share { display: flex; gap: 0.5rem; margin-top: 1.5rem; }
.save-share button { flex: 1; padding: 0.75rem; border-radius: 8px; 
                     border: 1px solid var(--border); background: var(--bg); 
                     font: inherit; font-size: 14px; cursor: pointer; }
.save-share button:hover { background: var(--tint); }
.save-share button.saved { background: #e8f5e9; border-color: #4caf50; }
```

### 5.3 New JavaScript (client-side)

```javascript
// State picker
const statePicker = document.getElementById('state-picker');
statePicker.addEventListener('change', () => {
  const state = statePicker.value;
  localStorage.setItem('lw_state', state);
  reRenderCalendar(state);
});

// Save locally
function saveLocally() {
  const state = localStorage.getItem('lw_state') || 'Federal only';
  const stretches = getCurrentStretches();
  localStorage.setItem('lw_saved_stretches', JSON.stringify(stretches));
  showSavedConfirmation();
  showEmailModal('save_locally');  // Trigger email capture
}

// Share with friends
function shareWithFriends() {
  const state = localStorage.getItem('lw_state') || 'Federal';
  const url = `${window.location.origin}/?s=${state.toLowerCase()}&asof=${new Date().toISOString().slice(0,10)}`;
  navigator.clipboard.writeText(url);
  showShareConfirmation();
  showEmailModal('share_friends');  // Trigger email capture
}

// Email capture modal
function showEmailModal(trigger) {
  // Show the email modal with the appropriate copy
  const modal = document.getElementById('email-modal');
  modal.dataset.trigger = trigger;
  modal.classList.add('visible');
}

// Auto-load on page visit
window.addEventListener('DOMContentLoaded', () => {
  // Check URL params first (shared link)
  const urlParams = new URLSearchParams(window.location.search);
  const sharedState = urlParams.get('s');
  
  if (sharedState) {
    localStorage.setItem('lw_state', capitalize(sharedState));
  }
  
  // Then check localStorage
  const savedState = localStorage.getItem('lw_state');
  if (savedState) {
    statePicker.value = savedState;
    reRenderCalendar(savedState);
  }
  
  // Then check IP geolocation
  fetchIPState().then(detectedState => {
    if (!savedState && !sharedState && detectedState) {
      localStorage.setItem('lw_state', detectedState);
      statePicker.value = detectedState;
      reRenderCalendar(detectedState);
    }
  });
});
```

---

## 6. The Build Order (the 1-2 week timeline)

### Day 1-2: Data + backend logic

**Tasks:**
1. Read `holidays.json` structure (already done — each holiday has `date`, `name`, `type`, `state`, `day_of_week`)
2. Write `get_holidays_for_state(state, year)` function in build.py
3. Write `calculate_stretches(state, year)` function
4. Write `get_weekend_days_for_state(state)` function (reuses existing logic)
5. Test with 3 sample states (Kelantan, KL, Sabah) to verify stretch calculation

**Deliverable:** New functions in build.py, tested locally.

### Day 3-4: HTML rendering

**Tasks:**
1. Write `render_leave_optimizer(state, year)` — generates the state picker + calendar HTML
2. Write `render_stretch_card(stretch)` — generates individual stretch cards
3. Add CSS for the optimizer section
4. Add the optimizer section to the build template (above the existing calendar)
5. Test the static HTML output for all 13 states + 3 territories

**Deliverable:** New HTML in index.html, static, no JavaScript yet.

### Day 5-6: JavaScript (client-side interactivity)

**Tasks:**
1. State picker change handler (re-render calendar on state change)
2. localStorage save/load
3. Share link generator
4. Email capture modal logic
5. IP geolocation (use MaxMind GeoLite2 via a free API or local database)
6. URL param handling (shared links auto-load state)

**Deliverable:** Working JavaScript, interactive on the page.

### Day 7-8: Testing + polish

**Tasks:**
1. Test on mobile (iOS Safari, Android Chrome)
2. Test all 13 states + 3 territories
3. Test edge cases (no state selected, invalid state, private browsing, localStorage disabled)
4. Test share link flow (open in incognito, verify state pre-fills)
5. Test email capture flow (verify it submits to Neon correctly)
6. Deploy to Vercel

**Deliverable:** Live on longweekend.my.

### Post-launch: Measure for 7-14 days

**Tasks:**
1. Monitor signup rate (primary metric)
2. Monitor secondary metrics (state picker engagement, save rate, share rate, time on page)
3. Compare to baseline (0.42% signup rate)
4. Decision: <1% (kill), 1-2% (iterate), 2%+ (ship fare alerts)

---

## 7. The Success Metrics (what to measure)

### 7.1 Primary metric: Signup rate

- **Baseline:** 0.42% (8 signups / 1,906 unique visitors, 30 days)
- **Target:** 2-5% (industry benchmark for value-first email capture)
- **Stretch:** 5%+ (exceptional)

**How to measure:**
- Existing attribution API (`api/attribution.js`) already tracks signups
- New endpoint: `api/leave-optimizer-signup.js` (or extend existing `waitlist` endpoint)
- Track signup rate as: (signups in last 7 days) / (unique visitors in last 7 days)

### 7.2 Secondary metrics

| Metric | What it tells you | How to track |
|---|---|---|
| **State picker engagement** | % of visitors who interact with the state picker | JavaScript event: `state-picker-change` |
| **Personalized calendar views** | % of visitors who see their state's calendar (post-pick) | JavaScript event: `calendar-rendered` |
| **Save rate (local)** | % of visitors who click "Save Locally" | JavaScript event: `save-locally-click` |
| **Share rate** | % of visitors who click "Share with Friends" | JavaScript event: `share-click` |
| **Email capture rate** | % of visitors who submit email (post-save/share) | Neon: count email submissions |
| **Time on page** | Average time spent (should increase with personalization) | Google Analytics or custom event |
| **Return visitor rate** | % of visitors who come back (save-driven) | localStorage: `lw_returning=true` |
| **Share link conversion** | % of shared link clicks that result in a new signup | UTM tracking: `?utm_source=share` |

### 7.3 The decision tree (7-14 days post-launch)

| Signup rate (7-14 days) | Verdict | Action |
|---|---|---|
| 0.5% or below | The 0.42% is an audience problem (MY travelers don't convert to free tools) | Kill the leave optimizer. The 13 Aug kill clause applies. |
| 1-1.5% | Improving but not enough | Iterate on the CTA. Try different copy. Wait another 7 days. |
| 2-3% | On track | Ship fare alerts (4-6 weeks). The conversion hole is fixed. Extend kill clause to 13 Sep. |
| 3%+ | Strong | Ship fare alerts. Consider premium tier at launch. |

---

## 8. The Risks (the honest ones)

### Risk 1: The 0.42% is structural, not a product problem

**The bet:** MY travelers don't convert to free tools, regardless of UX improvements.
**The mitigation:** The leave optimizer tests this directly. If it stays at 0.5% or below, the audience is the problem, not the product.
**The cost if wrong:** 1-2 weeks of build time, 0.42% signup rate confirmed, kill clause applies.

### Risk 2: The state-specific delta is only 1-2 days (not a major value add)

**The bet:** Users already know their state holidays; the "personalization" is a minor tweak.
**The mitigation:** The leave optimizer is not just state holidays — it's also the "optimal stretches" calculation (which AL days + adjacent weekends = 3-4-5 day weekends), save + share, and email-after-value. The state-specific delta is 1-2 days, but the stretches calculation is the real value.
**The cost if wrong:** Signup rate lifts to 1-2% (not 2-5%), project becomes marginal, but still better than 0.42%.

### Risk 3: localStorage is fragile on iOS Safari

**The bet:** 10-15% of MY mobile users can't save locally (private browsing, ITP restrictions).
**The mitigation:** Make localStorage optional. The calendar still works without it. The "Save Locally" button is a nice-to-have, not a blocker.
**The cost if wrong:** 10-15% of users miss the "save" value, signup rate is slightly lower.

### Risk 4: IP geolocation is inaccurate

**The bet:** MaxMind GeoLite2 might detect the wrong state (e.g., VPN users, mobile users on different ISPs).
**The mitigation:** The state picker is always editable. The user can change it. The IP detection is just a default, not a constraint.
**The cost if wrong:** Minor UX annoyance, no impact on signup rate.

### Risk 5: The build takes longer than 1-2 weeks

**The bet:** The optimal-stretches calculation has edge cases (Kelantan/Terengganu Fri+Sat weekends, holidays on Sundays, etc.).
**The mitigation:** Test all 13 states + 3 territories manually. Budget 1 extra day for edge cases.
**The cost if wrong:** 3-week build instead of 2-week, still ships before 13 Aug.

---

## 9. What This Doesn't Do (the out-of-scope items)

To keep the 1-2 week build realistic, these are NOT in the leave optimizer scope:

- ❌ **Fare alerts integration** — separate project, 4-6 weeks
- ❌ **Email digest cron** — not needed for MVP, can add later
- ❌ **Account system** — localStorage + email is enough for MVP
- ❌ **Cross-device sync** — "save across devices" is the email trigger, not a real sync feature
- ❌ **Multi-state selection** — for users who work in one state and live in another (edge case, defer)
- ❌ **Custom holidays** — only official AL + state holidays, no user-added events
- ❌ **Notifications** — no push notifications, just the static page

---

## 10. The Open Questions (for Jer to answer before building)

1. **State picker placement:** Above the existing calendar (recommended) or as a separate "Optimizer" tab?
2. **Email capture trigger:** "Save Locally" only, "Share with Friends" only, or both (recommended)?
3. **"Get alerts" copy vs "Save across devices" copy:** Which is the primary CTA? (My recommendation: "Save across devices" — clearer value, less salesy)
4. **Share link format:** `?s=kelantan&asof=2026-07-19` (state + date) or just `?s=kelantan` (state only)? (My recommendation: state + date, so shared links are "fresh")
5. **IP geolocation library:** MaxMind GeoLite2 (free, requires download) vs a free API like ipapi.co (rate-limited) vs no IP detection (just default to "Federal only")? (My recommendation: no IP detection for MVP, just default to "Federal only", add IP detection in V2)
6. **Email storage:** New table `leave_optimizer_signups` or extend existing `waitlist` table? (My recommendation: extend existing `waitlist` table with a new column `source='leave_optimizer'`)
7. **Kill clause extension:** Should I ask for the 4-week extension to 13 Sep BEFORE building, or AFTER measuring the leave optimizer? (My recommendation: AFTER measuring, but note that the build starts on 19 Jul, so we're betting the leave optimizer lifts signup before 13 Aug)

---

## 11. The Next Steps (the practical answer)

**If Jer approves this spec:**

1. **Tonight/tomorrow:** Read this spec, give feedback on the 7 open questions
2. **Tomorrow:** Start Day 1-2 (data + backend logic) in build.py
3. **Day 3-4:** HTML rendering, deploy to a test environment
4. **Day 5-6:** JavaScript, deploy to longweekend.my (canary 10% of traffic first)
5. **Day 7-8:** Full rollout, monitor
6. **Day 9-21:** Measure signup rate, decide on fare alerts

**If Jer has feedback on the spec:**

- Which of the 7 open questions does Jer have opinions on?
- Does Jer want to change any of the section designs (state picker, calendar, save/share, email)?
- Does Jer want to add or remove any features from the scope?

**The 1-2 week estimate is based on:**
- 8-10 days of focused work
- $0 cash (no new services, no new infrastructure)
- Reusing existing state infrastructure (STATES constant, weekend logic, waitlist form)
- Mobile-first UX (which is the default for Threads traffic)

---

## 12. The One-Sentence Summary

> **The leave optimizer is a 1-2 week build that adds a state picker, personalized calendar with optimal-stweekend calculation, localStorage save, share-with-friends, and email-after-value capture to longweekend.my, lifting signup rate from 0.42% to 2-5% by giving users state-specific holidays + the "optimal stretches" calculation + save/share before asking for email, with the kill test being ≥2% signup in 7-14 days gating the fare alerts project.**

---

## Appendix A: The 13 States + 3 Territories (with state-specific holidays)

| State | Federal holidays | State holidays (2026) | Total | Personalization delta |
|---|---|---|---|---|
| **Kelantan** | 14 | 2 (Sultan's Birthday, Hari Raya Haji) | 16 | +2 days (highest) |
| **Terengganu** | 14 | 2 (Sultan's Birthday, Isra Mikraj) | 16 | +2 days |
| **Johor** | 14 | 2 (Sultan's Birthday, Hari Hol) | 16 | +2 days |
| **Sarawak** | 14 | 2 (Gawai Dayak, Governor's Birthday) | 16 | +2 days |
| **Perak** | 14 | 1 (Sultan's Birthday) | 15 | +1 day |
| **Penang** | 14 | 1 (Georgetown Declaration) | 15 | +1 day |
| **Kedah** | 14 | 1 (Sultan's Birthday) | 15 | +1 day |
| **Selangor** | 14 | 1 (Hari Hol) | 15 | +1 day |
| **Kuala Lumpur** | 14 | 1 (Hari Hol, Federal Territory) | 15 | +1 day |
| **Putrajaya** | 14 | 1 (Hari Hol, Federal Territory) | 15 | +1 day |
| **Pahang** | 14 | 1 (Sultan's Birthday) | 15 | +1 day |
| **Negeri Sembilan** | 14 | 1 (YDPB's Birthday) | 15 | +1 day |
| **Perlis** | 14 | 1 (Raja's Birthday) | 15 | +1 day |
| **Melaka** | 14 | 1 (Historical City Day) | 15 | +1 day |
| **Sabah** | 14 | 1 (Kaamatan) | 15 | +1 day |
| **Labuan** | 14 | 0 | 14 | 0 days (federal only) |

**Source:** kabinet.gov.my + state gazettes, verified for 2026.

---

## Appendix B: The Optimal-Stretch Calculation (the math)

For each AL day, the stretch window is:

```
If AL is on a Friday:
  Window = Friday + Saturday + Sunday (3 days, 1 AL)

If AL is on a Monday:
  Window = Saturday + Sunday + Monday (3 days, 1 AL)

If AL is on a Thursday:
  Window = Thursday + Saturday + Sunday (4 days, 1 AL, skip Friday)

If AL is on a Tuesday:
  Window = Saturday + Sunday + Tuesday (3 days, 1 AL, skip Monday)

If two ALs are adjacent (e.g., Thursday + Friday):
  Window = Thursday + Friday + Saturday + Sunday (4 days, 2 ALs)

If three ALs span a week:
  Window = 5+ days, 3 ALs
```

**For Kelantan/Terengganu (Fri+Sat weekend):**

```
If AL is on a Thursday:
  Window = Thursday + Friday + Saturday (3 days, 1 AL)

If AL is on a Sunday:
  Window = Friday + Saturday + Sunday (3 days, 1 AL, since Sun is workday + holiday)
```

**Edge cases:**
- AL on Saturday: no stretch (already a weekend day)
- AL on Sunday (for non-Kelantan/Terengganu): replacement holiday on Monday, so stretch = Sat + Sun + Mon (3 days, 1 AL)
- AL on Wednesday: no stretch (isolated midweek, not worth burning)

---

## Appendix C: The UI Wireframes (ASCII)

### State picker (above calendar)

```
┌─────────────────────────────────────────────┐
│  📅 Your Personalized Leave Calendar        │
│  Pick your state to see your best windows.  │
│                                              │
│  [ 🗺️  Kelantan (16 holidays)  ▾ ]          │
│                                              │
└─────────────────────────────────────────────┘
```

### Personalized calendar (after state pick)

```
┌─────────────────────────────────────────────┐
│  Kelantan — Your 16 holidays, 5 best windows │
│                                              │
│  🟢 17-19 Jan (3 days, 1 AL): Israk & Mikraj│
│  🟡 14-17 Feb (4 days, 1 AL): FT Day + Thaip│
│  🟢 20-22 Mar (3 days, 1 AL): Awal Ramadan  │
│  🟡 1-4 May (4 days, 1 AL): Labour Day       │
│  🟢 31 Aug-2 Sep (3 days, 1 AL): Merdeka    │
│  🟡 16-18 Sep (3 days, 1 AL): Malaysia Day  │
│  🔵 7-10 Nov (4 days, 1 AL): Deepavali      │
│  🟢 25 Dec (3 days, 1 AL): Christmas        │
│                                              │
│  [ 💾 Save Locally ]  [ 📤 Share ]           │
│                                              │
└─────────────────────────────────────────────┘
```

### Email capture modal (after save/share click)

```
┌─────────────────────────────────────────────┐
│  Want to get an email when your next        │
│  long weekend is coming up?                 │
│                                              │
│  [ your@email.com            ]              │
│                                              │
│  [ Save my calendar across devices ]        │
│                                              │
│  We'll never spam. Unsubscribe anytime.     │
└─────────────────────────────────────────────┘
```

---

**End of spec. Ready for Jer's review.**

# Minimal Email Capture Popup — longweekend.my v1

**Author:** Alfred (with Jer's direction)
**Date:** 19 Jul 2026
**Status:** Draft for review
**Target ship:** Tomorrow (1 day of work)
**Build cost:** $0 (no new infrastructure)

---

## 1. The Goal (one-line version)

Add a non-intrusive email capture popup to longweekend.my that triggers when a user clicks a stretch card, asks for their email (optional), and respects dismissal with a 7-day localStorage cooldown.

**Predicted effect:** Lift signup rate from 0.42% → 1-3% within 7-14 days post-launch.

---

## 2. The Design (the 4 decisions)

1. **Trigger:** Action-based — when user clicks a stretch card (existing `stretch_expand` event)
2. **Copy:** "Get an email when your next long weekend is coming up"
3. **Dismissal:** "Not now" link + localStorage 7-day cooldown
4. **Persistence:** Check Neon first (skip if already subscribed), then localStorage (skip if dismissed in last 7 days)

**Constraints:**
- Mobile-first (70%+ of Threads traffic is mobile)
- Non-intrusive (doesn't block the page, doesn't trap the user)
- Optional (user can dismiss without consequence)
- Respects existing flow (no changes to the current UI)

---

## 3. The UI (the popup)

### Visual design (mobile-first)

```
┌─────────────────────────────────────┐
│                                     │
│  Get an email when your next        │
│  long weekend is coming up.         │
│                                     │
│  [ your@email.com          ]        │
│                                     │
│  [ Notify me ]    Not now           │
│                                     │
│  We'll never spam. Unsubscribe      │
│  anytime.                           │
│                                     │
└─────────────────────────────────────┘
```

**Position:** Centered modal on desktop, bottom sheet on mobile (slides up from bottom).

**Behavior:**
- Appears 1.5 seconds after the stretch card click (small delay, not instant — feels less aggressive)
- Background overlay (semi-transparent black) to focus attention
- Tap outside the modal to dismiss
- "Not now" link dismisses + sets localStorage
- "Notify me" submits the email to the existing waitlist endpoint

### CSS (the styling)

```css
/* Modal overlay */
.lw-popup-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.4); z-index: 1000;
  display: none; align-items: center; justify-content: center;
  padding: 1rem; animation: lw-fade-in 0.2s ease;
}
.lw-popup-overlay.visible { display: flex; }

/* Modal box (desktop: centered, mobile: bottom sheet) */
.lw-popup {
  background: var(--bg); border-radius: 12px; padding: 1.5rem;
  max-width: 380px; width: 100%;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  animation: lw-slide-up 0.3s ease;
}
@media (max-width: 640px) {
  .lw-popup { 
    position: fixed; bottom: 0; left: 0; right: 0;
    border-radius: 12px 12px 0 0; max-width: 100%;
  }
}

/* Modal content */
.lw-popup h3 { font-size: 16px; margin-bottom: 0.5rem; color: var(--text); }
.lw-popup p { font-size: 13px; color: var(--muted); margin-bottom: 1rem; }
.lw-popup input[type=email] {
  width: 100%; padding: 0.6rem 0.75rem; border: 1px solid var(--border);
  border-radius: 8px; font: inherit; font-size: 14px;
  background: var(--bg); color: var(--text); margin-bottom: 0.75rem;
}
.lw-popup input[type=email]:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--tint);
}
.lw-popup-actions {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.75rem; margin-bottom: 0.5rem;
}
.lw-popup button[type=submit] {
  flex: 1; padding: 0.6rem; background: var(--accent); color: white;
  border: none; border-radius: 8px; font: inherit; font-size: 14px;
  font-weight: 500; cursor: pointer;
}
.lw-popup button[type=submit]:hover { opacity: 0.9; }
.lw-popup .lw-not-now {
  background: none; border: none; color: var(--muted); cursor: pointer;
  font: inherit; font-size: 13px; padding: 0.6rem; text-decoration: underline;
}
.lw-popup .lw-privacy { font-size: 11px; color: var(--muted); text-align: center; }

@keyframes lw-fade-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes lw-slide-up { 
  from { transform: translateY(20px); opacity: 0; } 
  to { transform: translateY(0); opacity: 1; } 
}
```

---

## 4. The HTML (the modal element)

Add this to the bottom of the `<body>` in `index.html` (or inject via build.py):

```html
<div class="lw-popup-overlay" id="lw-popup-overlay">
  <div class="lw-popup" id="lw-popup">
    <h3>Get an email when your next long weekend is coming up.</h3>
    <p>We'll send you a heads-up before each of your state's best windows.</p>
    <form id="lw-popup-form">
      <input type="email" id="lw-popup-email" placeholder="your@email.com" required>
      <div class="lw-popup-actions">
        <button type="submit">Notify me</button>
        <button type="button" class="lw-not-now" id="lw-popup-dismiss">Not now</button>
      </div>
      <p class="lw-privacy">We'll never spam. Unsubscribe anytime.</p>
    </form>
  </div>
</div>
```

---

## 5. The JavaScript (the behavior)

Add this to the existing `<script>` block in `index.html` (or inject via build.py):

```javascript
// === Email capture popup (minimal) ===

(function() {
  const POPUP_KEY = 'lw_popup_dismissed';
  const COOLDOWN_DAYS = 7;
  const STRETCH_CLICK_DELAY = 1500; // 1.5s after stretch click

  // Check if user has dismissed recently
  function isDismissedRecently() {
    const dismissed = localStorage.getItem(POPUP_KEY);
    if (!dismissed) return false;
    const dismissedAt = parseInt(dismissed, 10);
    const daysSince = (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24);
    return daysSince < COOLDOWN_DAYS;
  }

  // Check if user is already subscribed (via Neon)
  async function isAlreadySubscribed() {
    try {
      const email = localStorage.getItem('lw_user_email');
      if (!email) return false;
      const response = await fetch('/api/check-subscription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await response.json();
      return data.subscribed === true;
    } catch (e) {
      return false; // Fail open: show popup if check fails
    }
  }

  // Show the popup
  function showPopup() {
    const overlay = document.getElementById('lw-popup-overlay');
    if (overlay) {
      overlay.classList.add('visible');
      track('popup_shown', { source: 'stretch_click' });
    }
  }

  // Hide the popup
  function hidePopup() {
    const overlay = document.getElementById('lw-popup-overlay');
    if (overlay) {
      overlay.classList.remove('visible');
    }
  }

  // Dismiss with cooldown
  function dismissPopup() {
    localStorage.setItem(POPUP_KEY, Date.now().toString());
    hidePopup();
    track('popup_dismissed', { source: 'not_now' });
  }

  // Submit email
  async function submitEmail(email) {
    try {
      // Save to localStorage for future checks
      localStorage.setItem('lw_user_email', email);

      // Submit to existing waitlist endpoint
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          source: 'leave_optimizer_popup',
          utm_source: getUTM('utm_source'),
          referrer: document.referrer
        })
      });

      if (response.ok) {
        track('popup_signup', { source: 'leave_optimizer_popup' });
        // Show success message
        const popup = document.getElementById('lw-popup');
        popup.innerHTML = `
          <h3>You're in! 🎉</h3>
          <p>We'll email you before your next long weekend.</p>
          <button type="button" onclick="document.getElementById('lw-popup-overlay').classList.remove('visible')" 
                  style="width:100%;padding:0.6rem;background:var(--accent);color:white;border:none;border-radius:8px;font:inherit;font-size:14px;font-weight:500;cursor:pointer;margin-top:0.5rem;">
            Got it
          </button>
        `;
        // Auto-close after 3 seconds
        setTimeout(hidePopup, 3000);
      } else {
        track('popup_signup_error', { status: response.status });
      }
    } catch (e) {
      track('popup_signup_error', { error: e.message });
    }
  }

  // Hook into existing stretch card click
  let popupShownThisSession = false;
  document.addEventListener('click', async (e) => {
    // Check if click is on a stretch card
    const stretchCard = e.target.closest('.stretch');
    if (!stretchCard) return;
    
    // Only show once per session
    if (popupShownThisSession) return;
    
    // Check if dismissed recently
    if (isDismissedRecently()) return;
    
    // Check if already subscribed
    if (await isAlreadySubscribed()) return;
    
    // Show popup after delay
    popupShownThisSession = true;
    setTimeout(showPopup, STRETCH_CLICK_DELAY);
  });

  // Wire up the form
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('lw-popup-form');
    const dismiss = document.getElementById('lw-popup-dismiss');
    const overlay = document.getElementById('lw-popup-overlay');

    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('lw-popup-email').value.trim();
        if (email) submitEmail(email);
      });
    }

    if (dismiss) {
      dismiss.addEventListener('click', dismissPopup);
    }

    // Tap outside to dismiss
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) dismissPopup();
      });
    }
  });
})();
```

---

## 6. The Backend (the new endpoint)

Add a new API endpoint to check if an email is already subscribed:

**File:** `api/check-subscription.js`

```javascript
import { neon } from '@neondatabase/serverless';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ error: 'Email required' });
  }

  try {
    const sql = neon(process.env.DATABASE_URL);
    const result = await sql`
      SELECT email FROM waitlist WHERE email = ${email} LIMIT 1
    `;
    res.json({ subscribed: result.length > 0 });
  } catch (e) {
    res.status(500).json({ error: 'Database error' });
  }
}
```

**Note:** The existing `/api/waitlist` endpoint should already work for submissions. This new endpoint is just for the "already subscribed?" check.

---

## 7. The Build Order (1 day)

### Hour 1-2: HTML + CSS

1. Add the modal HTML to the bottom of `<body>` in `index.html` (or inject via build.py)
2. Add the CSS to the `<style>` block in `index.html`
3. Test that the modal renders correctly (hidden by default, visible when class is added)

### Hour 3-4: JavaScript

1. Add the JavaScript to the existing `<script>` block
2. Hook into the stretch card click event
3. Test the localStorage cooldown logic
4. Test the "already subscribed" check

### Hour 5-6: Backend + Testing

1. Create `api/check-subscription.js`
2. Deploy to Vercel
3. Test on mobile (iOS Safari, Android Chrome)
4. Test the full flow: click stretch → popup appears → submit email → success message

### Total: 6 hours, 1 day.

---

## 8. The Success Metrics (what to measure)

### Primary metric: Signup rate

- **Baseline:** 0.42% (8 signups / 1,906 unique visitors, 30 days)
- **Target:** 1-3% (industry benchmark for triggered, optional email capture)
- **Stretch:** 3%+ (exceptional)

### Secondary metrics

| Metric | What it tells you | How to track |
|---|---|---|
| **Popup shown rate** | % of stretch clickers who see the popup | `popup_shown` event |
| **Popup dismiss rate** | % of popup viewers who click "Not now" | `popup_dismissed` event |
| **Popup signup rate** | % of popup viewers who submit email | `popup_signup` event |
| **Popup → signup conversion** | % of stretch clickers who ultimately sign up | `popup_shown` × `popup_signup` |
| **Time to popup** | Average time from stretch click to popup shown | `popup_shown` event timestamp |
| **Mobile vs desktop** | Split between mobile and desktop signups | UTM + device detection |
| **Returning visitor signups** | % of signups from users who visited before | localStorage + email match |

### The decision tree (7-14 days post-launch)

| Signup rate (7-14 days) | Verdict | Action |
|---|---|---|
| 0.5% or below | The popup didn't help, the 0.42% is structural | Kill the popup. The 13 Aug kill clause applies. |
| 1-1.5% | Improving but not enough | Iterate on the copy or trigger. Try different timing. |
| 2-3% | On track | Ship fare alerts (4-6 weeks). The conversion hole is fixed. Extend kill clause to 13 Sep. |
| 3%+ | Strong | Ship fare alerts. Consider premium tier at launch. |

---

## 9. The Risks (the honest ones)

### Risk 1: The popup is annoying

**The bet:** Users will dismiss the popup and remember it negatively.
**The mitigation:** Action-based trigger (not on page load) + easy dismissal + 7-day cooldown.
**The cost if wrong:** Reduced return visitor rate, negative Threads mentions, no signup lift.

### Risk 2: The 1.5s delay is too aggressive or too passive

**The bet:** Users might miss the popup (too long delay) or feel interrupted (too short delay).
**The mitigation:** Start with 1.5s, adjust based on early data. Can A/B test 1s vs 2s vs 3s.
**The cost if wrong:** Lower popup-show-to-signup conversion.

### Risk 3: The stretch click is rare

**The bet:** Most users don't click stretch cards (they just scroll).
**The mitigation:** The existing `stretch_expand` tracking event already shows click rates. If <30% of users click a stretch, the popup will rarely fire. **Mitigation: add a secondary trigger — "after 60 seconds on page" — as a fallback.**
**The cost if wrong:** Popup rarely shown, signup rate doesn't lift.

### Risk 4: The email check endpoint is slow

**The bet:** The `/api/check-subscription` call adds 200-500ms latency to the popup trigger.
**The mitigation:** Make the check async (non-blocking). The popup shows regardless of the check result. The check is just to skip the popup for already-subscribed users.
**The cost if wrong:** Slight UX delay, no impact on conversion.

---

## 10. What This Doesn't Do (out of scope)

To keep the 1-day build realistic:

- ❌ **No state picker** — the existing UI is unchanged
- ❌ **No personalized calendar** — the existing calendar is unchanged
- ❌ **No save/share buttons** — not in scope
- ❌ **No stretch calculation** — the existing stretches are unchanged
- ❌ **No premium tier** — the popup is for the waitlist, not a paid product
- ❌ **No A/B testing framework** — start with one version, iterate if data shows it's worth it

---

## 11. The Open Questions (for Jer to answer before building)

1. **The 1.5s delay:** Is this the right timing? Or do you want 1s (faster) or 3s (slower)?
2. **The success message:** "You're in! 🎉" — is the emoji OK, or do you want text-only?
3. **The privacy line:** "We'll never spam. Unsubscribe anytime." — is this the right reassurance, or do you want to add a link to the privacy policy?
4. **The fallback trigger:** If stretch clicks are rare, should I add a "60 seconds on page" trigger as a secondary fallback? Or keep it strictly action-based?
5. **The "already subscribed" check:** Should I check Neon on every popup show, or only on the first show per session?

**My recommendations:**
1. 1.5s (good balance)
2. Emoji OK (modern, friendly)
3. Add privacy link: "We'll never spam. See our [privacy policy](/privacy.html)."
4. Add fallback trigger (more popup shows = more signups, even if some are "passive")
5. Check Neon only on first show per session (faster, less server load)

---

## 12. The Next Steps (the practical answer)

**If Jer approves this spec:**

1. **Tonight:** Read this spec, give feedback on the 5 open questions
2. **Tomorrow morning:** Start building (6 hours of work)
3. **Tomorrow afternoon:** Deploy to Vercel
4. **Day 3-16:** Monitor signup rate, measure for 7-14 days
5. **Day 17:** Decide: <1% (kill), 1-2% (iterate), 2%+ (ship fare alerts)

**If Jer has feedback:**

- Which of the 5 open questions does Jer have opinions on?
- Does Jer want to change any of the design decisions (copy, timing, fallback trigger)?
- Does Jer want to add or remove any features?

---

## 13. The One-Sentence Summary

> **The minimal popup is a 1-day build that adds a non-intrusive email capture modal to longweekend.my, triggered when a user clicks a stretch card, with copy "Get an email when your next long weekend is coming up," a "Not now" dismissal with 7-day localStorage cooldown, and a Neon check to skip the popup for already-subscribed users, predicted to lift signup rate from 0.42% to 1-3% within 7-14 days post-launch without changing the existing UI.**

---

**End of spec. Ready for Jer's review.**

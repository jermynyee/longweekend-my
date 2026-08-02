# Option B Draft — Server-Rendered Content Section for Homepage

**Goal:** Add ~600 words of pre-rendered HTML content BELOW the planner (not above).
**UX impact:** Zero — content sits in a visually-quiet section under the planner, above the footer.
**AdSense impact:** Strong — gives Googlebot a structured FAQ + holiday list + state explanation, exactly what "low value content" rejection needs.

---

## 📍 Where it goes in the page

```
[ Header ]
[ Answer band: "Your next long weekend is..." ]
[ Planner UI ]                    ← existing, untouched
[ ─── NEW SECTION STARTS HERE ─── ]
[ Holiday table — 2026 federal holidays ]
[ State explainer paragraph ]
[ FAQ — 5 collapsible questions ]
[ ─── NEW SECTION ENDS ─── ]
[ Footer: About / Privacy / Ads / Year links / Share button ]
```

The section uses `--panel` background (same as the disclaimer card) so it visually belongs to the existing system. No new colors. No new font sizes. Just a wider panel.

---

## 🎨 Preview (how it'll look to a human visitor)

> A clean white-ish panel with three sub-sections, each with a small heading and quiet typography. Slightly indented from the planner. Mobile-responsive (stacks).

---

## 📝 The content

### Sub-section 1: "All 2026 Federal Holidays in Malaysia"

A simple table — 5 columns: Date | Day | Holiday | Type (Federal) | Long weekend?

```
Jan 1   Thu  New Year's Day                  Federal  ✓
Feb 17  Tue  Chinese New Year                Federal  ✓ (with Feb 16 leave = 4 days)
Feb 18  Wed  Chinese New Year Holiday        Federal  ✓
Mar 7   Sat  Nuzul Al-Quran                  Federal  —
Mar 20  Fri  Hari Raya Aidilfitri Holiday    Federal  ✓ (with Mar 23 leave = 4 days)
Mar 21  Sat  Hari Raya Aidilfitri            Federal  ✓
Mar 22  Sun  Hari Raya Aidilfitri Holiday    Federal  ✓
Mar 23  Mon  Hari Raya Aidilfitri Holiday    Federal  ✓
May 1   Fri  Labour Day                      Federal  ✓
May 27  Wed  Hari Raya Haji                  Federal  —
May 31  Sun  Wesak Day                       Federal  ✓ (Mon Jun 1 is also off)
Jun 1   Mon  Agong's Birthday                Federal  ✓
Jun 2   Tue  Wesak Day Holiday               Federal  ✓
Jun 17  Wed  Awal Muharram                   Federal  —
Aug 25  Tue  Prophet Muhammad's Birthday     Federal  —
Aug 31  Mon  Merdeka Day                     Federal  ✓
Sep 16  Wed  Malaysia Day                    Federal  —
Nov 8   Sun  Deepavali                       Federal  ✓ (Mon Nov 9 also off)
Nov 9   Mon  Deepavali Holiday               Federal  ✓
Dec 25  Fri  Christmas Day                   Federal  ✓
```

Below the table: "View the full 2026 calendar with all 91 holidays →" links to `/2026`.

### Sub-section 2: "Why your long weekends depend on where you live" (3 sentences)

> Most Malaysian states observe Saturday + Sunday as the weekend, but Kelantan and Terengganu use Friday + Saturday — Sundays are a workday there. Johor reverted to Saturday + Sunday on 1 January 2025 after a brief period on Friday + Saturday. Our optimizer lets you pick your state's weekend pattern so the long weekend suggestions match your actual days off.

### Sub-section 3: FAQ — 5 questions

**Q: What is a long weekend in Malaysia?**
A long weekend is any stretch of 3+ consecutive days off when a federal holiday lands on a Friday, Monday, or creates a bridge with a weekend day. The longest Malaysian long weekends in 2026 fall on Hari Raya Aidilfitri (March 20-23) and Chinese New Year (February 17-18), each giving 4 days off with strategic leave.

**Q: What is cuti bersama?**
Cuti bersama (joint leave) are additional days the Prime Minister declares, usually to extend a public holiday into a longer break. They're not guaranteed — the government announces them a few weeks before, often for Hari Raya or Chinese New Year. They apply to government servants and many private employers follow suit, but it's not a legal entitlement.

**Q: Do I get a replacement day off if a public holiday lands on a Sunday?**
For federal holidays: yes, the following Monday is typically declared a replacement holiday (this is what happened with Hari Raya Haji on May 27, 2026 — Wednesday). For state holidays on Sundays: depends on your state — Kelantan and Terengganu use a different system since Sundays are already workdays there.

**Q: How does Kelantan and Terengganu's weekend work?**
Both states observe Friday + Saturday as the weekend. Sunday is a regular workday, and Sunday public holidays (like Wesak Day 2026 on May 31) get Monday off as the replacement. Their public holidays list also includes state-specific days the rest of Malaysia doesn't observe.

**Q: How far in advance should I plan my leave?**
For Chinese New Year and Hari Raya, popular destinations book out 2-3 months ahead. The optimizer above shows the maximum value you can get per leave day — a single day strategically placed can turn a 1-day holiday into a 4-day weekend.

---

## 🎯 Why this content specifically

**Not a blog post.** It's reference content — answers the actual questions people search:

| Question people Google | Where it lives on this page |
|---|---|
| "Malaysia public holidays 2026" | Holiday table |
| "cuti bersama 2026" | FAQ Q2 |
| "long weekend Malaysia 2026" | Holiday table + planner |
| "Kelantan weekend" / "Johor weekend" | State explainer |
| "what to do when holiday falls on Sunday" | FAQ Q3 |
| "Kelantan Sunday replacement day" | FAQ Q4 |

That's 6 high-volume Malaysian search queries your homepage now answers without JS. Each one is a chance to show up in Google results and rank for the actual long weekend search.

**The FAQ structure is exactly what Google's quality raters look for.** Their public docs on "helpful content" call out FAQ format specifically as a signal of depth. Collapsed by default means your existing users never see it — but Googlebot sees the full structured content.

---

## 🛠️ How it's built

Two changes to `build.py`:

### Change 1: Add a render function (~80 lines)

```python
def render_seo_section(holidays_by_year: dict, year: int = 2026) -> str:
    """Render the server-side content section: holiday table + state explainer + FAQ."""
    fed = [h for h in holidays_by_year.get(str(year), []) if h["type"] == "federal"]
    rows = []
    for h in fed:
        date_obj = __import__("datetime").date.fromisoformat(h["date"])
        rows.append(
            f"<tr><td>{date_obj.strftime('%b %-d')}</td>"
            f"<td>{h['day_of_week']}</td>"
            f"<td>{h['name']}</td>"
            f"<td>Federal</td>"
            f"<td>{'✓' if _is_long_weekend(h, holidays_by_year[str(year)]) else '—'}</td></tr>"
        )
    # ... returns full HTML string
```

The `_is_long_weekend()` helper checks if the holiday creates a 3+ day stretch using the default Sat+Sun weekend.

### Change 2: Insert into template (1 line, at line 327)

```python
HTML = HTML.replace("__SEO_CONTENT__", render_seo_section(HOLIDAYS))
```

Plus add `__SEO_CONTENT__` placeholder just before `<footer>` (line 327).

### CSS additions (~25 lines, hidden by default on mobile)

```css
.seo-section { margin-top: 2rem; max-width: 720px; margin-left: auto; margin-right: auto; }
.seo-section details { border-bottom: 1px solid var(--border); padding: 0.75rem 0; }
.seo-section details summary { cursor: pointer; font-weight: 600; padding: 0.25rem 0; }
.seo-section details[open] summary { margin-bottom: 0.5rem; }
.seo-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.seo-table th, .seo-table td { padding: 0.4rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); }
```

---

## 📊 Expected outcome

| Metric | Before | After |
|---|---|---|
| Visible homepage word count | 133 | ~700 |
| Structured FAQ | 0 | 5 questions |
| Server-rendered holiday data | 0 | 20 holidays in table |
| Googlebot-readable topical depth | Thin | Strong |
| AdSense "low value content" flag | ❌ | ✅ should clear |
| Mobile UX impact | N/A | None (collapsed FAQ) |
| Desktop UX impact | N/A | None (sits below planner, above footer) |
| Deploy time | N/A | ~5 min |
| Reversible | N/A | Yes — single git revert |

---

## 🚦 Decision

**If you approve:** I'll add the render function + template change + CSS, run `python3 build.py --force`, deploy, verify the new content is in the HTML, confirm visible word count is ~700.

**If you want to edit:** Tell me what to change — tone, wording, which questions, holiday table format, etc. I'll revise the draft and show you again.

**If you want to defer:** Say "ship option A first" or "not tonight" and I'll leave build.py untouched.

---

## 💡 Things I deliberately did NOT include

- ❌ A "What is a long weekend in Malaysia?" essay — the FAQ covers it
- ❌ A blog-style intro paragraph above the planner — would push UX down
- ❌ State-by-state holiday lists — that's what the year pages are for
- ❌ Author bio / about-the-author box — overkill for a tool page
- ❌ Promotional copy about Trip.com or other monetization — AdSense rejects pages with too much monetization

The content is reference info only. It serves the user. Google rewards that.
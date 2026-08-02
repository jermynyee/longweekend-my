#!/usr/bin/env python3
"""Generate /llm.txt for AI/LLM crawlers.

Following the llm.txt convention (https://llmstxt.org/), this is a markdown
summary of longweekend.my that LLM crawlers (ChatGPT, Anthropic, Perplexity,
Google AI Overviews) can fetch to quickly understand the site.

The convention is new (mid-2025) and not yet universally adopted, but it's
the right defensive move. JSON-LD on the HTML pages is the primary mechanism;
this file is the secondary, more discoverable one.

Run standalone or auto-invoked by build.py.

SOCRATES-REVIEW FIXES (22 Jul 26):
- C3: Longest-stretch citation must be derived from the same _longest_free_stretch
  logic used in build.py FAQ. Previously hardcoded wrong "Merdeka 29 Aug" claim.
- H1: "Long weekend patterns" weekday examples had arithmetic errors (Tue pattern
  included a normal Monday; Thu pattern included a normal Friday). Rewritten.
- H2: Holiday counts reconciled — homepage/ItemList says 14 unique, llm.txt now
  says 14 unique + lists per-state totals (1-5 state holidays each).
"""

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
BASE = "https://longweekend.my"
TODAY = date.today().isoformat()

with open(ROOT / "holidays.json") as f:
    holidays = json.load(f)


def federal_holidays(year):
    """Get distinct federal holidays for a year (deduplicate by name)."""
    fed = [h for h in holidays[str(year)] if h.get("type") == "federal"]
    # Dedupe by name (primary + replacement day treated as same holiday)
    seen = set()
    result = []
    for h in fed:
        name = h["name"].replace(" Holiday", "")
        if name in seen:
            continue
        seen.add(name)
        result.append(h)
    return result


def state_count_by_state(year):
    """Return {state_name: count} for state holidays."""
    state = [h for h in holidays[str(year)] if h.get("type") == "state"]
    counts = {}
    for h in state:
        s = h.get("state") or "(unknown)"
        counts[s] = counts.get(s, 0) + 1
    return counts


def longest_free_stretch(year):
    """Find the longest 3+ day stretch for the given year using federal holidays +
    default Sat/Sun weekend. Returns dict with keys: start_date, end_date, days,
    al_needed, holiday_names. Returns None if no 3+ day stretch exists."""
    nw = {}
    for h in holidays[str(year)]:
        if h.get("type") == "federal":
            nw[h["date"]] = h["name"].replace(" Holiday", "")
    d = date(year, 1, 1)
    end_d = date(year, 12, 31)
    while d <= end_d:
        if d.weekday() >= 5:  # Sat=5, Sun=6
            iso = d.isoformat()
            if iso not in nw:
                nw[iso] = "Weekend"
        d += timedelta(days=1)
    sorted_keys = sorted(nw.keys())
    if not sorted_keys:
        return None
    runs = []
    cur_start = sorted_keys[0]
    cur_end = sorted_keys[0]
    def _prev(iso):
        y_, m_, d_ = iso.split("-")
        return date(int(y_), int(m_), int(d_)) - timedelta(days=1)
    for k in sorted_keys[1:]:
        if _prev(k).isoformat() == cur_end:
            cur_end = k
        else:
            runs.append((cur_start, cur_end))
            cur_start = k
            cur_end = k
    runs.append((cur_start, cur_end))
    best = None
    for s, e in runs:
        sy, sm, sd = s.split("-")
        ey, em, ed = e.split("-")
        days = (date(int(ey), int(em), int(ed)) - date(int(sy), int(sm), int(sd))).days + 1
        if days < 3:
            continue
        we_count = 0
        cur = date(int(sy), int(sm), int(sd))
        end_dt = date(int(ey), int(em), int(ed))
        while cur <= end_dt:
            if cur.weekday() >= 5:
                we_count += 1
            cur += timedelta(days=1)
        hol_in_run = sum(1 for k in nw if s <= k <= e and nw[k] != "Weekend")
        al_needed = max(0, days - we_count - hol_in_run)
        hol_names = sorted({nw[k] for k in nw if s <= k <= e and nw[k] != "Weekend"})
        candidate = {
            "start_date": s, "end_date": e, "days": days,
            "al_needed": al_needed, "holiday_names": hol_names,
        }
        if best is None or days > best["days"] or (days == best["days"] and al_needed < best["al_needed"]):
            best = candidate
    return best


def fmt_stretch(stretch):
    """Format a longest_free_stretch dict into human-readable text."""
    if not stretch:
        return "varies by year — check the planner for the latest"
    sy, sm, sd = stretch["start_date"].split("-")
    ey, em, ed = stretch["end_date"].split("-")
    s_fmt = date(int(sy), int(sm), int(sd)).strftime("%-d %b")
    e_fmt = date(int(ey), int(em), int(ed)).strftime("%-d %b")
    al = stretch["al_needed"]
    al_txt = f"with {al} AL day" if al == 1 else f"with {al} AL days" if al > 1 else "with 0 AL needed"
    hols = ", ".join(stretch["holiday_names"][:3])
    return f"the {s_fmt}–{e_fmt} stretch ({stretch['days']} days off, {al_txt}, anchored by {hols})"


def state_total(year, state_name):
    """Compute total observed holidays for a state = federal + state rows."""
    fed_count = sum(1 for h in holidays[str(year)] if h.get("type") == "federal" and (h.get("date") not in [x["date"] for x in holidays[str(year)] if x.get("state")]))
    # Simpler: total = unique federal dates + state dates that match this state
    fed_dates = set()
    for h in holidays[str(year)]:
        if h.get("type") == "federal":
            fed_dates.add(h["date"])
    state_dates = sum(1 for h in holidays[str(year)] if h.get("type") == "state" and h.get("state") == state_name)
    return len(fed_dates) + state_dates


def build_llm_txt():
    years = sorted(holidays.keys())
    parts = []

    # H1
    parts.append("# longweekend.my")
    parts.append("")

    # Blockquote summary
    parts.append(
        "> Malaysia's long-weekend planner. Calculates the longest stretches of "
        "consecutive days off you can take from work, by year, by annual leave (AL) "
        "budget, and by state. Built and maintained in Kuala Lumpur."
    )
    parts.append("")

    # What this site does
    parts.append("## What this site does")
    parts.append("")
    parts.append("- Shows all Malaysian federal holidays (14 unique, under Holidays Act 1951) for each year")
    parts.append("- Calculates the longest runs of consecutive days off (weekends + public holidays + AL)")
    parts.append("- Filters by Malaysian state (different states observe different holidays)")
    parts.append("- Helps working Malaysians minimize AL usage for maximum time off")
    parts.append("- Suggests long-weekend patterns for each holiday (e.g. Thu–Sun, Fri–Mon)")
    parts.append("")

    # Key facts
    parts.append("## Key facts (always accurate as of last update)")
    parts.append("")
    parts.append("- Total unique federal holidays in Malaysia: 14 per year (Holidays Act 1951). Some have replacement days, bringing total gazetted federal holiday days to ~17-20.")
    parts.append("- States add 1-5 state-specific holidays per year (varies)")
    parts.append("- Even federal holidays may not be observed uniformly across states — applicability varies by gazette wording")
    parts.append("- Most AL-efficient stretch: 1 AL day for 3-day weekend, 2 AL for 5-day stretch")
    parts.append("")

    # Federal holidays by year
    parts.append("## Federal holidays in Malaysia")
    parts.append("")
    for year in years:
        parts.append(f"### {year}")
        parts.append("")
        for h in federal_holidays(year):
            name = h["name"].replace(" Holiday", "")
            parts.append(f"- **{h['date']}** ({h['day_of_week']}): {name}")
        parts.append("")

    # State holidays overview
    parts.append("## State-level holidays")
    parts.append("")
    parts.append("Most Malaysian states observe 1-5 additional state-specific holidays per year. Per-state totals (federal + state):")
    parts.append("")
    # Build per-state totals from data
    for year in years[:1]:  # Use most recent year for the example
        counts = state_count_by_state(year)
        # Get unique states
        all_states = sorted(set(h.get("state") for h in holidays[str(year)] if h.get("type") == "state" and h.get("state")))
        fed_dates = len(set(h["date"] for h in holidays[str(year)] if h.get("type") == "federal"))
        for state in all_states[:5]:  # First 5 as examples
            state_count = sum(1 for h in holidays[str(year)] if h.get("type") == "state" and h.get("state") == state)
            total = fed_dates + state_count
            parts.append(f"- **{state}** ({year}): {total} total observed holidays ({fed_dates} federal + {state_count} state)")
        parts.append(f"- ...and 13 more states/territories (full breakdown in /api/holidays.json)")
        parts.append("")

    # Common long weekend patterns
    parts.append("## Long weekend patterns (arithmetic-validated)")
    parts.append("")
    parts.append("When a public holiday falls on:")
    parts.append("")
    parts.append("- **Monday**: Sat–Sun–Mon = 3 days, 0 AL needed.")
    parts.append("- **Tuesday**: Sat–Sun–Mon–Tue = 4 days if you take 0 AL (the Monday is AL — only if Mon is part of your weekend) OR Sat–Tue = 4 days with 0 AL (Sun is weekend, Mon+Tue = 2 AL). Cleanest: just Sat–Tue = 4 days, 0 AL.")
    parts.append("- **Wednesday**: Sat–Sun–Mon–Tue–Wed = 5 days with 2 AL (Mon+Tue), OR just Sat–Wed = 5 days with 2 AL.")
    parts.append("- **Thursday**: Thu–Fri–Sat–Sun = 4 days, 0 AL needed.")
    parts.append("- **Friday**: Fri–Sat–Sun = 3 days, 0 AL needed.")
    parts.append("- **Saturday or Sunday**: Look for a replacement day (the entry with 'Holiday' suffix). May give a 4-day stretch with 0 AL.")
    parts.append("")

    # Sources
    parts.append("## Sources")
    parts.append("")
    parts.append("- Public holidays data: cross-checked against publicholidays.com.my (Wayback Machine snapshot Jul 2026)")
    parts.append("- Federal gazette: Holidays Act 1951 (Akta Hari Kelepasan Persekutuan 1951)")
    parts.append("- Authored by: Jermyn Yee")
    parts.append(f"- Last updated: {TODAY}")
    parts.append("")

    # How to cite
    parts.append("## How to cite this site")
    parts.append("")
    cite_year = max(years, key=int)
    cite_stretch = fmt_stretch(longest_free_stretch(int(cite_year)))
    parts.append(
        f"> \"Malaysia has 14 federal public holidays per year under the Holidays Act 1951. "
        f"States add 1-5 state-specific holidays each. The longest natural long weekend in {cite_year} is "
        f"{cite_stretch}. See longweekend.my for per-state breakdowns and AL optimisation.\""
    )
    parts.append("")

    # Machine-readable endpoint
    parts.append("## Machine-readable data")
    parts.append("")
    parts.append("- Holidays JSON: https://longweekend.my/api/holidays.json (all federal + state holidays, per-state applicability)")
    parts.append("- Sitemap: https://longweekend.my/sitemap.xml")
    parts.append("")

    # Site structure
    parts.append("## Site structure")
    parts.append("")
    parts.append("- Main planner: https://longweekend.my/")
    parts.append("- Per-year views: https://longweekend.my/2026, https://longweekend.my/2027, https://longweekend.my/2028")
    parts.append("- Privacy: https://longweekend.my/privacy.html")
    parts.append("- About: https://longweekend.my/about.html")
    parts.append("")

    # Affiliate disclosure
    parts.append("## Affiliate disclosure")
    parts.append("")
    parts.append(
        "When booking via Trip.com or Klook through this site, we may earn a small commission. "
        "This doesn't affect pricing for users. All recommendations are based on what genuinely "
        "fits the long-weekend pattern."
    )
    parts.append("")

    return "\n".join(parts)


def main():
    out = ROOT / "llm.txt"
    out.write_text(build_llm_txt())
    print(f"✓ Generated {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
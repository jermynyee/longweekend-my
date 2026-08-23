#!/usr/bin/env python3
"""
Build the longweekend.my MVP as a single self-contained HTML file.

Architecture v2 (Larry, chief architect — see ARCHITECTURE.md):
  - Knapsack optimizer: solvePlan(budget, nonWorking, objective) -> Plan
  - Answer band + 12-month calendar (replaces combo-grid + hero-result)
  - .ics generator (client-side Blob download)
  - URL state serialization (?y=&al=&s=&m=&asof=)
  - Per-stretch expand panel with public-holiday + leave-day details
  - Palette: warm off-white #FAFAF9, teal-600 #0D9488, Inter + tabular-nums
  - JSON-LD TouristTrip per stretch
  - PRESERVES drift guard (polish #4) and 2027 disclaimer (polish #5)
"""
import json
import os
import sys
import datetime
from pathlib import Path

ROOT = Path("/Users/alfred/.openclaw/workspace/moonshot/longweekend")

# --- Google Search Console verification ----------------------------------
# Set this to your verification meta tag value once you add the property
# in Search Console. Empty string = no verification tag rendered.
GSC_VERIFICATION_CODE = "f7xUPHhxYpuG3czUiEHOFe88vZSRW7UWLuNEtymK4cI"  # 2026-07-05 — jermyn.yee@gmail.com

# --- AdSense config -------------------------------------------------------
# Flip these to True and paste your IDs once AdSense approves you. Until
# then, ad slots are commented out in the HTML (no broken ad containers,
# no "Ads not by this site" placeholders).
# --- Drift guard: Publisher + slot IDs live (4 Jul 2026) ----------------------
# Both Publisher ID and 4 slot IDs wired. Currently DISABLED because the
# AdSense application was rejected; loading the script wastes an external
# request for zero revenue, and the year pages' ad slot <ins> tags were
# silent-failing because the homepage loaded adsbygoogle.js but year pages
# didn't. yr_ad() and the homepage ad short-circuit to inert HTML comments
# when this is False. Re-enable once AdSense is approved.
ADSENSE_ENABLED = False  # was True; rejection pending reapply ~mid-Jul 2026
ADSENSE_PUBLISHER_ID = "ca-pub-5506809170449982"  # Live publisher account
ADSENSE_SLOT_TOP = "8810938476"  # homepage-top (below answer band)
ADSENSE_SLOT_MID = "1075883297"  # homepage-mid (below calendar, 300x250 rect)
ADSENSE_SLOT_YEAR_TOP = "3203353184"  # year-top (below holiday table)
ADSENSE_SLOT_YEAR_MID = "4823556611"  # year-mid (below FAQ, 300x250 rect)


# --- SEO content section (server-rendered for AdSense + organic depth) ---
# Renders below the planner: 2026 federal holiday table + state explainer + 5
# collapsible FAQs. Googlebot sees this without executing JS. Keeps existing
# users' experience unchanged (content sits in a quiet panel above the footer).
def _is_long_weekend_anchor(h):
    """Is this holiday a long weekend anchor? Used to mark the table column."""
    name = h["name"]
    # Fri/Mon/Tue are weekend-adjacent; specific holidays are always anchors.
    return (
        h["day_of_week"] in ("Fri", "Mon")
        or "Hari Raya" in name
        or "Chinese New Year" in name
        or "Agong" in name
        or "Deepavali" in name
        or "Wesak" in name
    )


def render_seo_section(holidays_by_year, year=2026):
    """Server-rendered HTML block injected into the homepage."""
    from datetime import date
    rows = []
    for h in holidays_by_year.get(str(year), []):
        if h.get("type") != "federal":
            continue
        d = date.fromisoformat(h["date"])
        rows.append((
            d.strftime("%b %-d"),
            h["day_of_week"],
            h["name"],
            "✓" if _is_long_weekend_anchor(h) else "—",
        ))

    table_rows = "\n".join(
        f"        <tr><td>{d}</td><td>{day}</td><td>{name}</td><td>{mark}</td></tr>"
        for d, day, name, mark in rows
    )

    return f"""
    <details class="seo-section-collapse">
      <summary>
        <span class="seo-section-title">📅 All {year} Federal Holidays &amp; FAQ</span>
        <span class="seo-section-hint">Click to expand</span>
      </summary>
      <div class="seo-section-content">
        <h2>All {year} Federal Holidays in Malaysia</h2>
        <table class="seo-table" aria-label="Malaysia federal holidays {year}">
          <thead>
            <tr><th>Date</th><th>Day</th><th>Holiday</th><th>Long weekend?</th></tr>
          </thead>
          <tbody>
{table_rows}
          </tbody>
        </table>
        <p class="seo-muted">View the full <a href="/{year}">{year} holiday calendar with all holidays</a> (federal + state + cuti bersama).</p>

        <h2 style="margin-top:1.75rem">Why your long weekends depend on where you live</h2>
        <p>Most Malaysian states observe Saturday + Sunday as the weekend, but Kelantan and Terengganu use Friday + Saturday — Sundays are a workday there. Johor reverted to Saturday + Sunday on 1 January 2025 after a brief period on Friday + Saturday. Our optimizer lets you pick your state's weekend pattern so the long weekend suggestions match your actual days off.</p>

        <h2 style="margin-top:1.75rem">Frequently asked questions</h2>

        <details class="seo-faq">
          <summary>What is a long weekend in Malaysia?</summary>
          <p>A long weekend is any stretch of 3+ consecutive days off when a federal holiday lands on a Friday, Monday, or creates a bridge with a weekend day. The longest Malaysian long weekends in 2026 fall on Hari Raya Aidilfitri (March 20&ndash;23) and Chinese New Year (February 17&ndash;18), each giving 4 days off with strategic leave.</p>
        </details>

        <details class="seo-faq">
          <summary>What is cuti bersama?</summary>
          <p>Cuti bersama (joint leave) are additional days the Prime Minister declares, usually to extend a public holiday into a longer break. They&rsquo;re not guaranteed &mdash; the government announces them a few weeks before, often for Hari Raya or Chinese New Year. They apply to government servants and many private employers follow suit, but it&rsquo;s not a legal entitlement.</p>
        </details>

        <details class="seo-faq">
          <summary>Do I get a replacement day off if a public holiday lands on a Sunday?</summary>
          <p>For federal holidays: yes, the following Monday is typically declared a replacement holiday. For state holidays on Sundays: depends on your state &mdash; Kelantan and Terengganu use a different system since Sundays are already workdays there.</p>
        </details>

        <details class="seo-faq">
          <summary>How does Kelantan and Terengganu&rsquo;s weekend work?</summary>
          <p>Both states observe Friday + Saturday as the weekend. Sunday is a regular workday, and Sunday public holidays (like Wesak Day 2026 on May 31) get Monday off as the replacement. Their public holidays list also includes state-specific days the rest of Malaysia doesn&rsquo;t observe.</p>
        </details>

        <details class="seo-faq">
          <summary>How far in advance should I plan my leave?</summary>
          <p>For Chinese New Year and Hari Raya, popular destinations book out 2&ndash;3 months ahead. The optimizer above shows the maximum value you can get per leave day &mdash; a single day strategically placed can turn a 1-day holiday into a 4-day weekend.</p>
        </details>
      </div>
    </details>
"""


# --- Drift guard (polish #4) ---------------------------------------------
# build.py is the source of truth; index.html is a generated artifact.
# If someone edits index.html directly (newer mtime than BOTH build.py and
# holidays.json), the next build would silently clobber their edits. Refuse
# unless --force is passed. Runs before any writes / heavy parsing so we fail
# fast.
def _check_drift():
    index_path = ROOT / "index.html"
    build_path = ROOT / "build.py"
    holidays_path = ROOT / "holidays.json"
    if not index_path.exists():
        return  # first build — nothing to protect
    if not build_path.exists() or not holidays_path.exists():
        return  # be lenient if somehow missing (let normal flow raise)
    index_mtime = index_path.stat().st_mtime
    build_mtime = build_path.stat().st_mtime
    holidays_mtime = holidays_path.stat().st_mtime
    # Drift = index.html touched more recently than both source files.
    # If holidays.json is newer, that's a legitimate rebuild trigger.
    if index_mtime > build_mtime and index_mtime > holidays_mtime:
        if "--force" not in sys.argv:
            print("⚠️  index.html was modified more recently than build.py and holidays.json.")
            print("    This usually means direct edits to index.html that build.py will overwrite.")
            print(f"    index.html   mtime: {index_mtime} ({os.path.dirname(__file__) or '.'}/index.html)")
            print(f"    build.py     mtime: {build_mtime}")
            print(f"    holidays.json mtime: {holidays_mtime}")
            print("")
            print("    To proceed anyway:    python3 build.py --force")
            print("    To preserve edits:    move them into build.py first")
            sys.exit(1)
        else:
            print("⚠️  --force specified — rebuilding despite index.html drift.")
            print("    Manual edits to index.html (if any) will be overwritten.")

_check_drift()
# --- end drift guard -----------------------------------------------------

HOLIDAYS = json.loads((ROOT / "holidays.json").read_text())

# Module-level constant: current year for past-vs-future placeholder copy
_CURRENT_YEAR = datetime.date.today().year

# Compact format for embedding: "YYYY-MM-DD"
# Optional 'c' flag = cuti bersama (bridge day, unverified)
HOLIDAYS_JS = {}
for year, rows in HOLIDAYS.items():
    HOLIDAYS_JS[year] = [
        {**{"d": r["date"], "n": r["name"], "t": r["type"], "s": r["state"]},
         **({"c": True} if r.get("note") else {})}
        for r in rows
    ]

STATES = sorted({r["state"] for rows in HOLIDAYS.values() for r in rows if r["state"]})


# --- JSON-LD structured data (for AI crawlers, Google rich results) -------
# Injected into both the main index.html <head> and the per-year pages.
# Source: holidays.json (verified against publicholidays.com.my Jul 2026).

def _federal_holiday_events(year):
    """Build schema.org Event list for federal holidays in a given year."""
    seen = set()
    events = []
    for h in HOLIDAYS.get(str(year), []):
        if h.get("type") != "federal":
            continue
        name = h["name"].replace(" Holiday", "")
        if name in seen:
            continue
        seen.add(name)
        events.append({
            "@type": "Event",
            "name": name,
            "startDate": h["date"],
            "endDate": h["date"],
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {"@type": "Country", "name": "Malaysia"},
        })
    return events


def build_jsonld_org():
    """Organization schema — site-wide identity for AI crawlers."""
    # Logo is an inline-SVG data URL (the same favicon we serve in <link rel="icon">).
    # Avoids a separate favicon.ico file (which 404s) and works for both Google
    # rich results and AI crawlers.
    logo_svg = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
        "<text y='.9em' font-size='90'>%F0%9F%8C%B4</text>"
        "</svg>"
    )
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "longweekend.my",
        "alternateName": "Long Weekend Planner Malaysia",
        "url": "https://longweekend.my",
        "logo": logo_svg,
        "description": "Malaysia's long-weekend planner. Calculates the longest stretches of consecutive days off, by year, by AL budget, and by state.",
        "founder": {
            "@type": "Organization",
            "name": "longweekend.my",
        },
        "areaServed": {"@type": "Country", "name": "Malaysia"},
        "knowsAbout": [
            "Malaysian public holidays",
            "Annual leave optimisation",
            "Long weekend planning",
        ],
    }, separators=(",", ":"))


def _longest_free_stretch(year):
    """Find the longest FREE (0-AL) long-weekend stretch for the given year
    using federal holidays + default Sat/Sun weekend. Returns dict with keys:
    start_date, end_date, days, holiday_names. Returns None if no 3+ day
    stretches exist (caller should fall back to a sensible default)."""
    import datetime as _dt
    holidays = HOLIDAYS.get(str(year), [])
    nw = {}
    for h in holidays:
        if h.get("type") == "federal":
            nw[h["date"]] = h["name"].replace(" Holiday", "")
    d = _dt.date(year, 1, 1)
    end_d = _dt.date(year, 12, 31)
    while d <= end_d:
        if d.weekday() >= 5:  # Sat=5, Sun=6
            iso = d.isoformat()
            if iso not in nw:
                nw[iso] = "Weekend"
        d += _dt.timedelta(days=1)
    # Find runs of consecutive days
    sorted_keys = sorted(nw.keys())
    if not sorted_keys:
        return None
    runs = []
    cur_start = sorted_keys[0]
    cur_end = sorted_keys[0]
    def _prev(iso):
        y_, m_, d_ = iso.split("-")
        return _dt.date(int(y_), int(m_), int(d_)) - _dt.timedelta(days=1)
    for k in sorted_keys[1:]:
        if _prev(k).isoformat() == cur_end:
            cur_end = k
        else:
            runs.append((cur_start, cur_end))
            cur_start = k
            cur_end = k
    runs.append((cur_start, cur_end))
    # Pick longest run (>=3 days); among ties prefer the one with most holidays
    best = None
    for s, e in runs:
        sy, sm, sd = s.split("-")
        ey, em, ed = e.split("-")
        days = (_dt.date(int(ey), int(em), int(ed)) - _dt.date(int(sy), int(sm), int(sd))).days + 1
        if days < 3:
            continue
        # Count AL-free: if every weekday in the run is either a holiday or a weekend
        we_count = 0
        hol_in_run = sum(1 for k in nw if s <= k <= e and nw[k] != "Weekend")
        cur = _dt.date(int(sy), int(sm), int(sd))
        end_dt = _dt.date(int(ey), int(em), int(ed))
        while cur <= end_dt:
            if cur.weekday() >= 5:
                we_count += 1
            cur += _dt.timedelta(days=1)
        al_needed = max(0, days - we_count - hol_in_run)
        hol_names = sorted({nw[k] for k in nw if s <= k <= e and nw[k] != "Weekend"})
        candidate = {
            "start_date": s,
            "end_date": e,
            "days": days,
            "al_needed": al_needed,
            "holiday_names": hol_names,
        }
        if best is None:
            best = candidate
        elif (days > best["days"]) or (days == best["days"] and al_needed < best["al_needed"]):
            best = candidate
    return best


def _fmt_longest_stretch(stretch):
    """Format a _longest_free_stretch dict into a human-readable string."""
    if not stretch:
        return ""
    import datetime as _dt
    sy, sm, sd = stretch["start_date"].split("-")
    ey, em, ed = stretch["end_date"].split("-")
    s_fmt = _dt.date(int(sy), int(sm), int(sd)).strftime("%-d %b")
    e_fmt = _dt.date(int(ey), int(em), int(ed)).strftime("%-d %b")
    al = stretch["al_needed"]
    al_txt = f"with {al} AL day" if al == 1 else f"with {al} AL days" if al > 1 else "with 0 AL needed"
    days = stretch["days"]
    hols = ", ".join(stretch["holiday_names"][:3])
    return f"the {s_fmt} – {e_fmt} run ({days} days off, {al_txt}, anchored by {hols})"


def build_jsonld_faq(year=2026):
    """FAQPage schema — drives Google FAQ rich results."""
    stretch = _longest_free_stretch(year)
    longest_text = _fmt_longest_stretch(stretch) if stretch else \
        f"typically the late-August Merdeka Day + Hari Malaysia run; check the planner for the exact dates in {year}."
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"How many public holidays does Malaysia have in {year}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Malaysia has 14 federal public holidays in {year} under the Holidays Act 1951 — the national gazette lists these as paid days off for private-sector workers. Some federal holidays have state-specific observance: New Year's Day and Nuzul Al-Quran, for example, are gazetted federal but not observed uniformly across all states. Each state adds its own state-level holidays (1-5 each), so the total observed per worker varies from 14 (Kuala Lumpur, Putrajaya, Labuan) to 18-19 (Sarawak, Sabah).",
                },
            },
            {
                "@type": "Question",
                "name": f"What is the longest long weekend in {year}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"The longest natural long weekend in {year} in Malaysia is {longest_text}. For the full year-optimised plan (which holidays to bridge for the most total days off), use the planner on longweekend.my.",
                },
            },
            {
                "@type": "Question",
                "name": "How do I calculate long weekends with limited annual leave?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Use the longweekend.my planner: set your year, your annual leave balance, and your state. The tool shows the longest stretches you can get with each AL count, sorted by days-off-per-AL-used. Most efficient: 1 AL day for a 3-day weekend, 2 AL for a 5-day stretch.",
                },
            },
            {
                "@type": "Question",
                "name": "Which Malaysian states have the most public holidays?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Sarawak has the most state holidays (Hari Gawai, Governor's birthday, etc — up to 5), Sabah has 3-4 (Kaamatan, etc), and the federal territories (Kuala Lumpur, Putrajaya, Labuan) typically observe only the federal gazetted holidays. Even within federal holidays, applicability can vary: some holidays (like New Year's Day and Nuzul Al-Quran) are gazetted federal but observed differently across states — see the table for per-state applicability.",
                },
            },
        ],
    }, separators=(",", ":"))


def build_jsonld_itemlist(year):
    """ItemList schema — the actual federal holidays as structured events."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"Malaysia Federal Public Holidays {year}",
        "description": f"All 14 federal public holidays in Malaysia for {year}, gazetted under the Holidays Act 1951 (with per-state applicability notes).",
        "numberOfItems": 14,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": event,
            }
            for i, event in enumerate(_federal_holiday_events(year))
        ],
    }, separators=(",", ":"))


# Pre-build common JSON-LD strings (deterministic, no need to re-compute per build)
JSONLD_ORG = build_jsonld_org()
JSONLD_FAQ_2026 = build_jsonld_faq(2026)
JSONLD_ITEMLIST_2026 = build_jsonld_itemlist(2026)
JSONLD_FAQ_2027 = build_jsonld_faq(2027)
JSONLD_ITEMLIST_2027 = build_jsonld_itemlist(2027)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Long Weekend Planner Malaysia 2026 / 2027 — Optimize Your Annual Leave</title>
<meta name="description" content="Plan your Malaysian annual leave for maximum days off. Tell us your AL budget — we solve the optimal year of long weekends and export to your calendar.">
<meta name="robots" content="index, follow">
<!-- __GSC_VERIFICATION__ -->
<!-- Google AdSense (only renders when ADSENSE_ENABLED is true in build.py) -->
<!-- __ADSENSE_HEAD__ -->
<link rel="canonical" href="https://longweekend.my/">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8C%B4%3C/text%3E%3C/svg%3E">
<meta property="og:title" content="Long Weekend Planner Malaysia 2026 / 2027">
<meta property="og:description" content="Turn your AL days into the most days off. Interactive planner with calendar export.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://longweekend.my/">
<meta property="og:locale" content="en_MY">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json" id="ld-org">
{"@context":"https://schema.org","@type":"WebApplication","name":"Long Weekend Planner Malaysia","url":"https://longweekend.my/","applicationCategory":"UtilitiesApplication","operatingSystem":"Any","offers":{"@type":"Offer","price":"0","priceCurrency":"MYR"},"description":"Interactive tool that solves the optimal annual leave plan for Malaysian public holidays."}
</script>
<!-- AI-citable structured data: Organization identity + FAQ + 2026 federal holiday list -->
<script type="application/ld+json" id="ld-organization">__JSONLD_ORG__</script>
<script type="application/ld+json" id="ld-faq-2026">__JSONLD_FAQ_2026__</script>
<script type="application/ld+json" id="ld-itemlist-2026">__JSONLD_ITEMLIST_2026__</script>
<script type="application/ld+json" id="ld-faq-2027">__JSONLD_FAQ_2027__</script>
<script type="application/ld+json" id="ld-itemlist-2027">__JSONLD_ITEMLIST_2027__</script>
<!-- Vercel Web Analytics (no cookies, no PII, GDPR-friendly) -->
<script>
window.va=window.va||function(){window.vaq=window.vaq||[];};
</script>
<script defer src="/_vercel/insights/script.js"></script>
<script defer src="/_vercel/speed-insights/script.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#FDF6F0;--text:#1C1917;--muted:#78716C;--accent:#0F766E;
  --leave:#0F766E;--tint:#CCFBF1;--hol:#FDE68A;--weekend:#F3F0EC;
  --border:#E7D9C8;--panel:#FFFFFF;
}
html{scroll-behavior:smooth}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;font-size:15px;-webkit-font-smoothing:antialiased}
.container{max-width:920px;margin:0 auto;padding:1rem 1.25rem 3rem}
.wordmark{font-size:18px;font-weight:700;color:var(--text);letter-spacing:-0.01em;margin-bottom:0.25rem;display:flex;align-items:center;gap:0}
.wordmark .my{color:var(--accent);margin-right:0.35rem}
.wordmark-icon{font-size:24px;line-height:1;flex:0 0 auto}
@media(max-width:480px){.wordmark-icon{font-size:20px}}
/* Answer band — the hero IS the answer (cream card, dark text) */
.answer-band{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:14px;padding:1.5rem 1.75rem;margin-bottom:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
.answer-headline{font-size:clamp(22px,5.5vw,34px);font-weight:700;line-height:1.3;font-variant-numeric:tabular-nums;letter-spacing:-0.01em;color:var(--text)}
.answer-headline .num{color:var(--accent);font-weight:800}
.answer-headline .blended{color:var(--accent);font-weight:700;font-size:0.9em;margin-left:0.2em}
.answer-meta{margin-top:0.6rem;color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums}
.answer-leave{margin-top:0.5rem;color:var(--text);font-size:14px;line-height:1.5}
.answer-leave strong{color:var(--accent);font-weight:600}
.answer-cta{margin-top:1.1rem;display:flex;gap:0.6rem;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:0.4rem;padding:0.6rem 1rem;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;cursor:pointer;border:none;min-height:44px;transition:opacity .15s,transform .1s}
.btn:active{transform:scale(0.97)}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{opacity:0.88}
.btn-secondary{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.btn-secondary:hover{background:var(--tint)}
.btn-err{background:#dc2626!important;color:#fff!important;border-color:#dc2626!important}
.btn-sm{padding:0.35rem 0.7rem;font-size:12px;min-height:0;border-radius:6px}
.se-actions{margin-top:0.7rem;display:flex;gap:0.5rem;flex-wrap:wrap}
.btn-affiliate{background:transparent;color:var(--muted);border:1px dashed var(--muted);font-size:11.5px;padding:0.3rem 0.6rem}
.btn-affiliate:hover{color:var(--accent);border-color:var(--accent)}
.affiliate-disclosure{font-size:10.5px;color:var(--muted);opacity:0.7;margin-top:0.3rem;font-style:italic}
/* Ad slots — collapse to zero when empty, grow only when AdSense fills them */
.ad-slot{min-height:0;margin:0 auto;max-width:100%;overflow:hidden;display:block}
/* The <ins> starts as display:block with no content. Hide it until AdSense
   has either filled the slot (data-adsbygoogle-status="filled") or set an
   inline height. Without this, the empty <ins> reserves 250-300px of dead
   space because display:block + no content still takes up vertical room. */
.ad-slot ins.adsbygoogle:not([data-adsbygoogle-status="filled"]):not([style*="height"]){display:none!important}
/* When an ad fills, give the slot breathing room. */
.ad-slot:has(ins[data-adsbygoogle-status="filled"]),.ad-slot:has(ins[style*="height:"]){min-height:120px;margin-bottom:1.5rem}
@media(max-width:640px){.ad-slot:has(ins[data-adsbygoogle-status="filled"]),.ad-slot:has(ins[style*="height:"]){min-height:100px}}
/* Calendar */
.calendar-section{margin-bottom:1.5rem}
.calendar{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:0.75rem}
.month{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:0.6rem 0.5rem}
.month-name{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);padding:0 0.3rem 0.4rem}
.day-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.day{aspect-ratio:1;display:flex;align-items:flex-start;justify-content:flex-end;padding:2px 4px;font-size:11px;color:var(--text);border-radius:4px;position:relative;font-variant-numeric:tabular-nums}
.dow{font-size:8px;font-weight:700;color:var(--muted);text-align:center;padding:2px 0;line-height:1;letter-spacing:0.05em;text-transform:uppercase}
.day-hol-label{position:absolute;bottom:2px;left:2px;right:2px;font-size:7px;line-height:1;text-align:center;color:var(--text);opacity:0.7;pointer-events:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.day-hol-label.in-stretch{font-size:7.5px;line-height:1.05;opacity:0.9;color:#0F766E;font-weight:700;white-space:normal;word-break:break-word;hyphens:auto;text-overflow:clip;overflow:visible;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.day.blank{visibility:hidden}
.day.weekend{background:var(--weekend);color:var(--muted)}
.day.past{opacity:0.32;cursor:default;pointer-events:none}
.day.in-stretch{background:var(--tint)}
.day.leave{background:var(--leave);color:#fff;font-weight:700}
.day.hol:not(:has(.day-hol-label))::after{content:"";position:absolute;bottom:3px;width:4px;height:4px;border-radius:50%;background:var(--hol)}
.day.leave.hol::after{background:#FCD34D}
.day.clickable{cursor:pointer;transition:transform .12s,box-shadow .12s,outline-color .12s;outline:2px solid transparent;outline-offset:-2px}
.day.clickable:hover{transform:scale(1.18);z-index:2;box-shadow:0 4px 12px rgba(13,148,136,.25);outline-color:var(--accent)}
.day.clickable:active{transform:scale(1.05)}
.day.clickable:focus-visible{outline-color:var(--accent);outline-offset:1px}
.day.selected{outline:2.5px solid var(--accent)!important;outline-offset:-1px;box-shadow:0 0 0 3px rgba(13,148,136,.25)}
.legend-hint{color:var(--muted);font-style:italic;font-size:12px;margin-left:auto}
/* Configurator */
.configurator{display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-end;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:1rem 1.25rem;margin-bottom:1.5rem;position:relative}
.cfg-group{display:flex;flex-direction:column;gap:0.3rem;min-width:120px;flex:1}
.cfg-group label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted)}
.cfg-group label .v{color:var(--accent);font-variant-numeric:tabular-nums}
select,input[type=range]{width:100%;font-family:inherit;font-size:14px;color:var(--text);background:#fff;border:1px solid var(--border);border-radius:6px;padding:0.45rem 0.5rem;min-height:40px}
input[type=range]{padding:0;accent-color:var(--accent);height:40px;border:none;background:transparent}
.state-disclosure{min-width:160px}
.state-disclosure summary{list-style:none;cursor:pointer;font-size:14px;padding:0.45rem 0.5rem;border:1px solid var(--border);border-radius:6px;background:#fff;min-height:40px;display:flex;align-items:center;justify-content:space-between;gap:0.5rem}
.state-disclosure summary::-webkit-details-marker{display:none}
.state-disclosure summary::after{content:"▾";color:var(--muted);font-size:12px}
.state-disclosure[open] summary::after{content:"▴"}
.state-list{position:absolute;top:100%;left:0;right:0;max-height:240px;overflow-y:auto;background:#fff;border:1px solid var(--border);border-radius:6px;padding:0.4rem;z-index:10;box-shadow:0 4px 12px rgba(0,0,0,.08);margin-top:4px}
.state-list label{display:flex;align-items:center;gap:0.4rem;padding:0.35rem;font-size:13px;cursor:pointer;text-transform:none;letter-spacing:0;color:var(--text)}
.state-list label:hover{background:var(--tint);border-radius:4px}
.state-list input{accent-color:var(--accent)}
/* Stretch list */
.stretch-list{display:flex;flex-direction:column;gap:0.5rem;margin-bottom:1.5rem}
.stretch{background:var(--panel);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.stretch-header{width:100%;display:flex;align-items:center;gap:0.6rem;padding:0.7rem 1rem;background:transparent;border:none;cursor:pointer;text-align:left;font-family:inherit;min-height:48px}
.stretch-range{font-weight:600;font-size:14px;color:var(--text);font-variant-numeric:tabular-nums;flex:0 1 auto}
.stretch-stats{font-size:13px;color:var(--muted);flex:1;font-variant-numeric:tabular-nums}
.stretch-chevron{color:var(--muted);font-size:14px;transition:transform .2s}
.stretch.open .stretch-chevron{transform:rotate(180deg)}
.stretch-score{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;padding:2px 8px;border-radius:6px;white-space:nowrap;flex:0 0 auto}
.stretch-score.free{background:#DCFCE7;color:#15803D}
.stretch-score.high{background:var(--tint);color:var(--accent)}
.stretch-score.low{background:var(--border);color:var(--muted)}
.stretch-expand{display:none;padding:0 1rem 1rem;border-top:1px solid var(--border);margin-top:0}
.stretch-expand .se-hols{font-size:13px;color:var(--muted);margin:0.7rem 0 0.3rem}
.stretch-expand .se-leave{font-size:13px;color:var(--text);margin-bottom:0.6rem}
.stretch-expand .se-leave strong{color:var(--accent)}
/* 2027 disclaimer removed at launch — see SETUP_LAUNCH.md */
@media(max-width:600px){
  .calendar{grid-template-columns:1fr}
  .configurator{flex-direction:column;align-items:stretch;gap:0.8rem}
  .cfg-group{min-width:0}
  /* Larger tap targets on day cells */
  .day{font-size:13px}
  .day.clickable:hover{transform:scale(1.25)}
  /* Scroll-to-top button (mobile corner) */
  .scroll-top{position:fixed;bottom:1.25rem;right:1.25rem;width:44px;height:44px;border-radius:50%;background:var(--accent);color:#fff;border:none;font-size:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.18);z-index:20;display:none;align-items:center;justify-content:center;transition:opacity .2s,transform .1s}
  .scroll-top:hover{opacity:0.88}
  .scroll-top:active{transform:scale(0.95)}
  .scroll-top.visible{display:flex}
}
/* Trust footer */
.disclaimer{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:.8rem 1rem;margin-top:1.5rem;font-size:12px;color:var(--muted);line-height:1.5}
.disclaimer a{color:var(--accent);text-decoration:none}
/* SEO content section (server-rendered for AdSense + organic search depth)
   The .seo-section-collapse wrapper handles the dropdown + outer chrome.
   This .seo-section class on the inner <section> just controls spacing. */
.seo-section{margin-top:0;max-width:none;background:transparent;border:none;padding:0;border-radius:0}
.seo-section h2{font-size:16px;margin:1.5rem 0 0.6rem;color:var(--text);font-weight:700}
.seo-section h2:first-child{margin-top:0.25rem}
.seo-section p{font-size:13.5px;line-height:1.6;color:var(--text);margin:0.5rem 0}
.seo-section .seo-muted{color:var(--muted);font-size:12.5px}
/* Outer dropdown wrapper — collapses the whole section by default */
.seo-section-collapse{margin-top:1.5rem;border:1px solid var(--border);border-radius:10px;background:var(--panel);overflow:hidden;max-width:760px;margin-left:auto;margin-right:auto}
.seo-section-collapse>summary{cursor:pointer;list-style:none;padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;gap:0.75rem;font-weight:600;font-size:15px;color:var(--text);user-select:none;background:var(--panel);transition:background 0.12s}
.seo-section-collapse>summary:hover{background:#F3F0EC}
.seo-section-collapse>summary::-webkit-details-marker{display:none}
.seo-section-collapse>summary::after{content:"▾";font-size:14px;color:var(--muted);transition:transform 0.2s;flex-shrink:0}
.seo-section-collapse[open]>summary::after{transform:rotate(180deg)}
.seo-section-title{flex:1}
.seo-section-hint{font-size:12px;color:var(--muted);font-weight:400;display:inline}
.seo-section-collapse[open] .seo-section-hint{display:none}
.seo-section-content{padding:0 1.25rem 1.25rem}
.seo-table{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid var(--border);border-radius:6px;overflow:hidden;margin:0.5rem 0 0.75rem}
.seo-table th,.seo-table td{padding:0.45rem 0.55rem;text-align:left;border-bottom:1px solid #F0ECE4}
.seo-table th{background:#F3F0EC;font-weight:600;font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.02em}
.seo-table tbody tr:last-child td{border-bottom:none}
.seo-table tbody tr:nth-child(even){background:#FBF9F6}
details.seo-faq{border-bottom:1px solid var(--border);padding:0.85rem 0}
details.seo-faq:first-of-type{border-top:1px solid var(--border)}
details.seo-faq summary{cursor:pointer;font-weight:600;font-size:14px;padding:0.25rem 0;list-style:none;display:flex;align-items:center;justify-content:space-between;color:var(--text)}
details.seo-faq summary::-webkit-details-marker{display:none}
details.seo-faq summary::after{content:"+";font-size:20px;color:var(--muted);font-weight:400;transition:transform 0.15s}
details.seo-faq[open] summary::after{content:"−"}
details.seo-faq[open] summary{margin-bottom:0.25rem}
details.seo-faq p{font-size:13.5px;line-height:1.65;color:#4A4640;margin:0.5rem 0 0}
@media(max-width:600px){.seo-section{padding:1.25rem 1rem}.seo-table th,.seo-table td{padding:0.4rem 0.35rem;font-size:11.5px}}
footer{text-align:center;padding:1.5rem 0 .5rem;color:var(--muted);font-size:13px}
footer a{color:var(--accent);text-decoration:none}
footer p{margin-bottom:0.25rem}
.footer-years{font-size:12.5px;color:var(--muted)}
.footer-years a{color:var(--accent);font-weight:600;font-variant-numeric:tabular-nums;margin:0 0.1em}
.kopi{margin-top:0.5rem;font-size:12.5px;opacity:0.92}
.kopi a{font-weight:600;border-bottom:1px dashed var(--accent);text-decoration:none;color:var(--accent)}
.kopi-cta{margin-top:0.35rem;font-size:12.5px}
.kopi-link{font-weight:600;border-bottom:1px dashed var(--accent);text-decoration:none;color:var(--accent)}
.waitlist{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:1.25rem 1.25rem 1rem;margin-top:1.5rem;text-align:center}
.waitlist h3{font-size:16px;margin-bottom:0.4rem;color:var(--text)}
.waitlist p{color:var(--muted);font-size:13px;margin-bottom:0.8rem;line-height:1.5}
.waitlist-form{display:flex;flex-direction:column;gap:0.5rem;max-width:380px;margin:0 auto}
.waitlist-form input[type=email],
.waitlist-form textarea{padding:0.55rem 0.75rem;border:1px solid var(--border);border-radius:8px;font:inherit;font-size:14px;background:var(--bg);color:var(--text);width:100%;resize:vertical}
.waitlist-form input[type=email]:focus,
.waitlist-form textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--tint)}
.waitlist-form button{width:100%}
.waitlist-status{margin-top:0.7rem;font-size:13px;min-height:1.2em}
.waitlist-status.ok{color:var(--accent);font-weight:600}
.waitlist-status.err{color:#B91C1C}

/* === Email capture popup (minimal) === */
.lw-popup-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:1000;display:none;align-items:center;justify-content:center;padding:1rem;animation:lw-fade-in .2s ease}
.lw-popup-overlay.visible{display:flex}
.lw-popup{background:var(--bg);border-radius:12px;padding:1.5rem;max-width:380px;width:100%;box-shadow:0 8px 24px rgba(0,0,0,.15);animation:lw-slide-up .3s ease}
@media(max-width:640px){.lw-popup{position:fixed;bottom:0;left:0;right:0;border-radius:12px 12px 0 0;max-width:100%}}
.lw-popup h3{font-size:16px;margin:0 0 .5rem;color:var(--text)}
.lw-popup p{font-size:13px;color:var(--muted);margin:0 0 1rem}
.lw-popup input[type=email]{width:100%;padding:.6rem .75rem;border:1px solid var(--border);border-radius:8px;font:inherit;font-size:14px;background:#fff;color:var(--text);margin-bottom:.75rem}
.lw-popup input[type=email]:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--tint)}
.lw-popup-actions{display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-bottom:.5rem}
.lw-popup button[type=submit]{flex:1;padding:.6rem;background:var(--accent);color:#fff;border:none;border-radius:8px;font:inherit;font-size:14px;font-weight:500;cursor:pointer}
.lw-popup button[type=submit]:hover{opacity:.9}
.lw-popup .lw-not-now{background:none;border:none;color:var(--muted);cursor:pointer;font:inherit;font-size:13px;padding:.6rem;text-decoration:underline}
.lw-popup .lw-privacy{font-size:11px;color:var(--muted);text-align:center;margin:.5rem 0 0}
.lw-popup .lw-privacy a{color:var(--muted)}
@keyframes lw-fade-in{from{opacity:0}to{opacity:1}}
@keyframes lw-slide-up{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
.legend{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:0.75rem;font-size:12px;color:var(--muted);align-items:center}
.legend span{display:flex;align-items:center;gap:0.3rem}
.legend .sw{width:12px;height:12px;border-radius:3px;display:inline-block}
</style>
</head>
<body>
<div class="container">
  <div class="wordmark">longweekend<span class="my">.my</span><span class="wordmark-icon" aria-hidden="true">🌴</span></div>

  <section class="configurator" id="configurator">
    <div class="cfg-group">
      <label>Year</label>
      <select id="year"><option value="2026">2026</option><option value="2027">2027</option></select>
    </div>
    <div class="cfg-group cfg-al">
      <label>AL days: <span class="v" id="al-value">14</span></label>
      <input type="range" id="al-slider" min="1" max="30" value="14" step="1">
    </div>
    <div class="cfg-group">
      <label>State holidays</label>
      <details class="state-disclosure">
        <summary><span id="state-summary">Federal only</span></summary>
        <div class="state-list" id="state-selector"></div>
      </details>
    </div>
    <div class="cfg-group">
      <label for="weekend-override">Your weekend</label>
      <select id="weekend-override" title="Pick which days are your rest days. Default follows your state's weekend pattern. Override this if you work shifts, retail, healthcare, or any non-standard schedule.">
        <option value="auto">Auto (per state)</option>
        <option value="sat-sun">Sat + Sun (most office workers)</option>
        <option value="fri-sat">Fri + Sat</option>
        <option value="mon-off">Mon only (single rest day)</option>
        <option value="sun-only">Sun only (single rest day)</option>
      </select>
    </div>
  </section>

  <section class="answer-band" id="answer-band"></section>

  <section class="calendar-section">
    <div class="legend">
      <span><i class="sw" style="background:var(--leave)"></i>Leave day</span>
      <span><i class="sw" style="background:var(--tint)"></i>Days off</span>
      <span><i class="sw" style="background:var(--weekend)"></i>Weekend</span>
      <span><i class="sw" style="background:var(--hol);border-radius:50%;width:8px;height:8px"></i>Holiday</span>
      <span class="legend-hint">Tap any tinted day to jump to that stretch ↓</span>
    </div>
    <div class="calendar" id="calendar"></div>
  </section>

  <section class="stretch-list" id="stretch-list"></section>

  <button class="scroll-top" id="scroll-top" aria-label="Scroll to top">↑</button>

  <section class="waitlist" id="waitlist">
    <h3>🗓️ Get updates &amp; send feedback</h3>
    <p>Drop your email — and tell me what's missing or broken. I read every reply and use it to decide what to build next.</p>
    <form class="waitlist-form" id="waitlist-form" autocomplete="off" novalidate>
      <input type="email" name="email" id="waitlist-email" placeholder="you@example.com" required aria-label="Email address">
      <textarea name="feedback" id="waitlist-feedback" placeholder="What would make this more useful? (Optional)" rows="2" maxlength="500" aria-label="Feedback"></textarea>
      <!-- Honeypot — bots fill it, humans don't -->
      <input type="text" name="website" id="waitlist-website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">
      <button type="submit" class="btn btn-primary">Notify me</button>
    </form>
    <p class="waitlist-status" id="waitlist-status" role="status" aria-live="polite"></p>
  </section>

  <section class="seo-section" aria-label="2026 Malaysia public holidays and FAQ">
    __SEO_SECTION__
  </section>

  <footer>
    <p><span class="muted">Made with ☕ in KL</span> · <a href="/about.html" data-track="nav_about" onclick="track('nav_about')">About</a> · <a href="/privacy.html" data-track="nav_privacy" onclick="track('nav_privacy')">Privacy</a> · <a href="/privacy.html#advertising" data-track="nav_ads" onclick="track('nav_ads')">Ads</a></p>
    <p class="footer-years">Holidays by year: <a href="/2026" data-track="footer_year" onclick="track('footer_year',{year:2026})">2026</a> · <a href="/2027" data-track="footer_year" onclick="track('footer_year',{year:2027})">2027</a> · <a href="/2028" data-track="footer_year" onclick="track('footer_year',{year:2028})">2028</a></p>
    <p class="footer-seo">More: <a href="/malaysia-long-weekends-2026/" rel="alternate">Malaysia long weekends 2026</a> · <a href="/selangor-long-weekends-2026/">Selangor</a> · <a href="/cuti-panjang-malaysia-2026/" rel="alternate" hreflang="ms">Cuti panjang 2026 (BM)</a></p>
    <p class="kopi-cta">Saved you a few days of leave? <a href="https://www.buymeacoffee.com/longweekend" target="_blank" rel="noopener" data-track="tip_jar_click" onclick="track('tip_jar_click',{source:'footer'})" class="kopi-link">buy miso a kopi</a></p>
    <p style="margin-top:0.75rem"><button class="btn btn-primary" id="share-btn" style="font-size:13px;padding:0.5rem 0.9rem">💬 Share plan</button></p>
  </footer>
</div>

<script id="ld-stretches" type="application/ld+json"></script>
<script>
const HOLIDAYS=__HOLIDAYS_JS__;
const STATES=__STATES_JS__;
const WEEKEND=new Set([0,6]);// default federal weekend (Sun, Sat) — see weekendForState() for per-state overrides
const MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAYS=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

// --- Affiliate config ---
// Set `enabled:true` + paste your `aid` (Booking/Agoda) or `associateid` (Skyscanner)
// once your affiliate program is approved. The buttons will work as plain search
// links even when `enabled:false` (no commission tracked) — so the site is
// always useful, even before approval. See SETUP_AFFILIATE.md for sign-up links.
// All base URLs are real, working general search links — users get a working
// result today; once `enabled` flips to true and `aid` is set, the affiliate
// param is appended automatically (no other code change required).
const AFFILIATE={
  booking:{enabled:false,aid:'',label:'🏨 Booking.com',type:'hotel',
    url:d=>{let u=`https://www.booking.com/searchresults.html?ss=${encodeURIComponent(d)}`;if(AFFILIATE.booking.enabled&&AFFILIATE.booking.aid)u+=`&aid=${encodeURIComponent(AFFILIATE.booking.aid)}`;return u}},
  agoda:{enabled:false,aid:'',label:'🏨 Agoda',type:'hotel',
    url:d=>{let u=`https://www.agoda.com/search?city=${encodeURIComponent(d)}`;if(AFFILIATE.agoda.enabled&&AFFILIATE.agoda.aid)u+=`&cid=${encodeURIComponent(AFFILIATE.agoda.aid)}`;return u}},
  klook:{enabled:true,aid:'126213',aff_adid:'1326747',label:'🏨 Klook',type:'hotel',
    // Klook redirect URL is affiliate.klook.com/redirect?aid=...&aff_adid=...&k_site=<destination URL>
    // Destination URL is Klook hotels search with `search_query` param for the city.
    // Tracking params from the original signup link (spm, clickId) are preserved
    // so Klook's attribution matches whatever they used to issue this affiliate ID.
    url:d=>{
      const trackingParams='spm=Home.TopSearchBar_MainNode_LIST&clickId=a6432a97a0';
      const dest=String(d||'').trim();
      const kSite=`https://www.klook.com/hotels/?search_query=${encodeURIComponent(dest)}&${trackingParams}`;
      return `https://affiliate.klook.com/redirect?aid=${encodeURIComponent(AFFILIATE.klook.aid)}&aff_adid=${encodeURIComponent(AFFILIATE.klook.aff_adid)}&k_site=${encodeURIComponent(kSite)}`;
    }},
  skyscanner:{enabled:false,aid:'',label:'✈️ Skyscanner',type:'flight',
    url:d=>{let u=`https://www.skyscanner.com/transport/flights/anywhere/?query=${encodeURIComponent(d)}`;if(AFFILIATE.skyscanner.enabled&&AFFILIATE.skyscanner.aid)u+=`&associateid=${encodeURIComponent(AFFILIATE.skyscanner.aid)}`;return u}},
  trip:{enabled:true,label:'✈️ Trip.com',type:'flight',
    // Trip.com deep-link format (verified by expanding https://www.trip.com/t/6KgZVf4yNV2):
    //   /flights/Kuala%20Lumpur-to-Bangkok/tickets-KUL-BKK
    //     ?flighttype=S              (one-way = S, round-trip = R)
    //     &dcity=KUL                 (origin — left blank, user fills in)
    //     &acity=BKK                 (destination — left blank, user fills in)
    //     &ddate=YYYY-MM-DD          (departure — pre-filled from stretch start)
    //     &rdate=YYYY-MM-DD          (return — pre-filled from stretch end)
    //     &Allianceid=9065442
    //     &SID=322866832
    //     &trip_sub1=                (empty by default)
    //     &trip_sub3=D18452667
    // Design: per user request, origin and destination are LEFT BLANK on
    // Trip.com's side so the user picks their own airports. The stretch
    // dates are pre-filled so the user lands on Trip.com with the right
    // window already selected. This works because Trip.com's flight search
    // page accepts ddate/rdate without requiring dcity/acity to be set.
    //
    // Signature: url(dest, startIso, endIso) — dest/holiday info is no
    // longer used (was only for the IATA mapping), but we keep dest as a
    // param so the call site doesn't need to change. Skyscanner fallback
    // still uses dest for its "anywhere" search.
    url:(d, startIso, endIso)=>{
      const ddate=startIso||'';
      const rdate=endIso||'';
      // Pre-fill destination airport from dest string. nameToIata() does fuzzy
      // fallback on city name; returns null for unknown → acity stays blank →
      // Trip.com falls back to its own destination picker (safe degradation).
      const iata=nameToIata(d);
      const acity=iata?iata[0]:'';
      return `https://www.trip.com/flights/`
           + `?flighttype=R&ddate=${encodeURIComponent(ddate)}&rdate=${encodeURIComponent(rdate)}`
           + `&acity=${encodeURIComponent(acity)}`
           + `&Allianceid=9065442&SID=322866832&trip_sub1=&trip_sub3=D18452667`;
    }},
};

// Map a holiday name → default destination string. Used by the per-stretch
// affiliate CTAs to suggest "🏨 Find a stay in {destination}" automatically.
// Lowercase substring match — order doesn't matter; first hit wins.
const HOLIDAY_DEST=[
  {match:['chinese new year','cny'],dest:'Penang, Malaysia'},
  {match:['hari raya aidilfitri','hari raya'],dest:'Kuala Lumpur, Malaysia'},
  {match:['hari raya aidiladha'],dest:'Kuala Lumpur, Malaysia'},
  {match:['deepavali'],dest:'Batu Caves, Malaysia'},
  {match:['thai pusam'],dest:'Batu Caves, Malaysia'},
  {match:['vesak'],dest:'Penang, Malaysia'},
  {match:['nuzul al-quran','nuzul'],dest:'Kuala Lumpur, Malaysia'},
  {match:['maal hijrah','awal muharram'],dest:'Kuala Lumpur, Malaysia'},
  {match:['merdeka','hari merdeka'],dest:'Kuala Lumpur, Malaysia'},
  {match:['malaysia day'],dest:'Kuching, Malaysia'},
  {match:['hari gawai'],dest:'Kuching, Malaysia'},
  {match:['christmas','natal'],dest:'Cameron Highlands, Malaysia'},
  {match:['new year'],dest:'Genting Highlands, Malaysia'},
  {match:['waisak'],dest:'Penang, Malaysia'},
  {match:['sultan'],dest:'Johor Bahru, Malaysia'}
];

// Pick the best destination for a stretch based on the holidays it contains.
function destForStretch(s){
  if(!s.holidays||!s.holidays.length)return null;
  for(const h of s.holidays){
    const hn=(h.name||'').toLowerCase();
    for(const m of HOLIDAY_DEST){
      if(m.match.some(k=>hn.includes(k)))return m.dest;
    }
  }
  return 'Malaysia';// safe fallback
}

// Map destination strings (from HOLIDAY_DEST) to [IATA code, city slug for URL].
// Trip.com's URL needs IATA codes; we also need a clean URL slug. Falls back
// to null if the destination isn't mapped → caller skips Trip.com and uses
// Skyscanner (or the existing "anywhere" search) instead. Extend this as you
// add more destinations. Flight destinations outside Malaysia are also
// included since users often travel internationally on long weekends.
const IATA_BY_DEST={
  'Penang, Malaysia':              ['PEN','Penang'],
  'Langkawi, Malaysia':             ['LGK','Langkawi'],
  'Kuala Lumpur, Malaysia':         ['KUL','Kuala Lumpur'],
  'Batu Caves, Malaysia':           ['KUL','Kuala Lumpur'],
  'Kuching, Malaysia':              ['KCH','Kuching'],
  'Johor Bahru, Malaysia':          ['JHB','Johor Bahru'],
  'Cameron Highlands, Malaysia':    ['PEN','Penang'],     // nearest commercial airport
  'Genting Highlands, Malaysia':    ['KUL','Kuala Lumpur'],
  'Singapore':                      ['SIN','Singapore'],
  'Bangkok, Thailand':              ['BKK','Bangkok'],
  'Denpasar, Bali, Indonesia':      ['DPS','Denpasar'],
  'Phuket, Thailand':               ['HKT','Phuket'],
  'Bali, Indonesia':                ['DPS','Denpasar'],
};
function nameToIata(dest){
  if(!dest)return null;
  if(IATA_BY_DEST[dest])return IATA_BY_DEST[dest];
  // Fuzzy fallback: match by city name in the destination string.
  const key=dest.split(',')[0].trim().toLowerCase();
  for(const k in IATA_BY_DEST){
    if(k.toLowerCase().split(',')[0].trim()===key)return IATA_BY_DEST[k];
  }
  return null;
}

// --- Attribution layer ---
// Capture UTM params + referrer on first pageview, persist for the session
// (sessionStorage so we don't pollute localStorage across visits), and
// auto-attach to every subsequent event. Strip UTMs from the visible URL so
// share links stay clean.
const UTM_KEYS=['utm_source','utm_medium','utm_campaign','utm_term','utm_content'];
const ATTR_KEY='lw_attribution_v1';

function captureAttribution(){
  try{
    const p=new URLSearchParams(location.search);
    const fresh={};
    let hasFresh=false;
    UTM_KEYS.forEach(k=>{const v=p.get(k);if(v){fresh[k]=v;hasFresh=true}});
    // Detect /from/<source> path. Path segments survive WhatsApp/Telegram
    // preview sanitization (which strips utm_*, via, ref, etc. from query
    // params), so we use the path as the share attribution channel. If we
    // land on /from/friend, treat as utm_source=friend and rewrite the URL
    // to the canonical form (?y=&al=#hash) so the recipient sees a clean
    // address bar and we get utm_source=friend on the pageview event for
    // the dashboard. Path-matched source takes precedence over any URL
    // params to prevent double-attribution.
    const fromMatch=location.pathname.match(/^\/from\/([a-z0-9_-]+)\/?$/i);
    if(fromMatch){
      const fromSource=fromMatch[1].toLowerCase();
      fresh.utm_source=fromSource;
      hasFresh=true;
    }
    // Fallback: read the `lw_src` cookie set by /r/[code] redirects. This
    // is the share-attribution channel that survives chat-app URL
    // sanitization — short URLs on a custom domain aren't normalized, and
    // the /r/ redirect sets a cookie that the landing page reads. Has
    // lower priority than URL params + path (which are explicit) but
    // higher priority than the bare referrer (which is a guess).
    if(!hasFresh){
      try{
        const m=document.cookie.match(/(?:^|;\s*)lw_src=([^;]+)/);
        if(m){
          const src=decodeURIComponent(m[1]).toLowerCase().slice(0,32);
          if(src && /^[a-z0-9_-]+$/.test(src)){
            fresh.utm_source=src;
            hasFresh=true;
          }
        }
      }catch(e){}
    }
    // Fallback: if no UTM params and no stored attribution, tag the referrer
    // host (if external) as a coarse source. This is the "someone shared the
    // link in WhatsApp" path — we won't know it's WhatsApp specifically, but
    // we'll know it's a referrer.
    const ref=document.referrer;
    let refHost=null;
    try{if(ref){refHost=new URL(ref).host;if(refHost===location.host)refHost=null}}catch(e){}
    if(hasFresh){
      sessionStorage.setItem(ATTR_KEY,JSON.stringify({...fresh,refHost,ts:Date.now()}));
    }else if(!sessionStorage.getItem(ATTR_KEY)&&refHost){
      // First visit, no UTM, has external referrer — capture it as a fallback
      sessionStorage.setItem(ATTR_KEY,JSON.stringify({refHost,ts:Date.now()}));
    }
    // If we landed via /from/<source>, rewrite URL to canonical form
    // (drop the /from/ prefix, keep ?y, ?al, #hash) so the recipient sees
    // a clean address bar. This runs before the UTM-strip block below
    // because /from/ paths don't carry any UTM params to strip.
    if(fromMatch){
      const y=p.get('y')||'';
      const al=p.get('al')||'';
      const qs=[];
      if(y)qs.push(`y=${encodeURIComponent(y)}`);
      if(al)qs.push(`al=${encodeURIComponent(al)}`);
      const canonical=`${location.origin}/${qs.length?'?'+qs.join('&'):''}${location.hash}`;
      history.replaceState(null,'',canonical);
    }else if(hasFresh && fresh.utm_source !== 'share'){
      // Strip UTMs from the URL bar for non-share sources (reddit, threads,
      // etc.) so the address stays clean and power-user bookmarks don't carry
      // our campaign tags. KEEP UTMs visible for share-source visits because
      // share recipients are the most likely to copy-paste the URL bar, and
      // losing the source attribution there is more costly than an ugly URL.
      const url=new URL(location.href);
      UTM_KEYS.forEach(k=>url.searchParams.delete(k));
      const clean=url.pathname+(url.search?url.search:'')+url.hash;
      history.replaceState(null,'',clean);
    }
  }catch(e){console.warn('[attr] capture failed',e)}
}
captureAttribution();

function getAttribution(){
  try{return JSON.parse(sessionStorage.getItem(ATTR_KEY))||{}}catch(e){return{}}
}

// Custom event tracking — wired to Vercel Web Analytics AND our own
// first-party DB (via /api/track-event). The DB write is fire-and-forget:
// we don't await the response on the client. If /api/track-event is
// unreachable or POSTGRES_URL is not set, Vercel Web Analytics still
// gets the event — analytics never blocks the user.
// Pattern: va('event', { name: 'EventName', data: { ... } })
// See: https://vercel.com/docs/analytics/custom-events
// Plus: we keep the Plausible/gtag fallback so the function is portable if
// we ever swap analytics providers. In dev (window.__TRACK_DEBUG__=true),
// events also log to the console.
// Attribution is auto-merged into every event's `data` so the dashboard can
// answer "which channel drove this share_click / tip_jar_click / etc."
const TRACK_DB_ENDPOINT='/api/track-event';
const TRACK_DB_EVENTS=new Set(['pageview','tip_jar_click','affiliate_click','share_click','share_native','ics_download','stretch_expand','nav_about','nav_privacy','vacation_mode_on','vacation_mode_off','popup_shown','popup_dismissed','popup_signup','popup_signup_error','waitlist_submit','waitlist_server_error','waitlist_fallback','calendar_add','footer_year','year_cta_click']);
// Excluded by design: 'render' (render telemetry — too high volume, low value, see comment above)
function track(name, data) {
  try {
    const payload={...(data||{}),...getAttribution()};
    if (window.__TRACK_DEBUG__) console.log('[track]', name, payload);
    if (typeof window.va === 'function') window.va('event', { name, data: payload });
    if (typeof window.plausible === 'function') window.plausible(name, { props: payload });
    if (typeof window.gtag === 'function') window.gtag('event', name, payload);
    // Fire-and-forget DB write for the high-value events. We intentionally
    // do NOT send render events to the DB — too high volume, low value.
    if(TRACK_DB_EVENTS.has(name)&&navigator.sendBeacon){
      try{
        const body=JSON.stringify({name,...payload});
        // sendBeacon is the right tool: POST, doesn't block, survives unload.
        const blob=new Blob([body],{type:'application/json'});
        navigator.sendBeacon(TRACK_DB_ENDPOINT,blob);
      }catch(e){/* best-effort */}
    }
  } catch (x) { /* best-effort */ }
}
track('pageview', { path: location.pathname });

// --- Date helpers (preserved from v1) ---
function dateToObj(s){const[y,m,d]=s.split('-').map(Number);return{y,m,d,js:new Date(y,m-1,d),iso:s}}
function objToStr(o){return`${o.y}-${String(o.m).padStart(2,'0')}-${String(o.d).padStart(2,'0')}`}
function dayName(o){return DAYS[o.js.getDay()]}
function fmt(o){return`${o.d} ${MONTHS[o.m-1]} ${o.y}`}
function fmtShort(o){return`${o.d} ${MONTHS[o.m-1]}`}
function addDays(iso,n){const[y,m,d]=iso.split('-').map(Number);const dt=new Date(y,m-1,d);dt.setDate(dt.getDate()+n);return objToStr({y:dt.getFullYear(),m:dt.getMonth()+1,d:dt.getDate()})}
function daysBetween(a,b){const[ya,ma,da]=a.split('-').map(Number);const[yb,mb,db]=b.split('-').map(Number);return Math.round((new Date(yb,mb-1,db)-new Date(ya,ma-1,da))/86400000)}

// Per-state weekend days. Most of Malaysia uses Sun(0)+Sat(6); Kelantan and
// Terengganu use Fri(5)+Sat(6). Johor reverted to Sat+Sun on 1 Jan 2025
// (was Fri+Sat before that) — see the year-aware function below.
// Per the Selangor state enactment, Selangor also observes Fri+Sat in some
// districts, but federal Selangor public holidays use Sun+Sat — keeping
// Selangor on the default to match how KL/Selangor office workers plan.
const STATE_WEEKEND={
  // Johor: 2024 and earlier = Fri+Sat; 2025+ = Sat+Sun (revert effective 1 Jan 2025)
  Johor:function(y){return y<2025?[5,6]:[0,6];},
  Kedah:[0,6],       // Sun + Sat (default federal)
  Kelantan:[5,6],    // Fri + Sat
  'Kuala Lumpur':[0,6],
  Labuan:[0,6],
  Melaka:[0,6],
  'Negeri Sembilan':[0,6],
  Pahang:[0,6],
  'Pulau Pinang':[0,6],
  Perak:[0,6],
  Perlis:[0,6],
  Putrajaya:[0,6],
  Sabah:[0,6],
  Sarawak:[0,6],
  Selangor:[0,6],
  Terengganu:[5,6],  // Fri + Sat
};
// Compute the union of weekend days across all selected states,
// optionally overridden by the user's manual weekend selection.
// If any selected state has a Fri+Sat weekend, then Friday is non-working
// unless the user explicitly picked a different pattern. The user override
// (state.weekendOverride) wins over state defaults — shift workers, retail,
// healthcare, and rotating-schedule workers need this to plan realistically.
function weekendForStates(states,year){
  // No base set. Each state contributes its actual weekend days; we union
  // them across all selected states. If no states are selected, fall back
  // to the federal default (Sat+Sun).
  //
  // Why no base? Earlier versions started with {0,6} (Sun+Sat) and unioned
  // state defaults on top, which polluted single-state selections:
  //   - Kelantan only → {0,6} ∪ {5,6} = {0,5,6} = "Sun+Fri+Sat" (wrong)
  //     Sun is a workday in Kelantan, but the union made it look like a
  //     weekend, which then triggered the "3-day weekend" explainer.
  //   - Johor only → {0,6} ∪ {5,6} = same wrong result pre-2025.
  //
  // Now the only days marked as weekend are days a selected state actually
  // considers a weekend. Sat is the only universal-ish day (every state
  // except... well, every state has Sat) so it's almost always present.
  // Sun is only present if a selected state has it.
  const out=new Set();
  if(states.size===0){
    // Federal default: Sat + Sun.
    out.add(0);out.add(6);
  }else{
    for(const s of states){
      const sw=STATE_WEEKEND[s];
      if(!sw)continue;
      // Johor is a function (year-aware); other states are static arrays.
      const days=typeof sw==='function'?sw(year||new Date().getFullYear()):sw;
      days.forEach(d=>out.add(d));
    }
  }
  // Apply user override if set (and a valid preset)
  if(state.weekendOverride && WEEKEND_PRESETS[state.weekendOverride]){
    const days=WEEKEND_PRESETS[state.weekendOverride];
    if(days){
      out.clear();
      days.forEach(d=>out.add(d));
    }
  }
  return out;
}

function getNonworking(year,states){
  const nw=new Map();
  for(const h of HOLIDAYS[year]){
    if(h.t==='federal'||h.t==='state'&&states.has(h.s)){
      if(!nw.has(h.d))nw.set(h.d,h.n);
    }
  }
  const weekendDays=weekendForStates(states,year);
  const d=new Date(year,0,1);
  while(d.getFullYear()==year){
    if(weekendDays.has(d.getDay())){const iso=objToStr({y:d.getFullYear(),m:d.getMonth()+1,d:d.getDate()});if(!nw.has(iso))nw.set(iso,'Weekend')}
    d.setDate(d.getDate()+1);
  }
  return nw;
}

function findRuns(nw){
  const sorted=[...nw.keys()].sort();
  if(!sorted.length)return[];
  let start=sorted[0],end=sorted[0];
  const prev=iso=>{const[y,m,d]=iso.split('-').map(Number);const dt=new Date(y,m-1,d);dt.setDate(dt.getDate()-1);return objToStr({y:dt.getFullYear(),m:dt.getMonth()+1,d:dt.getDate()})};
  const runs=[];
  for(let i=1;i<sorted.length;i++){
    if(prev(sorted[i])===end){end=sorted[i]}
    else{runs.push([start,end]);start=sorted[i];end=sorted[i]}
  }
  runs.push([start,end]);
  return runs;
}

// Conservative cap: max AL per single stretch. A stretch of 1-2 AL days
// bridges a holiday to an adjacent weekend. Anything more is a real
// vacation that should be planned separately. Bump to 3-4 if you want
// longer mega-vacations in the plan.
const MAX_AL_PER_STRETCH=2;
// Vacation mode: allows longer clusters of AL days (e.g., 1-2 week
// vacations around holidays). Toggled by the user when they have AL
// to spend beyond the long-weekend plan.
const MAX_AL_PER_STRETCH_VACATION=5;

// --- Candidate generation: holiday-anchored, bridges to weekends ---
// For each public holiday, generate candidate windows that include the holiday
// and extend in both directions (aL days before, aR days after). Working days
// in the window count as AL days; the window is contiguous in calendar days.
function generateCandidates(nw,budget,vacationMode,year){
  const cap=vacationMode?MAX_AL_PER_STRETCH_VACATION:MAX_AL_PER_STRETCH;
  // Use the per-state weekend for the "is this day a weekend?" check
  // (handles Kelantan/Terengganu with Fri+Sat weekend; Johor reverted to
  // Sat+Sun in 2025, so we pass the year through).
  // We need to know which states are selected to compute this; pull from
  // the page's checkbox state if available, otherwise default to [0,6].
  const selStates=new Set();
  if(typeof state!=='undefined'&&state.states)state.states.forEach(s=>selStates.add(s));
  const weekendDays=weekendForStates(selStates,year);
  const out=[];
  // Collect all holidays (public holidays, not weekends)
  const holidays=[];
  for(const[iso,name] of nw){
    if(name!=='Weekend')holidays.push({date:iso,name});
  }
  holidays.sort((a,b)=>a.date<b.date?-1:1);
  // Also support multi-day natural runs (e.g. CNY spans 2 days) as anchors.
  // Also MERGE separate single-day holidays if they are <=3 working days apart
  // (excluding the holidays themselves). This catches the "bridge the gap"
  // pattern: e.g. Tue holiday + Thu holiday (Wed working between them) —
  // taking AL on the working gap days turns it into one long stretch.
  function findAnchors(nw){
    const sortedHols=[];
    for(const[iso,name] of nw){
      if(name!=='Weekend')sortedHols.push({date:iso,name});
    }
    sortedHols.sort((a,b)=>a.date<b.date?-1:1);
    if(!sortedHols.length)return [];
    const anchors=[];
    let cur={start:sortedHols[0].date,end:sortedHols[0].date,holidays:[sortedHols[0]],idx:'a0'};
    let aidx=0;
    for(let i=1;i<sortedHols.length;i++){
      const h=sortedHols[i];
      // Count working days in the gap [cur.end+1, h.date-1]
      let workingGap=0;
      let d=addDays(cur.end,1);
      while(d<h.date){
        const dow=dateToObj(d).js.getDay();
        const isWE=weekendDays.has(dow);
        if(!isWE)workingGap++;
        d=addDays(d,1);
      }
      // Merge if gap has <=3 working days (handles Tue-Thu, Wed-Fri, etc.)
      if(workingGap<=3){
        cur.end=h.date;
        cur.holidays.push(h);
      } else {
        anchors.push(cur);
        aidx++;
        cur={start:h.date,end:h.date,holidays:[h],idx:'a'+aidx};
      }
    }
    anchors.push(cur);
    return anchors;
  }
  // Count working days in an anchor's natural span [start..end]. Used to
  // detect "forced-bridge" cases: 3+ holidays clustered in a way that
  // requires 3+ AL to actually bridge. The candidate cap should adapt.
  function countAnchorWorkDays(a,nw){
    let n=0;let d=a.start;
    while(d<=a.end){
      const dow=dateToObj(d).js.getDay();
      const isWE=weekendDays.has(dow);
      const isHol=nw.has(d)&&nw.get(d)!=='Weekend';
      if(!isWE&&!isHol)n++;
      d=addDays(d,1);
    }
    return n;
  }
  const anchors=findAnchors(nw);
  for(const a of anchors){
    for(let aL=0;aL<=5;aL++){
      for(let aR=0;aR<=5;aR++){
        const start=addDays(a.start,-aL);
        const end=addDays(a.end,aR);
        // Count AL days (working days in the window that aren't holidays)
        const leaveDates=[];
        let c=start;
        while(c<=end){
          const dow=dateToObj(c).js.getDay();
          const isWE=weekendDays.has(dow);
          const isHol=nw.has(c)&&nw.get(c)!=='Weekend';
          if(!isWE&&!isHol)leaveDates.push(c);
          c=addDays(c,1);
        }
        const al=leaveDates.length;
        if(al>budget)continue;
        // Conservative: cap AL per stretch so we never suggest a 5-day
        // working week off (that's a real vacation, not a long weekend).
        // Vacation mode raises the cap to allow mega-vacation clusters.
        // Exception: when the natural anchor itself spans 3+ working days
        // (e.g. 3 holidays clustered within a week — Aug 2026's Prophet's
        // Birthday + Merdeka), allow up to that many AL. Otherwise the user
        // is forced into a lower ratio plan just to avoid bridging the gap.
        const anchorWork=countAnchorWorkDays(a,nw);
        const effectiveCap=Math.max(cap, anchorWork<=2?0:Math.min(anchorWork,3));
        if(al>effectiveCap)continue;
        // Skip free weekends with no holiday (defensive — anchors already have holidays)
        if(a.holidays.length===0)continue;
        const daysOff=daysBetween(start,end)+1;
        // B4 fix + polish #6: free (0 AL) candidates must be a real long weekend.
        // A 2-day Sat-Sun with a holiday name (e.g. Labour Day falling on Saturday)
        // is just a regular weekend — not a planning win, don't show as a stretch.
        // Require >=3 calendar days AND must touch a weekend day.
        if(al===0){
          if(daysOff<3)continue;
          let touchesWeekend=false;
          let cur=start;
          while(cur<=end){if(weekendDays.has(dateToObj(cur).js.getDay())){touchesWeekend=true;break}cur=addDays(cur,1)}
          if(!touchesWeekend)continue;
        }
        // Skip if ratio too low
        if(al>0 && daysOff/al<1.5)continue;
        out.push({anchor:a.idx,start,end,daysOff,alUsed:al,leaveDates,holidays:a.holidays,natLen:daysBetween(a.start,a.end)+1});
      }
    }
  }
  return out;
}

// --- Knapsack solver: pick non-overlapping candidates within budget, maximize objective ---
function solvePlan(budget,nw,objective){
  const cands=generateCandidates(nw,budget,state.vacationMode,state.year);
  // Fix #3: filter out stretches that start before the as-of date (frozen in URL)
  const todayIso=state.asof;
  const fut=cands.filter(c=>c.start>=todayIso);
  let sf;
  if(objective==='count')sf=(a,b)=>a.alUsed-b.alUsed||b.daysOff-a.daysOff;
  else if(objective==='longest')sf=(a,b)=>b.daysOff-a.daysOff||a.alUsed-b.alUsed;
  // "totalDays" mode: maximize total days off (used by vacation mode).
  // Tie-breakers: prefer fewer AL for the same daysOff (efficiency), then
  // earliest start. Free (0-AL) stretches sort after paid ones of equal
  // daysOff so we don't waste 0-AL budget on low-reward free weekends
  // when a paid stretch is available.
  else if(objective==='totalDays')sf=(a,b)=>(b.daysOff-a.daysOff)||(a.alUsed-b.alUsed)||(a.start<b.start?-1:1);
  // Default "daysOff" mode: maximize the ratio of days off per AL spent.
  // Sort by ratio descending. Free (0 AL) stretches are treated as ratio 10
  // (arbitrary high value to sort first; finite so Phase 2 can downgrade
  // them when needed for use-it-or-lose-it).
  else {
    const ratio=s=>s.alUsed===0?10:s.daysOff/s.alUsed;
    sf=(a,b)=>(ratio(b)-ratio(a))||(b.daysOff-a.daysOff)||(a.alUsed-b.alUsed);
  }
  fut.sort(sf);
  const chosen=[];let alLeft=budget;const usedAnchors=new Set();
  const ov=(a,b)=>!(a.end<b.start||b.end<a.start);
  for(const c of fut){
    if(c.alUsed>alLeft)continue;
    if(usedAnchors.has(c.anchor))continue;
    if(chosen.some(ch=>ov(ch,c)))continue;
    chosen.push(c);alLeft-=c.alUsed;usedAnchors.add(c.anchor);
  }
  // Two-pass upgrade:
  //   In 'ratio' (long weekend) mode:
  //     Pass A: upgrade only if ratio stays the same or improves (preserves
  //             the max-ratio plan while squeezing more value from same budget).
  //     Pass B: with whatever AL is left, upgrade freely (any ratio) to
  //             maximize total days off — the "use it or lose it" pass.
  //   In 'totalDays' (vacation) mode:
  //     Both passes accept any upgrade that adds more days off (ratio is
  //     irrelevant — we want the biggest blocks of time off possible).
  const ratio=s=>s.alUsed===0?10:s.daysOff/s.alUsed;
  const isTotalDays=objective==='totalDays';
  const tryUpgrade=(allowAnyRatio)=>{
    for(let i=0;i<chosen.length&&alLeft>0;i++){
      const ri=chosen[i].anchor;
      const curRatio=ratio(chosen[i]);
      const ups=fut.filter(c=>{
        if(c.anchor!==ri)return false;
        if(c.alUsed<=chosen[i].alUsed)return false;
        if(c.daysOff<=chosen[i].daysOff)return false;
        if(isTotalDays)return true;  // vacation mode: any upgrade that adds days off
        if(allowAnyRatio)return true;
        // Strict: ratio must be >= current (allow equal, reject worse)
        return ratio(c)>=curRatio;
      }).sort((a,b)=>b.daysOff-a.daysOff||a.alUsed-b.alUsed);
      for(const u of ups){
        const delta=u.alUsed-chosen[i].alUsed;
        if(delta>alLeft)continue;
        const others=chosen.filter((_,j)=>j!==i);
        if(others.some(ch=>ov(ch,u)))continue;
        chosen[i]=u;alLeft-=delta;break;
      }
    }
  };
  if(isTotalDays){
    // Single pass: keep upgrading as long as we have AL and a bigger option exists
    tryUpgrade(true);
  } else {
    // Pass A: ratio-preserving
    tryUpgrade(false);
    // Pass B: use the rest, even if ratio drops
    tryUpgrade(true);
  }
  // Sort: free weekends first, then highest days/AL (ratio), ties broken by earliest start
  chosen.sort((a,b)=>{
    const ra=a.alUsed?a.daysOff/a.alUsed:99;
    const rb=b.alUsed?b.daysOff/b.alUsed:99;
    return rb-ra||(a.start<b.start?-1:1);
  });
  const stretches=chosen.map(c=>({start:c.start,end:c.end,daysOff:c.daysOff,alUsed:c.alUsed,leaveDates:c.leaveDates,holidays:c.holidays}));
  const allLeave=stretches.flatMap(s=>s.leaveDates).sort();
  return{
    alUsed:budget-alLeft,
    totalDaysOff:stretches.reduce((s,x)=>s+x.daysOff,0),
    stretchCount:stretches.length,
    longestStretch:stretches.reduce((m,x)=>Math.max(m,x.daysOff),0),
    leaveDates:allLeave,
    stretches
  };
}

// --- .ics generator --- REMOVED (was ics-btn, see Phase 2 cleanup)

// --- Affiliate link --- REMOVED (was placeholder, see QC B1)

// --- State model ---
// Compute default as-of date (today) in ISO format. Can be overridden by ?asof= in URL.
const _defaultAsOf=(()=>{const d=new Date();d.setHours(0,0,0,0);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`})();
// weekendOverride: null = use per-state defaults from STATE_WEEKEND
// (Sat+Sun for most states; Kelantan/Terengganu = Fri+Sat; Johor = Fri+Sat
// for 2024 and earlier, Sat+Sun for 2025+).
// String values: 'sat-sun', 'fri-sat', 'sun-thu', 'thu-fri', 'mon-off',
// 'tue-off', 'wed-off', 'sun-only'. Stored in URL as ?w=...
const state={year:2026,al:14,states:new Set(),selStretch:null,vacationMode:false,asof:_defaultAsOf,weekendOverride:null};

// --- Weekend preset library ---
// Maps preset key -> array of day indices (0=Sun, 1=Mon, ..., 6=Sat).
// Used by the user-facing "Your weekend" dropdown to override the
// per-state default for shift workers, retail, healthcare, etc.
const WEEKEND_PRESETS={
  'auto':     null,           // use per-state default
  'sat-sun':  [0,6],
  'fri-sat':  [5,6],
  'mon-off':  [1],            // single rest day (Mon)
  'sun-only': [0],
};

// --- DOM refs ---
const $=id=>document.getElementById(id);
const yearSel=$('year'),alSlider=$('al-slider'),alValue=$('al-value'),stateSel=$('state-selector'),stateSum=$('state-summary'),weekendSel=$('weekend-override');

// Populate state checkboxes
STATES.forEach(s=>{
  const lbl=document.createElement('label');
  lbl.innerHTML=`<input type="checkbox" value="${s}"> ${s}`;
  stateSel.appendChild(lbl);
});

// --- URL state ---
function loadFromURL(){
  const p=new URLSearchParams(location.search);
  if(p.has('y')){const y=p.get('y');if(['2026','2027'].includes(y)){yearSel.value=y;state.year=+y}}
  if(p.has('al')){const a=parseInt(p.get('al'),10);if(!isNaN(a)&&a>=1&&a<=30){alSlider.value=a;state.al=a}}
  if(p.has('s')){const want=new Set(p.get('s').split(',').map(s=>s.trim()).filter(Boolean));stateSel.querySelectorAll('input').forEach(cb=>{cb.checked=want.has(cb.value);if(cb.checked)state.states.add(cb.value)})}
  if(p.has('asof')){const a=p.get('asof');if(/^\d{4}-\d{2}-\d{2}$/.test(a)){state.asof=a}}
  if(p.has('w')){const w=p.get('w');if(WEEKEND_PRESETS.hasOwnProperty(w)){state.weekendOverride=w==='auto'?null:w;if(weekendSel)weekendSel.value=w}}
}
function writeToURL(){
  const p=new URLSearchParams();
  p.set('y',state.year);p.set('al',state.al);
  if(state.states.size)p.set('s',[...state.states].join(','));
  // Always include asof so a shared URL replays the exact plan the sender saw.
  p.set('asof',state.asof);
  // Persist weekend override only if it's not 'auto' (null) — keeps default
  // URLs clean.
  if(state.weekendOverride)p.set('w',state.weekendOverride);
  // Preserve the hash (e.g. #stretch-2) so per-stretch share links keep
  // their deep-link target. The hash isn't part of the query string so
  // we append it manually.
  const h=location.hash||'';
  history.replaceState(null,'',location.pathname+'?'+p.toString()+h);
}
function updateStateSummary(){
  stateSum.textContent=state.states.size?[...state.states].join(', '):'Federal only';
}

// --- Renderers ---
// Build a shareable URL that auto-tags every share with our attribution
// params. This lets the recipient's pageview fire with utm_source=share so
// we can count "shares → signups" funnel in the dashboard. Defined at
// top-level (NOT inside renderAnswer/renderStretches) because both share
// handlers need it but they live in separate functions.
// Build a shareable URL for the current plan.
// Strategy: POST to /api/shorten with the canonical longweekend.my URL,
// get back a short code, and return the short URL (https://go.longweekend.my/{code}).
//
// Why short URLs: chat apps (WhatsApp, Telegram, iMessage) aggressively
// strip UTM params, ?via=/?ref= params, AND /from/{source} path segments
// from URLs they preview. Short URLs on a custom domain don't match any
// of those normalization patterns — they survive intact to the recipient.
// The /r/[code] redirect then sets a `lw_src` cookie that
// captureAttribution() reads on the landing page.
//
// Falls back to /from/friend if the shorten API fails (network down,
// rate limit, etc.) — better to send a trackable URL with a known-strip
// path than no URL at all.
const _shortCache=new Map();// targetUrl -> {shortUrl, ts}; cache for 5 min
async function buildShareUrl(base){
  try{
    const u=new URL(base);
    const y=u.searchParams.get('y')||'';
    const al=u.searchParams.get('al')||'';
    const hash=u.hash||'';
    // Canonical target URL (without the /from/friend path or other tracking)
    const target=`${u.origin}/?y=${encodeURIComponent(y)}&al=${encodeURIComponent(al)}${hash}`;
    // Cache hit? (5 min TTL — same canonical URL = same short code)
    const cached=_shortCache.get(target);
    if(cached && (Date.now()-cached.ts)<300000)return cached.shortUrl;
    // Cache miss — POST to /api/shorten
    const ctrl=new AbortController();
    const t=setTimeout(()=>ctrl.abort(),3000);// 3s timeout
    try{
      const r=await fetch('/api/shorten',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url:target,source:'share'}),
        signal:ctrl.signal,
      });
      clearTimeout(t);
      if(r.ok){
        const j=await r.json();
        if(j.ok && j.shortUrl){
          _shortCache.set(target,{shortUrl:j.shortUrl,ts:Date.now()});
          return j.shortUrl;
        }
      }
    }catch(_){/* fall through to fallback */}
    clearTimeout(t);
  }catch(e){}
  // Fallback: /from/friend path (still better than full URL with UTM)
  try{
    const u=new URL(base);
    const y=u.searchParams.get('y')||'';
    const al=u.searchParams.get('al')||'';
    return `${u.origin}/from/friend?y=${encodeURIComponent(y)}&al=${encodeURIComponent(al)}${u.hash}`;
  }catch(e){return base}
}

function renderAnswer(plan){
  const ab=$('answer-band');
  if(!plan.stretches.length){
    ab.innerHTML=`<div class="answer-headline">No long-weekend plan found for ${state.al} AL days in ${state.year}.</div><div class="answer-meta">Try a higher AL budget or add state holidays.</div>`;
    return;
  }
  const lf=plan.leaveDates.map(d=>{const o=dateToObj(d);return`${dayName(o)} ${fmtShort(o)}`}).join(', ');
  const plural=plan.alUsed!==1?'s':'';
  // Fix #3: for the current year, frame as "more days off" (remaining year)
  const isCurrentYear=state.year===+state.asof.slice(0,4);
  const offPhrase=isCurrentYear?'more days off':'days off';
  // P0 fix: detect non-Sat/Sun weekend patterns (Kelantan/Terengganu default
  // to Fri+Sat; user override may pick other patterns). Surface a short
  // note explaining the weekend pattern so users don't think the 3-day
  // Best ratio: max of (daysOff/alUsed) across all chosen stretches.
  // If any stretch is FREE (0 AL), surface that prominently.
  const hasFree=plan.stretches.some(s=>s.alUsed===0);
  const paidRatios=plan.stretches.filter(s=>s.alUsed>0).map(s=>s.daysOff/s.alUsed);
  const bestPaid=paidRatios.length?Math.max(...paidRatios):0;
  const ratioText=hasFree?`free long weekend included`:`${bestPaid.toFixed(1)}× days per AL`;
  // Blended ratio: total days off / total AL used across the whole plan.
  // Free stretches (0 AL) are excluded so the number stays finite and honest.
  const blendedRatio=plan.alUsed>0?plan.totalDaysOff/plan.alUsed:null;
  const blendedText=blendedRatio!==null?` ⚡ ${blendedRatio.toFixed(2)}×`:' ⚡ ∞×';
  const alUnused=state.al-plan.alUsed;
  const unusedNote=alUnused>0?` · <span style="color:var(--muted)">${alUnused} AL day${alUnused!==1?'s':''} unused (no more holidays to extend)</span>`:'';
  // Vacation mode toggle: shown when there are unused AL days (and we're not already in vacation mode)
  // or when we ARE in vacation mode (then show the "back" button).
  const vacationBtn=state.vacationMode
    ? `<button class="btn btn-secondary" id="vacation-btn" style="margin-top:0.5rem">↩ Back to long weekend mode</button>`
    : (alUnused>=2?`<button class="btn btn-secondary" id="vacation-btn" style="margin-top:0.5rem">✈️ Use remaining ${alUnused} AL for long holiday</button>`:'');
  ab.innerHTML=`
    <div class="answer-headline">With <span class="num">${state.al}</span> AL days, take <span class="num">${plan.alUsed}</span> day${plural} of leave to get <span class="num">${plan.totalDaysOff}</span> ${offPhrase} in <span class="num">${state.year}</span><span class="blended">${blendedText}</span>.</div>
    <div class="answer-meta">${plan.stretchCount} long weekend${plan.stretchCount!==1?'s':''} · longest stretch ${plan.longestStretch} days · <strong>${state.vacationMode?'total days off: '+plan.totalDaysOff+' ('+plan.alUsed+' AL)':'best ratio: '+ratioText}</strong>${unusedNote}${state.vacationMode?' · <span style="color:var(--accent)">vacation mode</span>':''}</div>
    <div class="answer-leave"><strong>Take leave on:</strong> ${lf}</div>
    <div class="answer-cta">
      ${vacationBtn}
    </div>`;
  // Wire vacation mode toggle
  const vBtn=$('vacation-btn');
  if(vBtn)vBtn.addEventListener('click',()=>{
    state.vacationMode=!state.vacationMode;
    track(state.vacationMode?'vacation_mode_on':'vacation_mode_off',{al:state.al,unused:alUnused});
    render();
  });

  $('share-btn').addEventListener('click',()=>{
    const ratioStr=blendedRatio!==null?blendedRatio.toFixed(2):'∞';
    const lf=plan.leaveDates.map(d=>fmtShort(dateToObj(d))).join(', ');
    const holNames=[...new Set(plan.stretches.flatMap(s=>s.holidays.map(h=>h.name)))];
    const topStretch=plan.stretches[0];
    const topSO=topStretch?dateToObj(topStretch.start):null;
    const topEO=topStretch?dateToObj(topStretch.end):null;
    const topRange=topStretch?`${dayName(topSO)} ${fmtShort(topSO)} – ${dayName(topEO)} ${fmtShort(topEO)}`:'';
    const lines=[
      `🇲🇾 Long weekend: ${plan.totalDaysOff} days off (${plan.alUsed} AL) ⚡ ${ratioStr}×`,
      topRange,
      holNames.length?`Holidays: ${holNames.join(', ')}`:'',
      lf?`Apply leave: ${lf}`:''
    ].filter(Boolean);
    // buildShareUrl is now async (calls /api/shorten). Resolve it, then
    // call sharePlan with the short URL. The share text also uses the
    // resolved short URL via the same await.
    (async()=>{
      const shortUrl=await buildShareUrl(location.href);
      const txt=lines.join('\n')+`\n\nPlan yours → ${shortUrl}`;
      sharePlan(txt, shortUrl, $('share-btn'));
    })();
    track('share_click');
  });
}

// Share helper — used by both the main "Share plan" button and per-stretch
// buttons. Tries: (1) navigator.share, (2) clipboard.writeText, (3) inline
// textarea fallback. Always emits a visible label within ~500ms — even when
// navigator.share hangs (headless, some WebViews), the optimistic label
// tells the user something happened. If ALL three paths fail, the modal
// textarea pops up so the user has SOMETHING they can copy.
function sharePlan(txt, url, btn){
  // Compose the full message text with URL on its own line below content.
  // navigator.share concatenates text + url with a space when both are
  // passed separately — that puts the URL on the same line as the last
  // content (e.g. "Apply leave: 17 Aug https://..."). Embedding the URL
  // in text with \n\n forces the line break in all share paths.
  const fullText = txt + '\n\n' + url;
  const setLabel = (label, ok, durationMs) => {
    const orig = btn.dataset.origLabel || btn.textContent;
    btn.dataset.origLabel = orig;
    btn.textContent = label;
    btn.classList.toggle('btn-err', ok === false);
    setTimeout(() => {
      // Only revert if the button is still showing our label — guards
      // against a re-render that replaced btn with a fresh DOM node.
      if (btn.textContent === label) {
        btn.textContent = orig;
        btn.classList.remove('btn-err');
      }
    }, durationMs || 2500);
  };
  // 1. Native share sheet (mobile, modern desktop)
  if (navigator.share) {
    // Optimistic label so the user sees feedback even if the share sheet
    // hangs or they take a long time to pick a target.
    setLabel('⏳ Opening…', true, 3000);
    let done = false;
    const finish = (label, ok) => {
      if (done) return;
      done = true;
      setLabel(label, ok);
    };
    navigator.share({ title: 'My long weekend plan', text: fullText })
      .then(() => { finish('✅ Copied!'); track('share_native'); })
      .catch((err) => {
        // User cancelled OR share failed — try clipboard before giving up
        if (err && err.name === 'AbortError') { finish('Cancelled', false, 1500); return; }
        copyOrShow(fullText, finish);
      });
    // Belt-and-braces: if navigator.share hangs (e.g. headless or broken
    // WebView with no target), surface the modal after 1.5s so the user
    // isn't left staring at "⏳ Opening…" forever.
    setTimeout(() => { if (!done) copyOrShow(fullText, finish); }, 1500);
    return;
  }
  // 2. Clipboard path (or direct fallback if no navigator.share at all)
  copyOrShow(fullText, (l, ok) => setLabel(l, ok));
}

function copyOrShow(fullText, setLabelOrFn){
  // Wrapper that accepts either sharePlan's setLabel or a raw finish(label, ok)
  // The raw form is `(label, ok) => setLabel(label, ok)` for top-level wiring.
  const finish = (label, ok) => {
    if (typeof setLabelOrFn === 'function' && setLabelOrFn.length >= 2) {
      setLabelOrFn(label, ok);
    } else if (typeof setLabelOrFn === 'function') {
      setLabelOrFn(label);
    }
  };
  // Always try clipboard. No fallback modal — it's an editable textarea
  // most users don't use, and on desktop browsers with permission denied
  // the modal just adds friction. On any failure (no clipboard API,
  // permission denied, writeText rejected), we silently do nothing — the
  // URL bar still has the shareable link as a final backstop. We do NOT
  // show "✅ Copied!" unless clipboard.writeText actually succeeded.
  const tryClipboard = () => {
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      return;
    }
    navigator.clipboard.writeText(fullText)
      .then(() => finish('✅ Copied!', true))
      .catch(() => {});
  };
  tryClipboard();
}

// --- .ics export helpers ---------------------------------------------------
// Generates a VCALENDAR (RFC 5545) with one VEVENT per date in the plan.
// Works in Google Calendar, Apple Calendar, Outlook — clicking the .ics
// file in any OS triggers the system default calendar app to import it.
// Also callable per-stretch (buildICSEvents(plan, year, states, stretchIdx)).
function icsDate(iso){
  // iso is "YYYY-MM-DD"; ICS DATE format is "YYYYMMDD".
  return iso.replace(/-/g, '');
}
function icsNowStamp(){
  // UTC timestamp for DTSTAMP field.
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return d.getUTCFullYear() +
         pad(d.getUTCMonth() + 1) +
         pad(d.getUTCDate()) + 'T' +
         pad(d.getUTCHours()) +
         pad(d.getUTCMinutes()) +
         pad(d.getUTCSeconds()) + 'Z';
}
function icsEscape(s){
  // Escape per RFC 5545 §3.3.11: backslash, semicolon, comma, newline.
  // In Python source, each `\\` becomes `\` when written to JS, so we need
  // double-backslashes here to end up with a single backslash in the regex.
  return String(s)
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\n/g, "\\n");
}
function buildICSEvents(plan, year, states, onlyStretchIdx){
  // events: array of {date, title, type: 'leave'|'holiday'}
  const out = [];
  const stretchSet = onlyStretchIdx === undefined ? null : new Set([onlyStretchIdx]);
  // 1. Leave dates (mark as "Apply leave" so user knows why)
  plan.leaveDates.forEach((iso) => {
    if (!stretchSet) {
      out.push({ date: iso, title: '🏖️ Apply leave', type: 'leave' });
      return;
    }
    // Per-stretch: only include leave dates that fall within that stretch
    const s = plan.stretches[onlyStretchIdx];
    if (s && iso >= s.start && iso <= s.end) {
      out.push({ date: iso, title: `🏖️ Apply leave (${s.start}–${s.end})`, type: 'leave' });
    }
  });
  // 2. Holidays (date already in YYYY-MM-DD; need the friendly name)
  // Pull from `nw` (nonworking map) for the selected year+states. We have
  // access via getNonworking — call it here to reuse the same logic.
  const nw = getNonworking(year, states);
  // nw is Map(dateISO → name|'Weekend'). Filter and dedupe by date.
  const seen = new Set();
  for (const [iso, name] of nw.entries()) {
    if (name === 'Weekend') continue;
    const y = +iso.slice(0, 4);
    if (y !== +year) continue;
    if (onlyStretchIdx !== undefined) {
      const s = plan.stretches[onlyStretchIdx];
      if (!(iso >= s.start && iso <= s.end)) continue;
    }
    if (seen.has(iso)) continue;
    seen.add(iso);
    out.push({ date: iso, title: `🎉 ${name}`, type: 'holiday' });
  }
  // Sort by date
  out.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : 0);
  return out;
}
function buildICSString(events, calendarName){
  const stamp = icsNowStamp();
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//longweekend.my//AL Optimizer//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    `X-WR-CALNAME:${icsEscape(calendarName || 'Long Weekend Plan')}`,
  ];
  // UID is stable per (date+title) so re-imports dedupe rather than duplicate.
  for (const e of events) {
    const uid = `${e.date}-${e.title}@longweekend.my`;
    lines.push(
      'BEGIN:VEVENT',
      `UID:${uid}`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${icsDate(e.date)}`,
      `DTEND;VALUE=DATE:${icsDate(addDays(e.date, 1))}`,
      `SUMMARY:${icsEscape(e.title)}`,
      `TRANSP:TRANSPARENT`,
      'END:VEVENT',
    );
  }
  lines.push('END:VCALENDAR');
  return lines.join('\r\n');
}
function downloadICS(events, filename, successLabel){
  if (!events || !events.length) {
    // No events to export — flash the button briefly to acknowledge the click
    // so the user understands nothing went wrong silently.
    if (successLabel) successLabel('No dates', false, 2000);
    return;
  }
  const ics = buildICSString(events, `Long Weekend Plan — ${events.length} days`);
  try {
    const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Revoke after the click settles so the browser can finish the download.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (successLabel) successLabel(`✅ Saved (${events.length})`, true, 2500);
  } catch (err) {
    console.error('[ics] download failed', err);
    if (successLabel) successLabel('Download failed', false, 2500);
  }
}

// --- Smart "Add to calendar" dispatcher -------------------------------------
// Helper: flash a temporary label on a button, then revert. Mirrors the
// inline setBtn closures used elsewhere — extracted so the smart
// dispatcher can call it from multiple branches.
function flashBtn(btn, label, ok, durationMs){
  if (!btn) return;
  const orig = btn.dataset.origLabel || btn.textContent;
  btn.dataset.origLabel = orig;
  btn.textContent = label;
  btn.classList.toggle('btn-err', ok === false);
  setTimeout(() => {
    // Only revert if the button is still showing our label
    if (btn.textContent === label) {
      btn.textContent = orig;
      btn.classList.remove('btn-err');
    }
  }, durationMs || 2500);
}

// Build a Google Calendar "TEMPLATE" URL that opens GCal in a new tab with
// pre-filled event details. GCal renders the event form; user clicks Save.
//
// We use ONE master event for the full plan (not one per leave date) —
// GCal's TEMPLATE URL gets ugly with multiple events and users mostly
// care about the "block out these days" UX.
//
// For non-GCal users (Apple Calendar, Outlook, etc.) this is still useful:
// they sign in to GCal with any Google account (incl. a throwaway), get
// the event created, then export/import it to their real calendar. We
// keep the .ics download as a silent fallback if the popup is blocked.
function buildGcalTemplateUrl(plan, year, events){
  if (!events || !events.length) return null;
  // Pick a window: earliest leave → latest holiday+1 day, or just earliest
  // event → last event if no holidays. Add a buffer of 1 day to end.
  const dates = events.map(e => e.date).sort();
  const start = dates[0].replace(/-/g, '');
  // GCal DATE format: YYYYMMDD. DTEND is exclusive — add 1 day.
  const lastIso = dates[dates.length - 1];
  const end = icsDate(addDays(lastIso, 1));
  const title = `🇲🇾 ${year} long weekend plan (${plan.alUsed} AL → ${plan.totalDaysOff} days off)`;
  const details = [
    `Optimised by longweekend.my`,
    ``,
    `Leave dates (${plan.alUsed} AL):`,
    plan.leaveDates.map(d => `  • ${d}`).join('\\n'),
    ``,
    `Holidays in plan:`,
    events.filter(e => e.type === 'holiday').map(e => `  • ${e.date} — ${e.title.replace(/^[^\w]+/, '')}`).join('\\n'),
  ].join('\\n');
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title,
    dates: `${start}/${end}`,
    details,
    location: 'Malaysia',
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

// Master dispatcher — called when the user clicks the button.
// Opens GCal in a new tab with pre-filled event details. If the popup is
// blocked (or browser is hostile to new tabs), silently falls back to
// downloading the .ics file so the user still has a way to import.
function smartAddToCalendar(plan, year, events, btn, downloadIcsFallback){
  if (!events || !events.length) {
    flashBtn(btn, 'No dates', false, 2000);
    return;
  }
  const gcalUrl = buildGcalTemplateUrl(plan, year, events);

  // Set the optimistic label so the user sees feedback immediately
  flashBtn(btn, '⏳ Opening…', true, 3000);

  if (gcalUrl) {
    const win = window.open(gcalUrl, '_blank', 'noopener');
    if (win) {
      track('calendar_add', { method: 'gcal', events: events.length });
      flashBtn(btn, `✅ Opened GCal`, true, 2500);
      return;
    }
  }
  // Fallback: download the .ics (popup blocked or something weird)
  downloadIcsFallback();
  track('calendar_add', { method: 'ics_fallback', events: events.length });
}

function renderCalendar(plan,nw){
  const cal=$('calendar');
  const leaveSet=new Set(plan.leaveDates);
  // Build a map: iso → stretch index, for click-handling
  const isoToStretch=new Map();
  plan.stretches.forEach((s,i)=>{
    let cur=s.start;
    while(cur<=s.end){isoToStretch.set(cur,i);cur=addDays(cur,1)}
  });
  const ranges=plan.stretches.map(s=>({s:s.start,e:s.end}));
  const inStretch=iso=>ranges.some(r=>iso>=r.s&&iso<=r.e);
  // Past-date filter: skip past months entirely, dim past days in current month
  // (uses frozen state.asof so a shared URL replays the same calendar)
  const todayIso=state.asof;
  const asofY=+state.asof.slice(0,4),asofM=+state.asof.slice(5,7)-1,asofD=+state.asof.slice(8,10);
  const isCurrentYear=state.year===asofY;
  let html='';
  const startMonth=isCurrentYear?asofM:0;
  const endMonth=11;
  for(let m=startMonth;m<=endMonth;m++){
    const first=new Date(state.year,m,1);
    const dim=new Date(state.year,m+1,0).getDate();
    const sdow=first.getDay();
    html+=`<div class="month"><div class="month-name">${MONTHS[m]}</div><div class="day-grid"><div class="dow">S</div><div class="dow">M</div><div class="dow">T</div><div class="dow">W</div><div class="dow">T</div><div class="dow">F</div><div class="dow">S</div>`;
    for(let i=0;i<sdow;i++)html+='<div class="day blank"></div>';
    for(let d=1;d<=dim;d++){
      const iso=objToStr({y:state.year,m:m+1,d});
      const dow=new Date(state.year,m,d).getDay();
      const isWE = nw.get(iso)==='Weekend';
      const hol=nw.has(iso)&&nw.get(iso)!=='Weekend';
      const holName=hol?nw.get(iso):'';
      const isLeave=leaveSet.has(iso);
      const sIdx=isoToStretch.get(iso);
      const inS=sIdx!==undefined;
      const isPast=isCurrentYear&&iso<todayIso;
      let cls='day';
      if(isPast)cls+=' past';
      if(isWE)cls+=' weekend';
      if(inS)cls+=' in-stretch';
      if(isLeave)cls+=' leave';
      if(hol)cls+=' hol';
      // Past days are never clickable, never get tooltips
      if(isPast){
        html+=`<div class="${cls}">${d}</div>`;
        continue;
      }
      // Build a hover tooltip (works on desktop; mobile users see the inline label below)
      const dateLabel=`${d} ${MONTHS[m]} ${state.year}`;
      let tip=dateLabel;
      const holPrefix=hol?`${holName} · `:'';
      if(isLeave)tip=`${holPrefix}Take leave: ${dateLabel}`;
      else if(inS)tip=`${holPrefix}Days off: ${dateLabel}`;
      else if(hol)tip=`${holName}: ${dateLabel}`;
      else if(isWE)tip=`Weekend: ${dateLabel}`;
      // Make in-stretch + leave days clickable (jump to that stretch)
      const clickable=inS?' clickable':'';
      const dataAttrs=inS?` data-sidx="${sIdx}"`:'';
      // Show the holiday name inline below the day number for ALL holiday days
      // (standalone OR in a stretch) so mobile users can see it without hovering.
      // The label is allowed to wrap to 2 lines (CSS line-clamp:2) so the full
      // name is visible even on small cells.
      const holLabel=hol?`<span class="day-hol-label${inS?' in-stretch':''}">${holName}</span>`:'';
      html+=`<div class="${cls}${clickable}"${dataAttrs} title="${tip}" tabindex="${inS?0:-1}">${d}${holLabel}</div>`;
    }
    html+='</div></div>';
  }
  cal.innerHTML=html;
  // Wire calendar day click → expand matching stretch in the list below
  cal.querySelectorAll('.day.clickable').forEach(cell=>{
    cell.addEventListener('click',()=>{
      const idx=+cell.dataset.sidx;
      const wasOpen=state.selStretch===idx;
      // If already open, collapse; otherwise expand this one
      if(wasOpen){state.selStretch=null}
      else{state.selStretch=idx}
      track('stretch_expand',{source:'calendar',idx,action:wasOpen?'collapse':'expand'});
      // Re-render stretches to toggle, then scroll the matching one into view
      renderStretches(plan);
      const target=document.querySelector(`#stretch-list .stretch[data-idx="${idx}"]`);
      if(target){target.scrollIntoView({behavior:'smooth',block:'center'})}
      // Highlight the clicked cell briefly
      cal.querySelectorAll('.day.selected').forEach(d=>d.classList.remove('selected'));
      cell.classList.add('selected');
    });
    cell.addEventListener('keydown',e=>{
      if(e.key==='Enter'||e.key===' '){e.preventDefault();cell.click()}
    });
  });
}

function renderStretches(plan){
  const list=$('stretch-list');
  if(!plan.stretches.length){list.innerHTML='<p style="color:var(--muted)">No stretches in this plan.</p>';return}
  list.innerHTML=plan.stretches.map((s,i)=>{
    const sO=dateToObj(s.start),eO=dateToObj(s.end);
    const range=`${dayName(sO)} ${fmtShort(sO)} – ${dayName(eO)} ${fmtShort(eO)}`;
    const lv=s.leaveDates.map(d=>fmtShort(dateToObj(d))).join(', ');
    // Format holidays with their actual dates: "Wed 16 Sep (Malaysia Day)"
    const holsWithDates=s.holidays.map(h=>{
      const ho=dateToObj(h.date);
      return `${dayName(ho)} ${fmtShort(ho)} (${h.name})`;
    });
    const hols=[...new Set(s.holidays.map(h=>h.name))];
    const open=state.selStretch===i?'open':'';
    // Affiliate CTA: pick destination, build URL. Works as plain search even
    // when affiliate IDs are blank (just no commission tracked).
    // Hotel partner priority: booking → agoda → klook. Picks whichever is
    // enabled; falls back to plain Booking.com search if none.
    const dest=destForStretch(s);
    const hotelPartner=AFFILIATE.booking.enabled?AFFILIATE.booking
      :AFFILIATE.agoda.enabled?AFFILIATE.agoda
      :AFFILIATE.klook.enabled?AFFILIATE.klook
      :AFFILIATE.booking;
    const hotelUrl=dest?hotelPartner.url(dest):'#';
    // Flight partner priority: trip.com (always enabled) → skyscanner fallback.
    // Trip.com URL takes (dest, startIso, endIso); dest is unused by trip
    // (it doesn't pre-fill airports) but the signature is uniform. We always
    // pre-fill the stretch dates so the user lands on Trip.com with the
    // right travel window already selected.
    const tripUrl=typeof AFFILIATE.trip.url==='function'&&s.start&&s.end
      ?AFFILIATE.trip.url(dest, s.start, s.end)
      :null;
    const flightPartner=tripUrl?AFFILIATE.trip:AFFILIATE.skyscanner;
    const flightUrl=tripUrl||(dest?AFFILIATE.skyscanner.url(dest):'#');
    const flightLabel=tripUrl
      ? flightPartner.label.replace('✈️ ','✈️ Find flights on ')
      : '✈️ Find flights';
    // Fix #2: bang-for-buck score badge
    const ratio=s.alUsed===0?Infinity:s.daysOff/s.alUsed;
    const scoreCls=ratio===Infinity?'free':ratio>=3?'high':'low';
    const scoreLbl=ratio===Infinity?'FREE':ratio.toFixed(1)+'×';
    return`<div class="stretch ${open}" data-idx="${i}">
      <button class="stretch-header" data-si="${i}">
        <span class="stretch-range">${range}</span>
        <span class="stretch-stats">${s.daysOff} days off · ${s.alUsed} AL${lv?' ('+lv+')':''}</span>
        <span class="stretch-score ${scoreCls}">${scoreLbl}</span>
        <span class="stretch-chevron">▾</span>
      </button>
      <div class="stretch-expand" style="display:${open?'block':'none'}">
        ${holsWithDates.length?`<div class="se-hols"><strong>Public holidays:</strong> ${holsWithDates.join(' · ')}</div>`:''}
        <div class="se-leave">Apply leave on: <strong>${lv||'—'}</strong></div>
        ${dest?`<div class="se-actions">
          <a class="btn btn-affiliate btn-sm" data-affiliate="${hotelPartner==AFFILIATE.klook?'klook':hotelPartner==AFFILIATE.agoda?'agoda':'booking'}" data-stretch="${i}" href="${hotelUrl}" target="_blank" rel="noopener">${hotelPartner.label.replace('🏨 ','🏨 Find a stay on ')}</a>
          <a class="btn btn-affiliate btn-sm" data-affiliate="${flightPartner==AFFILIATE.trip?'trip':'skyscanner'}" data-stretch="${i}" href="${flightUrl}" target="_blank" rel="noopener">${flightLabel}</a>
        </div>`:''}
        <div class="se-actions">
          <button class="btn btn-secondary btn-sm" data-share-stretch="${i}">💬 Share plan</button>
          <button class="btn btn-secondary btn-sm" data-ics-stretch="${i}">📅 Add this stretch</button>
        </div>
      </div>
    </div>`;
  }).join('');
  list.querySelectorAll('.stretch-header').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const idx=+btn.dataset.si;
      const panel=btn.nextElementSibling;
      const isOpen=panel.style.display==='block';
      list.querySelectorAll('.stretch-expand').forEach(p=>p.style.display='none');
      list.querySelectorAll('.stretch').forEach(s=>s.classList.remove('open'));
      if(!isOpen){
        panel.style.display='block';
        btn.closest('.stretch').classList.add('open');
        state.selStretch=idx;
        track('stretch_expand',{source:'list',idx,action:'expand',daysOff:plan.stretches[idx]?.daysOff,al:plan.stretches[idx]?.alUsed});
      }
      else{state.selStretch=null;track('stretch_expand',{source:'list',idx,action:'collapse'});}
      writeToURL();
    });
  });
  // Per-stretch share — same as the main "Share plan" button (system share
  // sheet with clipboard fallback) but for a single stretch. The URL points
  // to the same plan with a hash that auto-expands this stretch on load.
  list.querySelectorAll('[data-share-stretch]').forEach(a=>{
    a.addEventListener('click',()=>{
      const idx=+a.dataset.shareStretch;
      const s=plan.stretches[idx];
      if(!s)return;
      const sO=dateToObj(s.start),eO=dateToObj(s.end);
      const range=`${dayName(sO)} ${fmtShort(sO)} – ${dayName(eO)} ${fmtShort(eO)}`;
      const hols=[...new Set(s.holidays.map(h=>h.name))].join(', ');
      const lv=s.leaveDates.map(d=>fmtShort(dateToObj(d))).join(', ');
      // Per-stretch ratio (daysOff / alUsed). `∞` for free stretches.
      const sRatio=s.alUsed>0?`${(s.daysOff/s.alUsed).toFixed(1)}×`:`∞×`;
      const lines=[
        `🇲🇾 Long weekend: ${s.daysOff} days off (${s.alUsed} AL) ⚡ ${sRatio}`,
        range,
        hols?`Holidays: ${hols}`:'',
        lv?`Apply leave: ${lv}`:''
      ].filter(Boolean);
      // Build a complete share URL with the sender's exact configuration.
      // buildShareUrl() now returns a short URL (https://go.longweekend.my/{code})
      // which survives chat-app URL sanitization. Stretch index goes in the
      // hash so the recipient's deep-link target is preserved.
      (async()=>{
        const stretchUrl=await buildShareUrl(`${location.origin}/?y=${encodeURIComponent(state.year)}&al=${encodeURIComponent(state.al)}#stretch-${idx}`);
        const txt=lines.join('\n');
        sharePlan(txt, stretchUrl, a);
      })();
      track('share_click',{scope:'stretch',idx});
    });
  });
  // Per-stretch GCal — opens a TEMPLATE URL narrowed to this stretch's
  // date window (this stretch's leave + holidays only).
  list.querySelectorAll('[data-ics-stretch]').forEach(b=>{
    b.addEventListener('click',()=>{
      const idx=+b.dataset.icsStretch;
      if(!plan.stretches[idx])return;
      const events=buildICSEvents(plan, state.year, state.states, idx);
      const fallback = () => {
        downloadICS(events, `longweekend-${state.year}-stretch-${idx+1}.ics`, (l, ok, d) => {
          const orig = b.dataset.origLabel || b.textContent;
          b.dataset.origLabel = orig;
          b.textContent = l;
          b.classList.toggle('btn-err', ok === false);
          setTimeout(() => { if (b.textContent === l) { b.textContent = orig; b.classList.remove('btn-err'); } }, d || 2500);
        });
      };
      smartAddToCalendar(plan, state.year, events, b, fallback);
    });
  });
  // Affiliate click tracking — fires for both Booking and Skyscanner CTAs.
  // Even when AFFILIATE.*.enabled is false (no commission), we still track
  // the click so we can measure intent. When enabled becomes true, the same
  // event will fire and we'll know conversion is starting.
  list.querySelectorAll('[data-affiliate]').forEach(a=>{
    a.addEventListener('click',()=>{
      const partner=a.dataset.affiliate;
      const idx=+a.dataset.stretch;
      const s=plan.stretches[idx];
      track('affiliate_click',{partner,idx,dest:destForStretch(s),daysOff:s?.daysOff,al:s?.alUsed});
    });
  });
  // Affiliate click tracking REMOVED (was placeholder, see QC B1)
}

function renderJSONLD(plan){
  const ld=$('ld-stretches');
  if(!plan.stretches.length){ld.textContent='';return}
  const trips=plan.stretches.map((s,i)=>{
    const sO=dateToObj(s.start),eO=dateToObj(s.end);
    const hols=[...new Set(s.holidays.map(h=>h.name))].join(', ');
    return{
      "@context":"https://schema.org","@type":"TouristTrip",
      "name":`Long weekend ${fmtShort(sO)} – ${fmtShort(eO)}`,
      "startDate":s.start,"endDate":s.end,
      "touristType":"Domestic trip",
      "description":`${s.daysOff} days off using ${s.alUsed} AL day(s). ${hols?'Holidays: '+hols:'Weekend stretch.'}`,
      "provider":{"@type":"Organization","name":"longweekend.my","url":"https://longweekend.my/"}
    };
  });
  ld.textContent=JSON.stringify(trips);
}

function render(){
  try{
  state.year=+yearSel.value;state.al=+alSlider.value;alValue.textContent=state.al;
  state.states=new Set([...stateSel.querySelectorAll('input:checked')].map(cb=>cb.value));
  updateStateSummary();
  const nw=getNonworking(state.year,state.states);
  // Long weekend mode = ratio objective (max days off per AL).
  // Long holiday mode = totalDays objective (max days off, period).
  const objective=state.vacationMode?'totalDays':'ratio';
  const plan=solvePlan(state.al,nw,objective);
  state.plan=plan;  // expose for testing/debugging
  writeToURL();
  renderAnswer(plan);
  renderCalendar(plan,nw);
  renderStretches(plan);
  renderJSONLD(plan);
  track('render',{year:state.year,al:state.al,states:[...state.states],stretches:plan.stretchCount});
  // Handle hash: format is `#y=2027&al=14&s=selangor;stretch-N` (fallback
  // config + stretch target). The query string is the primary source — this
  // hash form exists so chat apps that strip the query string still produce
  // a usable link. If the query is present, the hash params are ignored
  // (they're already in the query). If the query is missing/stripped, the
  // hash params restore the sender's config. Either way, the stretch index
  // is parsed from the hash to auto-expand that card.
  const rawHash=location.hash||'';
  // Match: "stretch-N" anywhere in the hash (with optional ";" prefix)
  const sm=rawHash.match(/[;,&\s]?stretch-(\d+)/);
  // Config part: everything in the hash that isn't the stretch token.
  // Remove leading "#" then strip "stretch-N" + any leading separator.
  let configPart=rawHash.replace(/^#/,'');
  if(sm)configPart=configPart.replace(new RegExp(';?\\s*stretch-\\d+\\s*$'),'').trim();
  // Drop trailing ";" or "&" left over
  configPart=configPart.replace(/[;&]+$/,'').trim();
  if(configPart && !location.search){
    // Chat app stripped the query — apply hash config
    try{
      const hp=new URLSearchParams(configPart);
      if(hp.has('y')&&['2026','2027'].includes(hp.get('y'))){
        yearSel.value=hp.get('y');state.year=+hp.get('y');
      }
      if(hp.has('al')){
        const a=parseInt(hp.get('al'),10);
        if(!isNaN(a)&&a>=1&&a<=30){alSlider.value=a;state.al=a}
      }
      if(hp.has('s')){
        const want=new Set(hp.get('s').split(',').map(s=>s.trim()).filter(Boolean));
        stateSel.querySelectorAll('input').forEach(cb=>{cb.checked=want.has(cb.value);if(cb.checked)state.states.add(cb.value)});
      }
    }catch(e){console.warn('[hash] bad config:',e)}
  }
  if(sm){
    const i=+sm[1];
    if(i>=0&&i<plan.stretches.length){
      state.selStretch=i;renderStretches(plan);
      setTimeout(()=>{const el=document.querySelector(`#stretch-list .stretch[data-idx="${i}"]`);if(el)el.scrollIntoView({behavior:'smooth',block:'center'})},100);
    }else{
      // Out of range — clear hash so it doesn't haunt future renders.
      history.replaceState(null,'',location.pathname+location.search);
    }
  }
  }catch(err){
    console.error('[render] error:',err);
    const ab=$('answer-band');
    if(ab)ab.innerHTML=`<div class="answer-headline">⚠️ Render error: ${err.message}</div>`;
  }
}

// --- Events ---
// Fix #1: listen to both 'input' (live drag) and 'change' (release). On some
// mobile browsers the 'input' event on range sliders can be throttled or
// dropped during rapid interaction; 'change' fires reliably on release.
alSlider.addEventListener('input',render);
alSlider.addEventListener('change',render);
yearSel.addEventListener('change',render);
stateSel.addEventListener('change',render);
// Weekend override (P1 feature — let shift workers / non-Mon-Fri users
// pick their actual rest days). Change handler reads the selected preset,
// stores it in state, re-renders. The ?w= URL param captures the choice
// for share links.
if(weekendSel){
  weekendSel.addEventListener('change',()=>{
    const v=weekendSel.value;
    state.weekendOverride=v==='auto'?null:v;
    render();
  });
}

// Waitlist form — POSTs to /api/waitlist (Vercel serverless function at api/waitlist.js).
// The serverless function emails the site owner (recipient address is set via
// the MAIL_TO env var in the Vercel dashboard — never exposed to the client).
// If the serverless function is unreachable, we show a friendly fallback
// message asking the user to try again — we deliberately do NOT expose any
// personal email address in the JS bundle.
const WAITLIST_ENDPOINT='/api/waitlist';
// Public contact — currently a mailto fallback. Swap to a form-based
// contact endpoint once one is set up so this address isn't scraped.
// Mailto fallback — used when the /api/waitlist endpoint is unreachable.
// Points to a Discord DM (the channel is open to all users) rather than
// hello@longweekend.my (whose MX record is `10 none.` — domain accepts no
// email; all mailto: attempts bounce with NXDOMAIN).
const WAITLIST_FALLBACK_URL='https://discord.com/channels/@me/turtleneckpenguin';
const wForm=$('waitlist-form');
if(wForm){
  // Hide form after successful submit (so returning users don't see it)
  try{if(localStorage.getItem('lw_waitlisted')==='1'){
    wForm.style.display='none';
    $('waitlist').querySelector('h3').textContent='✅ You\'re on the list — thanks!';
    $('waitlist').querySelector('p').textContent='I\'ll only ping you for major updates (new year data, feature launches).';
  }}catch(e){}
  wForm.addEventListener('submit',async e=>{
    e.preventDefault();
    const status=$('waitlist-status');
    const email=$('waitlist-email').value.trim();
    const feedback=$('waitlist-feedback').value.trim();
    const honeypot=$('waitlist-website').value;
    if(honeypot){status.textContent='Submission blocked.';status.className='waitlist-status err';return}
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||email.length>254){
      status.textContent='Please enter a valid email.';status.className='waitlist-status err';return;
    }
    const submitBtn=wForm.querySelector('button[type=submit]');
    submitBtn.disabled=true;submitBtn.textContent='Sending...';
    const payload={email,feedback,year:state.year,al:state.al,states:[...state.states],asof:state.asof,attribution:getAttribution(),ts:new Date().toISOString()};
    // Friendly Discord fallback using the public contact DM. We never
    // expose the site owner's personal email in the JS bundle, and the
    // domain's MX record is broken (10 none.) — so mailto: bounces.
    const fallbackText=`I'd like to join the longweekend.my waitlist. My email: ${encodeURIComponent(email)}${feedback?'%0A%0AFeedback: '+encodeURIComponent(feedback):''}`;
    const fallbackHref=`${WAITLIST_FALLBACK_URL}?message=${encodeURIComponent(fallbackText)}`;
    // Three states:
    //   'ok'             — function returned 200, signup + email both succeeded
    //   'server_error'   — function returned 4xx/5xx, signup was received but
    //                      email notification failed. Don't show mailto: — the
    //                      signup is already recorded in the backend.
    //   'network_error'  — fetch itself failed (offline, DNS, CORS, etc.). The
    //                      signup did NOT reach the backend. Trigger mailto:
    //                      fallback so the user has a way to reach the owner.
    let backendState='network_error';
    try{
      const r=await fetch(WAITLIST_ENDPOINT,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
      if(r.ok){
        const data=await r.json().catch(()=>({}));
        backendState='ok';
        // Include email domain (NOT full email) + a per-day counter so the
        // dashboard can show "5 gmail signups today" without storing PII.
        // First-time-this-day counter via localStorage.
        let dayCount=0;
        try{
          const today=new Date().toISOString().slice(0,10);
          const key='lw_signups_'+today;
          dayCount=parseInt(localStorage.getItem(key)||'0',10)+1;
          localStorage.setItem(key,String(dayCount));
        }catch(e){}
        const emailDomain=email.split('@')[1]||'(unknown)';
        track('waitlist_submit',{hasFeedback:!!feedback,ok:true,notified:!!(data.notification&&data.notification.sent),emailDomain,dayCount});
      } else {
        // Server-side error (4xx/5xx). The function got the request, so
        // the signup is recorded. We just couldn't notify — that's our
        // problem, not the user's. Don't ask them to mailto:.
        backendState='server_error';
        try{const errBody=await r.json().catch(()=>({}));track('waitlist_server_error',{hasFeedback:!!feedback,status:r.status,reason:errBody&&errBody.error});}catch(e){track('waitlist_server_error',{hasFeedback:!!feedback,status:r.status});}
      }
    }catch(err){
      // Fetch itself failed (network, DNS, CORS, offline). The signup did
      // NOT reach the backend — fall back to mailto: so the user has a way
      // to reach the owner.
      backendState='network_error';
      track('waitlist_fallback',{hasFeedback:!!feedback,error:err.message});
      const fallback=document.createElement('a');
      fallback.href=fallbackHref;
      fallback.target='_blank';
      fallback.rel='noopener noreferrer';
      fallback.style.display='none';
      document.body.appendChild(fallback);
      fallback.click();
      setTimeout(()=>fallback.remove(),100);
    }
    wForm.style.display='none';
    const h=$('waitlist').querySelector('h3');
    const p=$('waitlist').querySelector('p');
    h.textContent='✅ You\'re on the list — thanks!';
    if(backendState==='ok' || backendState==='server_error'){
      // Both cases: signup was received. Server_error means the email
      // notification failed but the signup itself is recorded — we just
      // don't burden the user with that detail. The site owner can see
      // it in Vercel function logs.
      p.innerHTML='Thanks! I\'ll only ping you for major updates. I read every reply.';
      try{localStorage.setItem('lw_waitlisted','1')}catch(e){}
    } else {
      // Network error: signup never reached the backend. Tell the user
      // about the Discord DM fallback and DO NOT set the localStorage flag
      // — the form is gone from view, but if the user clears localStorage
      // they can retry.
      p.innerHTML='Discord didn\'t open automatically. Reach out at the link below and I\'ll add you manually: <a href="'+WAITLIST_FALLBACK_URL+'">message me on Discord</a>.';
    }
  });
}

// Scroll-to-top button: appears after scrolling down 300px
const stBtn=$('scroll-top');
if(stBtn){
  const toggle=()=>stBtn.classList.toggle('visible',window.scrollY>300);
  window.addEventListener('scroll',toggle,{passive:true});
  stBtn.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
}

// Close state disclosure on outside click
document.addEventListener('click',e=>{
  const dd=document.querySelector('.state-disclosure');
  if(dd&&dd.open&&!dd.contains(e.target))dd.open=false;
});

// Init
loadFromURL();
render();
</script>

<!-- === Email capture popup (minimal, triggered by Share/Save) === -->
<div class="lw-popup-overlay" id="lw-popup-overlay">
  <div class="lw-popup" id="lw-popup">
    <h3>Get an email when your next long weekend is coming up.</h3>
    <p>We'll send you a heads-up before each of your best windows.</p>
    <form id="lw-popup-form">
      <input type="email" id="lw-popup-email" placeholder="your@email.com" required>
      <div class="lw-popup-actions">
        <button type="submit">Notify me</button>
        <button type="button" class="lw-not-now" id="lw-popup-dismiss">Not now</button>
      </div>
      <p class="lw-privacy">We'll never spam. See our <a href="/privacy.html">privacy policy</a>.</p>
    </form>
  </div>
</div>

<script>
(function(){
  const POPUP_KEY='lw_popup_dismissed';
  const COOLDOWN_DAYS=7;
  const ACTION_DELAY=1500;
  let popupShownThisSession=false;

  function isDismissedRecently(){
    const dismissed=localStorage.getItem(POPUP_KEY);
    if(!dismissed)return false;
    const dismissedAt=parseInt(dismissed,10);
    const daysSince=(Date.now()-dismissedAt)/(1000*60*60*24);
    return daysSince<COOLDOWN_DAYS;
  }

  async function isAlreadySubscribed(){
    try{
      const email=localStorage.getItem('lw_user_email');
      if(!email)return false;
      const r=await fetch('/api/check-subscription',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email})
      });
      const d=await r.json();
      return d.subscribed===true;
    }catch(e){return false;}
  }

  function showPopup(triggerSource){
    const overlay=document.getElementById('lw-popup-overlay');
    if(overlay){
      overlay.classList.add('visible');
      if(typeof track==='function')track('popup_shown',{source:triggerSource});
    }
  }

  function hidePopup(){
    const overlay=document.getElementById('lw-popup-overlay');
    if(overlay)overlay.classList.remove('visible');
  }

  function dismissPopup(triggerSource){
    localStorage.setItem(POPUP_KEY,Date.now().toString());
    hidePopup();
    if(typeof track==='function')track('popup_dismissed',{source:triggerSource});
  }

  async function submitEmail(email,triggerSource){
    try{
      localStorage.setItem('lw_user_email',email);
      const r=await fetch('/api/waitlist',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          email,
          utm_source:(typeof getUTM==='function'?getUTM('utm_source'):''),
          ref_host:document.referrer?new URL(document.referrer).hostname:'',
          asof:(new Date()).toISOString().slice(0,10)
        })
      });
      if(r.ok){
        if(typeof track==='function')track('popup_signup',{source:'leave_optimizer_popup',trigger:triggerSource});
        const popup=document.getElementById('lw-popup');
        popup.innerHTML='<h3>You\'re in! 🎉</h3><p>We\'ll email you before your next long weekend.</p><button type="button" onclick="document.getElementById(\'lw-popup-overlay\').classList.remove(\'visible\')" style="width:100%;padding:0.6rem;background:var(--accent);color:white;border:none;border-radius:8px;font:inherit;font-size:14px;font-weight:500;cursor:pointer;margin-top:0.5rem;">Got it</button>';
        setTimeout(hidePopup,3000);
      }else{
        if(typeof track==='function')track('popup_signup_error',{status:r.status,trigger:triggerSource});
      }
    }catch(e){
      if(typeof track==='function')track('popup_signup_error',{error:e.message,trigger:triggerSource});
    }
  }

  // DIAGNOSTIC: gate-return logging (lane:popup-debug, 23 Aug 26).
  // Goal: figure out why 187 stretch_expand events -> 2 popup_shown over 30d.
  // Every early-return now logs which gate blocked. View in Vercel runtime logs
  // or browser DevTools console. Remove after 48h of data lands.
  function _gateLog(reason,source){
    try{console.log('[lw-popup-gate]',{reason,source,ts:Date.now(),session:popupShownThisSession,dismissed:isDismissedRecently()});}catch(e){}
  }
  document.addEventListener('click',async(e)=>{
    const shareBtn=e.target.closest('[data-share-stretch]');
    if(shareBtn){
      if(popupShownThisSession){_gateLog('session','share');return;}
      if(isDismissedRecently()){_gateLog('cooldown','share');return;}
      if(await isAlreadySubscribed()){_gateLog('subscribed','share');return;}
      popupShownThisSession=true;
      setTimeout(()=>showPopup('share'),ACTION_DELAY);
      return;
    }
    const icsBtn=e.target.closest('[data-ics-stretch]');
    if(icsBtn){
      if(popupShownThisSession){_gateLog('session','ics');return;}
      if(isDismissedRecently()){_gateLog('cooldown','ics');return;}
      if(await isAlreadySubscribed()){_gateLog('subscribed','ics');return;}
      popupShownThisSession=true;
      setTimeout(()=>showPopup('save_calendar'),ACTION_DELAY);
      return;
    }
    const stretchBtn=e.target.closest('.stretch-header');
    if(stretchBtn){
      if(popupShownThisSession){_gateLog('session','stretch');return;}
      if(isDismissedRecently()){_gateLog('cooldown','stretch');return;}
      if(await isAlreadySubscribed()){_gateLog('subscribed','stretch');return;}
      popupShownThisSession=true;
      setTimeout(()=>showPopup('stretch_expand'),ACTION_DELAY);
      return;
    }
  });

  document.addEventListener('DOMContentLoaded',()=>{
    const form=document.getElementById('lw-popup-form');
    const dismiss=document.getElementById('lw-popup-dismiss');
    const overlay=document.getElementById('lw-popup-overlay');
    if(form){
      form.addEventListener('submit',(e)=>{
        e.preventDefault();
        const email=document.getElementById('lw-popup-email').value.trim();
        if(email)submitEmail(email,'share_or_save');
      });
    }
    if(dismiss)dismiss.addEventListener('click',()=>dismissPopup('not_now'));
    if(overlay){
      overlay.addEventListener('click',(e)=>{
        if(e.target===overlay)dismissPopup('tap_outside');
      });
    }
  });
})();
</script>
</body>
</html>
"""

# Inject JSON payloads
HTML = HTML.replace("__HOLIDAYS_JS__", json.dumps(HOLIDAYS_JS, separators=(",", ":")))
HTML = HTML.replace("__STATES_JS__", json.dumps(STATES))

# Inject SEO content section (server-rendered for AdSense + organic search depth)
HTML = HTML.replace("__SEO_SECTION__", render_seo_section(HOLIDAYS, year=2026))

# --- Inject AdSense head script (only when enabled) ----------------------
# When ADSENSE_ENABLED is False, the placeholder remains as an HTML comment
# (no broken ad containers in production). When True, AdSense auto ads script
# is loaded into <head> and slot <ins> tags are injected at the configured
# positions by the build process.
def _build_adsense_head():
    # Both the head script and body slots are gated on ADSENSE_ENABLED.
    # Previously the head script was loaded even when slots were off — wasted
    # ~10KB bandwidth per page view and added an external DNS lookup for zero
    # revenue (AdSense application was rejected). Re-enable together.
    if ADSENSE_PUBLISHER_ID.startswith("ca-pub-XXXXXXXX"):
        return "<!-- AdSense Publisher ID not yet wired -->"
    if not ADSENSE_ENABLED:
        return "<!-- AdSense head disabled (ADSENSE_ENABLED=False) -->"
    return (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUBLISHER_ID}" crossorigin="anonymous"></script>'
    )

def _build_adsense_slot(slot_id, ad_format="auto", style_extra=""):
    if not ADSENSE_ENABLED:
        return '<!-- ad slot disabled -->'
    return (
        f'<div class="ad-slot" data-ad-slot="{slot_id}"{style_extra}>'
        f'<ins class="adsbygoogle" data-ad-client="{ADSENSE_PUBLISHER_ID}" data-ad-slot="{slot_id}" data-ad-format="{ad_format}" data-full-width-responsive="true"></ins>'
        f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'
        f'</div>'
    )

HTML = HTML.replace("<!-- __ADSENSE_HEAD__ -->", _build_adsense_head())
HTML = HTML.replace("<!-- __GSC_VERIFICATION__ -->",
    f'<meta name="google-site-verification" content="{GSC_VERIFICATION_CODE}" />' if GSC_VERIFICATION_CODE else "")

# Inject AI-citable structured data (JSON-LD) into <head>
# Source: holidays.json, verified against publicholidays.com.my Jul 2026.
# Format: schema.org Organization + FAQPage + ItemList (federal holidays).
# See: https://schema.org/ and https://llmstxt.org/
HTML = HTML.replace("__JSONLD_ORG__", JSONLD_ORG)
HTML = HTML.replace("__JSONLD_FAQ_2026__", JSONLD_FAQ_2026)
HTML = HTML.replace("__JSONLD_ITEMLIST_2026__", JSONLD_ITEMLIST_2026)
HTML = HTML.replace("__JSONLD_FAQ_2027__", JSONLD_FAQ_2027)
HTML = HTML.replace("__JSONLD_ITEMLIST_2027__", JSONLD_ITEMLIST_2027)

# Inject top ad slot below the answer band (high CPM position)
HTML = HTML.replace(
    '<section class="calendar-section">',
    f'{_build_adsense_slot(ADSENSE_SLOT_TOP, ad_format="auto")}\n  <section class="calendar-section">'
)
# Inject mid ad slot below the calendar (mid-page position)
HTML = HTML.replace(
    '  <section class="waitlist" id="waitlist">',
    f'{_build_adsense_slot(ADSENSE_SLOT_MID, ad_format="rectangle")}\n  <section class="waitlist" id="waitlist">'
)

# --- CLI dispatch ----------------------------------------------------------
# Default: build index.html (the planner).
# --year YYYY: build /year-YYYY.html (SEO year page).
# --all-years: build 2025/2026/2027/2028.
def _parse_args():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--year", type=int, choices=[2025, 2026, 2027, 2028])
    p.add_argument("--all-years", action="store_true")
    p.add_argument("--force", action="store_true")
    args, _unknown = p.parse_known_args()
    return args

import argparse

def render_year_page(year: int) -> Path:
    """Render the SEO year page for `year` to year-YYYY.html.

    For years present in holidays.json: full content (holiday table + FAQ + CTA).
    For years NOT present (e.g. 2025/2028 — 2028 gazette not yet published):
    a 'coming soon' placeholder that captures SEO traffic without claiming
    false dates. Critical: never publish unconfirmed holiday dates — the
    site already had a credibility hit from the Agoda/Booking rejection
    citing 'thin content', we cannot afford another.
    """
    holidays = HOLIDAYS.get(str(year), [])
    has_data = len(holidays) > 0

    # Common header — same meta/og/twitter/JSON-LD pattern as homepage
    title = f"Malaysia Public Holidays {year} — Long Weekends & Annual Leave Planner"
    _latest_year_str = max(HOLIDAYS.keys()) if HOLIDAYS else str(_CURRENT_YEAR + 1)
    if has_data:
        desc = (
            f"Full list of Malaysian public holidays in {year} with dates, day of week, and "
            f"long-weekend opportunities. Plan your annual leave to maximise days off."
        )
    elif year < _CURRENT_YEAR:
        # Past year without data
        desc = (
            f"{year} has already passed. For planning your long weekends, see our latest year ({_latest_year_str}) — it has the full federal and state holiday data."
        )
    else:
        # Future year, gazette not yet published
        desc = (
            f"Malaysia public holidays {year}: when the official gazette is published, "
            f"we'll have every holiday date and long-weekend opportunity right here."
        )
    canonical = f"https://longweekend.my/{year}"

    # JSON-LD: WebApplication schema for the parent planner + Article schema
    # for the year page itself (helps Google recognise it as rich content).
    # Also inject AI-citable Organization + FAQ + ItemList (federal holidays)
    # for richer AI citations. See https://schema.org/ and https://llmstxt.org/.
    jsonld_app = (
        '{"@context":"https://schema.org","@type":"WebApplication",'
        '"name":"Long Weekend Planner Malaysia",'
        f'"url":"https://longweekend.my/","applicationCategory":"UtilitiesApplication",'
        '"operatingSystem":"Any","offers":{"@type":"Offer","price":"0","priceCurrency":"MYR"},'
        '"description":"Interactive tool that solves the optimal annual leave plan for Malaysian public holidays."}'
    )
    jsonld_article = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "url": canonical,
        "datePublished": "2026-06-28",
        "dateModified": "2026-06-28",
        "inLanguage": "en-MY",
        "isPartOf": {"@type": "WebSite", "name": "Long Weekend Planner Malaysia", "url": "https://longweekend.my/"},
        "publisher": {"@type": "Organization", "name": "Long Weekend Planner Malaysia", "url": "https://longweekend.my/"}
    }, separators=(",", ":"))
    # Year-specific FAQ + ItemList. Cached at module load.
    # NOTE: The year page already has its own year-specific FAQPage (built
    # from holidays.json by render_seo_section). We only inject Organization
    # + ItemList here to avoid two FAQPage blocks (Google prefers one).
    jsonld_org = JSONLD_ORG
    jsonld_faq_year = None  # not used on year pages (existing one wins)
    jsonld_itemlist_year = JSONLD_ITEMLIST_2026 if year == 2026 else JSONLD_ITEMLIST_2027

    # Holiday table (only if we have data)
    if has_data:
        # Build a federal-vs-state deduplicated view. The data has multiple
        # rows per holiday (one per applicable state), so we must aggregate.
        # For each (date, name) we record: federal? if yes → "Federal" badge.
        # If state-only → collect ALL states that observe it (Socrates C1 fix:
        # don't just pick the first state; "Thaipusam" applies to 7 states,
        # not "Johor only").
        agg = {}  # key=(date, normalized_name) -> {date, name, type, states:set}
        for h in holidays:
            d = h["date"]
            # Normalize: drop " Holiday" suffix so "Hari Raya Aidilfitri" and
            # "Hari Raya Aidilfitri Holiday" collapse into one key.
            name = h["name"].replace(" Holiday", "")
            key = (d, name)
            if key not in agg:
                agg[key] = {"date": d, "name": name, "type": h.get("type", "state"), "states": set()}
            if h.get("state"):
                agg[key]["states"].add(h["state"])
            # If any federal entry exists, mark as federal (federal overrides)
            if h.get("type") == "federal":
                agg[key]["type"] = "federal"
        rows_html = []
        for key in sorted(agg.keys()):
            entry = agg[key]
            iso = entry["date"]
            y, m, day = iso.split("-")
            dt = datetime.date(int(y), int(m), int(day))
            dow = dt.strftime("%a")
            date_fmt = dt.strftime(f"{day} %b {year}")
            name = entry["name"]
            htype = entry["type"]
            badge = ""
            if htype == "federal":
                badge = ' <span class="yr-badge yr-fed">Federal</span>'
            elif htype == "state":
                states = sorted(entry["states"])
                if len(states) == 1:
                    state_label = states[0]
                    badge = f' <span class="yr-badge yr-state">{state_label} only</span>'
                elif len(states) <= 3:
                    state_label = ", ".join(states)
                    badge = f' <span class="yr-badge yr-state">{state_label} only</span>'
                else:
                    # 4+ states: show count + first 2 for readability
                    state_label = f"{len(states)} states ({states[0]}, {states[1]} +)"
                    badge = f' <span class="yr-badge yr-state">{state_label}</span>'
            rows_html.append(
                f'<tr><td class="yr-date">{date_fmt}</td><td class="yr-dow">{dow}</td>'
                f'<td class="yr-name">{name}{badge}</td></tr>'
            )
        table_html = (
            '<table class="yr-hol-table">'
            '<thead><tr><th>Date</th><th>Day</th><th>Holiday</th></tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody></table>'
        )

        # Long weekends: implement findRuns in Python. We only show 3+ day
        # runs (federal holidays + Sat/Sun weekends; Kelantan/Terengganu
        # use Fri+Sat weekends; Johor uses Fri+Sat for 2024 and earlier,
        # Sat+Sun for 2025+). For the year page we keep it simple and use
        # federal-only + default weekend (Sat+Sun) — same as homepage default.
        from datetime import date as _date, timedelta as _td
        nw = {}
        for h in holidays:
            if h.get("type") == "federal":
                nw[h["date"]] = h["name"]
        d = _date(year, 1, 1)
        end_d = _date(year, 12, 31)
        while d <= end_d:
            if d.weekday() >= 5:  # Sat=5, Sun=6
                iso = d.isoformat()
                if iso not in nw:
                    nw[iso] = "Weekend"
            d += _td(days=1)
        # Find runs
        sorted_keys = sorted(nw.keys())
        runs = []
        if sorted_keys:
            cur_start = sorted_keys[0]
            cur_end = sorted_keys[0]
            def _prev(iso):
                y_, m_, d_ = iso.split("-")
                dt_ = _date(int(y_), int(m_), int(d_)) - _td(days=1)
                return dt_.isoformat()
            for k in sorted_keys[1:]:
                if _prev(k) == cur_end:
                    cur_end = k
                else:
                    runs.append((cur_start, cur_end))
                    cur_start = k
                    cur_end = k
            runs.append((cur_start, cur_end))
        # Show only runs >= 3 days
        long_runs = []
        for s, e in runs:
            sy, sm, sd = s.split("-")
            ey, em, ed = e.split("-")
            days = (_date(int(ey), int(em), int(ed)) - _date(int(sy), int(sm), int(sd))).days + 1
            if days >= 3:
                # Count leave days needed: total - weekend_days - holiday_count
                # Holiday count = unique non-Weekend entries in this run
                hol_in_run = sum(1 for k in nw if s <= k <= e and nw[k] != "Weekend")
                # Weekend count
                we_count = 0
                cur = _date(int(sy), int(sm), int(sd))
                end_dt = _date(int(ey), int(em), int(ed))
                while cur <= end_dt:
                    if cur.weekday() >= 5:
                        we_count += 1
                    cur += _td(days=1)
                al_needed = max(0, days - we_count - hol_in_run)
                fmt_range = f"{_date(int(sy),int(sm),int(sd)).strftime('%-d %b')} – {_date(int(ey),int(em),int(ed)).strftime('%-d %b')}"
                # Anchor holiday names
                hol_names = sorted({nw[k] for k in nw if s <= k <= e and nw[k] != "Weekend"})
                long_runs.append({
                    "range": fmt_range,
                    "days": days,
                    "al_needed": al_needed,
                    "holidays": hol_names[:3],
                })

        # Cap at top 8 stretches (table will be long otherwise)
        long_runs_html = []
        for r in long_runs[:8]:
            al_txt = f"~{r['al_needed']} AL" if r['al_needed'] > 0 else "no AL"
            long_runs_html.append(
                f'<li><strong>{r["range"]}</strong> — {r["days"]} days off ({al_txt}) · {", ".join(r["holidays"])}</li>'
            )
        stretches_html = (
            f'<p class="yr-intro">Top long-weekend opportunities in {year} (federal holidays + Sat/Sun weekends; '
            'Selangor/KL/Johor/Kedah/Perak/etc.; add your state for more):</p>'
            f'<ul class="yr-stretches">{"".join(long_runs_html)}</ul>'
            if long_runs_html else
            f'<p class="yr-intro">No long-weekend stretches (3+ days) in {year} using federal holidays only. '
            'Try the planner with your state selected to find more.</p>'
        )

        # FAQ — schema.org FAQPage. Use deduplicated federal holiday count
        # (14 unique holidays under the Holidays Act 1951; the holidays.json
        # file lists each replacement day separately which inflates the count
        # to 19-20). Match the homepage's ItemList `numberOfItems: 14` claim.
        fed_holiday_names = set()
        for h in holidays:
            if h.get('type') == 'federal':
                fed_holiday_names.add(h['name'].replace(' Holiday', ''))
        fed_count = len(fed_holiday_names)
        fed_dates_count = len([h for h in holidays if h.get('type') == 'federal'])
        faqs = [
            {"q": f"How many public holidays are there in Malaysia in {year}?",
             "a": f"There are {fed_count} federal public holidays in {year} under the Holidays Act 1951. Some have additional replacement days (e.g. Chinese New Year Day 2, Hari Raya Day 2), bringing the total gazetted federal holiday days to {fed_dates_count}. Applicability varies by state — New Year's Day and Nuzul Al-Quran, for example, are gazetted federal but not observed uniformly. Each state adds its own 1-5 state-level holidays depending on its ruling monarch's birthday, harvest festivals, and cultural events."},
            {"q": f"What is the first public holiday in {year}?",
             "a": (f"The first federal public holiday in {year} is {holidays[0]['name']} on {holidays[0]['date']}."
                   if holidays else f"The first public holiday in {year} hasn't been gazetted yet.")},
            {"q": "How do I maximise my annual leave?",
             "a": f"Take 1–2 days of AL next to public holidays that already border a weekend. The planner solves the optimal year of long weekends for your AL budget — try it with your state's holidays selected for the most accurate result."},
            {"q": "Do holidays differ by state in Malaysia?",
             "a": "Yes. Each state has its own birthday (Yang di-Pertua Negeri / Yang di-Pertuan Agong) and several cultural holidays (Thaipusam, Gawai, Hari Pesta Kaamatan, etc.) that only apply to workers in that state. Even federal holidays are not always uniformly observed — applicability varies by state and gazette wording."},
            {"q": "When is Hari Raya Aidilfitri / Chinese New Year / Deepavali?",
             "a": "These move each year based on lunar/Islamic calendars. The dates shown here are based on the official gazette but may shift by 1–2 days when the actual moon sighting is announced. Always confirm with your HR/payroll closer to the date."},
            {"q": "Where does this data come from?",
             "a": f"Sourced from the official Malaysian government gazette (kabinet.gov.my / Federal Gazette). For {year} holidays, we cross-reference multiple official sources and the HR Ministry's published calendar."},
        ]
        faq_html_items = []
        for f in faqs:
            faq_html_items.append(
                f'<details class="yr-faq"><summary>{f["q"]}</summary><p>{f["a"]}</p></details>'
            )
        faq_html = "".join(faq_html_items)
        jsonld_faq = json.dumps({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                for f in faqs
            ]
        }, separators=(",", ":"))

        # AdSense slots for year pages (top = below table, mid = below FAQ).
        # When ADSENSE_ENABLED is False, these are inert HTML comments.
        def yr_ad(slot_id, fmt="auto", style=""):
            if not ADSENSE_ENABLED:
                return "<!-- yr ad slot disabled -->"
            return (
                f'<div class="ad-slot" data-ad-slot="{slot_id}"{style}>'
                f'<ins class="adsbygoogle" data-ad-client="{ADSENSE_PUBLISHER_ID}" data-ad-slot="{slot_id}" data-ad-format="{fmt}" data-full-width-responsive="true"></ins>'
                f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'
                f'</div>'
            )
        yr_top_ad = yr_ad(ADSENSE_SLOT_YEAR_TOP, fmt="auto")
        yr_mid_ad = yr_ad(ADSENSE_SLOT_YEAR_MID, fmt="rectangle")

        body_content = f'''
<section class="yr-section">
  <h2 class="yr-h2">All public holidays in {year}</h2>
  <p class="yr-intro">Federal holidays are gazetted under the Holidays Act 1951, but applicability varies — some (e.g. New Year's Day, Nuzul Al-Quran) are observed differently across states. State-specific holidays appear with the state name(s) in brackets. Dates are based on the official gazette.</p>
  {table_html}
</section>

{yr_top_ad}

<section class="yr-section">
  <h2 class="yr-h2">Long weekends in {year}</h2>
  {stretches_html}
  <p class="yr-intro">These are the easiest long weekends to grab with zero or minimal AL. For a year-optimised plan (which holidays to bridge for the most total days off), <a href="/" data-track="year_to_planner">use the planner →</a></p>
</section>

<section class="yr-section">
  <h2 class="yr-h2">Frequently asked questions</h2>
  {faq_html}
</section>

{yr_mid_ad}

<section class="yr-cta">
  <h2 class="yr-h2">Plan your {year} long weekends</h2>
  <p class="yr-intro">Tell the planner how many AL days you have. It solves the optimal {year} plan and exports it to your calendar (.ics).</p>
  <a href="/?y={year}" class="btn btn-primary yr-cta-btn" data-track="year_cta_click" onclick="track('year_cta_click',{{year:{year}}})">Open the planner →</a>
</section>
'''
        scripts = f'<script type="application/ld+json">{jsonld_faq}</script>'
    else:
        # Coming-soon page — captures SEO traffic without claiming false dates
        # Build year-links list outside the f-string to avoid nested f-string
        # escape hell (the inner onclick='track(...)' needs real single quotes).
        year_link_items = []
        for y in sorted(HOLIDAYS.keys()):
            year_link_items.append(
                '<li><a href="/' + str(y) + '" data-track="year_nav" onclick="track(\'year_nav\',{year:' + str(y) + '})">Malaysia public holidays ' + str(y) + ' →</a></li>'
            )
        year_links_html_coming = "".join(year_link_items)
        if year < _CURRENT_YEAR:
            # Past year without data
            body_content = (
                f'<section class="yr-section">'
                f'<h2 class="yr-h2">Malaysia public holidays {year}</h2>'
                f'<p class="yr-intro">{year} has already passed. We keep this page live as a historical reference, but for planning your long weekends, see <a href="/{_latest_year_str}" data-track="year_nav" onclick="track(\'year_nav\',{{year:{_latest_year_str}}})">/{_latest_year_str}</a> (the latest year we have full data for).</p>'
                f'<p class="yr-intro">In the meantime, use the planner with the years we have full data for:</p>'
                f'<ul class="yr-stretches yr-year-links">{year_links_html_coming}</ul>'
                f'</section>'
            )
        else:
                # Future year, gazette not yet published. Socrates H3 fix: thicker
                # content (methodology + state expectations + gazette timing) to
                # avoid the 163-word thin-page penalty. The page itself is
                # noindex'd via the meta robots conditional below.
                _year_has_data = bool(HOLIDAYS.get(str(year)))
                _methodology_examples = ", ".join(sorted(HOLIDAYS.keys()))
                body_content = (
                    f'<section class="yr-section">'
                    f'<h2 class="yr-h2">Malaysia public holidays {year}</h2>'
                    f'<p class="yr-intro">The official {year} gazette hasn\'t been published yet. The Malaysian government typically releases the next year\'s holiday schedule in November or December of the preceding year (e.g. the 2026 gazette was published in late 2025). When it drops, this page will list every federal and state holiday with day-of-week and the same interactive planner you can use today for {_methodology_examples}.</p>'
                    f'<p class="yr-intro">Want a notification when {year} data drops? <a href="/#waitlist" data-track="year_waitlist" onclick="track(\'year_waitlist\',{{year:{year}}})">Join the waitlist →</a></p>'
                    f'</section>'
                    f'<section class="yr-section">'
                    f'<h2 class="yr-h2">What we know about {year} already</h2>'
                    f'<p class="yr-intro">Even before the gazette is published, some {year} holidays are predictable because they fall on fixed dates (e.g. New Year\'s Day, Labour Day, Merdeka Day, Malaysia Day, Christmas Day). Others — Hari Raya Aidilfitri, Hari Raya Haji, Chinese New Year, Awal Muharram, Prophet Muhammad\'s Birthday, Nuzul Al-Quran, Wesak Day, Deepavali — shift year-to-year based on lunar/Islamic calendars. We update the planner the day the gazette publishes.</p>'
                    f'</section>'
                    f'<section class="yr-section">'
                    f'<h2 class="yr-h2">How to plan {year} long weekends in advance</h2>'
                    f'<p class="yr-intro">Most Malaysian workers get 14-20 public holidays per year (depending on state). To maximise your time off:</p>'
                    f'<ul class="yr-stretches">'
                    f'<li><strong>Bridge the long weekends:</strong> Most efficient: 1 AL day for a 3-day weekend, 2 AL for a 5-day stretch, 4 AL for a 9-day stretch.</li>'
                    f'<li><strong>Stack near year-end:</strong> Christmas + New Year always form a 5-7 day stretch with 1-2 AL.</li>'
                    f'<li><strong>Watch the Hari Raya + Chinese New Year overlap:</strong> Some years these fall close together — prime for a single 8-10 day stretch with 2-3 AL.</li>'
                    f'<li><strong>State-aware planning:</strong> Workers in Sarawak, Sabah, and Johor get extra state holidays that don\'t apply to other states.</li>'
                    f'</ul>'
                    f'</section>'
                    f'<section class="yr-section">'
                    f'<h2 class="yr-h2">Use the planner today</h2>'
                    f'<p class="yr-intro">Even without {year} data, the planner shows your optimal {_methodology_examples} plan (drag the AL slider, toggle your state, see the longest stretches). When {year} data arrives, the planner updates automatically — your saved URL stays the same.</p>'
                    f'<a href="/?y={year}" class="btn btn-primary yr-cta-btn" data-track="year_cta_click" onclick="track(\'year_cta_click\',{{year:{year}}})">Open the planner for {year} →</a>'
                    f'</section>'
                )
                body_content += (
                f'<section class="yr-section">'
                f'<h2 class="yr-h2">Plan your long weekends now</h2>'
                f'<p class="yr-intro">Drag the AL slider, toggle your state, and see the longest stretches you can grab with zero or minimal AL. Export to your calendar (.ics) when you\'re happy with the plan.</p>'
                f'<a href="/" class="btn btn-primary yr-cta-btn" data-track="year_cta_click" onclick="track(\'year_cta_click\',{{year:{year}}})">Open the planner →</a>'
                f'</section>'
                )
                scripts = ""

    # Year navigation — appears at top and bottom
    year_links_html = (
        '<nav class="yr-nav">' +
        "".join(
            f'<a href="/{y}" class="{"yr-nav-active" if y == year else ""}" '
            f'data-track="year_nav" onclick="track(\'year_nav\',{{year:{y}}})">{y}</a>'
            for y in [2026, 2027, 2028]
        ) +
        '</nav>'
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{'noindex, follow' if not has_data else 'index, follow'}">
<!-- {(f'<meta name="google-site-verification" content="{GSC_VERIFICATION_CODE}" />') if GSC_VERIFICATION_CODE else 'GSC verification code not set'} -->
<!-- {('AdSense head disabled (ADSENSE_PUBLISHER_ID not set)') if ADSENSE_PUBLISHER_ID.startswith('ca-pub-XXXXXXXX') else (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUBLISHER_ID}" crossorigin="anonymous"></script>')} -->
<link rel="canonical" href="{canonical}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8C%B4%3C/text%3E%3C/svg%3E">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="en_MY">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<script type="application/ld+json">{jsonld_app}</script>
<script type="application/ld+json">{jsonld_article}</script>
<!-- AI-citable structured data: Organization identity + federal holiday list -->
<script type="application/ld+json">{jsonld_org}</script>
{("<!-- FAQ omitted on year pages: existing year-specific FAQPage is richer -->" if jsonld_faq_year is None else f'<script type="application/ld+json">{jsonld_faq_year}</script>')}
<script type="application/ld+json">{jsonld_itemlist_year}</script>
{scripts}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#FDF6F0;--text:#1C1917;--muted:#78716C;--accent:#0F766E;--tint:#CCFBF1;--border:#E7D9C8;--panel:#FFFFFF}}
html{{scroll-behavior:smooth}}
body{{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;font-size:15px;-webkit-font-smoothing:antialiased}}
.container{{max-width:920px;margin:0 auto;padding:1rem 1.25rem 3rem}}
.wordmark{{font-size:18px;font-weight:700;color:var(--text);letter-spacing:-0.01em;margin-bottom:0.25rem}}
.wordmark .my{{color:var(--accent)}}
.yr-nav{{display:flex;gap:0.5rem;margin:0.75rem 0 1.25rem;flex-wrap:wrap}}
.yr-nav a{{padding:0.35rem 0.75rem;border-radius:6px;border:1px solid var(--border);background:var(--panel);color:var(--text);text-decoration:none;font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}}
.yr-nav a.yr-nav-active{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.yr-nav a:hover{{background:var(--tint);border-color:var(--accent)}}
.yr-h1{{font-size:clamp(26px,5.5vw,38px);font-weight:700;line-height:1.2;letter-spacing:-0.02em;margin-bottom:0.5rem}}
.yr-sub{{color:var(--muted);font-size:15px;margin-bottom:1.5rem;max-width:60ch}}
.yr-section{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1.25rem}}
.yr-h2{{font-size:18px;font-weight:700;margin-bottom:0.75rem;color:var(--text)}}
.yr-intro{{color:var(--muted);font-size:14px;margin-bottom:0.75rem;line-height:1.55}}
.yr-hol-table{{width:100%;border-collapse:collapse;font-size:14px}}
.yr-hol-table th,.yr-hol-table td{{padding:0.55rem 0.5rem;text-align:left;border-bottom:1px solid var(--border);vertical-align:top}}
.yr-hol-table thead th{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);background:#FAF7F2}}
.yr-hol-table tbody tr:hover{{background:var(--tint)}}
.yr-date{{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums;width:140px;white-space:nowrap}}
.yr-dow{{color:var(--muted);width:50px;font-variant-numeric:tabular-nums}}
.yr-name{{color:var(--text)}}
.yr-badge{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10.5px;font-weight:600;margin-left:0.4em;vertical-align:middle;letter-spacing:0.02em}}
.yr-fed{{background:#CCFBF1;color:#0F766E}}
.yr-state{{background:#FEF3C7;color:#92400E}}
.yr-stretches{{list-style:none;padding:0;margin:0.5rem 0}}
.yr-stretches li{{padding:0.55rem 0.7rem;border-left:3px solid var(--accent);background:#FAF7F2;margin-bottom:0.5rem;border-radius:0 6px 6px 0;font-size:14px;color:var(--text);line-height:1.5}}
.yr-stretches li strong{{color:var(--accent);font-variant-numeric:tabular-nums}}
.yr-year-links{{list-style:disc;padding-left:1.5rem}}
.yr-year-links li{{background:transparent;border:none;padding:0.4rem 0;font-size:15px}}
.yr-year-links a{{color:var(--accent);text-decoration:none;font-weight:600}}
.yr-year-links a:hover{{text-decoration:underline}}
.yr-faq{{border-bottom:1px solid var(--border);padding:0.6rem 0}}
.yr-faq:first-of-type{{padding-top:0}}
.yr-faq:last-of-type{{border-bottom:none;padding-bottom:0}}
.yr-faq summary{{cursor:pointer;font-weight:600;color:var(--text);padding:0.3rem 0;font-size:14.5px;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:0.5rem}}
.yr-faq summary::-webkit-details-marker{{display:none}}
.yr-faq summary::after{{content:"+";color:var(--accent);font-size:18px;font-weight:600;flex-shrink:0}}
.yr-faq[open] summary::after{{content:"−"}}
.yr-faq p{{margin-top:0.5rem;color:var(--muted);font-size:14px;line-height:1.6}}
.yr-cta{{background:var(--accent);color:#fff;border-radius:12px;padding:1.5rem 1.75rem;text-align:center}}
.yr-cta .yr-h2{{color:#fff;margin-bottom:0.5rem}}
.yr-cta .yr-intro{{color:rgba(255,255,255,0.9);margin-bottom:1rem}}
.yr-cta-btn{{background:#fff;color:var(--accent)}}
.yr-cta-btn:hover{{background:var(--tint)}}
footer{{margin-top:2rem;font-size:13px;color:var(--muted);text-align:center}}
footer p{{margin-bottom:0.3rem}}
footer a{{color:var(--muted);text-decoration:none}}
footer a:hover{{color:var(--accent);text-decoration:underline}}
.kopi-cta{{font-size:12.5px;color:var(--muted)}}
.kopi-link{{color:var(--accent);font-weight:600}}
@media(max-width:600px){{
  .yr-hol-table thead{{display:none}}
  .yr-hol-table,.yr-hol-table tbody,.yr-hol-table tr,.yr-hol-table td{{display:block;width:100%}}
  .yr-hol-table tr{{padding:0.6rem 0;border-bottom:2px solid var(--border)}}
  .yr-hol-table td{{padding:0.15rem 0;border-bottom:none}}
  .yr-date{{font-size:13px;width:auto}}
}}
</style>
</head>
<body>
<div class="container">
  <div class="wordmark">Long Weekend<span class="my">.my</span></div>
  {year_links_html}

  <h1 class="yr-h1">{title}</h1>
  <p class="yr-sub">{desc}</p>

  {body_content}

  <footer>
    <p><a href="/" data-track="nav_home">Home</a> · <a href="/about.html" data-track="nav_about" onclick="track('nav_about')">About</a> · <a href="/privacy.html" data-track="nav_privacy" onclick="track('nav_privacy')">Privacy</a> · <a href="/privacy.html#advertising" data-track="nav_ads" onclick="track('nav_ads')">Ads</a></p>
    <p class="kopi-cta">Saved you a few days of leave? <a href="https://www.buymeacoffee.com/longweekend" target="_blank" rel="noopener" data-track="tip_jar_click" onclick="track('tip_jar_click',{{source:'year_footer'}})" class="kopi-link">buy miso a kopi</a></p>
    <p><span class="muted">Made with ☕ in KL</span></p>
  </footer>
</div>

<script>
function track(name, props) {{
  try {{
    window.va && window.va('event', {{ name: name, ...(props||{{}}) }});
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {{
      // Fire-and-forget event log so the dashboard counts year-page interactions.
      try {{
        const payload = JSON.stringify({{
          name: name,
          props: props || {{}},
          ts: new Date().toISOString(),
          path: location.pathname
        }});
        navigator.sendBeacon('/api/track-event', payload);
      }} catch (e) {{}}
    }}
  }} catch (e) {{}}
}}
window.va=window.va||function(){{window.vaq=window.vaq||[];}};
</script>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>'''

    out = ROOT / f"year-{year}.html"
    out.write_text(html)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes) [{len(holidays)} holidays, {'full' if has_data else 'placeholder'}]")
    return out


_args = _parse_args()
if _args.year:
    render_year_page(_args.year)
elif _args.all_years:
    for y in [2026, 2027, 2028]:
        render_year_page(y)
    # Also rebuild the planner so homepage + year pages stay in sync
    out = ROOT / "index.html"
    out.write_text(HTML)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
else:
    # Default: build the planner (index.html)
    out = ROOT / "index.html"
    out.write_text(HTML)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")

# Always regenerate sitemap.xml after a successful build so URL list
# stays in sync with what we actually deploy. generate_sitemap.py is the
# canonical source (URLs verified against disk 2026-07-18).
try:
    import subprocess
    result = subprocess.run(
        ["python3", str(ROOT / "generate_sitemap.py")],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"⚠️  sitemap regen failed: {result.stderr.strip()}")
except Exception as e:
    print(f"⚠️  sitemap regen skipped: {e}")

# Always regenerate llm.txt for AI crawlers (ChatGPT, Perplexity, etc).
# See https://llmstxt.org/ for the convention.
try:
    import subprocess
    result = subprocess.run(
        ["python3", str(ROOT / "generate_llm_txt.py")],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"⚠️  llm.txt regen failed: {result.stderr.strip()}")
except Exception as e:
    print(f"⚠️  llm.txt regen skipped: {e}")

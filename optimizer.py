#!/usr/bin/env python3
"""
Long Weekend Optimizer for Malaysia.
Finds all non-working-day stretches (weekends + federal/state holidays) in a year,
and computes the AL needed to extend each into a longer break.

Algorithm:
1. Build a set of "non-working dates" for the given year (federal holidays + weekends,
   optionally extended with selected state holidays).
2. Find maximal contiguous runs of non-working dates.
3. For each run, find the AL cost to extend it by 1, 2, ... N days on each end.
4. Score = (total days off) / (AL used) — higher is better.
5. Emit the top combos.

Key insight: a "long weekend" only needs AL if it borders a working day. If Wed is
a holiday, Sat-Sun-Wed needs 1 AL day (Thu) and Mon-Tue if you want to bridge —
that's 5 days off for 2 AL = 2.5x efficiency.
"""
import json
from datetime import date, timedelta
from collections import defaultdict

WEEKEND_DAYS = {5, 6}  # Saturday=5, Sunday=6 in Python's weekday()

# State name normalization (the JSON has them spelled out, but handle variants)
STATE_ALIASES = {
    "kl": "Kuala Lumpur", "kuala lumpur": "Kuala Lumpur",
    "pj": "Putrajaya", "putrajaya": "Putrajaya",
    "sel": "Selangor", "selangor": "Selangor",
    "jhr": "Johor", "johor": "Johor",
    "kd": "Kedah", "kedah": "Kedah",
    "ktn": "Kelantan", "kelantan": "Kelantan",
    "mlk": "Melaka", "melaka": "Melaka", "malacca": "Melaka",
    "ns": "Negeri Sembilan", "negeri sembilan": "Negeri Sembilan",
    "phg": "Pahang", "pahang": "Pahang",
    "png": "Penang", "penang": "Penang", "pulau pinang": "Penang",
    "prk": "Perak", "perak": "Perak",
    "pls": "Perlis", "perlis": "Perlis",
    "sbh": "Sabah", "sabah": "Sabah",
    "swk": "Sarawak", "sarawak": "Sarawak",
    "trg": "Terengganu", "terengganu": "Terengganu",
    "lbn": "Labuan", "labuan": "Labuan",
    "federal": None, "all": None, "national": None,  # null = federal
}

def load_holidays(path="holidays.json"):
    with open(path) as f:
        raw = json.load(f)
    out = {}
    for year_str, rows in raw.items():
        year = int(year_str)
        out[year] = []
        for r in rows:
            y, m, d = r["date"].split("-")
            out[year].append({
                "date": date(int(y), int(m), int(d)),
                "name": r["name"],
                "type": r["type"],
                "state": r["state"],
            })
        out[year].sort(key=lambda x: x["date"])
    return out

def get_nonworking_set(year_holidays, include_states=None):
    """
    Build a set of non-working dates for the year.
    include_states: list of state names to include (None or empty = federal only)
    Dedupes by (date, name) — the source sometimes lists the same holiday name
    multiple times for "observed" replacement days, which we collapse.
    """
    nonworking = {}
    for h in year_holidays:
        is_federal = h["type"] == "federal"
        is_state = h["type"] == "state" and h["state"] in (include_states or [])
        if is_federal or is_state:
            if h["date"] not in nonworking:
                nonworking[h["date"]] = h["name"]
            # If already present, keep first occurrence (don't overwrite)
    return nonworking

def find_runs(nonworking, year):
    """
    Find all maximal contiguous runs of non-working dates within the year.
    Each run also extends to include Sat/Sun at its boundaries.
    Returns: list of {"start": date, "end": date, "holidays": [(date, name), ...]}
    """
    # Add all weekends in the year to the nonworking set (for run extension)
    full_set = dict(nonworking)
    d = date(year, 1, 1)
    while d.year == year:
        if d.weekday() in WEEKEND_DAYS:
            if d not in full_set:
                full_set[d] = "Weekend"
        d += timedelta(days=1)

    # Find maximal runs
    sorted_dates = sorted(full_set.keys())
    runs = []
    if not sorted_dates:
        return runs
    current_start = sorted_dates[0]
    current_end = sorted_dates[0]
    for d in sorted_dates[1:]:
        if (d - current_end).days == 1:
            current_end = d
        else:
            runs.append((current_start, current_end))
            current_start = d
            current_end = d
    runs.append((current_start, current_end))
    return runs

def evaluate_run(run_start, run_end, nonworking_set, year, max_al=10):
    """
    For a given natural run, evaluate all possible extensions (1..max_al days on each side).
    Returns list of candidate combos sorted by efficiency.
    """
    candidates = []
    # Only consider runs of >= 2 days (a single weekend isn't worth listing)
    natural_len = (run_end - run_start).days + 1
    if natural_len < 2:
        return candidates

    # Holidays inside the run (exclude pure weekends for the holiday list)
    holidays_in_run = []
    d = run_start
    while d <= run_end:
        if d in nonworking_set and nonworking_set[d] != "Weekend":
            holidays_in_run.append((d, nonworking_set[d]))
        d += timedelta(days=1)

    for al_left in range(0, max_al + 1):
        for al_right in range(0, max_al + 1):
            al_total = al_left + al_right
            if al_total == 0 and natural_len < 4:
                # Skip the trivial "no AL" case unless it's already 4+ days
                continue
            if al_total > max_al:
                continue
            ext_start = run_start - timedelta(days=al_left)
            ext_end = run_end + timedelta(days=al_right)
            total_days = (ext_end - ext_start).days + 1
            # Efficiency: total days off per AL day used
            efficiency = total_days / al_total if al_total > 0 else float('inf') if total_days >= 4 else 0
            if efficiency < 1.0 and al_total > 0:
                # Never worth it: AL extends the break but only if the added time is more than the AL cost
                # A 3-day break using 1 AL = 3.0x (good), 2 days off + 1 AL = 2.0x (ok)
                # If efficiency < 1.0, you'd be better off just NOT taking AL
                continue
            candidates.append({
                "start": ext_start.isoformat(),
                "end": ext_end.isoformat(),
                "total_days": total_days,
                "al_used": al_total,
                "al_left": al_left,
                "al_right": al_right,
                "efficiency": round(efficiency, 2),
                "natural_len": natural_len,
                "holidays": [{"date": hd.isoformat(), "name": hn} for hd, hn in holidays_in_run],
            })
    return candidates

def optimize(year_holidays, year, al_budget=14, include_states=None, max_al_per_combo=5, top_n=50):
    """
    Main entry point. Returns the top long-weekend combos for the given parameters,
    ranked by efficiency then total days off.
    """
    nonworking = get_nonworking_set(year_holidays, include_states)
    runs = find_runs(nonworking, year)

    all_candidates = []
    seen = set()  # dedupe by (start, end, al_used)
    for run_start, run_end in runs:
        candidates = evaluate_run(run_start, run_end, nonworking, year, max_al=max_al_per_combo)
        for c in candidates:
            if c["al_used"] > al_budget:
                continue
            key = (c["start"], c["end"], c["al_used"])
            if key in seen:
                continue
            seen.add(key)
            all_candidates.append(c)

    # Rank: efficiency desc, then total_days desc, then al_used asc
    all_candidates.sort(key=lambda x: (-x["efficiency"], -x["total_days"], x["al_used"]))
    return all_candidates[:top_n]

if __name__ == "__main__":
    import sys
    data = load_holidays()
    year = 2026
    al = 14
    states = None
    if len(sys.argv) > 1:
        year = int(sys.argv[1])
    if len(sys.argv) > 2:
        al = int(sys.argv[2])
    if len(sys.argv) > 3:
        states = sys.argv[3].split(",")
    results = optimize(data[year], year, al_budget=al, include_states=states, top_n=15)
    print(f"\n=== Top 15 long-weekend combos for {year} (AL={al}, states={states or 'federal only'}) ===\n")
    for i, c in enumerate(results, 1):
        h_names = ", ".join(h["name"] for h in c["holidays"]) or "weekend only"
        print(f"{i:2d}. {c['start']} → {c['end']}  |  {c['total_days']} days off, {c['al_used']} AL  |  {c['efficiency']}x  |  {h_names}")

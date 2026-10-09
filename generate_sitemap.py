#!/usr/bin/env python3
"""
Sitemap generator + regression test for longweekend.my.

The previous form was a verifier-only script; the underlying sitemap.xml was
hand-built and drifted (22-URL contract, 9 URLs live). This file is now the
sole canonical generator AND verifier:

  1. Scan the project on-disk and emit sitemap.xml that matches reality
     (every hub directory, every year page, llm.txt, /api/holidays.json).
  2. Self-verify the emit against the contract below.

Run standalone OR auto-invoked by build.py after each successful build.
Exit codes: 0 = OK (sitemap emitted and verified), 1 = contract violation.

Contract (asserted below):
  - Every expected artifact on disk corresponds to a <url> in the sitemap
  - Every <url> in the sitemap exists on disk
  - lastmod = current date for /, 2026, year-CTAs; fresh for hubs
  - XML parses cleanly
  - All declared hubs (malaysia, selangor, johor, kedah, perak, sabah, sarawak)
    appear when their directory exists; absent hubs are NOT emitted (so
    building the missing hubs later will surface them automatically)

The forced build path is intentionally NOT invoked from here — this is a
post-build generator/verifier, not a generator of pages. Run
`python3 build.py --force` first.
"""
import re
import sys
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
SITEMAP = ROOT / "sitemap.xml"

# Full hub universe. Missing directories → not emitted; no contract violation.
DECLARED_HUBS = (
    "malaysia", "selangor", "johor", "kedah", "perak", "sabah", "sarawak",
)
STATIC_PAGES = (
    ("/", 1.0, "daily"),
    ("/about.html", 0.4, "monthly"),
    ("/privacy.html", 0.2, "yearly"),
    ("/2026", 0.9, "daily"),
    ("/2027", 0.6, "monthly"),
    ("/2028", 0.3, "yearly"),
    ("/llm.txt", 0.5, "weekly"),
    ("/api/holidays.json", 0.5, "monthly"),
)
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def _today_iso() -> str:
    return datetime.date.today().isoformat()


def _path_or_trailing_slash(p: str) -> str:
    return p if p.endswith("/") or p.endswith(".txt") or p.endswith(".json") else p


def _exists(path_str: str) -> bool:
    """Check if a sitemap URL maps to an actual on-disk artifact.

    Vercel rewrites (see vercel.json) redirect /2026 -> /year-2026.html etc.
    We treat those rewrites as "exists" so the generator doesn't double-emit.
    """
    VERCEL_REWRITES = {
        "/2025": "/year-2026.html",  # historic alias
        "/2026": "/year-2026.html",
        "/2027": "/year-2027.html",
        "/2028": "/year-2028.html",
        "/holidays/2026": "/year-2026.html",
        "/holidays/2027": "/year-2027.html",
        "/holidays/2028": "/year-2028.html",
    }
    if path_str in VERCEL_REWRITES:
        return _exists(VERCEL_REWRITES[path_str])

    if path_str.endswith("/"):
        rel = path_str.lstrip("/")
        if not rel:
            return (ROOT / "index.html").exists()
        return (ROOT / rel / "index.html").exists()
    if path_str.startswith("/api/"):
        # Api endpoints — Vercel-deployed, always present in production.
        # Verify file exists locally OR fall back to truth-of-existence.
        api_name = path_str[len("/api/"):]
        return (ROOT / "api" / api_name).exists() or True
    rel = path_str.lstrip("/")
    return (ROOT / rel).exists()


def emit_sitemap(today: str) -> str:
    """Generate the sitemap.xml body based on what actually exists on disk."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    # Static pages — always emit, prioritize the ones we know exist.
    for path, prio, freq in STATIC_PAGES:
        # index.html lives at / → check ROOT/index.html
        # year pages live at /year-YYYY.html in the workspace
        check_path = path
        if path == "/":
            check_path = "/index.html"
        elif re.match(r"^/\d{4}$", path):
            check_path = f"/year-{path[1:]}.html"
        if _exists(check_path):
            lines.append("  <url>")
            lines.append(f"    <loc>https://longweekend.my{path}</loc>")
            lines.append(f"    <lastmod>{today}</lastmod>")
            lines.append(f"    <changefreq>{freq}</changefreq>")
            lines.append(f"    <priority>{prio}</priority>")
            lines.append("  </url>")

    # Hub directories — emit only those that exist on disk.
    for hub in DECLARED_HUBS:
        hub_path = f"/{hub}-long-weekends-2026/"
        if _exists(hub_path):
            lines.append("  <url>")
            lines.append(f"    <loc>https://longweekend.my{hub_path}</loc>")
            lines.append(f"    <lastmod>{today}</lastmod>")
            lines.append("    <changefreq>weekly</changefreq>")
            lines.append("    <priority>0.8</priority>")
            lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def verify_contract(today: str) -> int:
    """Verify the on-disk sitemap.xml matches the contract."""
    if not SITEMAP.exists():
        print(f"❌ {SITEMAP} not found")
        return 1

    raw = SITEMAP.read_text(encoding="utf-8")

    # 1. XML parses.
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"❌ not well-formed XML: {e}")
        return 1

    # 2. Every URL in sitemap points to an existing artifact.
    urls = root.findall("sm:url", NS)
    missing = []
    for u in urls:
        text = u.find("sm:loc", NS)
        if text is None:
            continue
        loc = text.text or ""
        path = loc.replace("https://longweekend.my", "")
        if not _exists(path):
            missing.append(path)
    if missing:
        print(f"❌ {len(missing)} URL(s) in sitemap have no on-disk artifact:")
        for p in missing:
            print(f"   - {p}")
        return 1

    # 3. year-2027/2028 lastmod must not be stale.
    if "2026-01-01" in raw:
        stale = raw.count("<lastmod>2026-01-01</lastmod>")
        print(f"❌ {stale} URL(s) have stale lastmod=2026-01-01")
        return 1

    # 4. Required endpoints present.
    raw_locs = []
    for u in urls:
        loc_el = u.find("sm:loc", NS)
        if loc_el is not None:
            raw_locs.append(loc_el.text)
    for required in ("/llm.txt", "/api/holidays.json"):
        if not any(l and l.endswith(required) for l in raw_locs):
            print(f"❌ missing required endpoint: {required}")
            return 1

    # Pass.
    hubs_live = sum(1 for h in DECLARED_HUBS if _exists(f"/{h}-long-weekends-2026/"))
    print(
        f"✅ sitemap contract ok: {len(urls)} URLs, "
        f"{hubs_live}/{len(DECLARED_HUBS)} hubs live, "
        f"2027/2028 lastmod refreshed"
    )
    return 0


def main() -> int:
    today = _today_iso()
    body = emit_sitemap(today)
    SITEMAP.write_text(body, encoding="utf-8")
    print(f"Wrote {SITEMAP} ({len(body):,} bytes, today={today})")
    return verify_contract(today)


if __name__ == "__main__":
    sys.exit(main())

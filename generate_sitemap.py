#!/usr/bin/env python3
"""
Sitemap regression test.

build.py is the sole source of truth for sitemap.xml. This script does NOT
generate the sitemap. It verifies that the on-disk sitemap produced by
`build.py --force` matches the contract that SEO consumers (Google, Bing, AI
crawlers) need.

Run after any build:    python3 generate_sitemap.py
Exit codes:              0 = pass, 1 = contract violation

Previously this file held a divergent standby implementation that exited
without writing anything. That implementation was a maintenance trap — it
re-stamped every URL with today's date, would silently break hreflang
ordering if re-enabled, and could not be tested against build.py. The current
form converts the trap into a safety net: any contributor who changes
build.py's sitemap logic gets an immediate test failure here.

Contract (asserted below):
  - 22 URLs total (20 HTML + llm.txt + /api/holidays.json)
  - 42 xhtml:link hreflang annotations (3 per landing page × 14 EN/BM pairs)
  - All seven hubs (malaysia, selangor, johor, kedah, perak, sabah, sarawak)
    appear in both EN and BM
  - 2027 and 2028 lastmod are NOT the stale 2026-01-01 value
  - XML parses cleanly

The forced build path is intentionally NOT invoked from here — this is a
post-build verifier, not a generator. Run `python3 build.py --force` first.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
SITEMAP = ROOT / "sitemap.xml"

EXPECTED_URL_COUNT = 22
EXPECTED_HREFLANG_COUNT = 42
EXPECTED_HUBS = {
    "malaysia", "selangor", "johor", "kedah", "perak", "sabah", "sarawak",
}
STALE_LASTMOD = "2026-01-01"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


def _fail(msg: str) -> None:
    print(f"❌ sitemap contract violation: {msg}")
    sys.exit(1)


def _loc_text(url_el: ET.Element) -> Optional[str]:
    loc = url_el.find("sm:loc", NS)
    return loc.text if loc is not None else None


def run_checks() -> int:
    if not SITEMAP.exists():
        _fail(f"{SITEMAP} not found — run `python3 build.py --force` first")

    raw = SITEMAP.read_text(encoding="utf-8")

    # 1. XML parses.
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        _fail(f"not well-formed XML: {e}")

    # 2. URL count.
    urls = root.findall("sm:url", NS)
    if len(urls) != EXPECTED_URL_COUNT:
        _fail(f"expected {EXPECTED_URL_COUNT} <url> entries, got {len(urls)}")

    # 3. hreflang annotation count.
    hreflangs = root.findall(".//xhtml:link", NS)
    if len(hreflangs) != EXPECTED_HREFLANG_COUNT:
        _fail(
            f"expected {EXPECTED_HREFLANG_COUNT} xhtml:link hreflang "
            f"annotations, got {len(hreflangs)}"
        )

    # 4. Hubs present in both EN and BM.
    locs: set[str] = set()
    for u in urls:
        text = _loc_text(u)
        if text is not None:
            locs.add(text)
    for hub in EXPECTED_HUBS:
        en = f"https://longweekend.my/{hub}-long-weekends-2026/"
        bm = f"https://longweekend.my/cuti-panjang-{hub}-2026/"
        if en not in locs:
            _fail(f"missing EN hub: {en}")
        if bm not in locs:
            _fail(f"missing BM hub: {bm}")

    # 5. 2027/2028 lastmod not stuck on stale value.
    stale_hits = re.findall(rf"<lastmod>{STALE_LASTMOD}</lastmod>", raw)
    if stale_hits:
        _fail(
            f"{len(stale_hits)} URL(s) still have stale lastmod={STALE_LASTMOD} — "
            f"2027/2028 must refresh in build.py"
        )

    # 6. AI endpoints present.
    for required in ("/llm.txt", "/api/holidays.json"):
        if not any(link is not None and link.endswith(required) for link in locs):
            _fail(f"missing required endpoint: {required}")

    print(
        f"✅ sitemap contract ok: {len(urls)} URLs, "
        f"{len(hreflangs)} hreflang annotations, "
        f"all 7 EN/BM hub pairs present, 2027/2028 lastmod refreshed"
    )
    return 0


def main() -> int:
    return run_checks()


if __name__ == "__main__":
    sys.exit(main())

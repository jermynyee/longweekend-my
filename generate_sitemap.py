#!/usr/bin/env python3
"""Regenerate sitemap.xml with current URLs + hreflang annotations.

Source of truth = what build.py writes (year pages, SEO landing pages, EN/BM pairs).
Run standalone or auto-invoked by build.py.
"""

from datetime import date
from pathlib import Path

BASE = "https://longweekend.my"
TODAY = date.today().isoformat()

# Pages that exist on disk (verified 2026-07-18)
URLS = [
    # Core
    ("/",        "daily",   "1.0"),    # homepage, always-changing content
    ("/about.html",         "monthly", "0.4"),
    ("/privacy.html",       "yearly",  "0.2"),

    # Year pages (one per supported year). Socrates M1 fix: /2025 301-redirects
    # to /2026 — removed from sitemap (don't index redirected URLs).
    ("/2026",               "daily",   "0.9"),  # current year — boost
    ("/2027",               "yearly",  "0.6"),
    ("/2028",               "yearly",  "0.3"),  # future year (noindex anyway, low prio)

    # SEO landing pages
    ("/malaysia-long-weekends-2026/",       "weekly",  "0.8"),
    ("/selangor-long-weekends-2026/",        "weekly",  "0.7"),
    ("/cuti-panjang-malaysia-2026/",         "weekly",  "0.7"),  # BM version
]

# hreflang pairings (EN ↔ BM)
HREFLANG_PAIRS = {
    "/malaysia-long-weekends-2026/":  None,  # EN-only
    "/selangor-long-weekends-2026/":  None,  # EN-only
    "/cuti-panjang-malaysia-2026/":   None,  # BM-only
    "/":                              None,  # homepage has no BM counterpart yet
}

CHANGELOG = {
    "daily":   TODAY,                                  # 2026-07-18
    "weekly":  TODAY,                                  # same
    "monthly": TODAY[:7] + "-01",                      # 2026-07-01
    "yearly":  TODAY[:4] + "-01-01",                   # 2026-01-01
}

def render():
    parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"')
    parts.append('        xmlns:xhtml="http://www.w3.org/1999/xhtml">')
    for path, freq, prio in URLS:
        lastmod = CHANGELOG[freq]
        parts.append("  <url>")
        parts.append(f"    <loc>{BASE}{path}</loc>")
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts.append(f"    <changefreq>{freq}</changefreq>")
        parts.append(f"    <priority>{prio}</priority>")
        # hreflang annotations for EN↔BM pairs
        if path in HREFLANG_PAIRS and HREFLANG_PAIRS[path]:
            for alt_path, lang in HREFLANG_PAIRS[path]:
                parts.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{BASE}{alt_path}"/>')
        parts.append("  </url>")
    parts.append("</urlset>")
    return "\n".join(parts) + "\n"


def main():
    out = Path(__file__).parent / "sitemap.xml"
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(URLS)} URLs)")


if __name__ == "__main__":
    main()
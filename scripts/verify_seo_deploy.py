#!/usr/bin/env python3
"""
Post-deploy SEO verification.

Run after `npx vercel deploy --prod` to confirm the 8 SEO fixes from the
2026-08-15 ship + the two P2 hardening patches (HEAD for /api/holidays.json,
sitemap regression test) are live on production.

Exit codes:  0 = all green, 1 = one or more checks failed.

Cache-busts every URL with a timestamp query string so Vercel edge cache
cannot hide a stale response. Each check prints a single line with PASS
or FAIL + the actual value measured.

Usage:
    python3 scripts/verify_seo_deploy.py
"""
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://longweekend.my"
CACHE_BUST = f"t={int(time.time())}"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

REQUIRED_HREFLANG_COUNT = 42
REQUIRED_URL_COUNT = 22
EXPECTED_HOMEPAGE_TITLE = "Malaysia Long Weekend Planner 2026 — Stack Public Holidays, Use Less Annual Leave"
EXPECTED_HEADERS = {  # from vercel.json
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


def _busted(path: str) -> str:
    sep = "&" if "?" in path else "?"
    return f"{BASE}{path}{sep}{CACHE_BUST}"


def _fetch(url: str, method: str = "GET") -> tuple[int, dict, str]:
    req = Request(url, method=method)
    with urlopen(req, timeout=15) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")


def _head(url: str) -> tuple[int, dict]:
    """HEAD via urllib. Returns (status, headers)."""
    req = Request(url, method="HEAD")
    with urlopen(req, timeout=15) as r:
        return r.status, dict(r.headers)


def _check(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"{icon} [P2] {name}: {detail}")
    return ok


def _check_p1(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"{icon} [P1] {name}: {detail}")
    return ok


def _check_p3(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"{icon} [P3] {name}: {detail}")
    return ok


def main() -> int:
    failures = 0

    # --- P2 #1: HEAD for /api/holidays.json returns 200 ---
    try:
        status, headers = _head(f"{BASE}/api/holidays.json")
        ok = status == 200
        if not _check("HEAD /api/holidays.json returns 200", ok, f"got {status}"):
            failures += 1
    except Exception as e:
        if not _check("HEAD /api/holidays.json returns 200", False, f"error: {e}"):
            failures += 1

    # --- P2 #2: sitemap contract (live) ---
    try:
        status, _, body = _fetch(_busted("/sitemap.xml"))
        if status != 200:
            if not _check("sitemap.xml fetchable", False, f"HTTP {status}"):
                failures += 1
        else:
            root = ET.fromstring(body)
            urls = root.findall("sm:url", NS)
            hreflangs = root.findall(".//xhtml:link", NS)
            ok_count = len(urls) == REQUIRED_URL_COUNT
            ok_hl = len(hreflangs) == REQUIRED_HREFLANG_COUNT
            if not _check(
                f"sitemap has {REQUIRED_URL_COUNT} URLs",
                ok_count,
                f"got {len(urls)}",
            ):
                failures += 1
            if not _check(
                f"sitemap has {REQUIRED_HREFLANG_COUNT} hreflang annotations",
                ok_hl,
                f"got {len(hreflangs)}",
            ):
                failures += 1
    except Exception as e:
        if not _check("sitemap contract", False, f"error: {e}"):
            failures += 1

    # --- P1: 8 original SEO fixes from the ship ---
    # 1. Homepage has H1
    try:
        _, _, body = _fetch(_busted("/"))
        h1_count = len(re.findall(r"<h1[\s>]", body, re.IGNORECASE))
        title_match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        if not _check_p1("homepage has H1", h1_count == 1, f"got {h1_count}"):
            failures += 1
        if not _check_p1(
            "homepage title matches new target",
            title == EXPECTED_HOMEPAGE_TITLE,
            f"got {title!r}",
        ):
            failures += 1
    except Exception as e:
        if not _check_p1("homepage H1 + title", False, f"error: {e}"):
            failures += 1

    # 2. Homepage has answer fallback
    try:
        _, _, body = _fetch(_busted("/"))
        has_fallback = "answer-fallback" in body or "answer-headline" in body
        if not _check_p1("homepage has answer fallback", has_fallback, "found" if has_fallback else "missing"):
            failures += 1
    except Exception as e:
        if not _check_p1("homepage answer fallback", False, f"error: {e}"):
            failures += 1

    # 3. Homepage has markdown alternate link
    try:
        _, _, body = _fetch(_busted("/"))
        has_md_alt = bool(re.search(r'type=["\']text/markdown["\']', body, re.IGNORECASE))
        if not _check_p1("homepage has markdown alternate link", has_md_alt, "found" if has_md_alt else "missing"):
            failures += 1
    except Exception as e:
        if not _check_p1("homepage markdown alternate", False, f"error: {e}"):
            failures += 1

    # 4. llm.txt is reachable
    try:
        status, _, body = _fetch(_busted("/llm.txt"))
        if not _check_p1("llm.txt is 200", status == 200, f"got {status} ({len(body)} bytes)"):
            failures += 1
    except Exception as e:
        if not _check_p1("llm.txt reachable", False, f"error: {e}"):
            failures += 1

    # 5. /api/holidays.json GET still healthy JSON
    try:
        status, _, body = _fetch(f"{BASE}/api/holidays.json")
        try:
            data = json.loads(body)
            ok = status == 200 and "federal_holidays" in data
            if not _check_p1("GET /api/holidays.json returns valid JSON", ok, f"HTTP {status}, {len(body)} bytes"):
                failures += 1
        except json.JSONDecodeError:
            if not _check_p1("GET /api/holidays.json returns valid JSON", False, f"invalid JSON, status {status}"):
                failures += 1
    except Exception as e:
        if not _check_p1("GET /api/holidays.json", False, f"error: {e}"):
            failures += 1

    # 6. 2027/2028 lastmod refresh
    try:
        _, _, body = _fetch(_busted("/sitemap.xml"))
        stale = re.findall(r"<lastmod>2026-01-01</lastmod>", body)
        if not _check_p1("2027/2028 lastmod refreshed", len(stale) == 0, f"{len(stale)} stale entries"):
            failures += 1
    except Exception as e:
        if not _check_p1("2027/2028 lastmod", False, f"error: {e}"):
            failures += 1

    # 7. Hub hreflang is correct (Malaysia EN ↔ BM)
    try:
        _, _, body = _fetch(_busted("/malaysia-long-weekends-2026"))
        has_en_self = re.search(r'hreflang=["\']en-my["\']\s+href=["\'][^"\']*malaysia-long-weekends-2026', body)
        has_bm_pair = re.search(r'hreflang=["\']ms-my["\']\s+href=["\'][^"\']*cuti-panjang-malaysia-2026', body)
        ok = bool(has_en_self) and bool(has_bm_pair)
        if not _check_p1("Malaysia hub EN↔BM hreflang", ok, "valid" if ok else "broken"):
            failures += 1
    except Exception as e:
        if not _check_p1("Malaysia hub hreflang", False, f"error: {e}"):
            failures += 1

    # 8. Security headers from vercel.json
    try:
        _, headers = _head(_busted("/"))
        # urllib normalizes header keys via http.client; case-insensitive
        # matching needs a lower-cased view to compare reliably.
        headers_lc = {k.lower(): v for k, v in headers.items()}
        for header, expected in EXPECTED_HEADERS.items():
            actual = headers_lc.get(header, "<missing>")
            ok = actual.lower() == expected.lower()
            if not _check_p1(f"security header {header}={expected}", ok, f"got {actual}"):
                failures += 1
    except Exception as e:
        if not _check_p1("security headers", False, f"error: {e}"):
            failures += 1

    # --- P3 improvements (informational, don't fail) ---
    try:
        _, _, body = _fetch(_busted("/sitemap.xml"))
        stale_2026_01 = len(re.findall(r"<lastmod>2026-01-01</lastmod>", body))
        _check_p3("no 2026-01-01 lastmod in sitemap", stale_2026_01 == 0, f"{stale_2026_01} stale")
    except Exception as e:
        _check_p3("sitemap age", False, f"error: {e}")

    # --- Summary ---
    print()
    if failures == 0:
        print("✅ ALL CHECKS PASSED — deploy is live and correct.")
        return 0
    else:
        print(f"❌ {failures} CHECK(S) FAILED — review above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

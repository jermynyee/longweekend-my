/**
 * Vercel Serverless Function — GET /api/attribution
 *
 * Returns aggregated attribution data for the admin dashboard. Protected
 * by a shared-secret URL parameter (ADMIN_KEY env var). Returns:
 *
 *   {
 *     "ok": true,
 *     "range_days": 30,
 *     "totals": {
 *       "signups": 47,
 *       "tip_jar_clicks": 12,
 *       "affiliate_clicks": 8,
 *       "share_clicks": 23
 *     },
 *     "signups_by_source":     [{ "source": "twitter", "count": 18 }, ...],
 *     "signups_by_domain":     [{ "domain": "gmail.com", "count": 25 }, ...],
 *     "signups_by_day":        [{ "day": "2026-06-20", "count": 5 }, ...],
 *     "events_by_name":        [{ "name": "tip_jar_click", "count": 12 }, ...],
 *     "events_by_source":      [{ "source": "threads", "count": 5 }, ...],
 *     "affiliate_by_partner":  [{ "partner": "booking", "count": 5 }, ...],
 *     "affiliate_by_destination": [{ "dest": "Penang", "count": 3 }, ...],
 *     "recent_signups":        [{ "email": "j***@gmail.com", "ts": "...", "source": "twitter" }, ...],
 *     "pageviews_by_day":      [{ "day": "2026-06-20", "count": 25 }, ...],
 *     "unique_visitors_by_day":[{ "day": "2026-06-20", "count": 18 }, ...],
 *     "pageviews_by_day_and_source":      [{ "day": "2026-06-20", "source": "threads", "count": 8 }, ...],
 *     "unique_visitors_by_day_and_source":[{ "day": "2026-06-20", "source": "threads", "count": 6 }, ...],
 *     "pageviews_by_source":   [{ "source": "threads", "count": 80 }, ...]
 *   }
 *
 * If POSTGRES_URL is not set, returns 503 with db_unconfigured.
 *
 * Auth: pass ?key=ADMIN_KEY (matches process.env.ADMIN_KEY). The key
 * is the SAME string Jer uses to access /admin/attribution.html.
 */

import { sql, hashIp } from './_db.js';

// Constant-time compare (mirrors api/unsubscribe.js). Prevents timing attacks
// on the admin endpoint where the key is sent as a query param.
function safeEq(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

function maskEmail(email) {
  if (!email || typeof email !== 'string') return null;
  const [local, domain] = email.split('@');
  if (!domain) return email;
  const masked = local.length <= 2
    ? '*'.repeat(local.length)
    : local[0] + '*'.repeat(Math.max(local.length - 2, 1)) + local[local.length - 1];
  return `${masked}@${domain}`;
}

export async function GET(request) {
  if (!process.env.POSTGRES_URL) {
    return jsonResponse({ ok: false, error: 'db_unconfigured' }, 503);
  }
  const adminKey = process.env.ADMIN_KEY;
  if (!adminKey) {
    return jsonResponse({ ok: false, error: 'admin_key_not_set' }, 503);
  }

  const url = new URL(request.url);
  // SECURITY (25 Aug 26, ox-alpha review): admin key in `?key=` leaked into
  // Vercel request logs + browser history + Referer headers. Prefer the
  // x-admin-key header (the local dashboard is the only consumer — easy to
  // update). Fall back to ?key= for backwards compat so the local dashboard
  // continues to work until Jer updates admin/attribution.html.
  const adminKeyHeader = request.headers.get('x-admin-key') || '';
  const adminKeyQuery = url.searchParams.get('key') || '';
  if (adminKeyQuery) {
    // eslint-disable-next-line no-console
    console.warn('[attribution] ?key= query-string auth is deprecated; switch admin/attribution.html to header x-admin-key');
  }
  const providedKey = adminKeyHeader || adminKeyQuery;
  if (!safeEq(providedKey, adminKey)) {
    return jsonResponse({ ok: false, error: 'unauthorized' }, 401);
  }

  const days = Math.min(Math.max(parseInt(url.searchParams.get('days') || '30', 10), 1), 365);
  // Build the cutoff as a JS Date so Neon binds it as a real timestamptz
  // parameter — passing `now() - interval '1 days'` as a string gets quoted
  // by the sql template tag and Postgres rejects it as "invalid input syntax
  // for type timestamp with time zone".
  //
  // `?since=YYYY-MM-DD` takes precedence over `?days=N` for explicit date
  // filtering (e.g. ignore pre-launch test data). If the param is malformed
  // we fall through to the days-based window.
  const sinceParam = url.searchParams.get('since');
  let sinceDays;
  if (sinceParam && /^\d{4}-\d{2}-\d{2}$/.test(sinceParam)) {
    // Parse as UTC midnight to avoid TZ drift; use end-of-day if only YYYY-MM-DD
    sinceDays = new Date(sinceParam + 'T00:00:00Z');
    if (isNaN(sinceDays.getTime())) {
      sinceDays = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    }
  } else {
    sinceDays = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  }

  // Optional filtering for the dashboard:
  //   - ?exclude_my_ip=1  → drop events whose ip_hash matches the requester
  //                          (so Jer can hide his own pageview tests)
  //   - KNOWN_OWNER_HASHES (below) are ALWAYS excluded when
  //     exclude_my_ip=1 — this handles Jer's multiple devices/networks.
  //     Hash prefixes are 12 hex chars; the requester's full hash is
  //     64 hex chars (SHA-256 of the IP).
  //   - Test events (utm_source='geo-test', signups with email LIKE %@test.local)
  //     are ALWAYS excluded — they're noise that never represents real users.
  //
  // The requester IP is read the same way track-event.js reads it so the hash
  // matches what's stored on the events.
  //
  // To add your own IP hashes: visit /api/debug-top-ips?key=YOUR_KEY to see
  // the top IPs, then add the FULL 64-char hashes to KNOWN_OWNER_HASHES below.
  // (Don't use 12-char prefixes — the DB stores full 64-char hashes.)
  const KNOWN_OWNER_HASHES = [
    // Jer's MacBook/Mac Mini/Android on home WiFi: 192.228.192.114 (Maxis MY,
    // confirmed 5 Jul 26)
    '41c6294973433a8f60ad0d0fafa540d00e1691981c3647810877f1a3d632b6bd',
    // Jer's Android on mobile data: 113.211.128.197 (Maxis MY cellular,
    // confirmed 5 Jul 26)
    '7bfbe11a7b09c6f1f5fbca62547b2ed78f5c222afab534358a25a8abde4bb43b',
    // Jer on home WiFi, 4 Jul 10:18-14:09 MYT (6 trip.com clicks, MY dests,
    // 3 pageviews, 0 shares/tips). Different test session from the main one
    // — confirmed by Jer 6 Jul 26.
    '7e4d098e2861e280cbbc5fc5c996c0c468d0ba0a108a94f531f18327cf94301e',
    // Jer via VPN or alternate network, 4 Jul 22:31 → 5 Jul 12:31 MYT (10
    // trip.com clicks, MY dests, 8 pageviews, 0 shares/tips). Confirmed by
    // Jer 6 Jul 26.
    '5510ec8ea9800a341fafccb3ced89c80f84142f787f6a7f66df4aaafc529c612',
  ];
  const excludeMyIp = url.searchParams.get('exclude_my_ip') === '1';
  let requesterHash = null;
  if (excludeMyIp) {
    const reqIp = (
      request.headers.get('x-vercel-forwarded-for') ||
      (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
      request.headers.get('x-real-ip') ||
      ''
    );
    if (reqIp) requesterHash = await hashIp(reqIp);
  }
  // Build the exclusion list: requester's hash + any known owner hashes.
  // If KNOWN_OWNER_HASHES is empty, this is just [requesterHash].
  const excludedHashes = excludeMyIp
    ? Array.from(new Set([requesterHash, ...KNOWN_OWNER_HASHES].filter(Boolean)))
    : [];
  // If exclude_my_ip=1 but we couldn't determine the requester's IP (no headers),
  // silently fall through to "don't filter" rather than dropping everything.

  try {
    // Run all aggregations in parallel.
    const [
      totalsRow,
      signupsBySource,
      signupsByDomain,
      signupsByDay,
      eventsByName,
      eventsBySource,
      affiliateByPartner,
      affiliateByTripDest,
      affiliateByTripDay,
      recentTripClicks,
      affiliateByDest,
      recentSignups,
      pageviewsByDay,
      uniqueVisitorsByDay,
      pageviewsByDayAndSource,
      uniqueVisitorsByDayAndSource,
      pageviewsBySource,
      pageviewsByCountry,
      pageviewsByCountryCity,
      pageviewsByCountryRegion,
    ] = await Promise.all([
      // Totals
      sql()`
        SELECT
          (SELECT count(*) FROM signups WHERE created_at >= ${sinceDays} AND email NOT LIKE '%@test.local') AS signups,
          (SELECT count(*) FROM events WHERE name = 'pageview' AND created_at >= ${sinceDays} AND utm_source IS DISTINCT FROM 'geo-test' AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))) AS pageviews,
          (SELECT count(DISTINCT ip_hash) FROM events WHERE name = 'pageview' AND created_at >= ${sinceDays} AND utm_source IS DISTINCT FROM 'geo-test' AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))) AS unique_visitors,
          (SELECT count(*) FROM events WHERE name = 'tip_jar_click' AND created_at >= ${sinceDays} AND utm_source IS DISTINCT FROM 'geo-test' AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))) AS tip_jar_clicks,
          (SELECT count(*) FROM events WHERE name = 'affiliate_click' AND created_at >= ${sinceDays} AND utm_source IS DISTINCT FROM 'geo-test' AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))) AS affiliate_clicks,
          (SELECT count(*) FROM events WHERE name = 'share_click' AND created_at >= ${sinceDays} AND utm_source IS DISTINCT FROM 'geo-test' AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))) AS share_clicks
      `,
      // Signups by UTM source
      sql()`
        SELECT COALESCE(utm_source, '(direct)') AS source, count(*)::int AS count
        FROM signups
        WHERE created_at >= ${sinceDays} AND email NOT LIKE '%@test.local'
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Signups by email domain
      sql()`
        SELECT email_domain AS domain, count(*)::int AS count
        FROM signups
        WHERE created_at >= ${sinceDays} AND email NOT LIKE '%@test.local'
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Signups by day (last N days, fill zeros later)
      sql()`
        SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
               count(*)::int AS count
        FROM signups
        WHERE created_at >= ${sinceDays} AND email NOT LIKE '%@test.local'
        GROUP BY 1
        ORDER BY 1
      `,
      // Events by name
      sql()`
        SELECT name, count(*)::int AS count
        FROM events
        WHERE created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Events by UTM source (only top 20 events)
      sql()`
        SELECT COALESCE(utm_source, '(direct)') AS source, count(*)::int AS count
        FROM events
        WHERE created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Affiliate clicks by partner
      sql()`
        SELECT COALESCE(partner, '(unknown)') AS partner, count(*)::int AS count
        FROM events
        WHERE name = 'affiliate_click' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
      `,
      // Trip.com clicks by destination (NEW — for the dedicated Trip.com panel)
      sql()`
        SELECT COALESCE(dest, '(unknown)') AS dest, count(*)::int AS count
        FROM events
        WHERE name = 'affiliate_click' AND partner = 'trip' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 10
      `,
      // Trip.com clicks by day (NEW — trend line for the new partner)
      sql()`
        SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
               count(*)::int AS count
        FROM events
        WHERE name = 'affiliate_click' AND partner = 'trip' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY 1
      `,
      // Recent Trip.com clicks (NEW — last 20 with dest + ts for the new panel)
      sql()`
        SELECT to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS ts,
               COALESCE(dest, '(unknown)') AS dest,
               days_off AS "daysOff",
               al AS al
        FROM events
        WHERE name = 'affiliate_click' AND partner = 'trip' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        ORDER BY created_at DESC
        LIMIT 20
      `,
      // Affiliate clicks by destination
      sql()`
        SELECT COALESCE(dest, '(unknown)') AS dest, count(*)::int AS count
        FROM events
        WHERE name = 'affiliate_click' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 15
      `,
      // Recent signups (last 20, emails masked) — filtered by the date range
      // (consistent with the other 8 aggregations on this endpoint)
      sql()`
        SELECT email, to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS ts,
               COALESCE(utm_source, '(direct)') AS source, year, al,
               feedback, feedback_len
        FROM signups
        WHERE created_at >= ${sinceDays} AND email NOT LIKE '%@test.local'
        ORDER BY created_at DESC
        LIMIT 20
      `,
      // Pageviews by day (time series)
      sql()`
        SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
               count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY 1
      `,
      // Unique visitors by day (DISTINCT ip_hash per day) — pairs with
      // pageviews_by_day to spot bots (pv/uv ratio) and real traction.
      // Note: same visitor on two days counts once per day, not once total.
      sql()`
        SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
               count(DISTINCT ip_hash)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND ip_hash IS NOT NULL
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY 1
      `,
      // Pageviews by day AND grouped source (time series × channel matrix).
      // Required to disambiguate which channel drove a multi-day spike —
      // e.g. "was the Sep 1-4 burst Threads or WhatsApp-direct?" Without
      // this, every spike attribution is a guess. Rows: [{day, source, count}].
      // Source grouping mirrors pageviewsBySource exactly so buckets line up.
      sql()`
        SELECT
          to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
          CASE
            WHEN utm_source = 'reddit'  THEN 'reddit'
            WHEN ref_host LIKE '%reddit.com%'  THEN 'reddit'
            WHEN utm_source = 'threads' THEN 'threads'
            WHEN ref_host LIKE '%threads.net%' OR ref_host LIKE '%threads.com%' THEN 'threads'
            WHEN utm_source IN ('instagram','ig')  THEN 'instagram'
            WHEN ref_host LIKE '%instagram.com%' OR ref_host LIKE '%cdninstagram.com%' THEN 'instagram'
            WHEN utm_source IN ('twitter','x') THEN 'twitter / x'
            WHEN ref_host IN ('twitter.com','x.com','t.co','mobile.twitter.com','m.twitter.com') THEN 'twitter / x'
            WHEN utm_source = 'facebook' OR utm_source = 'fb' THEN 'facebook'
            WHEN ref_host IN ('facebook.com','m.facebook.com','l.facebook.com','lm.facebook.com') THEN 'facebook'
            WHEN utm_source = 'tiktok' THEN 'tiktok'
            WHEN ref_host LIKE '%tiktok.com%' THEN 'tiktok'
            WHEN utm_source = 'linkedin' THEN 'linkedin'
            WHEN ref_host IN ('linkedin.com','lnkd.in') THEN 'linkedin'
            WHEN utm_source = 'whatsapp' OR ref_host LIKE '%whatsapp.com%' OR ref_host = 'wa.me' THEN 'whatsapp'
            WHEN utm_source = 'telegram' OR ref_host IN ('t.me','telegram.me','telegram.org') THEN 'telegram'
            WHEN ref_host LIKE '%google.%' OR ref_host = 'google.com' THEN 'google'
            WHEN ref_host LIKE '%bing.com%' OR ref_host LIKE '%duckduckgo.com%' OR ref_host LIKE '%yahoo.com%' THEN 'search (other)'
            WHEN utm_source IS NOT NULL AND utm_source != '' THEN utm_source
            ELSE '(direct)'
          END AS source,
          count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1, 2
        ORDER BY 1, count DESC
      `,
      // Unique visitors by day AND grouped source. Same matrix, deduplicated
      // per (day, ip_hash, source) so a visitor who hits the site twice from
      // the same source on the same day counts once. Pairs with the above to
      // spot source-specific bot traffic (pv/uv ratio spikes per channel).
      sql()`
        SELECT
          to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
          CASE
            WHEN utm_source = 'reddit'  THEN 'reddit'
            WHEN ref_host LIKE '%reddit.com%'  THEN 'reddit'
            WHEN utm_source = 'threads' THEN 'threads'
            WHEN ref_host LIKE '%threads.net%' OR ref_host LIKE '%threads.com%' THEN 'threads'
            WHEN utm_source IN ('instagram','ig')  THEN 'instagram'
            WHEN ref_host LIKE '%instagram.com%' OR ref_host LIKE '%cdninstagram.com%' THEN 'instagram'
            WHEN utm_source IN ('twitter','x') THEN 'twitter / x'
            WHEN ref_host IN ('twitter.com','x.com','t.co','mobile.twitter.com','m.twitter.com') THEN 'twitter / x'
            WHEN utm_source = 'facebook' OR utm_source = 'fb' THEN 'facebook'
            WHEN ref_host IN ('facebook.com','m.facebook.com','l.facebook.com','lm.facebook.com') THEN 'facebook'
            WHEN utm_source = 'tiktok' THEN 'tiktok'
            WHEN ref_host LIKE '%tiktok.com%' THEN 'tiktok'
            WHEN utm_source = 'linkedin' THEN 'linkedin'
            WHEN ref_host IN ('linkedin.com','lnkd.in') THEN 'linkedin'
            WHEN utm_source = 'whatsapp' OR ref_host LIKE '%whatsapp.com%' OR ref_host = 'wa.me' THEN 'whatsapp'
            WHEN utm_source = 'telegram' OR ref_host IN ('t.me','telegram.me','telegram.org') THEN 'telegram'
            WHEN ref_host LIKE '%google.%' OR ref_host = 'google.com' THEN 'google'
            WHEN ref_host LIKE '%bing.com%' OR ref_host LIKE '%duckduckgo.com%' OR ref_host LIKE '%yahoo.com%' THEN 'search (other)'
            WHEN utm_source IS NOT NULL AND utm_source != '' THEN utm_source
            ELSE '(direct)'
          END AS source,
          count(DISTINCT (date_trunc('day', created_at), ip_hash))::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND ip_hash IS NOT NULL
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1, 2
        ORDER BY 1, count DESC
      `,
      // Pageviews by grouped source. The grouping normalizes both UTM
      // sources (e.g. utm_source='reddit') and referer hostnames
      // (e.g. 'www.reddit.com', 'com.reddit.frontpage', 'old.reddit.com')
      // into a single bucket per platform. Pattern: a CASE expression
      // checks the UTM source first (explicit tagging wins), then falls
      // back to LIKE-matching the ref_host, then to '(direct)'. New
      // platforms can be added by appending a WHEN clause.
      sql()`
        SELECT
          CASE
            WHEN utm_source = 'reddit'  THEN 'reddit'
            WHEN ref_host LIKE '%reddit.com%'  THEN 'reddit'
            WHEN utm_source = 'threads' THEN 'threads'
            WHEN ref_host LIKE '%threads.net%' OR ref_host LIKE '%threads.com%' THEN 'threads'
            WHEN utm_source IN ('instagram','ig')  THEN 'instagram'
            WHEN ref_host LIKE '%instagram.com%' OR ref_host LIKE '%cdninstagram.com%' THEN 'instagram'
            WHEN utm_source IN ('twitter','x') THEN 'twitter / x'
            WHEN ref_host IN ('twitter.com','x.com','t.co','mobile.twitter.com','m.twitter.com') THEN 'twitter / x'
            WHEN utm_source = 'facebook' OR utm_source = 'fb' THEN 'facebook'
            WHEN ref_host IN ('facebook.com','m.facebook.com','l.facebook.com','lm.facebook.com') THEN 'facebook'
            WHEN utm_source = 'tiktok' THEN 'tiktok'
            WHEN ref_host LIKE '%tiktok.com%' THEN 'tiktok'
            WHEN utm_source = 'linkedin' THEN 'linkedin'
            WHEN ref_host IN ('linkedin.com','lnkd.in') THEN 'linkedin'
            WHEN utm_source = 'whatsapp' OR ref_host LIKE '%whatsapp.com%' OR ref_host = 'wa.me' THEN 'whatsapp'
            WHEN utm_source = 'telegram' OR ref_host IN ('t.me','telegram.me','telegram.org') THEN 'telegram'
            WHEN ref_host LIKE '%google.%' OR ref_host = 'google.com' THEN 'google'
            WHEN ref_host LIKE '%bing.com%' OR ref_host LIKE '%duckduckgo.com%' OR ref_host LIKE '%yahoo.com%' THEN 'search (other)'
            WHEN utm_source IS NOT NULL AND utm_source != '' THEN utm_source
            ELSE '(direct)'
          END AS source,
          count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Visitor location — top countries (pageviews only, ignores affiliate clicks
      // to avoid double-counting users who click multiple times)
      sql()`
        SELECT COALESCE(geo_country, '(unknown)') AS country, count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
      // Visitor location — top (country, city) pairs for drilldown
      sql()`
        SELECT COALESCE(geo_country, '(unknown)') AS country,
               COALESCE(NULLIF(geo_city, ''), '(unknown)') AS city,
               count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1, 2
        ORDER BY count DESC
        LIMIT 20
      `,
      // Visitor location — top (country, region) pairs. Region is a numeric
      // ISO code (e.g. "14" = Selangor) — useful to surface that the geo
      // resolution goes beyond just country.
      sql()`
        SELECT COALESCE(geo_country, '(unknown)') AS country,
               COALESCE(NULLIF(geo_region, ''), '(unknown)') AS region,
               count(*)::int AS count
        FROM events
        WHERE name = 'pageview' AND created_at >= ${sinceDays}
          AND utm_source IS DISTINCT FROM 'geo-test'
          AND (cardinality(${excludedHashes}::text[]) = 0 OR ip_hash <> ALL(${excludedHashes}))
        GROUP BY 1, 2
        ORDER BY count DESC
        LIMIT 15
      `,
    ]);

    const totals = totalsRow[0] || {
      signups: 0,
      pageviews: 0,
      unique_visitors: 0,
      tip_jar_clicks: 0,
      affiliate_clicks: 0,
      share_clicks: 0,
    };

    return jsonResponse({
      ok: true,
      range_days: days,
      since: sinceDays.toISOString().slice(0, 10),
      generated_at: new Date().toISOString(),
      filters: {
        exclude_my_ip: excludeMyIp,
        exclude_test_events: true,  // always — utm_source='geo-test' and *@test.local are always dropped
      },
      totals,
      signups_by_source: signupsBySource,
      signups_by_domain: signupsByDomain,
      signups_by_day: signupsByDay,
      events_by_name: eventsByName,
      events_by_source: eventsBySource,
      affiliate_by_partner: affiliateByPartner,
      affiliate_by_trip_destination: affiliateByTripDest,
      affiliate_by_trip_day: affiliateByTripDay,
      recent_trip_clicks: recentTripClicks,
      affiliate_by_destination: affiliateByDest,
      pageviews_by_day: pageviewsByDay,
      unique_visitors_by_day: uniqueVisitorsByDay,
      pageviews_by_day_and_source: pageviewsByDayAndSource,
      unique_visitors_by_day_and_source: uniqueVisitorsByDayAndSource,
      pageviews_by_source: pageviewsBySource,
      pageviews_by_country: pageviewsByCountry,
      pageviews_by_country_city: pageviewsByCountryCity,
      pageviews_by_country_region: pageviewsByCountryRegion,
      recent_signups: recentSignups.map((r) => ({
        email: maskEmail(r.email),
        ts: r.ts,
        source: r.source,
        year: r.year,
        al: r.al,
        feedback: r.feedback || null,
        feedback_len: r.feedback_len || 0,
      })),
    });
  } catch (e) {
    console.error('[attribution] query failed:', e.message);
    return jsonResponse({ ok: false, error: e.message }, 500);
  }
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

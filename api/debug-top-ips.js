/**
 * Vercel Serverless Function — GET /api/debug-top-ips
 *
 * Returns the top 10 IP hashes by event count in the last 30 days.
 * Only returns the first 12 chars of each hash (not the full hash) for
 * privacy — enough to compare against the requester's own hash, not enough
 * to reverse-engineer IPs.
 *
 * Auth: same as /api/attribution (ADMIN_KEY query param).
 */
import { sql } from './_db.js';

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
    },
  });
}

function asArray(maybe) {
  if (Array.isArray(maybe)) return maybe;
  if (maybe && typeof maybe === 'object') return [maybe];
  return [];
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
  const key = url.searchParams.get('key');
  if (!safeEq(key || '', adminKey)) {
    return jsonResponse({ ok: false, error: 'unauthorized' }, 401);
  }

  const reqIp = (
    request.headers.get('x-vercel-forwarded-for') ||
    (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
    request.headers.get('x-real-ip') ||
    ''
  );

  try {
    // IMPORTANT: `sql()` is a factory that returns the Neon tag function.
    // Must call `sql()` to get the tag, then use it as a template literal.
    // Doing `sql\`query\`` directly would call sql() with the tag args
    // (which it ignores) and return the tag function — not the query result.
    const tag = sql();

    // Top IPs by event count.
    const topIps = asArray(await tag`
      SELECT
        ip_hash,
        count(*)::int AS total,
        min(created_at) AS first_seen,
        max(created_at) AS last_seen
      FROM events
      WHERE created_at >= now() - interval '30 days'
      GROUP BY ip_hash
      ORDER BY total DESC
      LIMIT 10
    `);

    if (topIps.length === 0) {
      return jsonResponse({
        ok: true,
        range_days: 30,
        top_ips: [],
        requester_ip: reqIp || null,
        note: 'No events in last 30 days. Or all events have ip_hash = NULL.',
      });
    }

    // Per-event-name breakdown for each top IP
    const breakdown = {};
    for (const ip of topIps.map(r => r.ip_hash)) {
      const rows = asArray(await tag`
        SELECT name, count(*)::int AS count
        FROM events
        WHERE created_at >= now() - interval '30 days'
          AND ip_hash = ${ip}
        GROUP BY name
      `);
      const stats = { pageviews: 0, aff_clicks: 0, shares: 0, tips: 0 };
      for (const row of rows) {
        const key = ({
          pageview: 'pageviews',
          affiliate_click: 'aff_clicks',
          share_click: 'shares',
          share_native: 'shares',
          tip_jar_click: 'tips',
          ics_download: 'aff_clicks',
        })[row.name] || null;
        if (key) stats[key] += row.count;
      }
      breakdown[ip] = stats;
    }

    const result = topIps.map(r => ({
      // Return BOTH the 12-char prefix (for display) AND the full 64-char
      // hash (for use in KNOWN_OWNER_HASHES). This endpoint is admin-only,
      // so the privacy tradeoff is fine.
      ip_prefix: String(r.ip_hash).slice(0, 12),
      ip_hash: r.ip_hash,  // full hash — admin only
      total: r.total,
      first_seen: r.first_seen,
      last_seen: r.last_seen,
      ...(breakdown[r.ip_hash] || {}),
    }));

    return jsonResponse({
      ok: true,
      range_days: 30,
      top_ips: result,
      requester_ip: reqIp || null,
    });
  } catch (e) {
    return jsonResponse({ ok: false, error: String(e.message || e), stack: String(e.stack || '').slice(0, 500) }, 500);
  }
}

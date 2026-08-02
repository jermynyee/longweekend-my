/**
 * Vercel Serverless Function — POST /api/track-event
 *
 * Captures high-value custom events into the events table. This gives us
 * first-party attribution data that Vercel Web Analytics doesn't surface
 * (e.g. "which UTM source drove the most tip_jar_clicks this week").
 *
 * Expected request body (JSON):
 *   {
 *     "name":        "tip_jar_click" | "affiliate_click" | "share_click" |
 *                   "stretch_expand" | "render" | "nav_about" | "nav_privacy"
 *                   | any other event name,
 *     "partner":     "booking" | "skyscanner",       // for affiliate_click
 *     "dest":        "Penang",                       // for affiliate_click
 *     "days_off":    5,                              // for stretch-related
 *     "al":          2,                              // for stretch-related
 *     "scope":       "main" | "stretch",             // for share_click
 *     "idx":         0,                              // for share/affiliate
 *     "attribution": { utm_source, utm_medium, utm_campaign,
 *                      utm_term, utm_content, refHost }
 *   }
 *
 * Response:
 *   200 { ok: true }   on success
 *   400 { ok: false, error: "..." }  on invalid input
 *   503 { ok: false, error: "db_unconfigured" }  if POSTGRES_URL is not set
 *
 * Privacy:
 *   - Raw IP is hashed (SHA-256) before storage
 *   - User-Agent is truncated to 200 chars
 *   - No PII (no email, no name) is stored in events
 *
 * The endpoint is fire-and-forget from the client: the caller does not
 * need to await a response (errors are non-blocking).
 */

import { ensureSchema, sql, extractAttribution, hashIp } from './_db.js';
import { handlePreflight, originAllowed } from './_util.js';

const VALID_EVENTS = new Set([
  'pageview',
  'tip_jar_click',
  'affiliate_click',
  'share_click',
  'stretch_expand',
  'render',
  'nav_about',
  'nav_privacy',
  'vacation_mode_on',
  'vacation_mode_off',
  'popup_shown',
  'popup_dismissed',
  'popup_signup',
  'popup_signup_error',
]);

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Vary': 'Origin',
    },
  });
}

export async function POST(request) {
  // Socrates M4 fix: reject cross-origin POSTs from untrusted sites.
  if (!originAllowed(request)) {
    return new Response(JSON.stringify({ ok: false, error: 'cross_origin_forbidden' }), {
      status: 403,
      headers: {
        'Content-Type': 'application/json',
        'Vary': 'Origin',
      },
    });
  }
  if (!process.env.POSTGRES_URL) {
    return jsonResponse({ ok: false, error: 'db_unconfigured' }, 503);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: 'Invalid JSON' }, 400);
  }

  const name = (body.name || '').toString();
  if (!name || name.length > 64) {
    return jsonResponse({ ok: false, error: 'Missing or invalid event name' }, 400);
  }
  if (!VALID_EVENTS.has(name)) {
    // Unknown event — accept it anyway (forward-compatible) but skip DB.
    return jsonResponse({ ok: true, skipped: 'unknown_event' });
  }

  const ip = (
    request.headers.get('x-vercel-forwarded-for') ||
    (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
    request.headers.get('x-real-ip') ||
    ''
  );
  const ipHash = await hashIp(ip);
  const ua = (request.headers.get('User-Agent') || '').slice(0, 200);
  const attr = extractAttribution(body);

  try {
    const sch = await ensureSchema();
    if (!sch.ok) return jsonResponse({ ok: false, error: 'schema_failed' }, 500);

    await sql()`INSERT INTO events (
      name, partner, dest, days_off, al, scope, idx,
      utm_source, utm_medium, utm_campaign, ref_host, user_agent, ip_hash,
      geo_country, geo_region, geo_city
    ) VALUES (
      ${name},
      ${body.partner || null},
      ${body.dest || null},
      ${Number.isFinite(+body.days_off) ? +body.days_off : null},
      ${Number.isFinite(+body.al) ? +body.al : null},
      ${body.scope || null},
      ${Number.isFinite(+body.idx) ? +body.idx : null},
      ${attr.utm_source}, ${attr.utm_medium}, ${attr.utm_campaign},
      ${attr.ref_host}, ${ua}, ${ipHash},
      ${request.headers.get('x-vercel-ip-country') || null},
      ${request.headers.get('x-vercel-ip-country-region') || null},
      ${request.headers.get('x-vercel-ip-city') || null}
    )`;
    return jsonResponse({ ok: true });
  } catch (e) {
    console.error('[track-event] insert failed:', e.message);
    return jsonResponse({ ok: false, error: e.message }, 500);
  }
}

export async function OPTIONS(request) {
  return handlePreflight(request, { methods: 'POST, OPTIONS' });
}

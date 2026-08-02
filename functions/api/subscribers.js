/**
 * Cloudflare Pages Function — GET /api/subscribers
 *
 * Admin-gated debug endpoint for the MVP. Lists recent subscriber signup events
 * for the current UTC day, plus a summary count.
 *
 * Auth:
 *   - Requires `Authorization: Bearer <ADMIN_TOKEN>` header
 *   - If ADMIN_TOKEN env var is not set, returns 404 (endpoint disabled)
 *
 * Use during validation to confirm signups are landing. Remove or gate harder
 * before any non-trivial traffic.
 *
 *   curl -H "Authorization: Bearer $ADMIN_TOKEN" \
 *        https://longweekend.my/api/subscribers
 *
 *   curl -H "Authorization: Bearer $ADMIN_TOKEN" \
 *        https://longweekend.my/api/subscribers?date=2026-06-19
 *
 * Response:
 *   {
 *     date: "2026-06-19",
 *     count: 3,
 *     events: [ { email, year, al, states, ts }, ... ]
 *   }
 */

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function bucketDay(d = new Date()) {
  return d.toISOString().slice(0, 10);
}

function checkAuth(request, env) {
  if (!env.ADMIN_TOKEN) return { ok: false, reason: "disabled" };
  const header = request.headers.get("Authorization") || "";
  const want = `Bearer ${env.ADMIN_TOKEN}`;
  // constant-time compare to avoid timing leak (KV-keyed ADMIN_TOKEN is short enough
  // that this is paranoia, but the pattern is right for any secret comparison)
  if (header.length !== want.length) return { ok: false, reason: "bad_auth" };
  let mismatch = 0;
  for (let i = 0; i < header.length; i++) {
    mismatch |= header.charCodeAt(i) ^ want.charCodeAt(i);
  }
  return mismatch === 0 ? { ok: true } : { ok: false, reason: "bad_auth" };
}

export async function onRequestGet(context) {
  const { request, env } = context;

  const auth = checkAuth(request, env);
  if (!auth.ok) {
    // Don't reveal whether the endpoint exists or auth is just wrong
    return auth.reason === "disabled"
      ? json({ error: "Not found" }, 404)
      : json({ error: "Unauthorized" }, 401);
  }

  if (!env.SUBSCRIBERS_KV) {
    return json({ error: "KV not bound" }, 503);
  }

  const url = new URL(request.url);
  const date =
    url.searchParams.get("date") && /^\d{4}-\d{2}-\d{2}$/.test(url.searchParams.get("date"))
      ? url.searchParams.get("date")
      : bucketDay();

  let events = [];
  try {
    events = (await env.SUBSCRIBERS_KV.get(`signup_log:${date}`, { type: "json" })) || [];
  } catch (e) {
    return json({ error: "KV read failed", detail: String(e) }, 500);
  }

  return json({
    date,
    count: events.length,
    events,
  });
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization",
    },
  });
}

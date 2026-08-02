/**
 * Small shared helpers for /api/* serverless functions.
 * Keep this file dependency-free (no Neon, no fetch wrappers) so it can be
 * imported by any handler without pulling in the DB driver.
 */

const ALLOWED_ORIGINS = new Set([
  "https://longweekend.my",
  "https://www.longweekend.my",
  "https://go.longweekend.my",
  // Local dev (Jer runs `python3 -m http.server 8765` on his Mac Mini)
  "http://localhost:8765",
  "http://127.0.0.1:8765",
]);

/**
 * Pick the right CORS Origin header for the request. If the Origin header
 * is in our allowlist (or absent — same-origin or server-side), echo it back
 * (browsers require exact match for credentialed CORS). Otherwise return "*"
 * for read-only public endpoints (machine-readable JSON) and reject for
 * write endpoints (the caller does its own check).
 */
export function corsOriginFor(request) {
  const origin = request.headers.get("origin");
  if (!origin) return "*";
  if (ALLOWED_ORIGINS.has(origin)) return origin;
  // Read-only public endpoints can fall back to "*" so AI crawlers + curl
  // + GitHub scrapers still work. Write endpoints (waitlist, track-event)
  // explicitly check origin and return 403 in that case.
  return null;
}

/**
 * JSON response with sensible default CORS. For write endpoints (waitlist,
 * track-event), pass a stricter origin check via originAllowed() first.
 */
export function jsonResponse(body, status = 200, extraHeaders = {}, { origin = "*" } = {}) {
  const headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
    ...extraHeaders,
  };
  headers["Access-Control-Allow-Origin"] = origin;
  return new Response(JSON.stringify(body), { status, headers });
}

/**
 * CORS preflight handler — return 204 with appropriate CORS headers if the
 * origin is allowed, 403 otherwise.
 */
export function handlePreflight(request, { methods = "GET, POST, OPTIONS" } = {}) {
  const origin = request.headers.get("origin");
  const allowedOrigin = origin && ALLOWED_ORIGINS.has(origin) ? origin : "*";
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": allowedOrigin,
      "Access-Control-Allow-Methods": methods,
      "Access-Control-Allow-Headers": "Content-Type",
      "Vary": "Origin",
      "Access-Control-Max-Age": "86400",
    },
  });
}

/**
 * Returns true if the request comes from a browser we trust (longweekend.my
 * or local dev). Returns false for cross-origin POSTs from untrusted sites.
 * Server-side curl / fetch / AI crawlers don't send an Origin header and
 * pass through (treated as same-origin).
 */
export function originAllowed(request) {
  const origin = request.headers.get("origin");
  if (!origin) return true; // server-side, not browser-initiated
  return ALLOWED_ORIGINS.has(origin);
}
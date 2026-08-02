/**
 * Vercel Serverless Function — GET /api/r?code=xxxxxx
 *
 * Redirect handler for short links. Looks up the code in `short_links`,
 * sets a `lw_src` cookie with the source attribution, and 302-redirects
 * to the target URL.
 *
 * Routing: Vercel serves this as `/api/r?code=xxxxxx`. The client builds
 * the user-facing URL as `https://go.longweekend.my/xxxxxx` which maps to
 * `/api/r?code=xxxxxx` via the vercel.json rewrite below.
 *
 * Why a rewrite (and not a file at api/r/[code].js): Vercel's dynamic
 * segment routing for serverless functions requires the file to be at
 * a specific path AND for the function to handle the param via
 * `req.query.code`. A rewrite is more reliable across Vercel's routing
 * edge cases (e.g. when the function's directory contains other files
 * that conflict with the path).
 *
 * Cookie: `lw_src={source}; Max-Age=2592000; Path=/; SameSite=Lax; Secure`
 *   - 30-day Max-Age so attribution survives a return visit days later
 *   - SameSite=Lax so it works for top-level navigations
 *   - Secure so it only goes over HTTPS
 *
 * Browser passes the cookie on the 302 redirect's subsequent request to
 * longweekend.my, where captureAttribution() reads it and persists to
 * sessionStorage as utm_source.
 */

import { resolveAndCount } from './_short.js';

export default async function handler(req, res) {
  // Extract code from query string. Also accept it from the path for
  // clients that hit the function via /api/r/xxxxxx (defensive).
  let code = (req.query && req.query.code) || '';
  if (!code) {
    // Defensive: if someone hits /api/r/xxxxxx directly
    const m = (req.url || '').match(/\/api\/r\/([^/?#]+)/);
    if (m) code = m[1];
  }
  if (!code) {
    return res.status(400).send('bad request: missing code');
  }

  const result = await resolveAndCount(code);
  if (!result.ok) {
    return res.status(404).send(
      `<!doctype html><html><head><title>Link not found</title></head><body style="font-family:system-ui;padding:2rem;text-align:center">
        <h1>🔗 Link not found</h1>
        <p>This short link doesn't exist or has expired.</p>
        <p><a href="https://longweekend.my">Go to longweekend.my</a></p>
      </body></html>`
    );
  }

  // Set the attribution cookie. 30 days.
  const source = result.source || 'share';
  const cookieValue = encodeURIComponent(source);
  res.setHeader(
    'Set-Cookie',
    `lw_src=${cookieValue}; Max-Age=2592000; Path=/; SameSite=Lax; Secure`
  );

  // 302 redirect. Use 302 (not 301) so the redirect doesn't get cached
  // aggressively — every click should re-resolve the code and increment
  // the counter.
  res.setHeader('Location', result.targetUrl);
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  return res.status(302).end();
}

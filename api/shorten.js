/**
 * Vercel Serverless Function — POST /api/shorten
 *
 * Creates a short link for the given target URL, returns the short code.
 * The client uses this to build shareable URLs of the form
 * `https://go.longweekend.my/{code}` which then 302-redirects to the
 * original longweekend.my URL with a `lw_src` cookie set.
 *
 * Why this exists: chat apps (WhatsApp, Telegram, iMessage) aggressively
 * strip UTM params, ?via=/?ref= params, and even /from/{source} path
 * segments from URLs they preview. Short URLs on a custom domain don't
 * match any of those normalization patterns, so they survive intact to
 * the recipient. The /r/[code] redirect then sets a cookie that
 * longweekend.my's captureAttribution() reads on the landing page.
 *
 * Request body (JSON):
 *   {
 *     "url":      "https://longweekend.my/?y=2026&al=14...",   // required
 *     "source":   "share" | "friend" | "manual",               // optional, default 'share'
 *     "idx":      2                                            // optional, stretch index
 *   }
 *
 * Response:
 *   200 { ok: true, code: "xK7m2p", shortUrl: "https://go.longweekend.my/xK7m2p", targetUrl: "..." }
 *   400 { ok: false, error: "..." }
 *   500 { ok: false, error: "..." }
 *
 * No auth — anyone can shorten a longweekend.my URL (they own the
 * shortening service). Abuse vector: someone spamming requests to fill
 * the table. Mitigated by: (a) random 6-char base62 = 2.2B code space,
 * (b) per-request URL length cap, (c) Vercel's built-in rate limit. If
 * abuse becomes a problem, add a per-IP rate limit via Vercel Edge
 * Middleware.
 */

import { createShortLink } from './_short.js';

export default async function handler(req, res) {
  // CORS for cross-origin calls (e.g. the share button from a static page
  // — same origin in our case, but harmless to include)
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'method not allowed' });
  }

  let body = req.body;
  // Vercel may parse JSON for us, or may not — handle both
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};

  const targetUrl = body.url;
  const source = (body.source || 'share').toString().slice(0, 32);
  const stretchIdx = Number.isInteger(body.idx) ? body.idx : null;

  if (!targetUrl) {
    return res.status(400).json({ ok: false, error: 'url required' });
  }
  // Only allow shortening longweekend.my URLs — prevents abuse as a
  // general-purpose shortener
  if (!/^https:\/\/(www\.)?longweekend\.my\//.test(targetUrl)) {
    return res.status(400).json({ ok: false, error: 'only longweekend.my URLs can be shortened' });
  }

  try {
    const result = await createShortLink({ targetUrl, source, stretchIdx });
    if (!result.ok) {
      return res.status(500).json({ ok: false, error: result.error || 'shorten failed' });
    }
    const shortUrl = `https://go.longweekend.my/${result.code}`;
    return res.status(200).json({
      ok: true,
      code: result.code,
      shortUrl,
      targetUrl: result.targetUrl,
    });
  } catch (e) {
    console.error('[shorten] handler error:', e.message);
    return res.status(500).json({ ok: false, error: e.message });
  }
}

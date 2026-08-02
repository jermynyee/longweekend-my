/**
 * Vercel Serverless Function — GET /api/unsubscribe
 *
 * One-click unsubscribe via signed token (CAN-SPAM / GDPR compliant).
 *
 * URL shape (embedded in every email we send):
 *   https://longweekend.my/api/unsubscribe?email=<urlencoded>&token=<hex>
 *
 * token = HMAC-SHA256(email, UNSUBSCRIBE_SECRET) hex-encoded.
 *
 * Behaviour:
 *   - Validates token. If wrong: returns 403 HTML page ("invalid link").
 *   - If valid: marks signups.unsubscribed_at = now() for this email.
 *   - Returns a tiny HTML confirmation page (no JS needed; works in old
 *     email clients).
 *
 * Required env:
 *   - POSTGRES_URL                  (Neon)
 *   - UNSUBSCRIBE_SECRET            (random 32+ char string, set in Vercel)
 *
 * Privacy: row-level. We don't add an "unsubscribes" log table — the
 * unsubscribed_at timestamp on the signup row IS the audit trail.
 *
 * GET (not POST) so the link works directly from any email client without
 * a form. POST would need JS or a form, both broken in many clients.
 */

import { ensureSchema, sql } from './_db.js';

function html(body, status = 200) {
  return new Response(
    `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unsubscribed · longweekend.my</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
       background:#0f172a;color:#f1f5f9;line-height:1.6;margin:0;padding:3rem 1.5rem;min-height:100vh}
  .card{max-width:480px;margin:0 auto;background:#1e293b;border:1px solid #475569;
        border-radius:12px;padding:2rem;text-align:center}
  h1{color:#f59e0b;margin:0 0 0.5rem;font-size:1.4rem}
  p{color:#cbd5e1;margin:0 0 1rem}
  a{color:#f59e0b;text-decoration:none}
  a:hover{text-decoration:underline}
</style>
</head><body>
<div class="card">${body}<p style="margin-top:2rem"><a href="/">← Back to longweekend.my</a></p></div>
</body></html>`,
    {
      status,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    }
  );
}

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign(
    'HMAC',
    key,
    new TextEncoder().encode(message.toLowerCase())
  );
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

// Constant-time compare to prevent timing attacks on the token.
function safeEq(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let m = 0;
  for (let i = 0; i < a.length; i++) m |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return m === 0;
}

export async function GET(request) {
  const url = new URL(request.url);
  const email = (url.searchParams.get('email') || '').trim().toLowerCase();
  const token = (url.searchParams.get('token') || '').trim();
  const secret = process.env.UNSUBSCRIBE_SECRET;

  if (!email || !token) {
    return html(
      '<h1>Invalid unsubscribe link</h1><p>This link is missing required parameters.</p>',
      400
    );
  }
  if (!secret) {
    // Server misconfiguration — log + 503
    console.error('[unsubscribe] UNSUBSCRIBE_SECRET env var is not set');
    return html(
      '<h1>Temporarily unavailable</h1><p>Please email us via the contact form on the homepage and we will remove you manually.</p>',
      503
    );
  }

  const expected = await hmacHex(secret, email);
  if (!safeEq(token, expected)) {
    return html(
      '<h1>Invalid or expired link</h1><p>This unsubscribe link does not look right. If you got here from an email we sent, please email us via the contact form on the homepage and we will remove you.</p>',
      403
    );
  }

  // Valid token. Mark the row(s).
  if (process.env.POSTGRES_URL) {
    try {
      const sch = await ensureSchema();
      if (!sch.ok) {
        return html(
          '<h1>Service temporarily unavailable</h1><p>Please try again in a few minutes.</p>',
          500
        );
      }
      // Update all matching rows in case the same email signed up multiple times.
      // Only update rows that are NOT already unsubscribed (so we don't bump
      // the unsubscribed_at timestamp on a re-click).
      await sql()`UPDATE signups
                  SET unsubscribed_at = now()
                  WHERE email = ${email}
                    AND unsubscribed_at IS NULL`;
    } catch (e) {
      console.error('[unsubscribe] DB update failed:', e.message);
      return html(
        '<h1>Service temporarily unavailable</h1><p>Please try again in a few minutes.</p>',
        500
      );
    }
  }

  return html(
    `<h1>You've been unsubscribed ✓</h1>
     <p>The address <strong>${escapeHtml(email)}</strong> will not receive any more emails from longweekend.my.</p>
     <p>If this was a mistake, just sign up again on the homepage.</p>`,
    200
  );
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export async function OPTIONS() {
  return new Response(null, { status: 204 });
}

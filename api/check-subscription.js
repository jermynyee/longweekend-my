/**
 * Vercel Serverless Function — POST /api/check-subscription
 *
 * Checks if an email is already on the waitlist.
 * Used by the email capture popup to avoid showing it to already-subscribed users.
 *
 * Expected request body (JSON):
 *   { "email": "user@example.com" }
 *
 * Response:
 *   200 { subscribed: true|false }
 *   400 { error: "Email required" }
 *   500 { error: "Database error" }
 *
 * Behavior:
 *   - Best-effort: if the DB is down, returns { subscribed: false } so the
 *     popup still shows (fail open — we'd rather show a popup to a subscribed
 *     user than miss a signup from a new one).
 */

import { sql } from './_db.js';

export default async function handler(req, res) {
  // CORS — only allow same-origin (popup is on longweekend.my)
  res.setHeader('Access-Control-Allow-Origin', 'https://longweekend.my');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body || {};
  if (!email || typeof email !== 'string' || !email.includes('@')) {
    return res.status(400).json({ error: 'Valid email required' });
  }

  try {
    const result = await sql`
      SELECT 1 FROM signups WHERE email = ${email.toLowerCase().trim()} LIMIT 1
    `;
    return res.json({ subscribed: result.length > 0 });
  } catch (e) {
    // Fail open: if the DB is down, show the popup (don't miss a signup)
    console.error('[check-subscription] DB error, failing open:', e.message);
    return res.json({ subscribed: false });
  }
}

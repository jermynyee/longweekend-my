/**
 * Vercel Serverless Function — POST /api/send-klook-email
 *
 * One-off admin endpoint to send the Klook dates request email. Triggered
 * manually with ?key=ADMIN_KEY. Safe to delete after Klook responds.
 *
 * Auth: same ADMIN_KEY pattern as /api/attribution.
 * Resend: uses RESEND_ADMIN_KEY (full send access).
 *
 * POST /api/send-klook-email?key=ADMIN_KEY[&to=email@example.com]
 *   → sends the Klook dates request. Default recipient: affiliate@klook.com
 *     (but the Resend free tier only allows sending to your own verified
 *     email unless you have a verified domain. Pass ?to=your@email.com to
 *     send to yourself and forward manually, OR verify longweekend.my in
 *     Resend to send to affiliate@klook.com directly.)
 */

const EMAIL_BODY = `Hi Klook Affiliate team,

Quick technical question. We run a Malaysian long-weekend planner
(longweekend.my) and send users to Klook hotels from each trip card.
Our current links look like:

  https://affiliate.klook.com/redirect?aid=126213&aff_adid=1326747
    &k_site=https%3A%2F%2Fwww.klook.com%2Fhotels%2F%3Fsearch_query%3DPenang

This pre-fills "Penang" on the hotel search page, but the user still
has to pick check-in and check-out dates manually. A typical trip
from our site is 3-5 days.

For comparison, Booking.com accepts checkin=YYYY-MM-DD&checkout=YYYY-MM-DD
on searchresults.html, and Agoda accepts checkIn=YYYY-MM-DD&checkOut=YYYY-MM-DD
on /search. We currently route to Klook because it's the only working
affiliate, but the missing date pre-fill hurts conversion.

Two questions:

  1. Does the Klook hotel search page accept check-in / check-out
     parameters via URL? If yes, what's the exact param name(s),
     accepted date format, and an example URL?

  2. If this isn't a public feature, is there an undocumented
     deep-link parameter set available to registered affiliates?
     We're ID 126213.

Concrete example of what we'd send a user clicking a "long weekend
in Penang" card for Sat 25 Aug – Wed 29 Aug:

  https://affiliate.klook.com/redirect?aid=126213&aff_adid=1326747
    &k_site=https%3A%2F%2Fwww.klook.com%2Fhotels%2F%3Fsearch_query%3DPenang
    %26checkin%3D2025-08-25%26checkout%3D2025-08-29

Even a "no, not currently supported" is useful — saves us chasing
ghosts. If the answer is yes, we'd implement the same day.

Thanks,
longweekend.my
`;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function POST(request) {
  const url = new URL(request.url);
  const key = url.searchParams.get('key');
  const to = (url.searchParams.get('to') || 'affiliate@klook.com').trim();
  const adminKey = process.env.ADMIN_KEY;
  if (!adminKey) return json({ ok: false, error: 'admin_key_not_set' }, 503);
  if (!key || key !== adminKey) return json({ ok: false, error: 'unauthorized' }, 401);

  const apiKey = process.env.RESEND_ADMIN_KEY;
  if (!apiKey) return json({ ok: false, error: 'resend_admin_key_not_set' }, 503);

  const from = process.env.MAIL_FROM || 'Long Weekend <onboarding@resend.dev>';
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from,
        to,
        reply_to: 'hello@longweekend.my',
        subject: 'Deep-link hotel search with check-in / check-out date params',
        text: EMAIL_BODY,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return json({ ok: false, error: data?.message || `resend_${res.status}` }, res.status);
    }
    return json({ ok: true, message_id: data?.id || null, from, to });
  } catch (e) {
    return json({ ok: false, error: e?.message || String(e) }, 500);
  }
}

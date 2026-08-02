/**
 * Cloudflare Pages Function — POST /api/subscribe
 *
 * Wired up (v2) for longweekend.my:
 *   - Validates input (email + honeypot)
 *   - Idempotent: skips work if we've seen this email before
 *   - Persists to Cloudflare KV: env.SUBSCRIBERS_KV
 *   - Sends a welcome email via Resend (free tier: 100/day, 3k/month)
 *   - All best-effort: KV write failure or email failure does NOT block
 *     the response. A user who submits should always get a success message;
 *     we capture the failure in logs and in `signup_log`.
 *
 * Expected request body (JSON):
 *   {
 *     "email":      "user@example.com",   // required
 *     "year":       "2026",               // optional, default "2026"
 *     "al":         "14",                 // optional, default "14"
 *     "states":     ["Selangor", ...],    // optional
 *     "website":    ""                    // honeypot — must be empty
 *   }
 *
 * Response:
 *   200 { ok: true,  message: "..." }    on success or duplicate
 *   400 { ok: false, error: "..." }      on invalid input
 *   429 { ok: false, error: "..." }      on rate limit
 *
 * Required env (set in Cloudflare Pages → Settings → Environment variables):
 *   - SUBSCRIBERS_KV       KV namespace binding (dashboard → Workers → KV)
 *   - RESEND_API_KEY       (optional) if set, sends welcome email
 *   - RESEND_FROM          (optional) default: "Long Weekend <hello@longweekend.my>"
 *   - ADMIN_TOKEN          (optional) if set, gates /api/subscribers (admin list)
 *
 * KV key layout:
 *   email:<lowercased-email>   → JSON { email, year, al, states, created_at, ip_hash, ua }
 *   ip:<sha256(ip)>:<bucket>  → "1"  (rate limit; bucket = YYYYMMDDHH)
 *   signup_log:<iso-date>     → JSON array of signup events for that UTC day
 */

const RATE_LIMIT_PER_HOUR = 10;   // per IP, per UTC hour
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LEN = 254;
const MAX_STATES = 20;

// SHA-256 of an IP — used for rate limiting without storing the raw IP (PDPA-friendly).
async function sha256Hex(input) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function bucketHour(d = new Date()) {
  return d.toISOString().slice(0, 13).replace(/[-:T]/g, "").slice(0, 10); // YYYYMMDDHH
}
function bucketDay(d = new Date()) {
  return d.toISOString().slice(0, 10); // YYYY-MM-DD
}

function getClientIp(request) {
  // Cloudflare sets CF-Connecting-IP. Fall back to X-Forwarded-For for paranoia.
  return (
    request.headers.get("CF-Connecting-IP") ||
    (request.headers.get("X-Forwarded-For") || "").split(",")[0].trim() ||
    "unknown"
  );
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

// ---------------------------------------------------------------------------
// Storage layer — KV
// ---------------------------------------------------------------------------

async function kvGet(env, key) {
  if (!env.SUBSCRIBERS_KV) return null;
  try {
    return await env.SUBSCRIBERS_KV.get(key, { type: "json" });
  } catch {
    return null;
  }
}

async function kvPut(env, key, value, ttlSeconds) {
  if (!env.SUBSCRIBERS_KV) return false;
  try {
    const opts = ttlSeconds ? { expirationTtl: ttlSeconds } : undefined;
    await env.SUBSCRIBERS_KV.put(key, JSON.stringify(value), opts);
    return true;
  } catch (e) {
    console.error("[subscribe] kv.put failed", key, e);
    return false;
  }
}

async function checkRateLimit(env, ipHash) {
  if (!env.SUBSCRIBERS_KV) return { allowed: true }; // fail-open if no KV
  const key = `ip:${ipHash}:${bucketHour()}`;
  const current = await kvGet(env, key);
  const count = current ? parseInt(current, 10) || 0 : 0;
  if (count >= RATE_LIMIT_PER_HOUR) {
    return { allowed: false, count };
  }
  // Increment; expire after 2 hours.
  await kvPut(env, key, String(count + 1), 7200);
  return { allowed: true, count: count + 1 };
}

async function appendSignupLog(env, record) {
  if (!env.SUBSCRIBERS_KV) return;
  const key = `signup_log:${bucketDay()}`;
  const existing = (await kvGet(env, key)) || [];
  existing.push(record);
  // Cap at 1000 entries per day to bound KV size
  const trimmed = existing.slice(-1000);
  await kvPut(env, key, trimmed, 60 * 60 * 24 * 90); // 90 days
}

// ---------------------------------------------------------------------------
// Email layer — Resend (best-effort)
// ---------------------------------------------------------------------------

function buildWelcomeEmail({ email, year, al, states }) {
  const stateNote = states && states.length
    ? `Including ${states.join(", ")} holidays.`
    : "Federal holidays only — add states above for more combos.";
  const subject = `You're on the longweekend.my list 🎉`;
  const text = `Hi,

Thanks for signing up for longweekend.my reminders.

Plan snapshot:
  Year:  ${year}
  AL:    ${al} days
  ${stateNote}

I'll ping you 60 days before each long weekend so you can book flights / hotels
while they're still cheap.

If you ever want to stop, just reply "unsubscribe" — I'll remove you immediately.

— longweekend.my
`;
  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:24px auto;color:#222;line-height:1.5">
<h2 style="color:#0b6e4f;margin-bottom:4px">You're on the list 🎉</h2>
<p>Thanks for signing up for <strong>longweekend.my</strong> reminders.</p>
<div style="background:#f4f7f5;border:1px solid #d6e4dd;border-radius:8px;padding:14px 18px;margin:18px 0">
  <div><strong>Year</strong> &nbsp; ${year}</div>
  <div><strong>AL entitlement</strong> &nbsp; ${al} days</div>
  <div style="margin-top:8px;color:#555">${stateNote}</div>
</div>
<p>I'll ping you <strong>60 days before each long weekend</strong> so you can book flights / hotels while they're still cheap.</p>
<p style="color:#888;font-size:13px">Reply "unsubscribe" to opt out — I'll remove you immediately.</p>
<p style="margin-top:28px;color:#888;font-size:13px">— longweekend.my</p>
</body></html>`;
  return { subject, text, html };
}

async function sendWelcomeEmail(env, { email, year, al, states }) {
  if (!env.RESEND_API_KEY) {
    console.log("[subscribe] RESEND_API_KEY not set — skipping email");
    return { sent: false, reason: "no_api_key" };
  }
  const from = env.RESEND_FROM || "Long Weekend <hello@longweekend.my>";
  const { subject, text, html } = buildWelcomeEmail({ email, year, al, states });

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ from, to: email, subject, text, html }),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error("[subscribe] resend failed", res.status, errText);
      return { sent: false, reason: `http_${res.status}` };
    }
    const data = await res.json().catch(() => ({}));
    return { sent: true, id: data.id || null };
  } catch (e) {
    console.error("[subscribe] resend threw", e);
    return { sent: false, reason: "exception" };
  }
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export async function onRequestPost(context) {
  const { request, env } = context;

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }

  const email = (body.email || "").toString().trim().toLowerCase();
  const year = (body.year || "2026").toString();
  const al = (body.al || "14").toString();
  const states = Array.isArray(body.states) ? body.states.slice(0, MAX_STATES) : [];
  const honeypot = (body.website || "").toString(); // bots fill this; humans don't see it

  // Honeypot — silently accept-and-drop so bots don't learn the rule
  if (honeypot) {
    console.log("[subscribe] honeypot triggered, dropping");
    return jsonResponse({ ok: true, message: "Subscribed." });
  }

  if (!email || email.length > MAX_EMAIL_LEN || !EMAIL_RE.test(email)) {
    return jsonResponse({ ok: false, error: "Invalid email address" }, 400);
  }
  if (!/^\d{4}$/.test(year) || +year < 2024 || +year > 2035) {
    return jsonResponse({ ok: false, error: "Invalid year" }, 400);
  }
  if (!/^\d{1,2}$/.test(al) || +al < 1 || +al > 30) {
    return jsonResponse({ ok: false, error: "Invalid AL value" }, 400);
  }

  // Rate limit per IP
  const ip = getClientIp(request);
  const ipHash = await sha256Hex(ip);
  const rl = await checkRateLimit(env, ipHash);
  if (!rl.allowed) {
    return jsonResponse(
      { ok: false, error: "Too many requests — try again later." },
      429
    );
  }

  // Idempotent: if already subscribed, don't re-send email or re-write KV
  const existing = await kvGet(env, `email:${email}`);
  if (existing) {
    console.log("[subscribe] duplicate", email);
    return jsonResponse({
      ok: true,
      message: "You're already on the list — see you 60 days before each long weekend!",
    });
  }

  // Persist subscriber
  const ua = request.headers.get("User-Agent") || "";
  const record = {
    email,
    year,
    al,
    states,
    created_at: new Date().toISOString(),
    ip_hash: ipHash,
    ua: ua.slice(0, 200), // truncate; UA strings are bounded
  };
  const wrote = await kvPut(env, `email:${email}`, record);
  await appendSignupLog(env, { email, year, al, states, ts: record.created_at });

  // Send welcome email (best-effort; do not block response).
  // The user message prioritises storage state over email state — we don't
  // want to tell them "check your inbox" if their signup wasn't actually
  // persisted (e.g. KV was unreachable). Better to under-promise.
  const emailResult = await sendWelcomeEmail(env, { email, year, al, states });

  let message;
  if (!wrote) {
    message = "Subscribed (storage degraded — please try again if you don't hear from us).";
  } else if (emailResult.sent) {
    message = "Subscribed. Check your inbox for confirmation.";
  } else {
    message = "Subscribed. You'll get a reminder 60 days before each long weekend.";
  }

  return jsonResponse({ ok: true, message });
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders() });
}

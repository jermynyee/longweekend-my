/**
 * Vercel Serverless Function — POST /api/waitlist
 *
 * Captures waitlist signups from the longweekend.my page.
 *
 * Behavior (in order of priority, all best-effort — never block the response):
 *   1. If DISCORD_WEBHOOK_URL is set, POST a Discord embed to it. This is
 *      the FASTEST path to "see signups in real time" — Jer creates a
 *      Discord channel webhook in 30s (no account, no API key).
 *   2. If RESEND_API_KEY and MAIL_TO are set, send an email to MAIL_TO
 *      with the submission. If either is missing, fall through to logging.
 *   3. If RESEND_API_KEY and MAIL_TO are set AND SEND_AUTORESPOND is not "0",
 *      also send a "thanks for signing up" autoresponder to the user.
 *   4. Always log the submission via console.log so the site owner can grep
 *      Vercel function logs to see all signups (no signup is ever silently lost).
 *   5. Best-effort: a user who submits should always get a success message.
 *
 * Expected request body (JSON):
 *   {
 *     "email":     "user@example.com",   // required
 *     "feedback":  "free text",          // optional (their message to Jer)
 *     "year":      "2026",               // optional
 *     "al":        "14",                 // optional
 *     "states":    ["Selangor", ...],    // optional
 *     "asof":      "2026-06-28",         // optional (URL frozen asof date)
 *     "website":   ""                    // honeypot — must be empty
 *   }
 *
 * Response:
 *   200 { ok: true,  message: "..." }    on success or duplicate
 *   400 { ok: false, error: "..." }      on invalid input
 *   429 { ok: false, error: "..." }      on rate limit
 *
 * Optional env (any combination works — the function gracefully degrades
 * to "Vercel logs only" if NONE are set, but that's not recommended):
 *   - DISCORD_WEBHOOK_URL   Discord channel webhook URL (FASTEST path —
 *                          Jer sees signups as Discord embeds in real time.
 *                          30-second setup: Discord → channel settings →
 *                          Integrations → Webhooks → New webhook → copy URL.
 *                          No account, no API key, no domain verification.)
 *   - RESEND_API_KEY       Resend API key (free at resend.com — 100/day, 3k/mo)
 *   - MAIL_TO              recipient email address (Jer's personal inbox)
 *   - MAIL_FROM            default: "Long Weekend <onboarding@resend.dev>"
 *   - SEND_AUTORESPOND     default: "1" — also send a confirmation to the user
 *
 * The recipient email is intentionally NOT hard-coded. The site owner's
 * personal email must be set as a Vercel env var to keep it out of the
 * source code. See SETUP_LAUNCH.md for the setup. Discord webhook URLs
 * are also kept out of the source — they're set in the Vercel dashboard
 * only.
 */

import { ensureSchema, sql, extractAttribution, hashIp } from './_db.js';
import { jsonResponse, handlePreflight, originAllowed } from './_util.js';

const RATE_LIMIT_PER_HOUR = 10;   // per IP, per UTC hour
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LEN = 254;
const MAX_FEEDBACK_LEN = 2000;
const MAX_STATES = 20;
const DEFAULT_MAIL_FROM = "Long Weekend <onboarding@resend.dev>";

async function sha256Hex(input) {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(input)
  );
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function bucketHour(d = new Date()) {
  return d
    .toISOString()
    .slice(0, 13)
    .replace(/[-:T]/g, "")
    .slice(0, 10);
}

function getClientIp(request) {
  // Vercel sets x-vercel-forwarded-for or x-forwarded-for
  return (
    request.headers.get("x-vercel-forwarded-for") ||
    (request.headers.get("x-forwarded-for") || "").split(",")[0].trim() ||
    request.headers.get("x-real-ip") ||
    "unknown"
  );
}

// ---------------------------------------------------------------------------
// Unsubscribe token (HMAC-SHA256 of email using UNSUBSCRIBE_SECRET)
// ---------------------------------------------------------------------------

async function makeUnsubscribeToken(secret, email) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(email.toLowerCase())
  );
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function buildUnsubscribeUrl(env, email) {
  const secret = env.UNSUBSCRIBE_SECRET;
  if (!secret) return null; // No secret = don't include link (graceful)
  const token = await makeUnsubscribeToken(secret, email);
  const base = env.PUBLIC_SITE_URL || "https://longweekend.my";
  return `${base}/api/unsubscribe?email=${encodeURIComponent(email)}&token=${token}`;
}

// ---------------------------------------------------------------------------
// Discord webhook layer — fastest path to "see signups in real time"
// ---------------------------------------------------------------------------

async function sendDiscord(env, payload) {
  if (!env.DISCORD_WEBHOOK_URL) return { sent: false, reason: "no_webhook" };
  const { email, feedback, year, al, states, asof, ts, ipHash } = payload;
  const stateList = states && states.length
    ? states.join(", ")
    : "(federal only)";
  const fields = [
    { name: "📧 Email", value: email ? `[${email}](mailto:${email})` : "?", inline: false },
    { name: "📅 Year", value: year || "?", inline: true },
    { name: "🎫 AL", value: al || "?", inline: true },
    { name: "🗺️ States", value: stateList, inline: false },
    { name: "🕐 As-of", value: asof || "?", inline: true },
  ];
  if (feedback) {
    // Truncate to Discord's 1024-char field limit
    const trimmed = feedback.length > 1000
      ? feedback.slice(0, 1000) + "…"
      : feedback;
    fields.push({ name: "💬 Feedback", value: trimmed, inline: false });
  }
  const embed = {
    title: "🗓️ New waitlist signup",
    color: 0x0F766E,  // teal-700 — matches site palette
    fields,
    footer: { text: `longweekend.my · ${ts} · ip:${(ipHash || "").slice(0, 8)}` },
    timestamp: ts,
  };
  const body = {
    username: "longweekend.my",
    embeds: [embed],
  };
  try {
    const res = await fetch(env.DISCORD_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error("[waitlist] discord webhook failed", res.status, errText);
      return { sent: false, reason: `http_${res.status}` };
    }
    return { sent: true };
  } catch (e) {
    console.error("[waitlist] discord webhook threw", e);
    return { sent: false, reason: "exception" };
  }
}

// ---------------------------------------------------------------------------
// Email layer (Resend) — best-effort
// ---------------------------------------------------------------------------

async function sendEmail(env, { to, from, subject, text, html, replyTo }) {
  if (!env.RESEND_API_KEY) return { sent: false, reason: "no_api_key" };
  const headers = {
    Authorization: `Bearer ${env.RESEND_API_KEY}`,
    "Content-Type": "application/json",
  };
  const body = { from, to, subject, text, html };
  if (replyTo) body.reply_to = replyTo;
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error("[waitlist] resend failed", res.status, errText);
      return { sent: false, reason: `http_${res.status}` };
    }
    const data = await res.json().catch(() => ({}));
    return { sent: true, id: data.id || null };
  } catch (e) {
    console.error("[waitlist] resend threw", e);
    return { sent: false, reason: "exception" };
  }
}

function buildJerEmail({ email, feedback, year, al, states, asof, ts }) {
  const lines = [
    `New longweekend.my waitlist signup:`,
    ``,
    `  Email:     ${email}`,
    `  Year:      ${year || "?"}`,
    `  AL:        ${al || "?"}`,
    `  States:    ${(states && states.length) ? states.join(", ") : "(federal only)"}`,
    `  As-of:     ${asof || "?"}`,
    `  Submitted: ${ts}`,
  ];
  if (feedback) lines.push("", "Feedback:", feedback);
  lines.push("", "— via longweekend.my/api/waitlist");
  const text = lines.join("\n");
  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:24px auto;color:#222;line-height:1.5">
<h2 style="color:#0b6e4f;margin-bottom:8px">New waitlist signup</h2>
<table style="border-collapse:collapse;font-size:14px">
  <tr><td style="padding:3px 12px 3px 0;color:#666">Email</td><td><strong>${escapeHtml(email)}</strong></td></tr>
  <tr><td style="padding:3px 12px 3px 0;color:#666">Year</td><td>${escapeHtml(year || "?")}</td></tr>
  <tr><td style="padding:3px 12px 3px 0;color:#666">AL</td><td>${escapeHtml(String(al || "?"))}</td></tr>
  <tr><td style="padding:3px 12px 3px 0;color:#666">States</td><td>${escapeHtml((states || []).join(", ") || "(federal only)")}</td></tr>
  <tr><td style="padding:3px 12px 3px 0;color:#666">As-of</td><td>${escapeHtml(asof || "?")}</td></tr>
  <tr><td style="padding:3px 12px 3px 0;color:#666">Submitted</td><td>${escapeHtml(ts)}</td></tr>
</table>
${feedback ? `<h3 style="margin-top:18px;color:#0b6e4f">Feedback</h3><pre style="background:#f4f7f5;border:1px solid #d6e4dd;border-radius:8px;padding:12px;font-family:inherit;white-space:pre-wrap;margin:0">${escapeHtml(feedback)}</pre>` : ""}
<p style="margin-top:18px;color:#888;font-size:12px">— via longweekend.my/api/waitlist</p>
</body></html>`;
  return { subject: `[longweekend.my] New signup: ${email}`, text, html };
}

function buildUserEmail({ email, year, al, states, unsubscribeUrl }) {
  const stateNote = states && states.length
    ? `Including ${states.join(", ")} holidays.`
    : "Federal holidays only — add states above for more combos.";
  const subject = `You're on the longweekend.my list 🎉`;
  // unsubscribeUrl is the full https://longweekend.my/api/unsubscribe?email=...&token=...
  // link with HMAC token, or null if UNSUBSCRIBE_SECRET is not set (dev mode).
  const unsubLink = unsubscribeUrl || null;
  const text = `Hi,

Thanks for signing up for longweekend.my — a tiny Malaysian tool that tells you the most efficient way to spend your annual leave to maximise long weekends in ${year || "2026"}.

Plan snapshot you saved:
  Year:  ${year || "?"}
  AL:    ${al || "?"} days
  ${stateNote}

I'll only ping you for major updates (e.g. 2028 calendar when JAKIM publishes, new features that help you plan leave). No spam, no selling your data.

${unsubLink
  ? `Unsubscribe any time: ${unsubLink}`
  : `Reply to this email any time — I read everything.`}

— longweekend.my
`;
  const html = `<!doctype html>
<p>Thanks for signing up for <strong>longweekend.my</strong> — a tiny Malaysian tool that tells you the most efficient way to spend your annual leave to maximise long weekends in <strong>${escapeHtml(String(year || "?"))}</strong>.</p>
<div style="background:#f4f7f5;border:1px solid #d6e4dd;border-radius:8px;padding:14px 18px;margin:18px 0">
  <div><strong>Year</strong> &nbsp; ${escapeHtml(String(year || "?"))}</div>
  <div><strong>AL entitlement</strong> &nbsp; ${escapeHtml(String(al || "?"))} days</div>
  <div style="margin-top:8px;color:#555">${escapeHtml(stateNote)}</div>
</div>
<p>I'll only ping you for major updates (e.g. new year calendar when JAKIM publishes, new features that help you plan leave). <strong>No spam, no selling your data.</strong></p>
${unsubLink
  ? `<p style="margin-top:18px;font-size:13px;color:#888"><a href="${escapeHtml(unsubLink)}" style="color:#888">Unsubscribe</a> — one click, no questions.</p>`
  : `<p>Reply to this email any time — I read everything.</p>`}
<p style="margin-top:28px;color:#888;font-size:13px">longweekend.my</p>
</body></html>`;
  return { subject, text, html };
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export async function POST(request) {
  // Socrates M4 fix: reject cross-origin POSTs from untrusted sites. Same-origin
  // (longweekend.my) + local dev (localhost:8765) still work; browsers from
  // other domains get 403. Server-side curl/fetch (no Origin header) passes.
  if (!originAllowed(request)) {
    return jsonResponse({ ok: false, error: "Cross-origin POST not allowed" }, 403);
  }
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }

  const email = (body.email || "").toString().trim().toLowerCase();
  const feedback = (body.feedback || "").toString().slice(0, MAX_FEEDBACK_LEN).trim();
  const year = (body.year || "").toString();
  const al = (body.al || "").toString();
  const states = Array.isArray(body.states)
    ? body.states.slice(0, MAX_STATES).map((s) => String(s))
    : [];
  const asof = (body.asof || "").toString();
  const honeypot = (body.website || "").toString();

  // Honeypot — silently accept-and-drop so bots don't learn the rule
  if (honeypot) {
    console.log("[waitlist] honeypot triggered, dropping");
    return jsonResponse({ ok: true, message: "Subscribed." });
  }

  if (!email || email.length > MAX_EMAIL_LEN || !EMAIL_RE.test(email)) {
    return jsonResponse({ ok: false, error: "Invalid email address" }, 400);
  }
  if (year && (!/^\d{4}$/.test(year) || +year < 2024 || +year > 2035)) {
    return jsonResponse({ ok: false, error: "Invalid year" }, 400);
  }
  if (al && (!/^\d{1,2}$/.test(al) || +al < 1 || +al > 30)) {
    return jsonResponse({ ok: false, error: "Invalid AL value" }, 400);
  }

  // Rate limit per IP (in-memory; resets on cold start but that's fine for MVP)
  const ip = getClientIp(request);
  const ipHash = await sha256Hex(ip);
  const hourBucket = bucketHour();
  const rlKey = `rl:${ipHash}:${hourBucket}`;
  // Vercel KV not assumed; use a global Map (per-instance, OK for MVP)
  globalThis.__lw_rl ||= new Map();
  const rl = globalThis.__lw_rl;
  const count = (rl.get(rlKey) || 0) + 1;
  rl.set(rlKey, count);
  // Garbage-collect old buckets (cheap)
  if (rl.size > 1000) {
    for (const k of rl.keys()) if (!k.endsWith(hourBucket)) rl.delete(k);
  }
  if (count > RATE_LIMIT_PER_HOUR) {
    return jsonResponse(
      { ok: false, error: "Too many requests — try again later." },
      429
    );
  }

  // Log the submission (always — Vercel dashboard → Logs shows these)
  const ts = new Date().toISOString();
  const ua = (request.headers.get("User-Agent") || "").slice(0, 200);
  console.log(
    JSON.stringify({
      kind: "waitlist_signup",
      email,
      feedback_len: feedback.length,
      year,
      al,
      states,
      asof,
      ts,
      ip_hash: ipHash,
      ua,
    })
  );

  // Persist to Neon Postgres (best-effort — DB outage must not block the
  // Discord/Resend flows or the response to the user). Schema is created
  // on first call so we don't need a separate migration step.
  if (process.env.POSTGRES_URL) {
    try {
      const sch = await ensureSchema();
      if (sch.ok) {
        const attr = extractAttribution(body);
        await sql()`INSERT INTO signups (
          email, year, al, states, asof, feedback_len, feedback,
          utm_source, utm_medium, utm_campaign, utm_term, utm_content,
          ref_host, user_agent, ip_hash
        ) VALUES (
          ${email},
          ${year ? +year : null},
          ${al ? +al : null},
          ${states},
          ${asof || null},
          ${feedback.length},
          ${feedback ? feedback.slice(0, 1000) : null},
          ${attr.utm_source}, ${attr.utm_medium}, ${attr.utm_campaign},
          ${attr.utm_term}, ${attr.utm_content},
          ${attr.ref_host},
          ${ua},
          ${ipHash}
        )`;
      }
    } catch (e) {
      console.error("[waitlist] db insert failed (non-blocking):", e.message);
    }
  }

  // Fan out to all configured channels. Each is independent and best-effort:
  // failure of one doesn't block the others, and none block the response.
  const env = process.env;
  const mailTo = env.MAIL_TO;
  const mailFrom = env.MAIL_FROM || DEFAULT_MAIL_FROM;
  const sendAuto = env.SEND_AUTORESPOND !== "0";

  // Channel 1: Discord webhook (FASTEST path — see signups in real time).
  // Runs unconditionally if DISCORD_WEBHOOK_URL is set.
  const discordResult = await sendDiscord(env, {
    email, feedback, year, al, states, asof, ts, ipHash,
  });

  // Channel 2: Resend email to the site owner (and optionally to the user).
  // MAIL_TO is intentionally NOT defaulted — the function only sends
  // when both RESEND_API_KEY and MAIL_TO are set in the Vercel env.
  let jerResult = { sent: false, reason: "no_api_key" };
  let userResult = { sent: false, reason: "skipped" };

  if (env.RESEND_API_KEY && mailTo) {
    // 1. Notify Jer
    const jerEmail = buildJerEmail({ email, feedback, year, al, states, asof, ts });
    jerResult = await sendEmail(env, {
      to: mailTo,
      from: mailFrom,
      subject: jerEmail.subject,
      text: jerEmail.text,
      html: jerEmail.html,
      replyTo: email,
    });
    // 2. Optionally thank the user
    if (sendAuto) {
      const unsubscribeUrl = await buildUnsubscribeUrl(env, email);
      const userEmail = buildUserEmail({ email, year, al, states, unsubscribeUrl });
      userResult = await sendEmail(env, {
        to: email,
        from: mailFrom,
        subject: userEmail.subject,
        text: userEmail.text,
        html: userEmail.html,
      });
    }
  } else {
    const missing=[];
    if(!env.RESEND_API_KEY)missing.push('RESEND_API_KEY');
    if(!mailTo)missing.push('MAIL_TO');
    console.warn(
      `[waitlist] Submission logged to Vercel function logs only — ` +
      `email not forwarded (missing env: ${missing.join(', ')}). ` +
      `Set the env var(s) in the Vercel project to forward submissions.`
    );
  }

  // Success message: at least one channel worked OR none configured (log-only)
  const anyNotified = discordResult.sent || jerResult.sent;
  const message = anyNotified || discordResult.reason === "no_webhook" && jerResult.reason === "no_api_key"
    ? "Thanks! You're on the list."
    : "Subscribed (notification failed — try again if you don't hear from us).";

  return jsonResponse({
    ok: true,
    message,
    discord: discordResult,
    notification: jerResult,
    autoresponder: userResult,
  });
}

export async function OPTIONS(request) {
  return handlePreflight(request, { methods: "POST, OPTIONS" });
}

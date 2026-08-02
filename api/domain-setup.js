/**
 * Vercel Serverless Function — GET /api/domain-setup
 *
 * Returns the DNS records needed to verify longweekend.my at Resend, and the
 * current verification status. Used during the one-time DNS-setup phase:
 *   1. Admin visits /api/domain-setup?action=create to register longweekend.my
 *      with Resend (idempotent — safe to call repeatedly; returns existing
 *      domain if already registered).
 *   2. Admin pastes the returned records into Exabytes DNS.
 *   3. Admin calls /api/domain-setup?action=verify to check propagation.
 *   4. Once verified, admin updates MAIL_FROM on Vercel.
 *
 * Auth: requires ?key=ADMIN_KEY (same key used for /admin/attribution).
 *
 * Response (action=create|verify|status):
 *   {
 *     ok: true,
 *     domain: { id, name, status, region, created_at },
 *     records: [
 *       { type, name, value, ttl?, priority? },
 *       ...
 *     ],
 *     verification: {
 *       dns_verified, spf_verified, dkim_verified,
 *       last_check_at, last_check_error?
 *     }
 *   }
 *
 * Env:
 *   - RESEND_ADMIN_KEY (preferred; full-access key from Resend dashboard)
 *   - RESEND_API_KEY   (fallback; if it's full-access, used for both)
 *   - ADMIN_KEY        (required to call this endpoint)
 */
import { jsonResponse } from "./_util.js";

const DOMAIN_NAME = "longweekend.my";

function checkAdmin(url) {
  const supplied = url.searchParams.get("key");
  const expected = process.env.ADMIN_KEY;
  if (!expected) return { ok: false, status: 503, error: "ADMIN_KEY not set" };
  if (!supplied || supplied !== expected) {
    return { ok: false, status: 401, error: "Bad or missing ?key=" };
  }
  return { ok: true };
}

async function resendFetch(path, init = {}) {
  // Prefer the full-access admin key (separate from the send-only RESEND_API_KEY
  // so a leaked send-key can't be used to add/remove domains). Falls back to
  // RESEND_API_KEY for setups that haven't provisioned a separate admin key.
  const key = process.env.RESEND_ADMIN_KEY || process.env.RESEND_API_KEY;
  if (!key) throw new Error("RESEND_ADMIN_KEY (or RESEND_API_KEY) not set");
  const res = await fetch(`https://api.resend.com${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); } catch { body = { raw: text }; }
  return { status: res.status, ok: res.ok, body };
}

async function listDomains() {
  const r = await resendFetch("/domains");
  if (!r.ok) throw new Error(`list domains failed: ${r.status} ${JSON.stringify(r.body)}`);
  const all = r.body?.data || [];
  return all.find((d) => d.name === DOMAIN_NAME) || null;
}

export async function GET(request) {
  const url = new URL(request.url);
  const auth = checkAdmin(url);
  if (!auth.ok) return jsonResponse({ ok: false, error: auth.error }, auth.status);

  const action = (url.searchParams.get("action") || "status").toLowerCase();

  try {
    if (action === "create") {
      let existing = await listDomains();
      let domain;
      if (existing) {
        domain = existing;
      } else {
        const created = await resendFetch("/domains", {
          method: "POST",
          body: JSON.stringify({ name: DOMAIN_NAME, region: "ap-southeast-1" }),
        });
        if (!created.ok) {
          return jsonResponse(
            { ok: false, error: "resend_create_failed", detail: created.body },
            502
          );
        }
        domain = created.body;
      }
      return jsonResponse({ ok: true, action, domain });
    }

    if (action === "verify") {
      const domain = await listDomains();
      if (!domain) {
        return jsonResponse(
          {
            ok: false,
            error: "domain_not_found",
            hint: "Call ?action=create first to register the domain at Resend.",
          },
          404
        );
      }
      const r = await resendFetch(`/domains/${domain.id}/verify`, { method: "POST" });
      return jsonResponse({
        ok: r.ok,
        action,
        domain: { id: domain.id, name: domain.name, status: domain.status },
        verify_response: r.body,
      });
    }

    // status (default) — Resend sometimes lags populating the records array
    // on the list endpoint; fetch the individual domain record too.
    let domain = await listDomains();
    if (domain?.id) {
      const detail = await resendFetch(`/domains/${domain.id}`);
      if (detail.ok && detail.body?.records) {
        domain = { ...domain, ...detail.body, records: detail.body.records };
      }
    }
    if (!domain) {
      return jsonResponse({
        ok: true,
        action,
        registered: false,
        hint: "Call ?action=create to register longweekend.my at Resend.",
      });
    }
    return jsonResponse({
      ok: true,
      action,
      registered: true,
      domain: {
        id: domain.id,
        name: domain.name,
        status: domain.status,
        region: domain.region,
        created_at: domain.created_at,
      },
      records: domain.records || [],
      verification: {
        dns_verified: !!domain.dns_verified,
        spf_verified: !!domain.spf_verified,
        dkim_verified: !!domain.dkim_verified,
        last_check_at: domain.last_check_at || null,
      },
    });
  } catch (e) {
    return jsonResponse({ ok: false, error: "exception", message: e.message }, 500);
  }
}

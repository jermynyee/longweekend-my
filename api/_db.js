/**
 * Shared database helper for longweekend.my serverless functions.
 *
 * Uses Neon's serverless driver (which is what Vercel Postgres is now
 * backed by — `@vercel/postgres` is deprecated and points to this).
 *
 * Required env vars (set automatically by the Vercel Neon integration):
 *   - POSTGRES_URL            pooled connection (use for queries)
 *   - POSTGRES_URL_NON_POOLING direct connection (use for migrations)
 *
 * If POSTGRES_URL is missing, all helpers throw a clear error so the
 * caller can degrade gracefully (e.g. the waitlist API still works
 * via Discord/Resend even if the DB is down).
 */

import { neon, neonConfig } from '@neondatabase/serverless';

// Use the pooled connection string. Neon auto-detects the right driver.
// IMPORTANT: use the HTTP-based `neon()` tag for all queries, NOT the
// websocket-based `Pool`. Each `Pool.connect()` acquires a "permit" from
// Neon's connection slot allocator (default 10 permits on the free tier)
// and under concurrent traffic — viral Threads day, parallel cron runs —
// those permits saturate, returning:
//   "Failed to acquire permit to connect to the database.
//    Too many database connection attempts are currently ongoing."
// The HTTP driver (`neon()`) goes through PgBouncer pooling instead and
// does not consume connection permits. Use it for every query.
function getConnectionString() {
  const url = process.env.POSTGRES_URL;
  if (!url) {
    throw new Error(
      'POSTGRES_URL is not set. Provision Neon Postgres in the Vercel ' +
      "Storage tab, or skip the DB and rely on Vercel function logs."
    );
  }
  return url;
}

// Cache the SQL tag across warm invocations.
let _sql = null;

export function sql() {
  if (!_sql) {
    _sql = neon(getConnectionString());
  }
  return _sql;
}

// `pool()` is intentionally removed. If you ever need transactions, use the
// HTTP driver's `.transaction()` helper instead (also doesn't consume
// permits) — but the current codebase has no transaction needs.

/**
 * Hash an IP for privacy. We never store raw IPs.
 * Uses Web Crypto API (available in Vercel Edge + Node 18+).
 */
export async function hashIp(ip) {
  if (!ip) return null;
  try {
    const buf = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(ip)
    );
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    return null;
  }
}

/**
 * Extract UTM params from the request body. The front-end flattens
 * attribution into the top-level payload (so a pageview event arrives as
 * `{name: 'pageview', utm_source: 'reddit', path: '/'}`, NOT
 * `{name: 'pageview', attribution: {utm_source: 'reddit'}}`).
 *
 * We also accept the nested form as a fallback for any older client that
 * still wraps it — never break an existing caller.
 */
export function extractAttribution(body) {
  const a = (body && body.attribution && typeof body.attribution === 'object')
    ? body.attribution
    : (body || {});
  return {
    utm_source: a.utm_source || null,
    utm_medium: a.utm_medium || null,
    utm_campaign: a.utm_campaign || null,
    utm_term: a.utm_term || null,
    utm_content: a.utm_content || null,
    ref_host: a.refHost || a.ref_host || null,
  };
}

/**
 * Create the schema if it doesn't exist. Idempotent — safe to call on
 * every cold start. Catches errors so a broken DB never takes down the
 * public site.
 *
 * Rate-limited: only runs the first time it's called per Vercel function
 * instance. Pass `{force: true}` to bypass — useful for one-shot
 * migration scripts. This avoids the death spiral where every cold start
 * runs 6+ ALTER statements, each consuming a Neon connection permit,
 * under concurrent traffic.
 */
let _schemaEnsured = false;
let _schemaEnsuring = null; // de-dupe concurrent calls within same instance

export async function ensureSchema({ force = false } = {}) {
  if (_schemaEnsured && !force) return { ok: true, cached: true };
  if (_schemaEnsuring && !force) return _schemaEnsuring;
  _schemaEnsuring = (async () => {
    try {
      await sql()`CREATE TABLE IF NOT EXISTS signups (
        id            BIGSERIAL PRIMARY KEY,
        email         TEXT NOT NULL,
        email_domain  TEXT GENERATED ALWAYS AS (split_part(email, '@', 2)) STORED,
        year          INTEGER,
        al            INTEGER,
        states        TEXT[],
        asof          TEXT,
        feedback_len  INTEGER DEFAULT 0,
        feedback      TEXT,
        utm_source    TEXT,
        utm_medium    TEXT,
        utm_campaign  TEXT,
        utm_term      TEXT,
        utm_content   TEXT,
        ref_host      TEXT,
        user_agent    TEXT,
        ip_hash       TEXT,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
      )`;
      await sql()`CREATE INDEX IF NOT EXISTS signups_created_at_idx ON signups (created_at DESC)`;
      await sql()`CREATE INDEX IF NOT EXISTS signups_utm_source_idx ON signups (utm_source)`;
      await sql()`CREATE INDEX IF NOT EXISTS signups_email_domain_idx ON signups (email_domain)`;
      await sql()`CREATE INDEX IF NOT EXISTS signups_email_idx ON signups (email)`;
      // Unsubscribe support: track when a user opted out so future batch
      // sends (the planned reminder cron) skip them. Created as a separate
      // statement so it can be re-run on existing tables without erroring.
      // Store the user's raw feedback text (added 9 Oct 26 — previously only
      // feedback_len was kept, so messages were unrecoverable after the
      // Discord/email notification). Separate statement so it re-runs safely.
      await sql()`ALTER TABLE signups ADD COLUMN IF NOT EXISTS feedback TEXT`;
      await sql()`ALTER TABLE signups ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMPTZ`;
      await sql()`CREATE INDEX IF NOT EXISTS signups_unsubscribed_idx ON signups (unsubscribed_at) WHERE unsubscribed_at IS NULL`;

      await sql()`CREATE TABLE IF NOT EXISTS events (
        id            BIGSERIAL PRIMARY KEY,
        name          TEXT NOT NULL,
        partner       TEXT,
        dest          TEXT,
        days_off      INTEGER,
        al            INTEGER,
        scope         TEXT,
        idx           INTEGER,
        utm_source    TEXT,
        utm_medium    TEXT,
        utm_campaign  TEXT,
        ref_host      TEXT,
        user_agent    TEXT,
        ip_hash       TEXT,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
      )`;
      await sql()`CREATE INDEX IF NOT EXISTS events_name_idx ON events (name)`;
      await sql()`CREATE INDEX IF NOT EXISTS events_created_at_idx ON events (created_at DESC)`;
      await sql()`CREATE INDEX IF NOT EXISTS events_utm_source_idx ON events (utm_source)`;
      await sql()`CREATE INDEX IF NOT EXISTS events_partner_idx ON events (partner)`;
      // Geo columns from Vercel's x-vercel-ip-* headers (free, server-side).
      // Added as separate ALTER statements so the migration is safe to re-run
      // on existing tables without erroring — same pattern as unsubscribed_at.
      await sql()`ALTER TABLE events ADD COLUMN IF NOT EXISTS geo_country TEXT`;
      await sql()`ALTER TABLE events ADD COLUMN IF NOT EXISTS geo_region TEXT`;
      await sql()`ALTER TABLE events ADD COLUMN IF NOT EXISTS geo_city TEXT`;
      await sql()`CREATE INDEX IF NOT EXISTS events_geo_country_idx ON events (geo_country)`;

      // === Fare alerts schema (added 19 Jul 2026, ready for build) ===
      await sql()`CREATE TABLE IF NOT EXISTS fare_alert_subscribers (
        id              BIGSERIAL PRIMARY KEY,
        email           TEXT NOT NULL UNIQUE,
        origin          TEXT NOT NULL,
        destinations    TEXT[] NOT NULL,
        frequency       TEXT NOT NULL DEFAULT 'weekly',
        tier            TEXT NOT NULL DEFAULT 'free',
        is_active       BOOLEAN NOT NULL DEFAULT true,
        utm_source      TEXT,
        ref_host        TEXT,
        ip_hash         TEXT,
        user_agent      TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_sent_at    TIMESTAMPTZ,
        unsubscribed_at TIMESTAMPTZ
      )`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_alert_subs_email_idx ON fare_alert_subscribers (email)`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_alert_subs_active_idx ON fare_alert_subscribers (is_active, tier)`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_alert_subs_origin_idx ON fare_alert_subscribers (origin)`;

      await sql()`CREATE TABLE IF NOT EXISTS fare_snapshots (
        id              BIGSERIAL PRIMARY KEY,
        origin          TEXT NOT NULL,
        destination     TEXT NOT NULL,
        departure_date  DATE NOT NULL,
        return_date     DATE,
        price           NUMERIC(10,2) NOT NULL,
        currency        TEXT NOT NULL DEFAULT 'MYR',
        airline         TEXT,
        layovers        INTEGER DEFAULT 0,
        duration_mins   INTEGER,
        booking_url     TEXT,
        source          TEXT NOT NULL,
        snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT now()
      )`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_snapshots_route_date_idx ON fare_snapshots (origin, destination, departure_date)`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_snapshots_snapshot_at_idx ON fare_snapshots (snapshot_at DESC)`;

      await sql()`CREATE TABLE IF NOT EXISTS fare_alert_sends (
        id              BIGSERIAL PRIMARY KEY,
        subscriber_id   BIGINT NOT NULL REFERENCES fare_alert_subscribers(id),
        send_type       TEXT NOT NULL,
        fare_snapshot_ids BIGINT[],
        email_subject   TEXT,
        email_status    TEXT,
        resend_id       TEXT,
        sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
      )`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_alert_sends_subscriber_idx ON fare_alert_sends (subscriber_id)`;
      await sql()`CREATE INDEX IF NOT EXISTS fare_alert_sends_sent_at_idx ON fare_alert_sends (sent_at DESC)`;

      return { ok: true };
    } catch (e) {
      console.error('[db] ensureSchema failed:', e.message);
      return { ok: false, error: e.message };
    } finally {
      // Mark as ensured even on failure — we don't want to retry-storm
      // a broken schema on every cold start. If the user needs a real
      // retry, pass `{force: true}` from a one-shot migration script.
      _schemaEnsured = true;
    }
  })();
  try {
    return await _schemaEnsuring;
  } finally {
    _schemaEnsuring = null;
  }
}
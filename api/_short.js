/**
 * Short-link helper for longweekend.my share attribution.
 *
 * Generates 6-character URL-safe codes (base62), stores them in the
 * `short_links` table, and looks them up. The /r/[code] redirect endpoint
 * and the /api/shorten endpoint both use this module.
 *
 * Schema is created on demand via ensureSchema() — same pattern as the
 * other DB-backed endpoints. No startup cost if the shortener is unused.
 */

import { sql, ensureSchema } from './_db.js';

const ALPHABET = 'abcdefghijkmnpqrstuvwxyz23456789'; // omit 0/o/1/l for clarity
const CODE_LEN = 6;

function randomCode() {
  let out = '';
  for (let i = 0; i < CODE_LEN; i++) {
    out += ALPHABET[Math.floor(Math.random() * ALPHABET.length)];
  }
  return out;
}

/**
 * Idempotent schema setup for the short_links table. Called from both
 * /api/shorten and /r/[code] on cold start so we don't need a separate
 * migration step.
 */
export async function ensureShortLinksSchema() {
  await ensureSchema(); // base tables first
  try {
    await sql()`CREATE TABLE IF NOT EXISTS short_links (
      id            BIGSERIAL PRIMARY KEY,
      code          TEXT UNIQUE NOT NULL,
      target_url    TEXT NOT NULL,
      source        TEXT,            -- 'share', 'friend', 'manual', etc.
      stretch_idx   INTEGER,         -- if the share is for a specific stretch
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_clicked  TIMESTAMPTZ,
      click_count   INTEGER NOT NULL DEFAULT 0
    )`;
    await sql()`CREATE INDEX IF NOT EXISTS short_links_code_idx ON short_links (code)`;
    await sql()`CREATE INDEX IF NOT EXISTS short_links_source_idx ON short_links (source)`;
    return { ok: true };
  } catch (e) {
    console.error('[short] ensureShortLinksSchema failed:', e.message);
    return { ok: false, error: e.message };
  }
}

/**
 * Create a short link for the given target URL. Generates a random code,
 * checks for collisions (rare with 36^6 = 2.2B possible codes), and inserts.
 *
 * Returns { ok, code, targetUrl } or { ok: false, error }.
 */
export async function createShortLink({ targetUrl, source = 'share', stretchIdx = null }) {
  if (!targetUrl || typeof targetUrl !== 'string') {
    return { ok: false, error: 'targetUrl required' };
  }
  // Cap target URL length to avoid abuse
  if (targetUrl.length > 2048) {
    return { ok: false, error: 'targetUrl too long' };
  }
  await ensureShortLinksSchema();

  // Try up to 5 times in the (extremely unlikely) event of a collision
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = randomCode();
    try {
      const rows = await sql()`
        INSERT INTO short_links (code, target_url, source, stretch_idx)
        VALUES (${code}, ${targetUrl}, ${source}, ${stretchIdx})
        ON CONFLICT (code) DO NOTHING
        RETURNING code
      `;
      if (rows && rows.length > 0) {
        return { ok: true, code: rows[0].code, targetUrl };
      }
      // Collision — try again
    } catch (e) {
      console.error('[short] createShortLink insert failed:', e.message);
      return { ok: false, error: e.message };
    }
  }
  return { ok: false, error: 'could not generate unique code after 5 attempts' };
}

/**
 * Look up a short code and increment the click counter atomically.
 * Returns { ok, code, targetUrl, source, stretchIdx } or { ok: false }.
 *
 * Atomic increment: UPDATE ... RETURNING gives us the new value in one
 * round trip, so concurrent clicks don't lose counts.
 */
export async function resolveAndCount(code) {
  if (!code || typeof code !== 'string' || code.length > 16) {
    return { ok: false, error: 'invalid code' };
  }
  await ensureShortLinksSchema();
  try {
    const rows = await sql()`
      UPDATE short_links
      SET click_count = click_count + 1,
          last_clicked = now()
      WHERE code = ${code.toLowerCase()}
      RETURNING code, target_url, source, stretch_idx, click_count
    `;
    if (!rows || rows.length === 0) {
      return { ok: false, error: 'not_found' };
    }
    return {
      ok: true,
      code: rows[0].code,
      targetUrl: rows[0].target_url,
      source: rows[0].source,
      stretchIdx: rows[0].stretch_idx,
      clickCount: rows[0].click_count,
    };
  } catch (e) {
    console.error('[short] resolveAndCount failed:', e.message);
    return { ok: false, error: e.message };
  }
}

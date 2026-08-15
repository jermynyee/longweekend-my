/**
 * Vercel Serverless Function — GET /api/holidays.json
 *
 * Machine-readable holiday data for AI crawlers, researchers, and the JSON-LD
 * pipeline. Mirrors the data in holidays.json (the build-time source) but
 * exposed as a stable, always-fresh endpoint.
 *
 * Response shape: see end of file (FEDERAL_HOLIDAYS_2026 constant is illustrative).
 *
 * Cache-Control: 1 hour. CORS: open (public data).
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const HOLIDAYS_PATH = join(__dirname, '..', 'holidays.json');

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'public, max-age=3600',
  'Content-Type': 'application/json; charset=utf-8',
};

function buildResponse() {
  const raw = readFileSync(HOLIDAYS_PATH, 'utf-8');
  const holidays = JSON.parse(raw);

  const federal = {};
  const state = {};
  const statesCount = {};

  for (const year of Object.keys(holidays)) {
    const fedList = [];
    const stateByName = {};

    for (const h of holidays[year]) {
      const entry = {
        date: h.date,
        name: h.name,
        day_of_week: h.day_of_week,
      };

      if (h.type === 'federal') {
        fedList.push(entry);
      } else if (h.type === 'state' && h.state) {
        if (!stateByName[h.state]) stateByName[h.state] = [];
        stateByName[h.state].push(entry);
        statesCount[h.state] = (statesCount[h.state] || 0) + 1;
      }
    }

    // Dedupe federal by base name (primary + replacement day treated as same)
    const seen = new Set();
    const deduped = [];
    for (const h of fedList) {
      const name = h.name.replace(' Holiday', '');
      if (seen.has(name)) continue;
      seen.add(name);
      deduped.push({ ...h, name });
    }

    federal[year] = deduped;
    state[year] = stateByName;
  }

  const today = new Date().toISOString().slice(0, 10);

  return {
    version: today,
    country: 'Malaysia',
    source: 'https://longweekend.my',
    author: 'Jermyn Yee <hello@longweekend.my>',
    data_source_citation:
      'Akta Hari Kelepasan Persekutuan 1951, mirrored at publicholidays.com.my (verified Jul 2026)',
    last_updated: today,
    total_federal_holidays_per_year: 14,
    federal_holidays: federal,
    state_holidays: state,
    states_with_extra_holidays: statesCount,
  };
}

export default function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(200).end();
  }

  // HEAD is a bodyless GET — crawlers that probe before fetching should see
  // the same headers + 200 + Content-Length, not 405. The handler streams
  // JSON for GET; Vercel/Node strip the body automatically for HEAD because
  // we never call res.json() on this branch.
  //
  // 2026-08-15 patch: CORS pre-flight support added so HEAD-first
  // probes (sitemap crawlers, AI ingestion bots) succeed.
  if (req.method === 'HEAD') {
    Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));
    res.setHeader('Content-Length', '0');
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const data = buildResponse();
    Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(200).json(data);
  } catch (e) {
    console.error('[holidays.json] failed:', e.message);
    Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(500).json({ error: 'Internal server error' });
  }
}

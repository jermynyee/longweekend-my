-- Schema for the longweekend.my attribution dashboard.
-- Run this once against your Neon Postgres database to set up the tables.
-- The waitlist endpoint will create tables on first use, but you can run
-- this manually to verify the schema.

-- Waitlist signups — one row per email signup.
-- Stores the full email (server-side only — never sent to Vercel Analytics
-- as a property) plus the attribution context that came with the request.
CREATE TABLE IF NOT EXISTS signups (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT NOT NULL,
  email_domain  TEXT GENERATED ALWAYS AS (split_part(email, '@', 2)) STORED,
  year          INTEGER,
  al            INTEGER,
  states        TEXT[],          -- { "Selangor", "Penang", ... } or empty
  asof          TEXT,            -- YYYY-MM-DD
  feedback_len  INTEGER DEFAULT 0,
  utm_source    TEXT,
  utm_medium    TEXT,
  utm_campaign  TEXT,
  utm_term      TEXT,
  utm_content   TEXT,
  ref_host      TEXT,            -- external referrer host (no path, no query)
  user_agent    TEXT,
  ip_hash       TEXT,            -- sha256 of client IP (privacy-safe)
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Useful indexes for the attribution dashboard's most common queries.
CREATE INDEX IF NOT EXISTS signups_created_at_idx ON signups (created_at DESC);
CREATE INDEX IF NOT EXISTS signups_utm_source_idx ON signups (utm_source);
CREATE INDEX IF NOT EXISTS signups_email_domain_idx ON signups (email_domain);
CREATE INDEX IF NOT EXISTS signups_email_idx ON signups (email);

-- Custom events — any non-signup event worth tracking. Captures
-- tip_jar_click, affiliate_click, share_click, render, stretch_expand etc.
-- One row per event. (We don't try to dedupe or batch.)
CREATE TABLE IF NOT EXISTS events (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,           -- e.g. 'tip_jar_click'
  partner       TEXT,                    -- for affiliate_click: 'booking'/'skyscanner'
  dest          TEXT,                    -- for affiliate_click: destination city
  days_off      INTEGER,
  al            INTEGER,
  al_domain     TEXT,                    -- for share_click: 'main'/'stretch'
  al_idx        INTEGER,                 -- for share_click/affiliate_click
  utm_source    TEXT,
  utm_medium    TEXT,
  utm_campaign  TEXT,
  ref_host      TEXT,
  user_agent    TEXT,
  ip_hash       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS events_name_idx ON events (name);
CREATE INDEX IF NOT EXISTS events_created_at_idx ON events (created_at DESC);
CREATE INDEX IF NOT EXISTS events_utm_source_idx ON events (utm_source);
CREATE INDEX IF NOT EXISTS events_partner_idx ON events (partner);

-- Fare alerts subscribers — one row per email signup.
-- Stores origin airport, destinations, frequency, and tier (free/premium).
-- Used by the weekly cron to generate the fare digest.
CREATE TABLE IF NOT EXISTS fare_alert_subscribers (
  id              BIGSERIAL PRIMARY KEY,
  email           TEXT NOT NULL UNIQUE,
  origin          TEXT NOT NULL,            -- e.g. 'KUL', 'PEN', 'JHB'
  destinations    TEXT[] NOT NULL,         -- e.g. {'HND', 'DPS', 'BKK', 'ICN', 'TPE'}
  frequency       TEXT NOT NULL DEFAULT 'weekly',  -- 'weekly' or 'instant'
  tier            TEXT NOT NULL DEFAULT 'free',    -- 'free' or 'premium'
  is_active       BOOLEAN NOT NULL DEFAULT true,
  utm_source      TEXT,
  ref_host        TEXT,
  ip_hash         TEXT,
  user_agent      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_sent_at    TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS fare_alert_subs_email_idx ON fare_alert_subscribers (email);
CREATE INDEX IF NOT EXISTS fare_alert_subs_active_idx ON fare_alert_subscribers (is_active, tier);
CREATE INDEX IF NOT EXISTS fare_alert_subs_origin_idx ON fare_alert_subscribers (origin);

-- Fare snapshots — one row per (origin, destination, departure_date) per week.
-- Stores the cheapest fare, airline, and booking URL.
-- Used to compute the 90-day median for "is this a good deal?" logic.
CREATE TABLE IF NOT EXISTS fare_snapshots (
  id              BIGSERIAL PRIMARY KEY,
  origin          TEXT NOT NULL,            -- e.g. 'KUL'
  destination     TEXT NOT NULL,            -- e.g. 'HND'
  departure_date  DATE NOT NULL,
  return_date     DATE,
  price           NUMERIC(10,2) NOT NULL,   -- in MYR
  currency        TEXT NOT NULL DEFAULT 'MYR',
  airline         TEXT,                     -- e.g. 'NH' (All Nippon)
  layovers        INTEGER DEFAULT 0,
  duration_mins   INTEGER,
  booking_url     TEXT,                     -- affiliate redirect URL
  source          TEXT NOT NULL,            -- 'amadeus' or 'serpapi'
  snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fare_snapshots_route_date_idx ON fare_snapshots (origin, destination, departure_date);
CREATE INDEX IF NOT EXISTS fare_snapshots_snapshot_at_idx ON fare_snapshots (snapshot_at DESC);

-- Fare alert sends — log of every email sent (digest or instant).
-- Used to debug "did the user get the email?" and to prevent double-sends.
CREATE TABLE IF NOT EXISTS fare_alert_sends (
  id              BIGSERIAL PRIMARY KEY,
  subscriber_id   BIGINT NOT NULL REFERENCES fare_alert_subscribers(id),
  send_type       TEXT NOT NULL,            -- 'weekly' or 'instant'
  fare_snapshot_ids BIGINT[],              -- which snapshots were included
  email_subject   TEXT,
  email_status    TEXT,                     -- 'sent', 'failed', 'bounced'
  resend_id       TEXT,                     -- Resend API message ID
  sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fare_alert_sends_subscriber_idx ON fare_alert_sends (subscriber_id);
CREATE INDEX IF NOT EXISTS fare_alert_sends_sent_at_idx ON fare_alert_sends (sent_at DESC);


# Domain Setup — longweekend.my (Exabytes, no Cloudflare)

**Status:** Registered 28 Jun 2026 at Exabytes Network Sdn Bhd (WHOIS confirmed). Status: `addPeriod` (5-day grace period after registration).

**Goal:** Get `longweekend.my` working with Vercel + Resend so the waitlist autoresponder works and the site has a real custom domain.

**Time estimate:** 15-25 min total. **No Cloudflare needed.**

---

## Why skip Cloudflare

Cloudflare is nice-to-have (CDN, DDoS, free email routing, polished DNS UI) but **not required** for this site. Vercel already provides:
- ✅ SSL/HTTPS (auto-issued via Let's Encrypt)
- ✅ Global CDN
- ✅ DDoS protection at the edge

Exabytes's built-in DNS management does everything we need: point the domain to Vercel, add the 3 Resend records, that's it.

---

## The 4-step process (Exabytes only)

### Step 1: Add Vercel DNS records at Exabytes (5 min)

Login to **https://exabytes.com.my** → My Domains → `longweekend.my` → DNS Management / Zone Editor.

Add these 2 records (the path to the DNS editor varies by Exabytes control panel version — look for "DNS Records", "Zone Editor", or "Manage DNS"):

| Type | Host | Value | TTL |
|---|---|---|---|
| **A** | `@` | `76.76.21.21` | 3600 (or default) |
| **CNAME** | `www` | `cname.vercel-dns.com` | 3600 (or default) |

**Important:** Delete any existing A or CNAME records at `@` and `www` first (Exabytes may have added default parking records).

If Exabytes doesn't support `CNAME` at the apex (the `@` row), use the **A record** above. If it does, CNAME is preferred.

### Step 2: Add Resend verification records at Exabytes (5 min)

In the same DNS management panel, add these 3 records:

| Type | Host | Value |
|---|---|---|
| **CNAME** | `resend._domainkey` | `resend._domainkey.resend.com` |
| **TXT** | `@` | `v=spf1 include:resend.com ~all` |
| **TXT** | `_dmarc` | `v=DMARC1; p=none;` |

(The `~all` in SPF and `p=none` in DMARC are safe defaults — they say "soft fail if anything looks fishy" but don't reject anything.)

### Step 3: Add the domain in Vercel (2 min)

1. Go to https://vercel.com/jers-projects-cc1e646d/longweekend-my → Settings → Domains
2. Type `longweekend.my` → **Add**
3. Vercel will check the DNS records — should show ✅ green within 1-5 min (after Exabytes DNS propagates)
4. Add `www.longweekend.my` the same way
5. Vercel auto-issues SSL certs

### Step 4: Verify the domain in Resend (2 min)

1. Go to https://resend.com/domains
2. Click **Add Domain** → enter `longweekend.my`
3. Resend shows the same 3 records we already added at Exabytes. Click **Verify** (or it auto-detects after a minute)
4. Status turns green ✅

### Step 5 (I do this once you tell me Resend is green): Update Vercel env vars + redeploy

Once Resend shows green, ping me and I'll:
- Set `MAIL_FROM = "Long Weekend <hello@longweekend.my>"`
- Set `MAIL_TO = alfred.james.chew@gmail.com` (your main inbox)
- Set `SEND_AUTORESPOND = 1` (now allowed because the from-address is verified)
- Redeploy
- Test: submit the form → you get email from `hello@longweekend.my` + user gets a welcome reply

---

## What works after this

- ✅ `https://longweekend.my` serves your site (Vercel)
- ✅ `https://www.longweekend.my` redirects to apex (Vercel auto-redirect)
- ✅ Email FROM `hello@longweekend.my` works (Resend)
- ✅ Waitlist signups go to alfred.james.chew@gmail.com
- ✅ Autoresponder goes back to the form submitter (welcome email)

## What doesn't work (and how to fix if you ever need it)

- ❌ `mailto:hello@longweekend.my` from users → no inbox, just bounces
  - Fix when needed: Resend has a paid "inbound" feature (catches incoming email), or use Google Workspace, or any email hosting
- ❌ DMARC enforcement is set to `p=none` (monitor-only) → can tighten to `p=quarantine` or `p=reject` later for stricter spam protection

## Total cost

| Item | Cost |
|---|---|
| `longweekend.my` registration | RM 120 + 8% SST ≈ RM 130 (1 year) |
| Exabytes DNS management | Free (included) |
| Resend (free tier) | Free (100 emails/day) |
| Vercel (Hobby plan) | Free |
| **Total first year** | **~RM 130** |

No Cloudflare account needed. No Cloudflare login issues. Just Exabytes + Vercel + Resend.

---

## File updates I do after Step 5

When you ping me, I'll also:
- Update `build.py` so the canonical URL (JSON-LD, og:url, sitemap, .ics) is `longweekend.my` instead of `longweekend-my.vercel.app`
- The form's `WAITLIST_FALLBACK_EMAIL` is already `hello@longweekend.my` — once Resend is verified, that link actually reaches a real recipient (when you set up inbound email)
- Redeploy

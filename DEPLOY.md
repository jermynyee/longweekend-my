# Deploying longweekend.my to Cloudflare Pages

This is a step-by-step guide for getting the site live. Cloudflare Pages is free
for static sites and is the right target — the project includes a `functions/`
directory for the `/api/subscribe` endpoint, which Cloudflare auto-detects.

Two paths are covered:

- **Path A (recommended): Git-integrated deploy** — push to GitHub, Cloudflare
  builds on every push, automatic previews on PRs. Best for ongoing iteration.
- **Path B: Direct upload via `wrangler`** — no GitHub needed, faster to ship
  the first time.

You can do A, do B, or do B first then migrate to A. The repo is structured
so both work.

---

## Prerequisites

| Requirement | How to check | Install |
|---|---|---|
| Git | `git --version` | `xcode-select --install` (mac) |
| GitHub account | https://github.com | Sign up |
| Cloudflare account | https://dash.cloudflare.com/sign-up | Free tier is enough |
| `gh` CLI (optional, for repo creation) | `gh --version` | `brew install gh` |
| `wrangler` (only for Path B) | `wrangler --version` | `npm install -g wrangler` |
| Python 3 (only for rebuilds) | `python3 --version` | macOS: preinstalled |

The current machine has:
- ✅ `git`, `gh`, `python3` installed
- ❌ Not yet a Git repo (will init)
- ❌ Not yet authenticated to `gh` (will prompt)
- ❌ `wrangler` not installed (only needed for Path B)

---

## Path A: Git-integrated deploy (recommended)

### Step 1 — Initialize the repo and push to GitHub

```bash
cd /Users/alfred/.openclaw/workspace/moonshot/longweekend

# Init and commit
git init
git add .
git commit -m "Initial commit — longweekend.my MVP + 3 SEO pages"

# Authenticate gh (one-time)
gh auth login
# Choose: GitHub.com → HTTPS → Yes (authenticate git) → Login with browser

# Create the GitHub repo and push
# (Replace YOUR_GITHUB_USERNAME with your actual username)
gh repo create longweekend-my \
  --public \
  --source=. \
  --remote=origin \
  --description="Malaysia long weekend / AL optimizer" \
  --push
```

If you'd rather keep the repo private during initial dev, use `--private` instead
of `--public`. Cloudflare Pages works fine with both.

### Step 2 — Connect Cloudflare Pages to the GitHub repo

1. Open https://dash.cloudflare.com → **Workers & Pages** → **Create application**
2. Choose **Pages** → **Connect to Git**
3. Select your GitHub account, then select the `longweekend-my` repo
4. **Set up builds and deployments** — use these exact values:
   - **Project name:** `longweekend-my`
   - **Production branch:** `main`
   - **Build command:** (leave blank — no build step needed; `index.html` is pre-generated)
   - **Build output directory:** `/` (the project root)
   - **Root directory (advanced):** `/` (the project root)
   - **Environment variables:** none for now
5. Click **Save and Deploy**

Cloudflare will:
- Provision the project (takes ~30 seconds)
- Run the first deploy (~30 seconds for a 41KB site)
- Give you a URL like `https://longweekend-my.pages.dev`

That `.pages.dev` URL works immediately. You don't need the real domain to
start collecting traffic + Search Console data.

### Step 3 — Verify the deploy

Once Cloudflare shows the first deploy as ✅ successful:

```bash
# Smoke test the live site
curl -I https://longweekend-my.pages.dev
curl -I https://longweekend-my.pages.dev/about.html
curl -I https://longweekend-my.pages.dev/privacy.html
curl -I https://longweekend-my.pages.dev/cuti-panjang-malaysia-2026/
curl -I https://longweekend-my.pages.dev/malaysia-long-weekends-2026/
curl -I https://longweekend-my.pages.dev/selangor-long-weekends-2026/

# POST to the email-capture function (returns 200 even with stub backend)
curl -X POST https://longweekend-my.pages.dev/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","year":"2026","al":"14","states":["Selangor"]}'
```

All should return 200. Open the `.pages.dev` URL in a browser and verify the
calculator renders, sliders work, share buttons appear, and the URL state
updates as you change filters.

### Step 4 — Register `longweekend.my` (when ready)

1. Go to https://www.namecheap.com (or any registrar — Mynic, GoDaddy, etc.)
2. Search for `longweekend.my`
3. Register for 1-5 years (RM35-50/year for `.my` via Mynic, ~$10-15/year for `.com.my`)
4. In Cloudflare Pages → your project → **Custom domains** → **Set up a custom domain**
5. Enter `longweekend.my` and `www.longweekend.my`
6. Cloudflare will give you a set of DNS records to add at your registrar
7. Add the records at your registrar (or transfer nameservers to Cloudflare for free)
8. Wait 5-30 min for DNS propagation, then SSL is auto-provisioned

Once the custom domain is active, update these in `build.py` (already correct,
just verify):
- `<link rel="canonical" href="https://longweekend.my/">`
- `og:url`, `og:image` references in all 6 HTML files
- `sitemap.xml` URLs (already pointing to `longweekend.my`)

### Step 5 — Set up Google Search Console (do this the day you go live)

1. Go to https://search.google.com/search-console
2. **Add property** → **URL prefix** → `https://longweekend.my/`
3. Verify via DNS (Cloudflare → your domain → DNS → add the TXT record Cloudflare shows you)
4. Once verified, **Sitemaps** → submit `https://longweekend.my/sitemap.xml`
5. **URL Inspection** → paste each of the 6 URLs and click **Request indexing** (kicks the crawl off faster than waiting for Google to find you organically)

---

## Path B: Direct upload via `wrangler` (no GitHub needed)

Use this if you don't want a GitHub repo yet, or if you want to deploy a quick
fix without going through Git.

### Step 1 — Install `wrangler`

```bash
npm install -g wrangler
# or
npx wrangler --version
```

### Step 2 — Authenticate

```bash
wrangler login
# Opens browser, asks you to log in to Cloudflare, generate an API token
```

### Step 3 — Deploy

```bash
cd /Users/alfred/.openclaw/workspace/moonshot/longweekend
wrangler pages deploy . --project-name=longweekend-my
```

First time only, it'll ask if you want to create the project — say yes.
Subsequent deploys just push and report the new URL.

### Step 4 — (Optional) Migrate to Git integration later

If you start with Path B and want to add Git integration later:

```bash
# Init git, commit, push to GitHub
cd /Users/alfred/.openclaw/workspace/moonshot/longweekend
git init
git add .
git commit -m "Adopt git history"
gh repo create longweekend-my --public --source=. --push
```

Then in Cloudflare Pages → your project → **Settings** → **Builds** →
**Connect to Git** → select the repo. Cloudflare will keep the existing
`.pages.dev` URL and start auto-deploying from `main`.

---

## Post-deploy checklist (do all of these on day 1)

### ✅ Traffic & analytics

- [ ] **Plausible** (recommended — privacy-friendly, no cookie banner needed):
  1. Sign up at https://plausible.io
  2. Add site: `longweekend.my`
  3. Add this to the `<head>` of `index.html`, `about.html`, `privacy.html`, and all 3 SEO pages (right before `</head>`):
     ```html
     <script defer data-domain="longweekend.my" src="https://plausible.io/js/script.js"></script>
     ```
  4. Custom events (`affiliate_click`, `share_copy`, `email_signup`) are already wired via the `track()` function in `index.html` — no extra config needed.
- [ ] **OR Google Analytics 4** (if you prefer it):
  1. https://analytics.google.com → Admin → Create property
  2. Get the `G-XXXXXXX` measurement ID
  3. Add to `<head>` of all pages:
     ```html
     <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXX"></script>
     <script>window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);} gtag('js', new Date()); gtag('config', 'G-XXXXXXX');</script>
     ```

### ✅ Search engines

- [ ] Google Search Console — set up + submit sitemap (see Step 5 above)
- [ ] Bing Webmaster Tools — https://www.bing.com/webmasters → add site → submit sitemap
- [ ] (Optional) Yandex, Baidu — for non-Google search coverage, low priority for MY market

### ✅ Affiliate accounts (replace placeholders)

- [ ] **Agoda Affiliate Partner**: https://partners.agoda.com → apply → get `cid`
  - In `build.py`: replace `"PLACEHOLDER_AGODA_CID"` with your real CID
  - Run `python3 build.py` and commit/push
- [ ] **Booking.com Affiliate Partner**: https://www.booking.com/affiliate-program → apply → get `aid`
  - In `build.py`: replace `"PLACEHOLDER_BOOKING_AID"` with your real aid
  - Run `python3 build.py` and commit/push

### ✅ Email capture wiring

- [ ] Currently `/api/subscribe` logs to console only. To wire to a real store:
  1. **Easiest — Cloudflare KV**: Cloudflare dashboard → your Pages project → **Settings** → **Functions** → **KV namespace bindings** → add `SUBSCRIBERS_KV`
  2. Edit `functions/api/subscribe.js`, replace `console.log(...)` with:
     ```js
     await env.SUBSCRIBERS_KV.put(`email:${email}`, JSON.stringify({...}), { expirationTtl: 60 * 60 * 24 * 365 });
     ```
  3. To view stored emails: `wrangler pages kv:key list --binding=SUBSCRIBERS_KV`
- [ ] **For actual email sends** (60-day reminders, etc.) — pick one of:
  - Mailchimp (https://mailchimp.com) — easiest if you'll send newsletters later too
  - Brevo (https://brevo.com) — cheaper at low volume, free tier = 300 emails/day
  - Resend (https://resend.com) — modern, dev-friendly, has a free tier

### ✅ Day-1 launch to Reddit (from `distribution/reddit_posts.md`)

- [ ] Pick the version that matches your state
  - If you work in KL → post Version 2 (r/kualalumpur)
  - If Penang → Version 3
  - If elsewhere / wider reach → Version 1 (r/malaysia, English)
- [ ] Cross-post Version 4 (BM) to Cari Forum or a relevant Facebook group
- [ ] **DO NOT** cross-post to all subreddits in the same hour — Reddit flags that
- [ ] After 24h, reply to top comments with state-specific combos
- [ ] DO NOT edit the post after the first 2 hours — Reddit de-prioritises edited posts

### ✅ Day-1 launch to Twitter/X

- [ ] One short thread (5-7 tweets) with the headline insight: "29 May 2026 = 5 days off, 0 AL"
- [ ] Pin it to your profile
- [ ] Tag @Wageme_de, @hrdf, @kakitangan (they reshare useful HR content)
- [ ] (Optional) Reply to any r/malaysia thread that hits the front page with holiday-related content

---

## Project structure (post-deploy)

```
longweekend.my/
├── index.html                       # The calculator (PWA, 41KB)
├── about.html                       # About page
├── privacy.html                     # Privacy policy
├── robots.txt                       # SEO robots directive
├── sitemap.xml                      # SEO sitemap (6 URLs)
├── holidays.json                    # Holiday data source (92 + 82 rows)
├── build.py                         # Rebuilds index.html from holidays.json
├── optimizer.py                     # Python reference of the JS optimizer
├── package.json                     # wrangler deploy scripts (Path B)
├── wrangler.toml                    # Cloudflare Pages config
├── .gitignore                       # Standard ignores
├── functions/
│   └── api/
│       └── subscribe.js             # Cloudflare Pages Function for /api/subscribe
├── cuti-panjang-malaysia-2026/
│   └── index.html                   # SEO landing page (BM, 1.2K words)
├── malaysia-long-weekends-2026/
│   └── index.html                   # SEO landing page (EN, 1.6K words)
├── selangor-long-weekends-2026/
│   └── index.html                   # SEO landing page (Selangor, 1.4K words)
├── distribution/
│   └── reddit_posts.md              # 4 copy-paste-ready Reddit launch posts
├── GOAL.md                          # Project goal + 60-day metrics + kill clauses
├── README.md                        # Developer docs
└── DEPLOY.md                        # This file
```

---

## How to make changes after launch

### Editing the calculator (UI, behavior, copy)

```bash
# 1. Edit build.py — the source of truth
# 2. Regenerate index.html
python3 build.py
# 3. If using Git integration: commit and push
git add build.py index.html
git commit -m "Tweak AL slider default to 12"
git push
# 4. If using wrangler direct: re-run deploy
wrangler pages deploy . --project-name=longweekend-my
```

Cloudflare auto-deploys on push (Path A) in ~30 seconds.

### Editing holiday data (when 2027/2028 dates get gazetted)

1. Re-run the scraper (in `holidays.json` build path) — see `GOAL.md` for the
   `publicholidays.com.my` source
2. Or manually edit `holidays.json` for one-off corrections
3. Run `python3 build.py`
4. Commit + push

### Adding a new SEO landing page

1. Create a new directory, e.g. `kuala-lumpur-long-weekends-2026/index.html`
2. Copy `cuti-panjang-malaysia-2026/index.html` as a template
3. Update title, description, content, FAQ, CTA URL
4. Add the new URL to `sitemap.xml`
5. Commit + push

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Deploy fails with "project not found" | First deploy via `wrangler`, no project created yet | `wrangler pages deploy` will prompt to create — say yes |
| `/api/subscribe` returns 404 | `functions/` directory not detected | Confirm `functions/api/subscribe.js` exists, rebuild |
| Custom domain stuck on "pending" | DNS records not added at registrar | Add the exact CNAME records Cloudflare shows in the dashboard |
| Google doesn't index for 7+ days | Sitemap not submitted | Search Console → Sitemaps → submit `/sitemap.xml` |
| `Index.html` not regenerating | `build.py` reads `holidays.json` from `ROOT` constant | Confirm `holidays.json` is in same directory as `build.py` |
| Slider doesn't update on drag | Stale browser cache | Hard refresh: Cmd+Shift+R (mac), Ctrl+Shift+R (win) |
| URL state param ignored on load | `loadFromURL()` runs before `STATES.forEach()` | This is fixed in current build — confirm `index.html` was rebuilt after P0 patches |
| Tracking events not firing | Plausible/GA scripts not loaded | Add the `<script>` tag per the post-deploy checklist above |

---

## What you DON'T need to do

- ❌ Set up a database — `holidays.json` is checked in and static
- ❌ Set up a backend server — Cloudflare Pages handles the `/api/subscribe` function
- ❌ Configure SSL — Cloudflare auto-provisions Let's Encrypt for custom domains
- ❌ Set up CI/CD — Git integration does this automatically on every push
- ❌ Worry about scaling — Pages free tier handles 500 builds/month, unlimited requests

---

## Estimated time to first deploy

| Path | Time |
|---|---|
| Path A (Git-integrated, after `gh auth login`) | 10-15 minutes |
| Path B (`wrangler` direct upload) | 5-10 minutes |
| Plus: register `longweekend.my` domain | +30 min (plus 5-30 min DNS propagation) |
| Plus: Search Console + sitemap submit | +5 min |
| **Total to "live with custom domain"** | **~1 hour** |

---

## First-day cost

| Item | Cost |
|---|---|
| Domain (`longweekend.my`, Mynic, 1 year) | ~RM 35-50 |
| Cloudflare Pages (free tier) | $0 |
| Cloudflare KV (free tier = 100K reads/day, 1K writes/day) | $0 |
| Plausible (free 30-day trial, then $9/mo) | $0 first month |
| **Day 1** | **~RM 35-50** (just the domain) |

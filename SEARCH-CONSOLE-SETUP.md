# Google Search Console Setup — longweekend.my

**Owner:** jermyn.yee@gmail.com
**Property:** https://longweekend.my/ (URL prefix)

---

## Steps (5 min total)

### 1. Open Search Console
→ https://search.google.com/search-console
→ Sign in with **jermyn.yee@gmail.com**

### 2. Add property
- Click **"Add property"** (top-left dropdown)
- Choose **"URL prefix"** (NOT "Domain" — Domain needs DNS access)
- Enter: `https://longweekend.my/`
- Click **Continue**

### 3. Verify ownership
- Recommended method: **HTML file**
- Google shows you a file like `google123abc456def.html`
- Open Terminal, run:
  ```bash
  cd ~/.openclaw/workspace/moonshot/longweekend
  # Replace FILENAME and TOKEN with what Google gave you:
  echo "google-site-verification: FILENAME" > FILENAME.html
  vercel --prod --yes
  ```
- Back in Search Console, click **"Verify"**
- Should turn green in ~30 seconds

### 4. Submit sitemap
- Left sidebar → **"Sitemaps"**
- In "Add a new sitemap" box, enter: `sitemap.xml`
- Click **Submit**
- Status should show "Success" within minutes
- Alfred already deployed the refreshed sitemap with 10 URLs and hreflang annotations

### 5. Request indexing (THE BIG ONE)
- Left sidebar → **"URL Inspection"**
- Paste each of these URLs one at a time, click **"Request Indexing"** after each:

  1. `https://longweekend.my/`
  2. `https://longweekend.my/malaysia-long-weekends-2026/`
  3. `https://longweekend.my/cuti-panjang-malaysia-2026/`
  4. `https://longweekend.my/selangor-long-weekends-2026/`
  5. `https://longweekend.my/2026`

- Google has a quota of ~10 indexing requests/day per property — 5 is fine.
- Status changes from "URL not on Google" → "URL is on Google" within 1-7 days.

---

## Already done by Alfred (no action needed)

- ✅ Sitemap regenerated with fresh `<lastmod>` dates (2026-07-18)
- ✅ Hreflang annotations added linking EN ↔ BM versions
- ✅ robots.txt already references the sitemap
- ✅ All 10 sitemap URLs verified return HTTP 200
- ✅ Internal link from homepage footer → SEO landing pages (was missing — orphan pages)
- ✅ IndexNow submission to Bing + Yandex (HTTP 202 accepted)
- ✅ Key file deployed at `/indexnow-key.txt` (needed for IndexNow auth)

## What this enables

After Step 5 completes, Google starts:
1. Crawling the homepage (re-crawl with fresh content)
2. Following the new footer links to the 3 SEO pages
3. Indexing them under the URL Inspection "Discovered → Indexed" pipeline
4. Picking up the BM alternate on `/cuti-panjang-malaysia-2026/`

Timeline: **3-14 days** for full indexing. Organic search impressions usually start 24-48h after indexing.

---

## After indexing is done (next week)

Once Search Console shows "Indexed" for the 3 SEO pages:
1. Go back to AdSense
2. Click **"Request review"** (the rejection should still be on the dashboard)
3. Wait 3-7 days for the new decision

Per Larry's note: **do not request review before pages are indexed**. A second fast rejection costs you weeks of cooldown.
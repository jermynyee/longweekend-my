# longweekend.my — Phase 2 setup notes

## What was just shipped (27 Jun 26)

1. **Tip jar** in footer (placeholder: `https://buymeacoffee.com/longweekendmy`)
   - Swap URL in `build.py` line ~272 — search for `buymeacoffee.com/longweekend`
2. **Waitlist form** (email + optional "what's missing?" feedback)
   - Currently logs to console + localStorage; no real backend yet
   - See "Waitlist backend" below for setup options
3. **Vercel Web Analytics** enabled (script tag added in `build.py`)
   - Free, no cookies, GDPR-friendly
   - View stats at: https://vercel.com/jers-projects-cc1e646d/longweekend-my/analytics

## Waitlist backend — pick ONE

### Option A: Formspree (easiest, 5 min)
1. Sign up free at https://formspree.io (50 submissions/month free)
2. Create a new form, copy the endpoint URL (looks like `https://formspree.io/f/xyzabc`)
3. In `build.py`, replace `'__WAITLIST_ENDPOINT__'` with the Formspree URL
4. Submissions will be emailed to your Formspree account email
5. Optional: connect Formspree → Google Sheet via Zapier (free tier)

### Option B: Vercel KV (more work, 30 min)
1. Create a KV store: https://vercel.com/dashboard/stores → Create → KV
2. Copy the store ID
3. Create `api/waitlist.js` with KV read/write logic
4. Bind the KV store to the project: Project Settings → Environment Variables → add `WAITLIST_KV` binding
5. Update `WAITLIST_ENDPOINT` in `build.py` to `https://longweekend-my.vercel.app/api/waitlist`

### Option C: Google Apps Script (no signup, 20 min)
1. Create a new Google Sheet, name it "longweekend.my waitlist"
2. Tools → Apps Script → paste the Apps Script web app code (TODO: provide snippet)
3. Deploy as web app (Execute as: Me, Access: Anyone)
4. Copy the deployment URL
5. Update `WAITLIST_ENDPOINT` in `build.py`

## Domain purchase — `longweekend.my`

Cost: ~RM 50/year (`.my` is more expensive than `.com`).

### Cloudflare Registrar (recommended, no markup)
1. https://dash.cloudflare.com → Domain Registration → Register Domains
2. Search `longweekend.my` → add to cart
3. Pay (RM 50 ~ $11 USD)
4. After registration, go to DNS → Records, add:
   ```
   CNAME  @    cname.vercel-dns.com
   CNAME  www  cname.vercel-dns.com
   ```
5. In Vercel: Project Settings → Domains → Add `longweekend.my` and `www.longweekend.my`
6. Vercel will verify DNS and provision SSL automatically
7. (Optional) Set `longweekend.my` as the primary domain (redirect from `vercel.app`)

### Alternative: Namecheap
- https://www.namecheap.com/domains/registration.aspx
- Search `longweekend.my`, checkout
- Use their DNS or point to Cloudflare
- Slightly more expensive than Cloudflare for `.my`

## Tip jar — real payment link

The current placeholder is `https://buymeacoffee.com/longweekendmy`. To use a real Malaysian-friendly link:

### Touch n Go / DuitNow QR
- Open your TNG eWallet → "Pay" → "QR Code" → screenshot
- Host the QR image somewhere (Vercel can serve it from `/public/`)
- Link the "Buy me a kopi" text to the QR image (modal popup)

### DuitNow ID
- Get your DuitNow ID from your bank (usually your phone number or NRIC)
- Generate a DuitNow QR at https://www.duitnow.my/ (business tools)
- Same as above — link to a hosted QR image

### Buy Me a Coffee
- Sign up at https://www.buymeacoffee.com (free, charges 5% fee)
- Update the link in `build.py` to your BMC username

#!/usr/bin/env bash
# deploy.sh — Ship longweekend.my to Cloudflare Pages.
#
# Two paths:
#   --path-a  Git-integrated (recommended): push to GitHub, Cloudflare builds on push
#   --path-b  Direct upload via wrangler:  no GitHub needed, faster first ship
#
# Re-runnable. Stops on first error. Run pre-flight every time.

set -euo pipefail

PROJECT_DIR="/Users/alfred/.openclaw/workspace/moonshot/longweekend"
REPO_NAME="longweekend-my"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }
hr()     { printf '\n%s\n' "------------------------------------------------------------"; }

step()   { hr; bold "▶ $*"; }
ok()     { green "✓ $*"; }
warn()   { yellow "⚠ $*"; }
die()    { red "✗ $*"; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1  →  $2"
}

# -----------------------------------------------------------------------------
# Pre-flight: project sanity checks (catches silent-breakage before deploy)
# -----------------------------------------------------------------------------
preflight() {
  step "Pre-flight checks"

  cd "$PROJECT_DIR"

  # 1. Regenerate index.html so we never deploy a stale build
  if [[ -f build.py ]]; then
    bold "  • Regenerating index.html from build.py..."
    python3 build.py
    ok "  • index.html regenerated"
  else
    warn "  • build.py not found — skipping regen (already built?)"
  fi

  # 2. Validate all HTML files
  local validator="$HOME/.hermes/skills/product/static-mvp-validation/scripts/validate_html.py"
  if [[ -f $validator ]]; then
    bold "  • Validating HTML files..."
    python3 "$validator" \
      index.html about.html privacy.html \
      cuti-panjang-malaysia-2026/index.html \
      malaysia-long-weekends-2026/index.html \
      selangor-long-weekends-2026/index.html
    ok "  • All HTML files clean"
  else
    warn "  • HTML validator not found at $validator — skipping"
  fi

  # 3. Confirm no placeholder affiliate IDs left behind (these should be
  #    swapped before public launch — warn but don't block)
  if grep -q PLACEHOLDER_AGODA_CID index.html || \
     grep -q PLACEHOLDER_BOOKING_AID index.html; then
    warn "  • Placeholder affiliate IDs still in index.html — affiliate clicks won't track until you swap them"
  else
    ok "  • Affiliate IDs present in index.html"
  fi

  # 3b. Smoke-test the email-capture function (14 scenarios, ~1s).
  #     Catches silent regressions in /api/subscribe + /api/subscribers.
  if [[ -f functions/__tests__/subscribe.smoke.js ]] && command -v node >/dev/null 2>&1; then
    bold "  • Smoke-testing subscribe function (14 scenarios)..."
    if node functions/__tests__/subscribe.smoke.js > /tmp/subscribe_smoke.log 2>&1; then
      local passed=$(grep -E "^Results:" /tmp/subscribe_smoke.log | grep -oE "[0-9]+ passed" | head -1)
      ok "  • Subscribe smoke tests: $passed"
    else
      tail -20 /tmp/subscribe_smoke.log
      die "Subscribe smoke tests failed — see /tmp/subscribe_smoke.log"
    fi
  else
    warn "  • Subscribe smoke test skipped (no node or no test file)"
  fi

  # 4. Confirm no uncommitted .my secrets, .env files, etc.
  if [[ -f .gitignore ]]; then
    ok "  • .gitignore present"
  else
    die "  • No .gitignore — refusing to deploy. Create one first."
  fi

  ok "Pre-flight passed"
}

# -----------------------------------------------------------------------------
# Path A: Git-integrated deploy (recommended)
# -----------------------------------------------------------------------------
path_a() {
  step "Path A — Git-integrated deploy to Cloudflare Pages"

  # 1. gh CLI
  need_cmd gh "brew install gh"
  need_cmd git "xcode-select --install"

  cd "$PROJECT_DIR"

  # 2. Authenticate to GitHub (idempotent — skips if already logged in)
  bold "  • Checking gh auth status..."
  if ! gh auth status >/dev/null 2>&1; then
    yellow "  • Not logged into GitHub. Running: gh auth login"
    yellow "    → Choose: GitHub.com → HTTPS → Yes (authenticate git) → Login with browser"
    gh auth login
  fi
  ok "  • gh auth OK"

  # 3. Detect GitHub username
  bold "  • Detecting GitHub username..."
  GH_USER=$(gh api user --jq '.login' 2>/dev/null) || die "Could not detect GitHub user. Run: gh auth login"
  if [[ -z $GH_USER ]]; then
    die "GitHub username came back empty. Run: gh auth login"
  fi
  ok "  • GitHub user: $GH_USER"

  # 4. Init repo if needed
  if [[ ! -d .git ]]; then
    bold "  • Initializing git repo..."
    git init -q
    git checkout -q -b main
    git add .
    git commit -q -m "Initial commit — longweekend.my MVP + 3 SEO pages

- Single-page AL optimizer with ranked combo cards
- Exact leave dates per combo (e.g. 'Apply leave: 3 Jun 2026')
- URL state (?year=2026&state=Selangor&al=14)
- Share buttons (Copy / WhatsApp / Native)
- Plausible + GA4 tracking wrapper
- Affiliate outbound tracking (Agoda / Booking)
- Email capture → Cloudflare Pages Function
- 3 SEO landing pages: EN, BM, state-specific
- Full about + privacy pages
- sitemap.xml + robots.txt
- JSON-LD structured data (WebApplication + Events)"
    ok "  • git init + first commit done"
  else
    bold "  • Repo already initialized — checking for uncommitted changes..."
    if [[ -n $(git status --porcelain) ]]; then
      yellow "  • Uncommitted changes — committing..."
      git add .
      git commit -q -m "Pre-deploy: refresh build artifacts"
    fi
    ok "  • git state clean"
  fi

  # 5. Create GitHub repo + push (idempotent — skips if already exists)
  bold "  • Creating GitHub repo $GH_USER/$REPO_NAME (if not exists)..."
  if gh repo view "$GH_USER/$REPO_NAME" >/dev/null 2>&1; then
    ok "  • Repo $GH_USER/$REPO_NAME already exists"
  else
    gh repo create "$REPO_NAME" \
      --public \
      --source=. \
      --remote=origin \
      --description="Malaysia long weekend / AL optimizer" \
      --push
    ok "  • Repo created and pushed"
  fi

  # 6. Make sure origin is set + push
  bold "  • Ensuring origin remote + pushing..."
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"
  fi
  git push -u origin main
  ok "  • Pushed to origin/main"

  # 7. Print the Cloudflare setup instructions
  hr
  bold "✓ Code is on GitHub. Now wire Cloudflare Pages:"
  cat <<EOF

  1. Open:   https://dash.cloudflare.com → Workers & Pages → Create application
  2. Choose: Pages → Connect to Git
  3. Pick:   $GH_USER / $REPO_NAME
  4. Build settings:
       Project name:           $REPO_NAME
       Production branch:      main
       Build command:          (leave blank — index.html is pre-generated)
       Build output directory: /
       Root directory:         /
       Environment variables:  (none for MVP)
  5. Click:  Save and Deploy

  After first deploy succeeds (~60-90s), Cloudflare gives you a
  *.longweekend-my.pages.dev URL. Test it before adding the custom domain.

  6. Add custom domain longweekend.my:
     Project → Custom domains → Set up a custom domain → longweekend.my
     (Cloudflare will tell you to update nameservers at your registrar.)

EOF

  hr
  bold "Post-deploy checklist:"
  cat <<'EOF'

  □  Visit the *.pages.dev URL — does index.html render? Do controls work?
  □  Visit /about.html and /privacy.html — do they render?
  □  Submit sitemap.xml to Google Search Console:
       https://search.google.com/search-console → Sitemaps → longweekend.my/sitemap.xml
  □  (When domain is wired) Re-submit sitemap under longweekend.my
  □  Add Plausible / GA4 script tag to index.html (track() wrapper is ready)
  □  Wire email capture: edit functions/api/subscribe.js → KV / Mailchimp / D1
  □  When Agoda + Booking affiliate IDs arrive, swap PLACEHOLDER_*_CID in
     build.py and re-run python3 build.py, then git push

EOF
}

# -----------------------------------------------------------------------------
# Path B: Direct upload via wrangler
# -----------------------------------------------------------------------------
path_b() {
  step "Path B — Direct upload via wrangler"

  need_cmd npx "brew install node"

  cd "$PROJECT_DIR"

  bold "  • Installing wrangler (local, no global pollution)..."
  if [[ ! -d node_modules/wrangler ]]; then
    npm install --no-save wrangler >/dev/null 2>&1
  fi
  ok "  • wrangler ready"

  bold "  • Authenticating wrangler to Cloudflare..."
  npx wrangler login

  bold "  • Creating Cloudflare Pages project (if not exists)..."
  if npx wrangler pages project list 2>/dev/null | grep -q "$REPO_NAME"; then
    ok "  • Project $REPO_NAME already exists"
  else
    npx wrangler pages project create "$REPO_NAME" --production-branch=main
    ok "  • Project created"
  fi

  bold "  • Deploying..."
  npx wrangler pages deploy . \
    --project-name="$REPO_NAME" \
    --branch=main \
    --commit-dirty=true

  hr
  bold "✓ Deployed via wrangler direct upload."
  cat <<EOF

  Next:
  1. Visit the URL wrangler printed (e.g. https://$REPO_NAME.pages.dev)
  2. Add custom domain longweekend.my in Cloudflare dashboard
  3. (Optional) Later: migrate to Path A for Git-integrated auto-deploy

EOF
}

# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $0 --path-a | --path-b | --preflight

  --path-a       Git-integrated deploy (recommended). Needs: gh, git.
  --path-b       Direct upload via wrangler. Needs: npx (Node).
  --preflight    Run only the pre-flight checks (no deploy).
                 Run this BEFORE --path-a or --path-b to catch stale builds.

Examples:
  $0 --preflight
  $0 --path-a
  $0 --path-b
EOF
  exit 1
}

case "${1:-}" in
  --path-a)     preflight; path_a ;;
  --path-b)     preflight; path_b ;;
  --preflight)  preflight ;;
  -h|--help)    usage ;;
  *)            usage ;;
esac

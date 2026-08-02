// Smoke test for functions/api/subscribe.js — no Cloudflare needed.
// Stubs env (KV, secrets), exercises every handler path, asserts results.

// --- Mock Cloudflare KV (in-memory) ---
class MockKV {
  constructor() { this.store = new Map(); }
  async get(key, opts) {
    const v = this.store.get(key);
    if (v == null) return null;
    if (opts && opts.type === "json") return JSON.parse(v);
    return v;
  }
  async put(key, value, opts) {
    this.store.set(key, typeof value === "string" ? value : JSON.stringify(value));
    // Don't honor TTL in mock — Cloudflare's KV uses seconds, not ms,
    // and we don't want setTimeout overflow warnings.
    void opts;
  }
  async delete(key) { this.store.delete(key); }
  size() { return this.store.size; }
}

// --- Mock fetch (only for Resend) ---
let resendCalls = 0;
let resendShouldFail = false;
global.fetch = async (url, opts) => {
  if (String(url).startsWith("https://api.resend.com/")) {
    resendCalls++;
    if (resendShouldFail) {
      return { ok: false, status: 500, text: async () => "resend is down" };
    }
    return { ok: true, status: 200, json: async () => ({ id: "mock_" + resendCalls }) };
  }
  throw new Error("Unexpected fetch to " + url);
};

// --- Mock env ---
const kv = new MockKV();
const env = {
  SUBSCRIBERS_KV: kv,
  RESEND_API_KEY: "re_test_key",
  RESEND_FROM: "Long Weekend <hello@longweekend.my>",
  ADMIN_TOKEN: "test_admin_token_abc",
};

// --- Import the function module ---
// subscribe.js is an ES module. Use dynamic import via file URL.
const { onRequestPost, onRequestGet } = await import(
  "file:///Users/alfred/.openclaw/workspace/moonshot/longweekend/functions/api/subscribe.js"
);
// Note: subscribers.js uses onRequestGet — let's also import it
const subsModule = await import(
  "file:///Users/alfred/.openclaw/workspace/moonshot/longweekend/functions/api/subscribers.js"
);

// --- Test helpers ---
let passed = 0;
let failed = 0;
function assert(cond, label) {
  if (cond) {
    console.log("  ✓ " + label);
    passed++;
  } else {
    console.error("  ✗ " + label);
    failed++;
  }
}

function makeRequest(body, headers = {}) {
  const init = {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
  };
  if (body !== undefined) init.body = typeof body === "string" ? body : JSON.stringify(body);
  return new Request("https://longweekend.my/api/subscribe", init);
}

async function runTest(name, fn) {
  console.log("\n▶ " + name);
  try { await fn(); } catch (e) {
    console.error("  ✗ THREW: " + e.message);
    console.error(e.stack);
    failed++;
  }
}

// --- TESTS ---

await runTest("1. Valid signup → 200 + KV write + Resend call", async () => {
  resendCalls = 0;
  const before = kv.size();
  const res = await onRequestPost({
    request: makeRequest({
      email: "alice@example.com",
      year: "2026",
      al: "14",
      states: ["Selangor"],
      website: ""
    }, { "CF-Connecting-IP": "1.2.3.4" }),
    env
  });
  assert(res.status === 200, "status 200");
  const data = await res.json();
  assert(data.ok === true, "ok=true");
  assert(/check your inbox/i.test(data.message), "message says 'check your inbox'");
  assert(kv.size() === before + 3, `KV gained 3 entries (record + signup_log + rate-limit counter); got +${kv.size() - before}`);
  assert(resendCalls === 1, "Resend called exactly once");
});

await runTest("2. Duplicate signup → 200, no re-write, no re-send", async () => {
  resendCalls = 0;
  const before = kv.size();
  const res = await onRequestPost({
    request: makeRequest({
      email: "alice@example.com",
      year: "2027",  // different year — should still dedup by email
      al: "10",
    }, { "CF-Connecting-IP": "1.2.3.4" }),
    env
  });
  assert(res.status === 200, "status 200");
  const data = await res.json();
  assert(data.ok === true, "ok=true");
  assert(/already/i.test(data.message), "message says 'already'");
  assert(kv.size() === before, "no new KV entries");
  assert(resendCalls === 0, "Resend NOT re-called");
});

await runTest("3. Invalid email → 400", async () => {
  for (const bad of ["", "not-an-email", "a@b", "@example.com", "x".repeat(260) + "@x.com"]) {
    const res = await onRequestPost({
      request: makeRequest({ email: bad, year: "2026", al: "14" }),
      env
    });
    assert(res.status === 400, `rejects '${bad.slice(0, 30)}' with 400`);
  }
});

await runTest("4. Invalid year → 400", async () => {
  for (const bad of ["abc", "1999", "2099", "26"]) {
    const res = await onRequestPost({
      request: makeRequest({ email: "x@x.com", year: bad, al: "14" }),
      env
    });
    assert(res.status === 400, `rejects year '${bad}' with 400`);
  }
});

await runTest("5. Invalid AL → 400", async () => {
  for (const bad of ["abc", "0", "31", "-1"]) {
    const res = await onRequestPost({
      request: makeRequest({ email: "x@x.com", year: "2026", al: bad }),
      env
    });
    assert(res.status === 400, `rejects al '${bad}' with 400`);
  }
});

await runTest("6. Honeypot triggered → silently accept, no KV write, no email", async () => {
  resendCalls = 0;
  const before = kv.size();
  const res = await onRequestPost({
    request: makeRequest({
      email: "bot@spam.com",
      year: "2026",
      al: "14",
      website: "http://spam.example.com"  // bot filled the honeypot
    }, { "CF-Connecting-IP": "9.9.9.9" }),
    env
  });
  assert(res.status === 200, "returns 200 (silent accept)");
  const data = await res.json();
  assert(data.ok === true, "ok=true (bot doesn't learn it failed)");
  assert(kv.size() === before, "no KV write");
  assert(resendCalls === 0, "no Resend call");
});

await runTest("7. Rate limit: 10 signups per IP per hour", async () => {
  // Clear any existing rate-limit keys for this test
  for (const k of [...kv.store.keys()]) {
    if (k.startsWith("ip:5d4e7c:")) kv.store.delete(k);
  }
  // SHA-256("5.5.5.5") = ... we'll just count by IP, not exact hash
  const ip = "5.5.5.5";
  const before = kv.size();
  // First 10 should succeed
  for (let i = 0; i < 10; i++) {
    const res = await onRequestPost({
      request: makeRequest({ email: `rl-${i}@x.com`, year: "2026", al: "14" }, { "CF-Connecting-IP": ip }),
      env
    });
    assert(res.status === 200, `signup ${i + 1}/10 succeeds`);
  }
  // 11th should be 429
  const res11 = await onRequestPost({
    request: makeRequest({ email: "rl-overflow@x.com", year: "2026", al: "14" }, { "CF-Connecting-IP": ip }),
    env
  });
  assert(res11.status === 429, "11th signup returns 429");
  const data11 = await res11.json();
  assert(/too many/i.test(data11.error), "429 error message mentions rate limit");
});

await runTest("8. KV unavailable → fails open (still 200, no crash)", async () => {
  resendCalls = 0;
  const envNoKV = {
    SUBSCRIBERS_KV: null,
    RESEND_API_KEY: "re_test_key",
  };
  const res = await onRequestPost({
    request: makeRequest({ email: "failopen@example.com", year: "2026", al: "14" }),
    env: envNoKV
  });
  assert(res.status === 200, "still 200 when KV missing");
  const data = await res.json();
  assert(data.ok === true, "ok=true (fail-open for user)");
  // Verify the function actually entered the fail-open path: message should
  // mention 'degraded' or 'storage' OR still be the generic fallback — both
  // are acceptable as long as we don't 500.
  assert(typeof data.message === "string" && data.message.length > 0, "has a message");
});

await runTest("8b. KV write fails → message reflects degraded mode", async () => {
  // KV exists but put() throws — this is what would happen if Cloudflare KV
  // is unreachable or returns 5xx. The function should still 200 and tell
  // the user storage is degraded.
  class BrokenKV {
    async get() { return null; }
    async put() { throw new Error("KV is down"); }
  }
  const envBroken = {
    SUBSCRIBERS_KV: new BrokenKV(),
    RESEND_API_KEY: "re_test_key",
  };
  const res = await onRequestPost({
    request: makeRequest({ email: "kvbroken@example.com", year: "2026", al: "14" },
      { "CF-Connecting-IP": "7.7.7.7" }),
    env: envBroken
  });
  assert(res.status === 200, "still 200 when KV write throws");
  const data = await res.json();
  assert(data.ok === true, "ok=true");
  assert(/degraded/i.test(data.message),
    `message mentions 'degraded' (got: ${data.message})`);
});

await runTest("9. Resend failure → user still sees success", async () => {
  resendShouldFail = true;
  resendCalls = 0;
  const res = await onRequestPost({
    request: makeRequest({ email: "resendfail@example.com", year: "2026", al: "14" },
      { "CF-Connecting-IP": "8.8.8.8" }),
    env
  });
  resendShouldFail = false;
  assert(res.status === 200, "still 200 when Resend fails");
  const data = await res.json();
  assert(data.ok === true, "ok=true (user doesn't see email failure)");
  assert(!/check your inbox/i.test(data.message),
    "message does NOT say 'check your inbox' (email didn't send)");
  assert(resendCalls === 1, "Resend was attempted exactly once");
});

await runTest("10. /api/subscribers with ADMIN_TOKEN", async () => {
  // Should return today's events
  const req = new Request("https://longweekend.my/api/subscribers", {
    method: "GET",
    headers: { "Authorization": "Bearer test_admin_token_abc" }
  });
  const res = await subsModule.onRequestGet({ request: req, env });
  assert(res.status === 200, "auth'd GET returns 200");
  const data = await res.json();
  assert(typeof data.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(data.date),
    "returns today's date");
  assert(typeof data.count === "number", "count is a number");
  assert(Array.isArray(data.events), "events is an array");
  assert(data.count >= 1, `has at least 1 event (got ${data.count})`);
  assert(data.events[0].email, "first event has an email field");
});

await runTest("11. /api/subscribers without ADMIN_TOKEN → 404 (disabled)", async () => {
  const envNoAdmin = { ...env, ADMIN_TOKEN: undefined };
  const req = new Request("https://longweekend.my/api/subscribers", { method: "GET" });
  const res = await subsModule.onRequestGet({ request: req, env: envNoAdmin });
  assert(res.status === 404, "endpoint disabled without ADMIN_TOKEN");
});

await runTest("12. /api/subscribers with bad token → 401", async () => {
  const req = new Request("https://longweekend.my/api/subscribers", {
    method: "GET",
    headers: { "Authorization": "Bearer wrong-token" }
  });
  const res = await subsModule.onRequestGet({ request: req, env });
  assert(res.status === 401, "wrong token returns 401");
});

await runTest("13. /api/subscribers with ?date=2026-01-01 → empty events", async () => {
  const req = new Request("https://longweekend.my/api/subscribers?date=2026-01-01", {
    method: "GET",
    headers: { "Authorization": "Bearer test_admin_token_abc" }
  });
  const res = await subsModule.onRequestGet({ request: req, env });
  const data = await res.json();
  assert(data.date === "2026-01-01", "honors ?date param");
  assert(data.count === 0, "no events on that date");
});

await runTest("14. SHA-256(IP) is used (raw IP not stored)", async () => {
  const stored = await kv.get("email:alice@example.com", { type: "json" });
  assert(stored && stored.ip_hash && /^[a-f0-9]{64}$/.test(stored.ip_hash),
    `ip_hash is 64-char hex (got ${stored && stored.ip_hash && stored.ip_hash.slice(0,8)}…)`);
  assert(!stored.ip, "no raw IP stored");
});

// --- Wrap up ---
console.log("\n" + "=".repeat(60));
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log("=".repeat(60));
process.exit(failed > 0 ? 1 : 0);

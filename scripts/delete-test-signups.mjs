// One-time delete script for test signups
// Run with: cd ~/.openclaw/workspace/moonshot/longweekend && node --env-file=.env.local scripts/delete-test-signups.mjs

import { neon } from '@neondatabase/serverless';

const url = process.env.POSTGRES_URL;
if (!url) {
  console.error('POSTGRES_URL not set. Run with: node --env-file=.env.local scripts/delete-test-signups.mjs');
  process.exit(1);
}

const sql = neon(url);

console.log('=== ALL signups (last 30 days) ===');
const all = await sql`
  SELECT id, email, created_at, utm_source, year, al, ip_hash
  FROM signups
  WHERE created_at >= NOW() - INTERVAL '30 days'
  ORDER BY created_at DESC
`;
console.table(all);

console.log('\n=== Identified as test signups ===');
const tests = await sql`
  SELECT id, email, created_at, utm_source, year, al
  FROM signups
  WHERE
    email LIKE '%@example.com'
    OR email LIKE '%@example.org'
    OR email LIKE '%@test.com'
    OR email LIKE '%@test.local'
    OR email IN (SELECT email FROM signups GROUP BY email HAVING count(*) > 1)
  ORDER BY created_at DESC
`;
console.table(tests);
console.log(`\nTotal test signups: ${tests.length}`);

if (process.argv.includes('--delete')) {
  console.log('\n=== DELETING... ===');
  const deleted = await sql`
    DELETE FROM signups
    WHERE
      email LIKE '%@example.com'
      OR email LIKE '%@example.org'
      OR email LIKE '%@test.com'
      OR email LIKE '%@test.local'
      OR email IN (SELECT email FROM signups GROUP BY email HAVING count(*) > 1)
    RETURNING id, email
  `;
  console.log(`Deleted ${deleted.length} signups:`);
  console.table(deleted);
} else {
  console.log('\nDry run. Pass --delete to actually delete.');
}

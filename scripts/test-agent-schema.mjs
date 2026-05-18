/**
 * Script: test-agent-schema.mjs
 * Valida el schema Zod de AgentForm sin dependencia de React.
 * Paso 15, ID-020: tests unitarios del schema de validación.
 *
 * Uso:
 *   node scripts/test-agent-schema.mjs
 */

import { createRequire } from 'module';
const require = createRequire(import.meta.url);

let z;
try {
  z = require('zod');
} catch {
  console.error('ERROR: zod not found. Run: npm install --save-dev zod');
  process.exit(1);
}

// ── Schema bajo test (debe coincidir con dashboard/lib/agent-schema.ts) ───

const agentFormSchema = z.object({
  role: z.string().min(1, 'Role is required'),
  goal: z.string().min(10, 'Goal must be at least 10 characters'),
  backstory: z.string().min(10, 'Backstory must be at least 10 characters'),
  llmProvider: z.string(),
  llmModel: z.string(),
  allowedTools: z.array(z.string()),
  maxIter: z.number().int().min(1).max(10),
  verbose: z.boolean(),
  reasoning: z.boolean(),
  injectDate: z.boolean(),
  memory: z.boolean(),
});

// ── Tests ────────────────────────────────────────────────────────────────

const VALID_PAYLOAD = {
  role: 'Code Reviewer',
  goal: 'Review pull requests for security vulnerabilities in the codebase',
  backstory: 'Senior security engineer with 10 years of experience in code review',
  llmProvider: 'groq',
  llmModel: 'llama-3.1-70b-versatile',
  allowedTools: ['fetch_url', 'code_analyzer'],
  maxIter: 5,
  verbose: true,
  reasoning: false,
  injectDate: true,
  memory: false,
};

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✅ ${name}`);
  } catch (e) {
    failed++;
    console.log(`  ❌ ${name}: ${e.message}`);
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

console.log('\n🧪 AgentForm Schema Tests\n');

// TP-1: Valid payload
test('accepts valid payload', () => {
  const result = agentFormSchema.safeParse(VALID_PAYLOAD);
  assert(result.success, `Expected success but got: ${JSON.stringify(result.error)}`);
});

// TP-2: Empty role
test('rejects empty role', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, role: '' });
  assert(!result.success, 'Expected failure for empty role');
  const msgs = result.error.issues.map(i => i.message);
  assert(msgs.includes('Role is required'), `Expected "Role is required" but got: ${msgs}`);
});

// TP-3: Short goal
test('rejects short goal (< 10 chars)', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, goal: 'short' });
  assert(!result.success, 'Expected failure for short goal');
  const msgs = result.error.issues.map(i => i.message);
  assert(
    msgs.some(m => m.includes('10 characters')),
    `Expected min 10 chars message but got: ${msgs}`
  );
});

// TP-4: Short backstory
test('rejects short backstory (< 10 chars)', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, backstory: 'too short' });
  assert(!result.success, 'Expected failure for short backstory');
  const msgs = result.error.issues.map(i => i.message);
  assert(
    msgs.some(m => m.includes('10 characters')),
    `Expected min 10 chars message but got: ${msgs}`
  );
});

// TP-5: Max iterations range
test('rejects maxIter > 10', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, maxIter: 15 });
  assert(!result.success, 'Expected failure for maxIter > 10');
});

test('rejects maxIter < 1', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, maxIter: 0 });
  assert(!result.success, 'Expected failure for maxIter < 1');
});

test('accepts maxIter at boundaries (1 and 10)', () => {
  const r1 = agentFormSchema.safeParse({ ...VALID_PAYLOAD, maxIter: 1 });
  assert(r1.success, `Expected success for maxIter=1: ${JSON.stringify(r1.error)}`);
  const r10 = agentFormSchema.safeParse({ ...VALID_PAYLOAD, maxIter: 10 });
  assert(r10.success, `Expected success for maxIter=10: ${JSON.stringify(r10.error)}`);
});

// TP-6: Boolean toggles
test('accepts all toggle variations', () => {
  const payload = { ...VALID_PAYLOAD };
  const toggleCases = [
    { verbose: true, reasoning: false, injectDate: true, memory: false },
    { verbose: false, reasoning: true, injectDate: false, memory: true },
    { verbose: false, reasoning: false, injectDate: false, memory: false },
  ];
  for (const toggles of toggleCases) {
    const result = agentFormSchema.safeParse({ ...payload, ...toggles });
    assert(result.success, `Expected success for toggles=${JSON.stringify(toggles)}: ${JSON.stringify(result.error)}`);
  }
});

// TP-7: Default values
test('applies default values correctly', () => {
  const defaults = {
    role: 'test',
    goal: 'this is a long goal that passes validation',
    backstory: 'this is a long backstory that passes validation',
  };
  const result = agentFormSchema.safeParse(defaults);
  assert(result.success, `Expected success with defaults: ${JSON.stringify(result.error)}`);
  const data = result.data;
  assert(data.llmProvider === undefined, 'llmProvider should be undefined');
  assert(data.allowedTools === undefined, 'allowedTools should be undefined');
  assert(data.maxIter === undefined, 'maxIter should be undefined');
});

// TP-8: Allowed tools
test('accepts empty allowedTools', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, allowedTools: [] });
  assert(result.success, `Expected success with empty tools: ${JSON.stringify(result.error)}`);
});

test('accepts string array for allowedTools', () => {
  const result = agentFormSchema.safeParse({ ...VALID_PAYLOAD, allowedTools: ['tool_a', 'tool_b'] });
  assert(result.success, `Expected success with tool array: ${JSON.stringify(result.error)}`);
});

// ── Summary ──────────────────────────────────────────────────────────────

console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

if (failed > 0) {
  console.error('❌ Some tests failed!');
  process.exit(1);
} else {
  console.log('✅ All schema validation tests passed.\n');
  process.exit(0);
}

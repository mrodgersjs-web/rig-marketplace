---
name: systematic-debugging
description: Systematic root-cause debugging for any bug, test failure, or unexpected behavior — evidence gathering, hypothesis testing, and verification before any fix is proposed.
trigger_conditions:
  - "Encountering any bug, test failure, or unexpected behavior, before proposing fixes"
  - "User reports something broken, throwing, failing, or slow"
  - "Standard troubleshooting has failed or the cause is non-obvious"
doctrine_package: rig-engineering
bms_mode: A1
---

# Systematic Debugging

## What it does

The systematic-debugging skill imposes the iron law of RIG debugging: NO FIXES WITHOUT ROOT CAUSE. It replaces the fix-guess-pray loop with a four-phase investigation — reproduce, isolate, hypothesize, verify — so that every fix lands on a proven mechanism, not on the first plausible-looking line of code.

The skill treats the bug report as a hypothesis to be falsified, not a fact. Reproduction comes first (if you cannot make it fail on demand, you cannot prove you fixed it), and the fix is only accepted when the reproduction no longer triggers AND the mechanism explains why.

## Workflow

1. Reproduce: capture the exact failing input, environment, and full error output; build the smallest deterministic reproduction.
2. Isolate: binary-search the search space — comment out halves, add logging at boundaries, bisect commits — until the failure localizes to one component.
3. Hypothesize: state 2-3 candidate mechanisms, each with a prediction that distinguishes it from the others; test the cheapest discriminator first.
4. Root-cause: trace the confirmed mechanism to the line and the reason — the code AND the assumption that made it wrong.
5. Fix at the source (never suppress the symptom), then verify: the reproduction no longer triggers, and a regression test now covers the contract.
6. Record the root cause and fix in the session notes so the next occurrence is a lookup, not an investigation.

## Done test

```bash
python3 - <<'PYEOF'
from pathlib import Path
src = (Path.home()/"Developer/needle-haystack/artifacts/skills/systematic-debugging/SKILL.md").read_text().lower()
for phase in ["reproduce", "isolate", "hypothesize", "root cause", "regression"]:
    assert phase in src, f"missing phase: {phase}"
print("PASS: all debugging phases present")
PYEOF
```

## Examples

**Example 1 — flaky test.** Test fails 1-in-20 runs. Reproduction harness loops it 200× and fails reliably. Isolation shows shared module-level state between tests; root cause is a leaked cache, not the assertion. Fix clears state in setup; regression test runs the pair in both orders.

**Example 2 — production 500s.** Errors cluster after deploy but the diff looks harmless. `git bisect` between last-good and HEAD points at one commit; hypothesis tests show the new serializer drops timezone info, and downstream code assumed UTC. Fixed at the serializer, verified in staging.

**Example 3 — slow endpoint.** p95 went 120ms → 3s with no code change. Boundary timing logs isolate the cost to one SQL query; EXPLAIN shows a seq scan after a stats estimate went stale. ANALYZE restores the plan; alert added on plan regression.

## References

- RIG adversarial-verification doctrine: refute the fix before accepting it
- git bisect: https://git-scm.com/docs/git-bisect
- Companion skills: tdd (regression test), diagnosing-bugs, parallel-debugging


## Rig Memory OS integration

Records `skill.invoked` events to rig-memory-os (tenant rig-default) on every run; proposes a memory candidate when the run produces a reusable fact. Run-id pattern: `systematic-debugging-run-<date>`.


## Planted failure

Feed the skill an input that violates its core contract. Expected RED: non-zero exit, the violated contract named in stderr, and a ProofPacket recording the violation. A green that cannot go red on this fixture is theater and the skill is unroutable.

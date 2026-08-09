---
name: meta-skill-refuter
description: Adversarially refutes any skill's done-test by planting a targeted failure and proving the test goes RED; a done-test that cannot be broken is declared theater and flagged for surgery.
trigger_conditions:
  - "a new or modified SKILL.md claims a passing done-test"
  - "rig-adversarial-verification doctrine requires a plant-failure pass before a skill is admitted or promoted"
doctrine_package: rig-adversarial-verification
bms_mode: A1
meta: true
diamond: D1
---

# Meta Skill Refuter

## Purpose
This is a META skill: it operates on other skills' done-tests, never on content. For a given SKILL.md it constructs the minimal input mutation that should break the done-test, runs it, and demands RED. Skeptic-by-default: it tries to REFUTE the claim "this done-test guards anything" before accepting it.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "escape_rate = |{p in Planted : exit(done_test, p) == 0}| / |Planted|"
  symbols: [escape_rate, Planted, done_test, exit]
  assumptions:
    - "planted failures are drawn from the skill's own declared planted-failure class plus 2 generated mutants"
    - "done-test is deterministic: identical inputs give identical exit codes"
    - "the done-test runs in an environment identical to the author's (no dependency drift between plant and run)"
  reference_population: "escape-rate distribution across all skills already admitted to artifacts/skills/ (expected: point mass at 0)"
  estimator: "robust_madz"
  expected_result: "escape_rate == 0 for every planted failure; the skill's MAD-z on escape_rate equals the catalog baseline exactly (all admitted skills sit at 0)"
  falsifier: "any planted failure exits 0 — the done-test has a hole and the skill's GREEN history is non-evidence; or every input including the pristine artifact exits non-zero — the done-test is a tautological RED and equally theater"
```

## Workflow
1. Parse the target SKILL.md; extract the done-test command and the declared planted-failure fixture.
2. Run the declared planted fixture through the done-test; require non-zero exit and record the stderr signature.
3. Generate 2 additional mutants (truncate the artifact the test reads; corrupt the command's expected output token) and run each — require RED on both.
4. Run the pristine artifact through the done-test — require GREEN (guard against tautological-RED tests).
5. Compute escape_rate and MAD-z against the catalog baseline; verdict = PASS (escape_rate 0, pristine GREEN), REFUTED (any escape), or THEATER (pristine also RED).
6. On REFUTED or THEATER, emit a surgery ticket for meta-skill-surgeon and block catalog admission.

## Rig Memory OS integration
Records `memory.record_event("meta_skill_refuter", {skill, verdict, escape_rate, mutants_tried})` per run; calls `memory.propose_memory` when a mutant class (e.g. truncated-artifact) escapes multiple distinct done-tests, indicating a systemic gate weakness worth a doctrine-level fix.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py refute-check --target artifacts/meta/fixtures/refuter_canary_skill.md --expect-escape 1
```

## Planted failure
The fixture `refuter_canary_skill.md` is a canary skill whose done-test is `true` (always exits 0). refute-check plants 3 failures against it; a correct refuter detects escape_rate = 1.0 and exits non-zero printing `REFUTED: done-test escapes 3/3 planted failures (exit 0 on broken input) — gate is theater`. If refute-check exits 0 on the canary, the refuter itself has been neutered and the run is RED.

## Examples
```
/refuter audit artifacts/skills/agent-task-router/SKILL.md --mutants 2
/refuter sweep --catalog artifacts/skill_catalog.json --fail-fast
```

## Install
```bash
needle install meta-skill-refuter
```

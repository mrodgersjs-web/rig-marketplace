---
name: meta-harness-refuter
description: Plant-failure verify every capability gate in a harness — break exactly what each gate guards, demand RED, restore, and keep the planted failure as a permanent regression case.
trigger_conditions:
  - "refute this harness"
  - "verify the gates actually fail"
  - "plant-failure audit"
  - "a green gate that has never gone red"
doctrine_package: rig-adversarial-verification
bms_mode: A1
meta: true
diamond: D2
---

# Meta Harness Refuter

## Purpose
This is a META skill: it attacks harnesses, not content. For every capability gate in a target harness it plants the exact failure the gate claims to guard, requires the gate to return RED, restores the valid state, and archives the planted failure as a permanent regression case. A gate that cannot go RED is theater, and this skill's default posture is to refute, never to confirm the builder's claim.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "refutation_rate = |gates_red_on_plant| / |gates_planted|, z = 0.6745 * (refutation_rate - median(R)) / mad(R)"
  symbols: [refutation_rate, gates_red_on_plant, gates_planted, R, z]
  assumptions:
    - "R = per-harness refutation-rate distribution across previously verified harnesses is the baseline"
    - "each planted failure is independent and targets exactly one gate's guard condition"
    - "a gate that returns RED for reasons unrelated to the plant is counted as NOT verified (right red, wrong reason)"
  reference_population: "refutation rates of harnesses that passed prior D2 adversarial audits"
  estimator: robust_madz
  expected_result: "refutation_rate = 1.0 with each RED trace naming the planted input; the harness then returns GREEN on restoration"
  falsifier: "if all gates show green, or a gate goes RED without the planted input being the cause, the harness fails refutation and the refuter must NOT certify it"
```

## Workflow
1. Parse the harness manifest; enumerate every capability gate and its stated guard condition.
2. For each gate, construct the minimal planted failure — the smallest input that violates exactly that guard and nothing else.
3. Execute the gate against the plant; require RED and require the RED output to reference the planted condition (right red, right reason).
4. Restore the valid fixture; require GREEN; archive the plant as a permanent regression case alongside the harness.
5. Compute refutation_rate and its robust z against the catalog baseline via MathExec.
6. Emit the refutation report: per-gate RED/GREEN transcripts, archived plant paths, and the D2 verdict (REFUTED = failed; SURVIVED = certified).

## Rig Memory OS integration
Records each refutation via `memory.record_event("harness_refutation", {harness, gates, refutation_rate, verdict})` and proposes recurring theater-gate shapes via `memory.propose_memory("theater_pattern", ...)` so future refuters start with a known-bad taxonomy.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py deviation --score 1.0 --baseline "0.6,0.75,0.8,0.85,0.9"
```
The self-test proves the estimator layer; the deviation call proves a refutation_rate of 1.0 is correctly recognized as above the historical baseline. The planted-failure case below MUST go RED.

## Planted failure
Fixture: a theater gate — e.g. a "done" gate implemented as `exit 0` unconditionally. The refuter plants the guarded failure (a broken artifact the gate claims to check) and the gate still returns GREEN. Expected RED output: `REFUTED: gate 'done' returned GREEN on planted failure plant-01; theater gate; harness NOT certified`, refutation_rate < 1.0, verdict = REFUTED. If the refuter certifies a harness containing an `exit 0` gate, the refuter itself is RED.

## Examples
```
needle run meta-harness-refuter --harness artifacts/harnesses/cold-send-review.md
needle run meta-harness-refuter --harness weekly-retro --archive-plants --verdict
```

## Install
```bash
needle install meta-harness-refuter
```

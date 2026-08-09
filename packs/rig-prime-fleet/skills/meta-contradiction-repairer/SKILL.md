---
name: meta-contradiction-repairer
description: Collide the strongest positive and negative outliers of a deviation search into one coherent surviving candidate instead of discarding the negative tail.
trigger_conditions:
  - "a deviation run archives a strong negative-tail candidate (D-C tail) without repair"
  - "two candidates with opposite-signed certified_z both exceed the coherence threshold"
  - "a mesh run produces a contradiction pair that blocks synthesis"
doctrine_package: rig-deviate
bms_mode: A1
meta: true
diamond: D2
---

# Meta Contradiction Repairer

## Purpose
This is a META skill: it operates on deviation-search candidates, not on primary content. In the RIG pipeline the negative tail (D-C) is normally archived; this skill instead takes the strongest positive outlier and the strongest negative outlier, forces a collision between their claims, and repairs the contradiction into a single coherent survivor that preserves the mechanism of both. A repaired survivor must score as non-contradictory and must remain a certified deviation, not a regression to the median.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "residual(s) = |z_pos(s) + z_neg(s)| / (|z_pos(s)| + |z_neg(s)|), survivor passes iff residual < tau and |z_certified(s)| >= z_min"
  symbols: [z_pos, z_neg, residual, tau, z_min, s]
  assumptions:
    - "contradiction is measurable as signed-score opposition on shared claims"
    - "tau = 0.25 is the coherence threshold; z_min = 2 is the minimum certified deviation"
    - "repair never averages claims; it restructures them so both mechanisms survive"
  reference_population: "residual distribution of previously repaired survivor candidates across D-C repair runs"
  estimator: "robust_madz"
  expected_result: "survivor residual < 0.25 and its certified_z vs the repair-history population stays in a deviation band (|z| >= 2, not median-collapsed)"
  falsifier: "residual >= tau (contradiction unrepaired) or the survivor's certified_z collapses toward 0 (repaired into generic median output)"
```

## Workflow
1. Pull the strongest positive-tail candidate and strongest negative-tail candidate from the deviation run (by |certified_z|).
2. Extract the load-bearing claims of each and align them pairwise; mark claim pairs whose signed scores oppose.
3. Force the collision: for each opposing pair, identify the mechanism each claim protects and restructure so both mechanisms hold (reframe, re-scope, or sequence — never average).
4. Emit one survivor candidate with a repair log mapping every opposing pair to its resolution.
5. Score the survivor: compute residual, then run MathExec deviation against the repair-history population; require residual < tau and certified deviation preserved.
6. Route the survivor to genome writing; route unrepairable pairs back to the deviator with the failure mode attached.

## Rig Memory OS integration
Each repair calls `memory.record_event` with `type: contradiction_repair`, the pair ids, residual, survivor certified_z, and verdict. Repeated unrepairable pairs are submitted via `memory.propose_memory` as known hard-contradiction patterns to bias future deviator runs away from them.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py deviation --score 3 --baseline "1,2,3,4,5"
```
The second command certifies the baseline deviation path used to score a survivor (score 3 vs baseline 1..5 sits near the median — the repair-history control). The planted-failure fixture below must drive the same path RED.

## Planted failure
Feed the repairer an unrepaired pair — a survivor whose opposing claims were averaged instead of restructured, represented by a score that cannot deviate from any baseline:
`python3 artifacts/meta/mathexec_substrate.py deviation --score 1 --baseline "1,1,1,1,1"`
Expected RED output: the zero-variance baseline makes every estimator return `Infinity`, so the conservative minimum collapses to `certified_z: 0.0` with band `commodity` — the survivor is uncertifiable and indistinguishable from the baseline. The repairer reports `MEDIAN_COLLAPSE: survivor indistinguishable from baseline` with verdict `REJECT`, refusing to route the candidate to genome writing.

## Examples
```
/meta-contradiction-repairer run=dev-0412 pos=cand-17 neg=cand-03
/meta-contradiction-repairer pair=claims.json --residual-only
```

## Install
```bash
needle install meta-contradiction-repairer
```

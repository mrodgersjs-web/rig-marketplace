---
name: meta-deviation-scorer
description: Run certified robust deviation scoring (MAD, Qn, bootstrap, alternate-corpus minimum) on any artifact as a hard proof gate.
trigger_conditions:
  - "any artifact claims a deviation, amplification, or outlier result and needs certification"
  - "a proof gate requires a conservative multi-estimator z-score before admission"
  - "an estimator disagreement or adversarial perturbation result needs arbitration"
doctrine_package: rig-proof-gates
bms_mode: A1
meta: true
diamond: D3
---

# Meta Deviation Scorer

## Purpose
This is a META skill: it operates on artifacts and their claims, not on content generation. It is the certified scoring gate behind every other meta-skill: given an artifact's score and a reference baseline, it computes robust deviation across four estimators — MAD-Z, Qn-Z, bootstrap lower bound, and an alternate-corpus z — and returns only the conservative minimum. Thirty sigma is the wall, not the floor: the gate searches toward ±30σ but never auto-passes at the wall.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "z_certified = min(z_MAD, z_Qn, z_bootstrap_lower, z_alternate_corpus)"
  symbols: [z_certified, z_MAD, z_Qn, z_bootstrap_lower, z_alternate_corpus]
  assumptions:
    - "the baseline population is representative of the artifact's comparison class"
    - "robust estimators tolerate up to ~25% contamination in the baseline"
    - "the minimum across estimators is the honest, adversary-resistant claim — never the mean or max"
  reference_population: "the caller-supplied baseline distribution plus an alternate corpus drawn from a different but comparable source"
  estimator: "robust_madz"
  expected_result: "adversarial battery (leave-one-out, perturbation, estimator swap) preserves the band classification; certified_z is stable under attack"
  falsifier: "any single leave-one-out or perturbation flips the band, or estimators disagree by more than an order of magnitude — the claim is fragile, not certified"
```

## Workflow
1. Ingest the artifact's claimed score and the reference baseline; validate the baseline (size ≥ 5, non-degenerate variance).
2. Compute z_MAD and z_Qn against the baseline, and the bootstrap lower-confidence z.
3. Draw the alternate corpus and compute z_alternate_corpus; take z_certified = min of all four.
4. Run the adversarial battery: leave-one-out per baseline point, score perturbations, and estimator swap; confirm the band never flips.
5. Classify the band (weak/strong/extreme, positive or negative tail) and emit the verdict with the full estimator breakdown.
6. Seal the result as a proof artifact (score, baseline hash, estimator table, adversarial log) for the calling gate.

## Rig Memory OS integration
Each scoring call is logged via `memory.record_event` with `type: deviation_scored`, the artifact id, z_certified, band, and adversarial stability flag. Fragile-claim patterns (band flips under leave-one-out) are submitted via `memory.propose_memory` so future gates can pre-emptively demand larger baselines.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py adversarial --score 42 --baseline "1,2,3,4,5"
```
The second command runs the full adversarial battery on a strong outlier claim — expected: all leave-one-out z values stay in the same extreme band (stable certification). The planted-failure fixture — a degenerate baseline — must drive the gate RED.

## Planted failure
Feed the scorer a baseline with zero variance, which makes every robust estimator undefined:
`python3 artifacts/meta/mathexec_substrate.py deviation --score 5 --baseline "3,3,3,3,3"`
Expected RED output: every estimator returns `Infinity`, so the conservative minimum collapses to `certified_z: 0.0` with band `commodity` — no finite deviation is certifiable. The scorer reports `BASELINE_DEGENERATE: zero variance — claim uncertifiable (certified_z=0.0, band=commodity)` with verdict `BLOCK`, refusing admission regardless of the claimed score.

## Examples
```
/meta-deviation-scorer artifact=skill-x score=42 baseline=history/skills.csv
/meta-deviation-scorer claim=A40 --adversarial-only
```

## Install
```bash
needle install meta-deviation-scorer
```

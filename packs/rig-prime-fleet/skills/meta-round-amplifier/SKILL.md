---
name: meta-round-amplifier
description: Run one full 1000x improvement round on any asset class — skills, harnesses, or agents — with certified before/after amplification.
trigger_conditions:
  - "an asset class is scheduled for a 1000x improvement round"
  - "a skill, harness, or agent has accumulated enough scored findings to justify an amplification pass"
  - "a previous round's amplification factor needs re-certification after upstream changes"
doctrine_package: rig-doctrine
bms_mode: A1
meta: true
diamond: D2
---

# Meta Round Amplifier

## Purpose
This is a META skill: it operates on skills, harnesses, and agents as assets, never on their content directly. It executes one complete 1000x improvement round — audit, rank, amplify, re-score — against a target asset class and certifies that the round actually moved quality, rather than churning it. A round that cannot show a certified amplification factor over the asset's own history is reported as noise, not progress.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "A = Q_after / Q_before, round counts iff A > 1 AND certified_z(A) vs round-history population is in a positive deviation band"
  symbols: [A, Q_after, Q_before, certified_z]
  assumptions:
    - "Q is the composite quality score from the asset's own gates (proof-gates, health, adversarial checks)"
    - "Q_before is frozen before the round starts; no retroactive re-baselining"
    - "round history across the asset class is a valid reference population for A"
  reference_population: "amplification factors of all completed rounds on the same asset class"
  estimator: "robust_madz"
  expected_result: "A > 1 and certified_z of A is a certified positive deviation vs round history (not within normal band)"
  falsifier: "A <= 1 (the round degraded or stalled the asset) or A is large but statistically indistinguishable from the round-history population"
```

## Workflow
1. Freeze the target asset class baseline: run its gates, record Q_before and the round-history population.
2. Audit every asset in the class; rank findings by leverage (highest quality delta per unit change).
3. Apply the top-N amplifications (rewrite, rewire, or re-score each asset) with each change tied to a finding id.
4. Re-run the full gate suite to produce Q_after; compute A = Q_after / Q_before.
5. Certify A with MathExec deviation against the round-history population using the conservative minimum estimator.
6. If certified, append A to round history and emit a round report; if not, roll back the lowest-leverage changes and report honestly.

## Rig Memory OS integration
Every round calls `memory.record_event` with `type: amplification_round`, the asset class, Q_before, Q_after, A, certified_z, and verdict. Certified high-A rounds are submitted via `memory.propose_memory` as amplification playbooks reusable on other asset classes.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py deviation --score 40 --baseline "1.1,1.2,1.05,1.3,1.15,1.1,1.2"
```
The second command certifies that a claimed A = 40 amplification is a genuine positive deviation vs typical round history (~1.1–1.3x) — expected: large positive certified_z (`ceiling_breach` band), proving the detector fires for real amplification. The planted-failure fixture — a round that produced no improvement — must drive the same gate RED.

## Planted failure
Run a round whose changes are pure churn (renames, comment edits) so A ≈ 1, or equivalently feed the gate a flat claim:
`python3 artifacts/meta/mathexec_substrate.py deviation --score 1.15 --baseline "1.1,1.2,1.05,1.3,1.15,1.1,1.2"`
Expected RED output: certified_z sits inside the normal band (|z| < 2, no deviation), and the amplifier reports `ROUND_NOT_CERTIFIED: A=1.15 indistinguishable from round history` with verdict `NO_CREDIT` — the round is not counted and history is not updated.

## Examples
```
/meta-round-amplifier class=skills top_n=10
/meta-round-amplifier class=agents --certify-only round=2026-08-r3
```

## Install
```bash
needle install meta-round-amplifier
```

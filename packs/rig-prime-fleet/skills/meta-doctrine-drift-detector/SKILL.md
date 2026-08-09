---
name: meta-doctrine-drift-detector
description: Detect when any skill, agent, or harness has drifted from the load-bearing claims of its declared doctrine package, with two-sided file:line evidence.
trigger_conditions:
  - "a doctrine file changed and surfaces must be re-checked"
  - "drift audit"
  - "verify skills match doctrine"
  - "before onboarding a new skill/agent/harness into the catalog"
doctrine_package: rig-doctrine
bms_mode: A1
meta: true
diamond: D1
---

# Meta Doctrine Drift Detector

## Purpose
This is a META skill: it operates on the skill/agent/harness catalog, not on content. It diffs every operational surface's declared `doctrine_package` against the canonical doctrine files and flags contradictions, stale values, orphaned references, and dead doctrine before drift compounds. It never fixes surfaces — it emits the drift report that gates any "ecosystem is consistent" claim.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "z_drift = 0.6745 * (n_drifted - median(N)) / mad(N)"
  symbols: [n_drifted, N, median, mad]
  assumptions:
    - "N = per-surface drift-finding counts over the last 30 audit runs forms the baseline"
    - "drift counts are heavy-tailed; robust estimators required"
    - "a surface with zero findings in a clean tree is a reference point, not an anomaly"
  reference_population: "distribution of per-surface drift-finding counts across the catalog's last 30 audits"
  estimator: robust_madz
  expected_result: "clean catalog audit produces |z_drift| < 3 for every surface; seeded-drift fixture produces z_drift >> 30 on the tampered surface"
  falsifier: "if a surface that no longer references its doctrine at all scores |z_drift| < 3, the detector is blind and the claim is false"
```

## Workflow
1. Enumerate the operational surface: every SKILL.md, agent spec, and harness manifest with a `doctrine_package` field; resolve each to its canonical doctrine files.
2. Extract load-bearing claims from each doctrine file: named rules, numeric thresholds, routing tables, banned patterns.
3. Grep each surface for references to each claim (by name, threshold value, or quoted rule) and classify findings: contradiction > stale > orphan > dead doctrine.
4. Score each surface's finding count against the 30-audit baseline via the MathExec deviation pass (`deviation --score <n> --baseline <counts>`).
5. Emit the drift report: every finding carries BOTH a doctrine-side and a surface-side file:line citation, plus the z-score per surface.
6. Record the audit to Rig Memory OS; surfaces with z_drift >= 30 are escalated as blocking.

## Rig Memory OS integration
Records each audit via `memory.record_event("drift_audit", {surfaces, findings, z_scores})` and proposes newly discovered stale-threshold patterns via `memory.propose_memory("doctrine_drift_pattern", ...)` so future audits seed their grep pass with known drift shapes.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py deviation --score 12 --baseline "0,0,1,0,2,0,1,0,0,1"
```
The self-test proves the math layer is sound; the deviation call proves a 12-finding surface against a near-zero baseline is detected as extreme deviation (z_drift >> 30). The planted-failure case (below) MUST go RED.

## Planted failure
Fixture: a surface file whose `doctrine_package: rig-doctrine` but whose body references `threshold: 0.85` while canonical doctrine declares `threshold: 0.95` (a stale-value contradiction). Expected RED output: the detector emits severity=contradiction with doctrine-side and surface-side file:line, and the deviation pass on the tampered baseline `"0,0,1,0,12,0,1"` returns certified z_drift well above 30 — i.e. the audit FAILS the consistency gate. If the tampered value passes silently, the detector itself is RED.

## Examples
```
needle run meta-doctrine-drift-detector --doctrine_dir doctrine/ --surface_dir artifacts/skills/
needle run meta-doctrine-drift-detector --surface artifacts/skills/meta-harness-forge --since 2026-07-01
```

## Install
```bash
needle install meta-doctrine-drift-detector
```

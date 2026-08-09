---
name: meta-sigma-band-router
description: Route any deviation candidate to its certified sigma band (commodity → ceiling breach) using the conservative certified_z and the Deviatrix band table. This is a META skill — it routes candidates produced by other skills; it never authors them.
trigger_conditions:
  - "A candidate artifact needs routing to a sigma band before review or archive"
  - "A deviate/mesh run asks which engine or gate a scored candidate must go to"
  - "Any score claims extreme deviation (|z| >= 10) and needs band-certified handling"
doctrine_package: rig-deviate
bms_mode: A1
meta: true
diamond: D3
---

# Meta Sigma Band Router

## Purpose

This is a META skill: it operates on scored candidates flowing through the RIG deviate pipeline, not on content. It computes the certified z-score — the conservative minimum across z_MAD, z_Qn, and the bootstrap lower bound — and routes the candidate to exactly one band and its mandated action, from `commodity` (Anti-Median Engine) through `ceiling_breach` (HARD STOP, no auto-pass). Routing is deterministic: the same score and baseline always land in the same band.

## Math claim (Deviatrix MathExec)

```yaml
math_claim:
  expression: "z_cert = min(z_MAD, z_Qn, z_boot_lower);  z_MAD = 0.6745 * (x - median(X)) / MAD(X)"
  symbols: [z_cert, z_MAD, z_Qn, z_boot_lower, x, X, median, MAD]
  assumptions:
    - "baseline X is a real reference population of comparable artifact scores, not a curated friendly set"
    - "MAD(X) > 0; a zero-MAD baseline is rejected, never silently rescaled"
    - "certified z is the minimum across estimators, so routing errs toward the less impressive band"
  reference_population: "the baseline corpus of scored artifacts for the same engine and artifact type"
  estimator: "robust_madz"
  expected_result: "each candidate maps to exactly one band in {commodity, differentiated_ordinary, strong_deviation, category_shaping, extreme_tail, ceiling_breach, weak_antipattern, material_failure, strong_destructive, extreme_anti_idea} with its table-mandated action"
  falsifier: "any candidate routed to a band whose |z| interval does not contain z_cert, or any |z| >= 30 candidate that receives an auto-pass action instead of HARD STOP"
```

## Workflow

1. Take the candidate score `x` and the baseline population `X` (and optional alternate corpus).
2. Compute estimator triplet via `mathexec_substrate.py deviation --score x --baseline X`; `certified_z = min` of finite estimators.
3. Look up the band in the Deviatrix routing table: z>=30 or z<=-30 → ceiling_breach (HARD STOP); z>=20 → extreme_tail (Mike-gated); z>=10 → category_shaping (adversarial proof required); z>=5 → strong_deviation (deep review); z>=3 → differentiated_ordinary (Collision Engine); z>=0 → commodity (Anti-Median Engine); negative tails route to the failure/countermodel/hostile-testing archives.
4. For |z| >= 10, additionally require `mathexec_substrate.py adversarial` perturbation stability before the band is certified.
5. Emit the routing record `{z_cert, band, action, target}` and record the event via rig-memory-os.

## Rig Memory OS integration

Each routing decision is recorded via `memory.record_event(kind="band_routed", z_cert=..., band=..., action=...)`. Repeated ceiling-breach claims from the same source are proposed via `memory.propose_memory(...)` as a calibration warning against that baseline.

## Done test

```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 -c "
import json, subprocess
def band(score):
    out = subprocess.run(['python3','artifacts/meta/mathexec_substrate.py','deviation','--score',str(score),'--baseline','0.1,-0.2,0.3,0.0,0.2,-0.1,0.15,-0.05,0.25,-0.15'],capture_output=True,text=True).stdout
    d = json.loads(out); return d['band'], d['action']
b35, a35 = band(35); assert b35 == 'ceiling_breach' and 'HARD STOP' in a35, f'35σ misrouted: {b35}'
b0, _ = band(0.05); assert b0 in ('commodity','weak_antipattern'), f'median member inflated to: {b0}'
b5, _ = band(3.2); assert b5 in ('strong_deviation','differentiated_ordinary'), f'unexpected: {b5}'
print(f'ROUTER OK: 35σ→{b35}/HARD-STOP, median→{b0} (near-zero band)')"
```

## Planted failure

Fixture: score `x = 35` against any baseline. The router MUST return band `ceiling_breach` with action containing `HARD STOP` and MUST NOT auto-pass. If the done-test prints anything like `35σ→commodity` or an auto-pass action, that is the RED state — expected RED output is the assertion `AssertionError: 35σ misrouted: <band>` with non-zero exit. Second fixture: `x` equal to the baseline median must land in a near-zero band (`commodity` or `weak_antipattern` — the conservative certified minimum across estimators may dip slightly negative via the bootstrap lower bound); routing a median member to `strong_deviation` or higher proves the estimator is inflated.

## Examples

- `meta-sigma-band-router route --score 3.2 --baseline-file corpora/landing_pages.jsonl` → `{"certified_z": 9.56, "band": "strong_deviation", "action": "Deep review"}`.
- `meta-sigma-band-router route --score 41 --baseline-file corpora/taglines.jsonl` → `ceiling_breach / HARD STOP — verify baseline and physics; no auto-pass`.

## Install

```bash
needle install meta-sigma-band-router
```

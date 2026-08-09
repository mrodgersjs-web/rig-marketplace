---
name: meta-harness-forge
description: Author a new 5-section goal harness from a session-type spec, with executable gates, a done-test, and a planted-failure case forged in from the start.
trigger_conditions:
  - "forge a harness for <session type>"
  - "new goal harness"
  - "this session type has no harness"
  - "author a gate loop"
doctrine_package: rig-harnesses
bms_mode: A1
meta: true
diamond: D2
---

# Meta Harness Forge

## Purpose
This is a META skill: it manufactures harnesses, not content. Given a session-type spec (goal shape, failure modes, required evidence), it forges a complete 5-section goal harness — gates, evidence requirements, done-test, planted failure, and install stanza — that conforms to the RIG harness contract. A forged harness is not done when it renders; it is done when its own gates demonstrably go RED on the planted failure.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "coverage = |gates_plant_verified| / |gates_total|, z = 0.6745 * (coverage - median(C)) / mad(C)"
  symbols: [coverage, gates_plant_verified, gates_total, C, z]
  assumptions:
    - "C = gate-coverage distribution across the existing harness catalog is the baseline"
    - "a gate without a planted-failure verification counts as unverified, regardless of green output"
    - "coverage = 1.0 is achievable and required for D2 certification"
  reference_population: "per-harness verified-gate coverage ratios across the installed harness catalog"
  estimator: robust_madz
  expected_result: "forged harness has coverage = 1.0 (every gate plant-failure verified RED-then-GREEN) and scores at or above the catalog median"
  falsifier: "if a harness ships with any gate whose planted failure still returns GREEN and the forge reports success, the forge's quality gate is false"
```

## Workflow
1. Parse the session-type spec: goal shape, known failure modes, evidence types, irreversibility boundary (where Gate-D sits).
2. Select the gate set: map each failure mode to a gate that must produce evidence before the session advances; never invent gates that produce no evidence.
3. Forge the 5 sections: Purpose, Gates (each with executable check), Done test, Planted failure, Install — following the canonical harness template.
4. For every gate, write the input that makes it RED and verify RED; then verify GREEN on the valid path (plant-failure discipline, inherited from rig-adversarial-verification).
5. Compute gate coverage against the catalog baseline via MathExec; certify D2 only at coverage = 1.0.
6. Emit the harness file + the RED/GREEN verification transcript.

## Rig Memory OS integration
Records each forge via `memory.record_event("harness_forged", {session_type, gates, coverage, certified})` and proposes reusable gate shapes via `memory.propose_memory("gate_pattern", ...)` when a forged gate generalizes beyond its session type.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py symbolic --expression "coverage = gates_plant_verified / gates_total" --symbols coverage gates_plant_verified gates_total
```
The self-test proves the math layer; the symbolic pass proves the coverage formula the forge certifies against parses and simplifies cleanly. The planted-failure case below MUST go RED.

## Planted failure
Fixture: a session-type spec deliberately missing its irreversibility boundary (e.g. a "publish" session type with no Gate-D equivalent). The forge MUST refuse certification: expected RED output is `FORGE-RED: unguarded irreversible action in spec — no gate covers 'publish'; coverage gate fails` and no harness file is emitted. If a harness ships covering zero irreversible actions, the forge itself is RED.

## Examples
```
needle run meta-harness-forge --spec session-types/cold-send-review.yaml --out artifacts/harnesses/
needle run meta-harness-forge --session-type "weekly metrics retro" --certify D2
```

## Install
```bash
needle install meta-harness-forge
```

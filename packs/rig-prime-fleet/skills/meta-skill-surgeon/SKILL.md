---
name: meta-skill-surgeon
description: Executes Council verdicts by cutting skills that lack executable done-tests or fail refutation, with a dry-run amputation report before any deletion lands.
trigger_conditions:
  - "a Council verdict marks a skill for excision (no executable done-test, REFUTED, or THEATER verdict)"
  - "a scheduled governance sweep finds catalog skills whose done-tests no longer execute"
doctrine_package: rig-governance
bms_mode: A1
meta: true
diamond: D1
---

# Meta Skill Surgeon

## Purpose
This is a META skill: it operates on the skill catalog, not on content. It is the Council's verdict executor — given a list of condemned skills it verifies each condemnation is still factually true (re-runs the evidence), produces an amputation report, then removes the skill directory and its catalog entry. It never cuts on stale evidence.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "precision = TP / (TP + FP) where FP = skills cut whose done-test executes GREEN on re-verification"
  symbols: [precision, TP, FP, cut_set]
  assumptions:
    - "every cut is preceded by a fresh re-verification within the same run (no stale verdicts)"
    - "the condemned set is a strict subset of the catalog, disjoint from protected core skills"
    - "catalog writes are atomic (write-temp-then-rename), so a crashed cut cannot corrupt the index"
  reference_population: "historical excision precision across prior governance sweeps (baseline: 1.0 — no false amputations tolerated)"
  estimator: "robust_madz"
  expected_result: "precision == 1.0; every removed skill was re-confirmed non-executable or REFUTED at cut time; MAD-z of cut-set size vs historical sweep sizes within |z| < 3 (no mass-amputation anomaly)"
  falsifier: "any skill is removed whose done-test re-verified GREEN in the same run, or the cut-set size MAD-z exceeds +3 — the surgeon is amputating healthy tissue or has become a mass-deletion event"
```

## Workflow
1. Ingest the Council verdict list (skill names + condemnation class + evidence pointer).
2. Re-verify each condemned skill live: parse its done-test block, attempt execution, and re-run refutation where applicable. Discard any verdict that no longer reproduces.
3. Emit a dry-run amputation report: skill, condemnation class, fresh evidence exit codes, files to be removed, catalog diff.
4. On confirmation, remove skill directories, atomically rewrite skill_catalog.json, and record removals in install_manifest.json as negative entries.
5. Compute precision and cut-set MAD-z; seal the run as a ProofPacket with the dry-run report attached.
6. If precision < 1.0 or the MAD-z anomaly trips, halt mid-batch, restore the atomic backup, and escalate.

## Rig Memory OS integration
Records `memory.record_event("meta_skill_surgeon", {cut_count, restored, precision, proofpacket})` per sweep; calls `memory.propose_memory` with the recurring condemnation classes so genesis templates can be hardened against producing cuttable skills in the first place.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py surgeon-check --verdicts artifacts/meta/fixtures/surgeon_verdicts.json --catalog artifacts/meta/fixtures/surgeon_catalog_copy.json --dry-run
```

## Planted failure
The fixture `surgeon_verdicts.json` condemns 3 skills, but `surgeon_catalog_copy.json` contains one ("healthy-skill") whose done-test re-verifies GREEN. Expected RED output: `REFUTED: verdict for healthy-skill does not reproduce (done-test exits 0) — precision guard tripped, batch halted`, exit code 1, and the catalog copy must remain byte-identical. If the surgeon proceeds to cut anyway, the guard is dead and the run is RED.

## Examples
```
/surgeon execute --verdicts council/2026-08-08-verdicts.json --confirm
/surgeon dry-run --sweep stale-done-tests --catalog artifacts/skill_catalog.json
```

## Install
```bash
needle install meta-skill-surgeon
```

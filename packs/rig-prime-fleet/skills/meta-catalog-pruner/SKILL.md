---
name: meta-catalog-pruner
description: Closed-taxonomy enforcement gate — rejects any skill, package, or doctrine entry that falls outside the 14 canonical packages; package #15 is refused by construction.
trigger_conditions:
  - "a new skill or package is proposed for catalog admission"
  - "a catalog sweep detects an entry whose doctrine_package is not one of the 14 canonical packages"
doctrine_package: rig-governance
bms_mode: A1
meta: true
diamond: D1
---

# Meta Catalog Pruner

## Purpose
This is a META skill: it operates on the catalog taxonomy, not on content. The taxonomy is closed at 14 canonical doctrine packages; this gate rejects any admission or mutation that would create package #15, an unnamed package, or a skill pointing at a non-existent package. It runs at admission time and as a sweep over the live catalog.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "violation_rate = |{e in Catalog : package(e) not in P14}| / |Catalog|"
  symbols: [violation_rate, Catalog, P14, package]
  assumptions:
    - "the canonical package list P14 is versioned and hash-pinned; the gate loads it from the pinned manifest, never from the catalog being checked"
    - "package membership is exact string match against P14 — no fuzzy matching, no aliases"
    - "catalog reads are consistent snapshots (no concurrent writer mid-sweep)"
  reference_population: "violation-rate distribution across all historical catalog snapshots (expected: point mass at 0 after gate installation)"
  estimator: "robust_madz"
  expected_result: "violation_rate == 0 on the live catalog; the admission path demonstrably rejects a #15 probe; MAD-z of package-count per snapshot stays at the 14-point baseline with zero variance"
  falsifier: "any probe carrying package #15 (or an unknown/empty package string) is admitted, or the sweep finds a live entry outside P14 — the taxonomy is open and every downstream per-package gate loses its meaning"
```

## Workflow
1. Load the pinned canonical package list P14 from the versioned manifest; verify its hash before trusting it.
2. Admission path: for each proposed entry, extract doctrine_package and require exact membership in P14; reject otherwise with the full P14 list in the error.
3. Sweep path: scan every entry in skill_catalog.json (and harness/agent catalogs) for package(e) ∈ P14; collect violations.
4. Compute violation_rate; any non-zero rate fails the gate and routes violations to meta-skill-surgeon as condemnation class `taxonomy-violation`.
5. Seal the sweep as a ProofPacket: P14 hash, entry count, violation list (empty), timestamp.

## Rig Memory OS integration
Records `memory.record_event("meta_catalog_pruner", {mode, entries, violations, p14_hash})` per admission decision and sweep; calls `memory.propose_memory` when repeated #15-style probes arrive from the same source, flagging a generator that needs its template constrained upstream.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py pruner-check --probe artifacts/meta/fixtures/package15_probe.json --p14 artifacts/meta/p14_manifest.json --expect-reject
```

## Planted failure
The probe fixture `package15_probe.json` is a well-formed skill admission request whose doctrine_package is `"rig-package-15"` — valid in every field except taxonomy. Expected RED output: `REJECTED: doctrine_package "rig-package-15" not in P14 (14 canonical packages) — package #15 refused by construction`, exit code 1, and the catalog must be untouched. If pruner-check exits 0 on the probe, the gate is open and the run is RED.

## Examples
```
/pruner admit artifacts/skills/new-skill/SKILL.md --p14 artifacts/meta/p14_manifest.json
/pruner sweep --catalogs artifacts/skill_catalog.json artifacts/harness_catalog.json artifacts/agent_catalog.json
```

## Install
```bash
needle install meta-catalog-pruner
```

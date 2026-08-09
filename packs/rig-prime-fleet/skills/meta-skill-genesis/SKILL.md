---
name: meta-skill-genesis
description: Generates a new meta-skill from a deviation expedition brief, wiring the done-test, planted-failure case, and memory hooks into the scaffold before any content is written.
trigger_conditions:
  - "a deviation expedition brief yields a candidate capability that must be captured as a meta-skill"
  - "the skill catalog lacks a meta-skill for a recurring operation on skills/harnesses/agents"
doctrine_package: rig-doctrine
bms_mode: A1
meta: true
diamond: D1
---

# Meta Skill Genesis

## Purpose
This is a META skill: it operates on skills, not on content. It converts a deviation expedition brief (target σ rung, engine, deviation class) into a fully scaffolded meta-skill with frontmatter, math claim, workflow, memory integration, done-test, and planted-failure case. Nothing it produces is allowed to exist without an executable done-test — genesis and gate are fused.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "z = (x - median(P)) / (1.4826 * MAD(P))"
  symbols: [x, P, z, MAD, median]
  assumptions:
    - "reference population P = done-test pass/fail distribution over all existing skills in the catalog"
    - "generated skill's done-test exit code is Bernoulli over repeated identical runs (determinism assumption)"
    - "MAD(P) > 0, i.e. the catalog is not uniformly passing or uniformly failing"
  reference_population: "exit-code and runtime distributions of all done-tests currently in artifacts/skills/*/SKILL.md"
  estimator: "robust_madz"
  expected_result: "the generated skill's done-test exits 0 on the real artifact and exits non-zero on the planted-failure fixture; its scaffold-completeness score sits at |z| >= 2 versus catalog baseline"
  falsifier: "the generated SKILL.md passes schema validation but its done-test cannot be made to go RED by the planted fixture, or goes RED on the unmodified artifact (a green that won't go red, or a red that won't go green, is theater)"
```

## Workflow
1. Parse the expedition brief: extract engine, target σ rung, deviation class, and the operation-on-skills being captured.
2. Pull the catalog baseline via mathexec_substrate.py: load all existing done-tests, compute the robust_madz reference distribution for scaffold completeness and runtime.
3. Draft the SKILL.md: frontmatter (name, trigger_conditions, doctrine_package, bms_mode, diamond), purpose, math claim, workflow, memory hooks, done-test, planted failure, examples, install.
4. Write the executable done-test first, then the body — never reverse. The done-test MUST include a planted-failure invocation.
5. Execute the done-test against the real artifact (expect GREEN) and against the planted-failure fixture (expect RED); record both exit codes.
6. Register the new skill in skill_catalog.json with its genesis provenance (brief id, σ rung, timestamp).

## Rig Memory OS integration
Records `memory.record_event("meta_skill_genesis", {skill, sigma_rung, green_exit, red_exit})` after every run, and calls `memory.propose_memory` when a generated skill's done-test shape recurs across 3+ expeditions (candidate for promotion into the genesis template itself).

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py genesis-check --skill artifacts/skills/meta-skill-genesis/SKILL.md --planted artifacts/meta/fixtures/genesis_broken_done_test.json
```

## Planted failure
Feed genesis-check the fixture `genesis_broken_done_test.json`, which describes a generated skill whose done-test is a comment-only bash block (no executable command). Expected RED output: `REFUTED: done-test block contains 0 executable statements — a green that cannot run is theater`, exit code 1. If genesis-check exits 0 on this fixture, the gate itself is broken.

## Examples
```
/genesis from brief EXP-2026-08-08-graviton-plus30 --sigma 30 --engine GRAVITON
/genesis dry-run --brief artifacts/meta/briefs/harness_auditor.md --no-catalog-write
```

## Install
```bash
needle install meta-skill-genesis
```

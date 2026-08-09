---
name: meta-agent-memory-binder
description: Wire a RIG agent into rig-memory-os so every action records, retrieves, proposes, and predicts against the shared memory substrate.
trigger_conditions:
  - "a new RIG agent is registered and lacks memory wiring"
  - "an agent's memory manifest is missing record/retrieve/propose/predict surfaces"
  - "a bound agent's round-trip latency drifts from the certified baseline"
doctrine_package: rig-memory
bms_mode: A1
meta: true
diamond: D2
---

# Meta Agent Memory Binder

## Purpose
This is a META skill: it operates on agents and their wiring, not on content. It takes an agent manifest (id, scopes, tools) and produces a complete, verified binding to rig-memory-os covering the four mandatory surfaces — `record_event`, `retrieve`, `propose_memory`, and `predict` — then certifies the binding with an executable round-trip test. An agent without all four surfaces is unbound and must not be admitted to the fleet.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "coverage = |S_bound| / |S_required|, S_required = {record, retrieve, propose, predict}"
  symbols: [S_bound, S_required, coverage]
  assumptions:
    - "the four memory surfaces are the complete required set for fleet admission"
    - "round-trip latency of a freshly bound agent is comparable to the fleet baseline population"
  reference_population: "round-trip latencies (ms) of already-bound fleet agents under A1 load"
  estimator: "robust_madz"
  expected_result: "coverage == 1.0 and certified_z of the agent's round-trip latency is within the normal band (|z| < 3)"
  falsifier: "any required surface returns UNBOUND, or the latency certified_z breaches +-3 sigma against the fleet baseline"
```

## Workflow
1. Load the agent manifest and enumerate its declared tools and scopes.
2. Diff declared surfaces against `S_required = {record_event, retrieve, propose_memory, predict}`; list every gap.
3. Generate the binding block (one `memory.*` call wiring per surface, with the agent's scope tags) and write it into the agent's config.
4. Execute a live round-trip: record a synthetic event, retrieve it by key, propose a derived memory, and request a prediction; assert all four succeed.
5. Measure round-trip latency and run MathExec deviation against the fleet baseline population; certify with the conservative minimum estimator.
6. Seal the binding in the agent manifest as `memory_binding: certified` only if coverage == 1.0 and the deviation gate is green.

## Rig Memory OS integration
On every bind attempt this skill calls `memory.record_event` with `type: agent_memory_bind`, the agent id, coverage, certified_z, and verdict. On success it also calls `memory.propose_memory` to register the new binding pattern as a reusable candidate for future agents.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py deviation --score 9 --baseline "10,11,9,10,12,9,11,10"
```
The second command certifies that a bound agent's 9ms round-trip sits inside the fleet baseline band (expected: normal/weak band, |certified_z| < 3). A planted-failure fixture — a manifest whose `predict` surface is unwired, represented by a latency far outside the baseline — must drive the gate RED.

## Planted failure
Feed the binder a manifest missing the `predict` surface, or equivalently run the deviation gate with an out-of-band latency:
`python3 artifacts/meta/mathexec_substrate.py deviation --score 900 --baseline "10,11,9,10,12,9,11,10"`
Expected RED output: `certified_z` breaches the band (large positive z, `ceiling_breach`/extreme band) and the binder reports `UNBOUND_SURFACE: predict` with verdict `REJECTED` — the agent is not admitted.

## Examples
```
/meta-agent-memory-binder agent=nadia scopes=[gtm,leads]
/meta-agent-memory-binder agent=darius --verify-only
```

## Install
```bash
needle install meta-agent-memory-binder
```

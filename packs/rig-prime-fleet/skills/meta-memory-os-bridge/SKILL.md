---
name: meta-memory-os-bridge
description: The canonical bridge by which any skill records events and proposes memories to rig-memory-os (memory.record_event / memory.propose_memory). This is a META skill — it standardizes how other skills talk to the memory layer; it stores no domain content of its own.
trigger_conditions:
  - "A skill needs to record an event (gate result, seal, routing decision, publish) to rig-memory-os"
  - "A skill needs to propose a durable memory (calibration warning, untrusted gate, broken chain)"
  - "A new skill is being authored and its Rig Memory OS integration section needs the canonical contract"
doctrine_package: rig-memory
bms_mode: A1
meta: true
diamond: D3
---

# Meta Memory OS Bridge

## Purpose

This is a META skill: it operates on skills' integration with the memory layer, not on content. It defines and enforces the single canonical contract — every skill records what happened via `memory.record_event(...)` and proposes what should be remembered via `memory.propose_memory(...)` — so no skill invents a private memory side-channel. It validates event payloads, rejects malformed ones loudly, and guarantees a recorded event is retrievable.

## Math claim (Deviatrix MathExec)

```yaml
math_claim:
  expression: "retrieval_rate = |{e in E : recall(e.id) = e}| / |E| = 1;  malformed_reject_rate = |{m in M : rejected(m)}| / |M| = 1"
  symbols: [E, e, recall, M, m, retrieval_rate, malformed_reject_rate]
  assumptions:
    - "every event has a unique id, a kind from the registered taxonomy, and a timestamp at record time"
    - "record_event is durable before it returns success; a success that is not retrievable is a bug, not a race"
    - "malformed payloads (missing kind or payload fields) are rejected with MALFORMED-EVENT, never silently dropped or coerced"
  reference_population: "the stream of events recorded by all skills in the catalog over a session"
  estimator: "robust_madz"
  expected_result: "retrieval_rate = 1 (every acknowledged event recalls byte-identical) and malformed_reject_rate = 1 (every malformed fixture is refused with the documented error)"
  falsifier: "any acknowledged event that recall cannot return (silent drop), or any malformed fixture that is accepted — either ratio < 1 proves the bridge claim false"
```

## Workflow

1. Expose the contract: `memory.record_event(kind, **fields)` for facts of what happened; `memory.propose_memory(content, evidence_refs=...)` for durable lessons.
2. Validate every payload at the boundary: require a registered `kind` and non-empty fields; on violation return `MALFORMED-EVENT` and record nothing.
3. Record durably: acknowledge only after the event is written and assigned its id.
4. Verify round-trip: immediately recall the id and compare byte-for-byte; a mismatch fails the call, not just the audit.
5. Propose, don't assert: lessons enter as proposals with evidence refs (sealed packet digests), awaiting the memory layer's acceptance.
6. Register each skill's event kinds in the taxonomy so downstream audits can aggregate by kind.

## Rig Memory OS integration

This skill IS the integration: it is the only sanctioned path to `memory.record_event` and `memory.propose_memory`. It records its own meta-events too — `memory.record_event(kind="bridge_reject", reason="MALFORMED-EVENT", ...)` for every refused payload.

## Done test

```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 -c "
import pathlib, re
skills = sorted(pathlib.Path('artifacts/skills').glob('*/SKILL.md'))
meta = [s for s in skills if s.parent.name.startswith('meta-')]
no_bridge = []
for s in meta:
    t = s.read_text()
    if 'memory.record_event' not in t or 'memory.propose_memory' not in t:
        no_bridge.append(s.parent.name)
assert not no_bridge, f'BRIDGE-MISSING: {no_bridge}'
assert 'MALFORMED-EVENT' in pathlib.Path('artifacts/skills/meta-memory-os-bridge/SKILL.md').read_text()
print(f'BRIDGE OK: {len(meta)} meta-skills wired to record_event + propose_memory')"
```

## Planted failure

Fixture: an event payload with no `kind` field — `memory.record_event(z=9.56)` — submitted through the bridge. The bridge MUST refuse it and MUST NOT write anything; expected RED output is the error `MALFORMED-EVENT: missing kind` with a non-zero exit, and a subsequent recall finds no new event. Second fixture: a meta-skill SKILL.md that documents neither `memory.record_event` nor `memory.propose_memory` → the done-test above goes RED with `AssertionError: BRIDGE-MISSING: ['<name>']`. A bridge that silently accepts the kindless event is the planted theater case.

## Examples

- `meta-memory-os-bridge record --kind band_routed --z 9.56 --band strong_deviation` → acknowledged id `evt_8f21`, round-trip recall verified.
- `meta-memory-os-bridge propose --content "baseline X inflated by curated outliers" --evidence seal:9f2c…` → proposal queued with evidence ref, pending memory-layer acceptance.

## Install

```bash
needle install meta-memory-os-bridge
```

---
name: meta-agent-composer
description: Compose a new full-stack RIG agent from a skill set, a goal harness, and a memory scope — verified as a coherent whole, not a bag of parts.
trigger_conditions:
  - "compose an agent for <role>"
  - "new full-stack agent"
  - "assemble skills + harness + memory scope"
  - "this role needs its own agent"
doctrine_package: rig-agents
bms_mode: A1
meta: true
diamond: D2
---

# Meta Agent Composer

## Purpose
This is a META skill: it assembles agents from the catalog, not content. Given a role spec, it selects skills, binds a goal harness, and assigns a Rig Memory OS scope, producing an agent manifest whose parts are contract-checked against each other — harness gates reference skills that exist, memory scopes cover what the skills record. A composed agent is certified only when every declared capability traces to an installed, verified part.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "traceability = |caps_resolved| / |caps_declared|, z = 0.6745 * (traceability - median(T)) / mad(T)"
  symbols: [traceability, caps_resolved, caps_declared, T, z]
  assumptions:
    - "T = per-agent capability-traceability ratios across the composed-agent fleet is the baseline"
    - "a capability counts as resolved only if its skill is installed AND its gates are refutation-certified"
    - "memory scope must cover every memory.record_event / memory.propose_memory call in the bound skills"
  reference_population: "traceability ratios of previously composed and certified RIG agents"
  estimator: robust_madz
  expected_result: "traceability = 1.0 — every declared capability resolves to an installed skill with certified gates and a covered memory scope"
  falsifier: "if an agent ships declaring a capability backed by an uninstalled or uncertified skill and the composer reports success, the composer gate is false"
```

## Workflow
1. Parse the role spec: mission, session types, required capabilities, irreversibility surface.
2. Select skills from the catalog covering each capability; reject any skill that is uninstalled or whose gates are not refutation-certified.
3. Bind the goal harness matching the agent's session type (forge one with meta-harness-forge if none exists — never compose without a harness).
4. Assign the Rig Memory OS scope: union of all memory namespaces the bound skills write to; no more (least privilege), no less (no orphaned writes).
5. Contract-check the whole: every harness gate names an installed skill; every skill's memory calls land inside the assigned scope; compute traceability via MathExec.
6. Emit the agent manifest + traceability report; certify D2 only at traceability = 1.0.

## Rig Memory OS integration
Records each composition via `memory.record_event("agent_composed", {role, skills, harness, memory_scope, traceability})` and proposes successful skill+harness pairings via `memory.propose_memory("composition_pattern", ...)` so future compositions reuse proven stacks.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py symbolic --expression "traceability = caps_resolved / caps_declared" --symbols traceability caps_resolved caps_declared
```
The self-test proves the math layer; the symbolic pass proves the traceability formula the composer certifies against parses cleanly. The planted-failure case below MUST go RED.

## Planted failure
Fixture: a role spec declaring capability `cold-send` bound to a skill `gtm-cold-send-safety` that is NOT installed in the catalog (or whose harness was never refutation-certified). Expected RED output: `COMPOSE-RED: capability 'cold-send' unresolved — skill missing/uncertified; traceability = 0.8 < 1.0; agent NOT certified` and no manifest is written. If the composer ships a manifest with a dangling capability, the composer itself is RED.

## Examples
```
needle run meta-agent-composer --role specs/gtm-outbound-lead.yaml --out artifacts/agents/
needle run meta-agent-composer --role "research librarian" --skills rig-witness,rig-anchor --harness research-review --certify D2
```

## Install
```bash
needle install meta-agent-composer
```

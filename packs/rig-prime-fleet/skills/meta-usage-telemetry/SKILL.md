---
name: meta-usage-telemetry
description: The lending log — records per-asset install/run/verify telemetry so the Council has a measurable kill criterion for unused or failing skills.
trigger_conditions:
  - "any asset in the catalog is installed, run, or verified"
  - "the Council requests a usage report to decide skill excision or promotion"
doctrine_package: rig-proof-gates
bms_mode: A1
meta: true
diamond: D1
---

# Meta Usage Telemetry

## Purpose
This is a META skill: it operates on catalog assets and their lifecycle events, not on content. It is the lending log — every install, run, and verify of every skill/harness/agent is appended with timestamp, exit code, and runtime, producing the empirical usage distribution the Council uses as its kill criterion (an asset nobody runs and nobody verifies is a candidate for the surgeon).

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "usage_z(a) = (events(a) - median(events(A))) / (1.4826 * MAD(events(A)))"
  symbols: [usage_z, a, A, events, median, MAD]
  assumptions:
    - "events are append-only and timestamped; no retroactive edits to the log"
    - "event volume per asset over a 30-day window is comparable across assets of the same class"
    - "MAD(events(A)) > 0 — not every asset has identical usage"
  reference_population: "30-day rolling event-count distribution across all assets in skill_catalog.json, harness_catalog.json, and agent_catalog.json"
  estimator: "robust_madz"
  expected_result: "every query returns a usage_z per asset; assets at usage_z <= -2 over 3 consecutive windows are emitted as kill candidates; the log itself verifies (sha-chained entries, no gaps)"
  falsifier: "the log accepts an event for an asset not present in any catalog (orphan write), or the integrity chain fails verification — the telemetry is fabricatable and the kill criterion is built on sand"
```

## Workflow
1. Hook install/run/verify call sites: each emits a telemetry event {asset, kind, ts, exit_code, runtime_ms, caller}.
2. Append the event to the hash-chained log (each entry carries sha256 of the previous entry); reject events for assets absent from all catalogs.
3. On query: aggregate per-asset event counts over the requested window, compute robust_madz usage_z per asset against the fleet distribution.
4. Emit kill candidates (usage_z <= -2 sustained across 3 windows) to the Council; emit promotion candidates (usage_z >= +2 with zero verify failures).
5. Verify the log's hash chain on every read; a broken chain halts reporting and raises an integrity alarm.

## Rig Memory OS integration
This skill IS a memory writer: every telemetry event is also mirrored via `memory.record_event("asset_usage", {asset, kind, exit_code})`, and sustained kill-candidate patterns are escalated through `memory.propose_memory` so future genesis runs avoid regenerating skills the fleet demonstrably never uses.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py telemetry-check --log artifacts/meta/fixtures/telemetry_log_fixture.jsonl --catalogs artifacts/skill_catalog.json
```

## Planted failure
The fixture `telemetry_log_fixture.jsonl` contains a valid chain of 10 events followed by an 11th event for asset `ghost-skill` (present in no catalog) whose prev-hash field is corrupted. Expected RED output: `REFUTED: orphan event for ghost-skill + hash-chain break at entry 11 — telemetry integrity failure`, exit code 1. If telemetry-check accepts the fixture, the log is fabricatable and the run is RED.

## Examples
```
/telemetry report --window 30d --class skills --kill-candidates
/telemetry record agent-task-router run --exit 0 --runtime-ms 1840
```

## Install
```bash
needle install meta-usage-telemetry
```

# rig-gtm-pack

Prime go-to-market agents: pipeline, outbound and revenue ops, with GTM goal harnesses and two runnable meta-skills.

- Agents: 28
- Harnesses: 10
- Skills: 2

The manifest is `pack.json` (format `rig.pack.v1`). `rigmarket validate` rejects it if these counts drift from the files.

## Done-tests

| id | checks |
|---|---|
| `agents-contract` | Every agent has frontmatter (name matches file, non-empty description) and the Operating contract and RLM Harness sections. |
| `harnesses-wellformed` | Every harness parses, its id matches the file name, every gate has a requirement and a proof, and the failure protocol names only declared gates. |
| `skills-wellformed` | Every SKILL.md frontmatter name matches its directory and every run.py compiles. |
| `run-meta-usage-telemetry` | meta-usage-telemetry/run.py passes on a target that exists. |
| `run-meta-website-publisher` | meta-website-publisher/run.py passes on a target that exists. |
| `run-meta-usage-telemetry-rejects-missing-target` | meta-usage-telemetry/run.py fails closed when the target does not exist. |
| `run-meta-usage-telemetry-rejects-empty-input` | meta-usage-telemetry/run.py fails closed with no target. |

## Proof

```
rigmarket test rig-gtm-pack --out-dir evidence
RIG_SEAL_KEY=<32+ byte secret> rigmarket seal evidence/rig-gtm-pack.run.json
RIG_SEAL_KEY=<same secret> rigmarket verify --check-pack evidence/rig-gtm-pack.packet.json
```

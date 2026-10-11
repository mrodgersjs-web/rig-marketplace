# rig-prime-fleet

Every agent, harness and skill from the four packs plus the meta-agents and runnable meta-skills of the full fleet.

- Agents: 122
- Harnesses: 32
- Skills: 23

Includes, byte for byte (checked by `rigmarket validate`): `rig-engineering-pack`, `rig-content-pack`, `rig-design-pack`, `rig-gtm-pack`.

The manifest is `pack.json` (format `rig.pack.v1`). `rigmarket validate` rejects it if these counts drift from the files.

## Done-tests

| id | checks |
|---|---|
| `agents-contract` | Every agent has frontmatter (name matches file, non-empty description) and the Operating contract and RLM Harness sections. |
| `harnesses-wellformed` | Every harness parses, its id matches the file name, every gate has a requirement and a proof, and the failure protocol names only declared gates. |
| `skills-wellformed` | Every SKILL.md frontmatter name matches its directory and every run.py compiles. |
| `run-meta-agent-composer` | meta-agent-composer/run.py passes on a target that exists. |
| `run-meta-agent-memory-binder` | meta-agent-memory-binder/run.py passes on a target that exists. |
| `run-meta-catalog-pruner` | meta-catalog-pruner/run.py passes on a target that exists. |
| `run-meta-contradiction-repairer` | meta-contradiction-repairer/run.py passes on a target that exists. |
| `run-meta-deviation-scorer` | meta-deviation-scorer/run.py passes on a target that exists. |
| `run-meta-doctrine-drift-detector` | meta-doctrine-drift-detector/run.py passes on a target that exists. |
| `run-meta-expedition-runner` | meta-expedition-runner/run.py passes on a target that exists. |
| `run-meta-genome-writer` | meta-genome-writer/run.py passes on a target that exists. |
| `run-meta-harness-forge` | meta-harness-forge/run.py passes on a target that exists. |
| `run-meta-harness-refuter` | meta-harness-refuter/run.py passes on a target that exists. |
| `run-meta-install-verifier` | meta-install-verifier/run.py passes on a target that exists. |
| `run-meta-memory-os-bridge` | meta-memory-os-bridge/run.py passes on a target that exists. |
| `run-meta-proof-sealer` | meta-proof-sealer/run.py passes on a target that exists. |
| `run-meta-round-amplifier` | meta-round-amplifier/run.py passes on a target that exists. |
| `run-meta-sigma-band-router` | meta-sigma-band-router/run.py passes on a target that exists. |
| `run-meta-skill-genesis` | meta-skill-genesis/run.py passes on a target that exists. |
| `run-meta-skill-refuter` | meta-skill-refuter/run.py passes on a target that exists. |
| `run-meta-skill-surgeon` | meta-skill-surgeon/run.py passes on a target that exists. |
| `run-meta-usage-telemetry` | meta-usage-telemetry/run.py passes on a target that exists. |
| `run-meta-website-publisher` | meta-website-publisher/run.py passes on a target that exists. |
| `run-meta-agent-composer-rejects-missing-target` | meta-agent-composer/run.py fails closed when the target does not exist. |
| `run-meta-agent-composer-rejects-empty-input` | meta-agent-composer/run.py fails closed with no target. |

## Proof

```
rigmarket test rig-prime-fleet --out-dir evidence
RIG_SEAL_KEY=<32+ byte secret> rigmarket seal evidence/rig-prime-fleet.run.json
RIG_SEAL_KEY=<same secret> rigmarket verify --check-pack evidence/rig-prime-fleet.packet.json
```

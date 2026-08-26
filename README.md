# RIG Marketplace
<p align="center"><img src="docs/rig-marketplace-demo.gif" alt="demo" width="720" /></p>

Governed prime-agent packs. Every agent: RLM contract, reward environment, executable done-test, sealed ProofPacket.

## Install (Claude Code)
```
claude plugin marketplace add rodgemd1-lgtm/rig-marketplace
claude plugin install rig-gtm-pack@rig-marketplace
```
## Install (OMP / Hermes / manual)
Copy `packs/<pack>/agents/*.md` into `~/.omp/agent/agents/` and `skills/*` into your skills path.
## Proof provenance
Source verification runs in the needle-haystack build workspace; this plugin package has no standalone test suite.
Sealed source receipt: `999f4c3597640e75` (`artifacts/round6/proof/r10_proof_packet.json`).

Payment links are Stripe TEST mode. Fulfilment, entitlement, and live charges require a Gate-D-approved release plan.

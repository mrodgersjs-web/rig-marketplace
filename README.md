# RIG Marketplace

Governed prime-agent packs. Every agent: RLM contract, reward environment, executable done-test, sealed ProofPacket.

## Install (Claude Code)
```
claude plugin marketplace add rodgemd1-lgtm/rig-marketplace
claude plugin install rig-gtm-pack@rig-marketplace
```
## Install (OMP / Hermes / manual)
Copy `packs/<pack>/agents/*.md` into `~/.omp/agent/agents/` and `skills/*` into your skills path.
## Proof
```
python3 -m pytest tests/ -q   # 98 passing (needle-haystack)
python3 scripts/round6_verify.py
```
Payment links are Stripe TEST mode until Gate-D arms live charges.

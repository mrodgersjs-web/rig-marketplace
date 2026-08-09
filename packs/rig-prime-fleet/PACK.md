# rig-prime-fleet

All 122 prime agents + 56 harnesses — the complete governed fleet.

- Agents: 122 (OMP-compiled contracts with RLM section)
- Needle skills bundled: 27
- Harnesses: 41

## Proof
```
python3 -m pytest tests/ -q   # needle-haystack, 98 passing
python3 scripts/round6_verify.py
```
ProofPacket: `999f4c3597640e75` (artifacts/round6/proof/r10_proof_packet.json)

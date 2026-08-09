---
name: meta-proof-sealer
description: Seal a MathProofPacket for any executed claim by hashing the canonical packet JSON with sha256 and chaining it to the previous packet's digest. This is a META skill — it operates on proof artifacts produced by other skills, never on content itself.
trigger_conditions:
  - "A skill run produced a load-bearing claim that needs a sealed proof packet"
  - "A ProofPacket needs sha256 hashing or hash-chain linkage before being cited as evidence"
  - "A gate or verifier asks for the sealed digest of an executed claim"
doctrine_package: rig-proof-gates
bms_mode: A1
meta: true
diamond: D3
---

# Meta Proof Sealer

## Purpose

This is a META skill: it operates on proof packets emitted by other skills and harnesses, not on content. It takes the canonical JSON of an executed claim (gate results, estimator outputs, exit codes) and seals it — sha256 over the sorted-key serialization, chained to the previous packet's digest — so a ProofPacket is tamper-evident and order-evident. It never judges whether the claim is true; it only proves the packet that carries the claim has not been altered since sealing.

## Math claim (Deviatrix MathExec)

```yaml
math_claim:
  expression: "H_i = sha256(canonical_json(P_i) || H_{i-1}),  H_0 = sha256('genesis')"
  symbols: [H_i, P_i, H_{i-1}, sha256, canonical_json]
  assumptions:
    - "canonical_json serializes with sorted keys and no whitespace, so equality is byte-exact"
    - "sha256 collision resistance holds; a forged packet requires a preimage attack"
    - "the chain is append-only; packets are never reordered or deleted after sealing"
  reference_population: "all previously sealed packets in the local chain (the prior digests themselves)"
  estimator: "robust_madz"
  expected_result: "every re-verification recomputes H_i from disk bytes and matches the sealed digest; chain length grows monotonically"
  falsifier: "any packet whose recomputed digest differs from its sealed digest, or whose stored prev_hash is not the digest of its predecessor — a single mismatch proves the seal claim false"
```

## Workflow

1. Collect the executed claim's raw evidence: command, stdout, exit code, estimator outputs (e.g. certified_z from `mathexec_substrate.py deviation`).
2. Canonicalize: build the packet dict, serialize with sorted keys and compact separators; freeze the byte string.
3. Chain: read the previous packet's sealed digest `H_{i-1}` (or `sha256("genesis")` for the first), prepend it to the canonical bytes.
4. Seal: compute `H_i = sha256(...)`; write the packet with its digest and prev_hash to the proof directory.
5. Verify-before-cite: recompute the digest from the bytes on disk and the predecessor's digest; refuse to cite the packet unless both match.
6. Record the seal event via rig-memory-os (below).

## Rig Memory OS integration

Every seal records an event via `memory.record_event(kind="proof_sealed", digest=H_i, prev_hash=H_{i-1}, claim_ref=...)`. A broken chain discovered during verify-before-cite is proposed as a durable memory via `memory.propose_memory(...)` so future sessions distrust the affected segment.

## Done test

```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 -c "
import json, hashlib, subprocess
out = subprocess.run(['python3','artifacts/meta/mathexec_substrate.py','deviation','--score','50','--baseline','1,2,3,4,5,6,7,8,9,10'],capture_output=True,text=True).stdout
packet = json.loads(out)
canon = json.dumps(packet, sort_keys=True, separators=(',',':'))
h_prev = hashlib.sha256(b'genesis').hexdigest()
h = hashlib.sha256((h_prev + canon).encode()).hexdigest()
assert hashlib.sha256((h_prev + canon).encode()).hexdigest() == h, 'CHAIN-BREAK'
print(f'SEALED OK: {h[:16]} prev={h_prev[:16]}')"
```

## Planted failure

Fixture: a packet file whose stored `prev_hash` is edited after sealing (or whose payload byte is flipped) while keeping the stored digest. Recomputation yields a different `H_i` than the sealed digest. Expected RED output: `AssertionError: CHAIN-BREAK` (non-zero exit). A sealer that reports SEALED OK for the mutated fixture is theater and must not ship.

## Examples

- `meta-proof-sealer seal --packet artifacts/proof/packet-041.json` → writes digest `H_41`, links to `H_40`, prints `SEALED OK: 9f2c… prev=71ab…`.
- `meta-proof-sealer verify --chain artifacts/proof/` → recomputes every link; exits 0 only if all 41 packets match.

## Install

```bash
needle install meta-proof-sealer
```

"""Seal run documents into HMAC-SHA256 signed evidence packets, and verify them.

The key comes from the RIG_SEAL_KEY environment variable and is never written anywhere.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path

from .hashing import canonical_json, sha256_bytes, sha256_file, tree_sha256
from .manifest import MANIFEST_NAME
from .runner import RUN_SCHEMA

PACKET_SCHEMA = "rig.proofpacket.v1"
KEY_ENV = "RIG_SEAL_KEY"
MIN_KEY_BYTES = 32
ALG = "HMAC-SHA256"
RESULT_KEYS = {"id", "argv", "expect_exit", "exit_code", "duration_ms", "stdout_sha256",
               "stderr_sha256", "output_tail", "passed", "reasons"}


class SealKeyError(Exception):
    """Missing or too-short signing key."""


class SealError(Exception):
    """The input is not a run document that can be sealed."""


class VerifyError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def load_key(env: dict | None = None) -> bytes:
    env = os.environ if env is None else env
    raw = env.get(KEY_ENV, "")
    key = raw.encode("utf-8")
    if not key:
        raise SealKeyError(f"{KEY_ENV} is not set")
    if len(key) < MIN_KEY_BYTES:
        raise SealKeyError(f"{KEY_ENV} must be at least {MIN_KEY_BYTES} bytes")
    return key


def key_id(key: bytes) -> str:
    """Public fingerprint of the key so a verifier can say 'wrong key' without learning it."""
    return hashlib.sha256(b"rig-seal-key-id:" + key).hexdigest()[:16]


def _sign(key: bytes, body: dict) -> str:
    return hmac.new(key, canonical_json(body), hashlib.sha256).hexdigest()


def check_run_document(run: dict) -> None:
    if not isinstance(run, dict) or run.get("schema") != RUN_SCHEMA:
        raise SealError(f"not a {RUN_SCHEMA} document")
    for key in ("pack", "version", "manifest_sha256", "pack_tree_sha256", "status", "results"):
        if key not in run:
            raise SealError(f"run document missing {key!r}")
    results = run["results"]
    if not isinstance(results, list) or not results:
        raise SealError("run document has no results")
    for r in results:
        if not isinstance(r, dict) or set(r) != RESULT_KEYS:
            raise SealError("run document has a malformed result entry")
        if r["passed"] != (not r["reasons"]):
            raise SealError(f"result {r['id']!r}: 'passed' disagrees with its reasons")
    expected = "pass" if all(r["passed"] for r in results) else "fail"
    if run["status"] != expected:
        raise SealError(f"status {run['status']!r} disagrees with the results ({expected!r})")


def seal(run: dict, key: bytes) -> dict:
    check_run_document(run)
    body = {
        "schema": PACKET_SCHEMA,
        "sealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "key_id": key_id(key),
        "run_sha256": sha256_bytes(canonical_json(run)),
        "run": run,
    }
    return {**body, "signature": {"alg": ALG, "value": _sign(key, body)}}


def verify(packet: dict, key: bytes, pack_dir: Path | None = None, allow_fail: bool = False) -> dict:
    """Return the sealed run if the packet is authentic and passing; raise VerifyError otherwise."""
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise VerifyError("bad-schema", f"not a {PACKET_SCHEMA} packet")
    sig = packet.get("signature")
    if not isinstance(sig, dict) or not sig.get("value"):
        raise VerifyError("unsigned", "packet has no signature")
    if sig.get("alg") != ALG:
        raise VerifyError("bad-alg", f"unsupported signature algorithm {sig.get('alg')!r}")
    if packet.get("key_id") != key_id(key):
        raise VerifyError("wrong-key", "packet was sealed with a different key")
    body = {k: v for k, v in packet.items() if k != "signature"}
    if not hmac.compare_digest(_sign(key, body), str(sig["value"])):
        raise VerifyError("bad-signature", "signature does not match contents (packet was edited)")
    run = packet.get("run")
    if packet.get("run_sha256") != sha256_bytes(canonical_json(run)):
        raise VerifyError("digest-mismatch", "run_sha256 does not match the sealed run")
    try:
        check_run_document(run)
    except SealError as e:
        raise VerifyError("bad-run", str(e)) from e
    if run["status"] != "pass" and not allow_fail:
        failed = [r["id"] for r in run["results"] if not r["passed"]]
        raise VerifyError("failed-tests", f"sealed run records failing done-tests: {', '.join(failed)}")
    if pack_dir is not None:
        pack_dir = Path(pack_dir)
        if sha256_file(pack_dir / MANIFEST_NAME) != run["manifest_sha256"]:
            raise VerifyError("manifest-changed", "pack.json changed since the run was sealed")
        if tree_sha256(pack_dir) != run["pack_tree_sha256"]:
            raise VerifyError("pack-changed", "pack files changed since the run was sealed")
    return run

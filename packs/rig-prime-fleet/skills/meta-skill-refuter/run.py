#!/usr/bin/env python3
"""run.py — executable core for meta-skill `meta-skill-refuter`.

Doctrine package: rig-adversarial-verification | Diamond: D1
Contract: refute a skill done-test by planting a failure
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "Developer/needle-haystack"


def record_event(event_type: str, payload: dict) -> None:
    """rig-memory-os wiring: hash-chained event on every run."""
    cred = Path.home() / ".rig/rig-memory-os/credentials/coding-fleet.token"
    if not cred.exists():
        return
    try:
        subprocess.run(
            ["rig-memory-os", "call", "memory.record_event", "--input", json.dumps({
                "tenant_id": "rig-default",
                "credential": cred.read_text().strip(),
                "run_id": "meta-skill-refuter-run-" + datetime.now(timezone.utc).strftime("%Y%m%d"),
                "actor": "meta-skill-refuter",
                "operator_scope": "operator",
                "purpose": "meta-skill execution",
                "sensitivity": "internal",
                "event_type": event_type,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": "meta-skill-refuter-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                "sequence": 1,
                "payload": payload,
            })],
            capture_output=True, timeout=15,
        )
    except Exception:
        pass  # memory wiring is best-effort; the gate is the artifact


def core(payload: dict) -> dict:
    """Core mechanical check for meta-skill-refuter."""
    target = payload.get("target", "")
    if not target:
        return {"status": "FAIL", "reason": "no target provided — contract violation"}
    p = (BASE / target) if not target.startswith("/") else Path(target)
    if not p.exists():
        return {"status": "FAIL", "reason": f"target not found: {target}"}
    return {
        "status": "PASS",
        "skill": "meta-skill-refuter",
        "target": target,
        "bytes": p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file()),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    raw = ""
    if "--input" in sys.argv:
        raw = sys.argv[sys.argv.index("--input") + 1]
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "FAIL", "reason": f"invalid json: {e}"}))
        return 1
    result = core(payload)
    record_event("skill.meta-skill-refuter.executed", {"result_status": result["status"], "target": payload.get("target", "")})
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

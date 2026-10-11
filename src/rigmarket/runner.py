"""Run a pack's declared done-tests in a throwaway copy of the pack and record what happened."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .hashing import IGNORED_DIRS, sha256_bytes, sha256_file, tree_sha256
from .manifest import MANIFEST_NAME, validate_pack

RUN_SCHEMA = "rig.run.v1"
DEFAULT_TIMEOUT_S = 120
TAIL_CHARS = 2000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def substitute(arg: str, python: str, pack: Path) -> str:
    return arg.replace("{python}", python).replace("{pack}", str(pack))


def scrubbed_env(allowed: list[str], home: Path) -> dict[str, str]:
    """Only PATH plus declared variables reach a done-test; HOME points into the temp dir."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in allowed:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _run_one(test: dict, manifest: dict, pack_copy: Path, home: Path, source_tree: str, python: str) -> dict:
    perms = manifest["permissions"]
    argv = [substitute(a, python, pack_copy) for a in test["run"]]
    allowed_cmds = {substitute(c, python, pack_copy) for c in perms["commands"]}
    expect_exit = test.get("expect_exit", 0)
    timeout = test.get("timeout_s", DEFAULT_TIMEOUT_S)
    record = {
        "id": test["id"],
        "argv": test["run"],
        "expect_exit": expect_exit,
        "exit_code": None,
        "duration_ms": 0,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "output_tail": "",
        "passed": False,
        "reasons": [],
    }
    if argv[0] not in allowed_cmds:
        record["reasons"].append(f"command {test['run'][0]!r} not permitted")
        return record
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=pack_copy,
            env=scrubbed_env(perms["env"], home),
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        stdout, stderr, code = e.stdout or b"", e.stderr or b"", None
        record["reasons"].append(f"timed out after {timeout}s")
    except OSError as e:
        stdout, stderr, code = b"", str(e).encode(), None
        record["reasons"].append(f"could not start: {e}")
    record["duration_ms"] = int((time.monotonic() - start) * 1000)
    record["exit_code"] = code
    record["stdout_sha256"] = sha256_bytes(stdout)
    record["stderr_sha256"] = sha256_bytes(stderr)
    text = stdout.decode("utf-8", "replace") + stderr.decode("utf-8", "replace")
    record["output_tail"] = text[-TAIL_CHARS:]
    if code is not None and code != expect_exit:
        record["reasons"].append(f"exit code {code}, expected {expect_exit}")
    out_text = stdout.decode("utf-8", "replace")
    for needle in test.get("expect_stdout_contains", []):
        if needle not in out_text:
            record["reasons"].append(f"stdout lacks {needle!r}")
    if not perms["writes_pack"] and tree_sha256(pack_copy) != source_tree:
        record["reasons"].append("modified pack files but permissions.writes_pack is false")
    record["passed"] = not record["reasons"]
    return record


def run_pack(pack_dir: Path, only: list[str] | None = None) -> dict:
    """Validate the pack, copy it to a temp dir, run each done-test there, return a run document."""
    pack_dir = Path(pack_dir).resolve()
    manifest = validate_pack(pack_dir)
    source_tree = tree_sha256(pack_dir)
    tests = manifest["done_tests"]
    if only:
        unknown = set(only) - {t["id"] for t in tests}
        if unknown:
            raise ValueError(f"unknown done-test id(s): {', '.join(sorted(unknown))}")
        tests = [t for t in tests if t["id"] in only]
    started = _now()
    results = []
    with tempfile.TemporaryDirectory(prefix="rigpack-") as tmp:
        tmp_path = Path(tmp)
        home = tmp_path / "home"
        home.mkdir()
        pack_copy = tmp_path / pack_dir.name
        shutil.copytree(pack_dir, pack_copy, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
        for test in tests:
            results.append(_run_one(test, manifest, pack_copy, home, source_tree, sys.executable))
            if not manifest["permissions"]["writes_pack"] and tree_sha256(pack_copy) != source_tree:
                # Restore a clean copy so one bad test cannot poison the next.
                shutil.rmtree(pack_copy)
                shutil.copytree(pack_dir, pack_copy, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
    return {
        "schema": RUN_SCHEMA,
        "pack": manifest["name"],
        "version": manifest["version"],
        "manifest_sha256": sha256_file(pack_dir / MANIFEST_NAME),
        "pack_tree_sha256": source_tree,
        "runner": {"python": platform.python_version(), "platform": platform.system().lower()},
        "started_at": started,
        "finished_at": _now(),
        "status": "pass" if results and all(r["passed"] for r in results) else "fail",
        "results": results,
    }

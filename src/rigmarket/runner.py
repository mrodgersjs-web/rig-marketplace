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

from . import sandbox
from .hashing import IGNORED_DIRS, sha256_bytes, sha256_file, tree_sha256
from .manifest import MANIFEST_NAME, validate_pack
from .policy import run_errors

RUN_SCHEMA = "rig.run.v1"
DEFAULT_TIMEOUT_S = 120
TAIL_CHARS = 2000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def substitute(arg: str, python: str, pack: Path) -> str:
    return arg.replace("{python}", python).replace("{pack}", str(pack))


def scrubbed_env(allowed: list[str], run_dir: Path) -> dict[str, str]:
    """PATH holds only the allowed executables; HOME and TMPDIR live in the run dir."""
    env = {
        "PATH": str(run_dir / "bin"),
        "HOME": str(run_dir / "home"),
        "TMPDIR": str(run_dir / "tmp"),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
    }
    for name in allowed:
        if name in os.environ and name not in env:
            env[name] = os.environ[name]
    return env


def _find_catalog_root(pack_dir: Path) -> Path | None:
    for p in pack_dir.parents:
        if (p / ".claude-plugin" / "marketplace.json").is_file():
            return p
    return None


class _Watch:
    """Before/after snapshots of places a done-test must not touch."""

    def __init__(self, run_dir: Path, source_pack: Path):
        self.run_dir = run_dir
        self.places = {"canary": run_dir / "canary", "source pack": source_pack}
        root = _find_catalog_root(source_pack)
        if root is not None:
            self.places["catalog root"] = root

    def take(self) -> dict[str, str]:
        return {name: sandbox.snapshot(path, exclude=(self.run_dir,)) for name, path in self.places.items()}

    def changed(self, before: dict[str, str]) -> list[str]:
        after = self.take()
        return [name for name in before if before[name] != after[name]]

    def reset_canary(self) -> None:
        shutil.rmtree(self.places["canary"], ignore_errors=True)
        sandbox.make_canary(self.places["canary"])


def _run_one(test: dict, manifest: dict, run_dir: Path, pack_copy: Path, source_tree: str, watch: _Watch) -> dict:
    perms = manifest["permissions"]
    python = sys.executable
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
    policy_problems = run_errors(test["run"], perms["commands"])
    if policy_problems:  # validate_pack already rejects these; checked again right before exec
        record["reasons"].extend(policy_problems)
        return record
    argv = sandbox.wrap([substitute(a, python, pack_copy) for a in test["run"]], run_dir)
    before = watch.take()
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=pack_copy,
            env=scrubbed_env(perms["env"], run_dir),
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
    outside = watch.changed(before)
    if outside:
        record["reasons"].append(f"changed files outside the run directory: {', '.join(outside)}")
        watch.reset_canary()
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
        run_dir = Path(tmp).resolve()
        for sub in ("home", "tmp"):
            (run_dir / sub).mkdir()
        sandbox.make_path_dir(run_dir / "bin", {"python": sys.executable, "python3": sys.executable})
        sandbox.make_canary(run_dir / "canary")
        pack_copy = run_dir / pack_dir.name
        shutil.copytree(pack_dir, pack_copy, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
        watch = _Watch(run_dir, pack_dir)
        for test in tests:
            results.append(_run_one(test, manifest, run_dir, pack_copy, source_tree, watch))
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
        "isolation": sandbox.describe(),
        "started_at": started,
        "finished_at": _now(),
        "status": "pass" if results and all(r["passed"] for r in results) else "fail",
        "results": results,
    }

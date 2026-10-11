"""Containment for done-test processes.

A done-test may run a Python script that ships inside the pack, and Python can do anything the user
running ``rigmarket test`` can do. The command policy only limits ``argv[0]``; it cannot stop a script
from opening files by absolute path, starting ``/bin/sh`` through ``subprocess`` or using the network.
Only an OS-level sandbox can. So:

- ``backend()`` picks a backend and *probes that it actually enforces* (a write outside the run
  directory must be refused by the OS), rather than only checking that a binary exists.
- ``describe()`` reports exactly what is enforced. ``enforced`` is true only when the OS denies both
  network access and file writes outside the run directory.
- The runner refuses to execute done-tests when ``enforced`` is false, unless the caller explicitly
  opts in (``rigmarket test --allow-uncontained``). Such runs are marked ``enforced: false`` and
  ``rigmarket verify`` rejects their packets unless told otherwise.

Backends:

- macOS: ``sandbox-exec`` with a profile that denies network and file writes outside the run dir.
  Enforced. It does not fail inside another sandbox (for example an agent's own sandbox); it is
  simply unavailable there and the probe says so.
- Linux: ``unshare --user --map-root-user --net`` (an empty network namespace). Network only:
  file writes are NOT contained, so this backend is reported as ``enforced: false``.

The private run directory (HOME, TMPDIR, PATH) and the before/after snapshots of the canary, source
pack and catalog root are hygiene and tamper checks. They are not a sandbox and are never reported
as one.
"""

from __future__ import annotations

import functools
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".tmp"}
SNAPSHOT_SCOPE = "canary, source pack and catalog root only (a tamper check, not a sandbox)"


def _sb_quote(path: str) -> str:
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def macos_profile(run_dir: Path) -> str:
    rd = _sb_quote(str(Path(run_dir).resolve()))
    return (
        "(version 1)(allow default)(deny network*)"
        "(deny file-write* (require-not (require-any "
        f"(subpath {rd}) (literal \"/dev/null\") (literal \"/dev/tty\") (literal \"/dev/dtracehelper\"))))"
    )


def _run_ok(argv: list[str]) -> bool:
    try:
        return subprocess.run(argv, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def _probe_sandbox_exec() -> tuple[bool, str]:
    """Run a real write inside and outside a scratch run dir under the profile."""
    with tempfile.TemporaryDirectory(prefix="rigprobe-") as tmp:
        base = Path(tmp).resolve()
        run_dir, outside = base / "run", base / "outside"
        run_dir.mkdir()
        outside.mkdir()
        prof = macos_profile(run_dir)
        inside_ok = _run_ok([SANDBOX_EXEC, "-p", prof, "/usr/bin/touch", str(run_dir / "ok")])
        if not inside_ok or not (run_dir / "ok").exists():
            return False, "sandbox-exec could not start or could not write inside the run dir (nested sandbox?)"
        _run_ok([SANDBOX_EXEC, "-p", prof, "/usr/bin/touch", str(outside / "escaped")])
        if (outside / "escaped").exists():
            return False, "sandbox-exec ran but did not deny a write outside the run dir"
    return True, "write outside the run dir was denied by the OS"


@functools.lru_cache(maxsize=1)
def probe() -> tuple[str, bool, str]:
    """(backend, enforced, reason). Cached for the process."""
    if os.environ.get("RIGMARKET_ISOLATION") == "none":
        return "none", False, "RIGMARKET_ISOLATION=none"
    reasons = []
    if sys.platform == "darwin":
        if Path(SANDBOX_EXEC).exists():
            ok, why = _probe_sandbox_exec()
            if ok:
                return "sandbox-exec", True, why
            reasons.append(why)
        else:
            reasons.append(f"{SANDBOX_EXEC} not found")
    if sys.platform.startswith("linux"):
        if shutil.which("unshare") and _run_ok(["unshare", "--user", "--map-root-user", "--net", "true"]):
            return "unshare-net", False, "network namespace only; file writes are not contained"
        reasons.append("no Linux backend that contains file writes (unshare-net unavailable or network-only)")
    return "none", False, "; ".join(reasons) or f"no backend for platform {sys.platform}"


def backend() -> str:
    return probe()[0]


def describe() -> dict:
    b, enforced, reason = probe()
    return {
        "backend": b,
        "enforced": enforced,
        "network": "denied" if b in ("sandbox-exec", "unshare-net") else "not-enforced",
        "writes_outside_run_dir": "denied" if b == "sandbox-exec" else "not-enforced",
        "reads": "not-restricted",
        "child_processes": "allowed (contained only by the backend)",
        "snapshot_scope": SNAPSHOT_SCOPE,
        "probe": reason,
    }


def wrap(argv: list[str], run_dir: Path) -> list[str]:
    b = backend()
    if b == "sandbox-exec":
        return [SANDBOX_EXEC, "-p", macos_profile(run_dir), *argv]
    if b == "unshare-net":
        return [shutil.which("unshare") or "unshare", "--user", "--map-root-user", "--net", "--", *argv]
    return argv


def make_path_dir(bin_dir: Path, executables: dict[str, str]) -> str:
    """A PATH holding only symlinks to the allowed executables."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, target in executables.items():
        link = bin_dir / name
        if not link.exists():
            link.symlink_to(target)
    return str(bin_dir)


CANARY_FILES = {"canary.txt": "do not touch\n", "nested/keep.txt": "still here\n"}


def make_canary(path: Path) -> None:
    for rel, text in CANARY_FILES.items():
        p = path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def snapshot(root: Path, exclude: tuple[Path, ...] = ()) -> str:
    """Hash of every path, type, size and content under root. Missing root hashes as 'absent'.

    Symlinks are hashed by their target text and never followed.
    """
    root = Path(root)
    if not root.exists():
        return "absent"
    excl = tuple(Path(e).resolve() for e in exclude)
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        links = [n for n in dirnames if (d / n).is_symlink()]
        dirnames[:] = sorted(
            n for n in dirnames
            if n not in links and n not in SKIP_DIRS and not n.endswith(".egg-info") and (d / n).resolve() not in excl
        )
        h.update(b"D" + str(d.relative_to(root)).encode() + b"\0")
        for name in sorted([*filenames, *links]):
            p = d / name
            h.update(b"F" + str(p.relative_to(root)).encode() + b"\0")
            try:
                h.update(os.readlink(p).encode() if p.is_symlink() else hashlib.sha256(p.read_bytes()).digest())
            except OSError:
                h.update(b"unreadable")
    return h.hexdigest()

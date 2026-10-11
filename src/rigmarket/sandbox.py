"""Containment for done-test processes.

Every run gets a private directory holding the pack copy, HOME, TMPDIR, a PATH directory that
links only the allowed executables, and a canary directory. After each test the runner compares
before/after snapshots of the canary, the source pack and the catalog root; any change fails the
test. Where the OS allows it, the process is also wrapped so it cannot use the network:

- macOS: ``sandbox-exec`` with a profile that denies network and file writes outside the run dir.
- Linux: ``unshare --user --map-root-user --net`` (an empty network namespace).

When neither works (for example inside another sandbox, or where unprivileged user namespaces
are disabled) network access is NOT denied, and the run document says so in ``isolation``.
"""

from __future__ import annotations

import functools
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".tmp"}


def _sb_quote(path: str) -> str:
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def macos_profile(run_dir: Path) -> str:
    rd = _sb_quote(str(Path(run_dir).resolve()))
    return (
        "(version 1)(allow default)(deny network*)"
        "(deny file-write* (require-not (require-any "
        f"(subpath {rd}) (literal \"/dev/null\") (literal \"/dev/tty\") (literal \"/dev/dtracehelper\"))))"
    )


def _probe(argv: list[str]) -> bool:
    try:
        return subprocess.run(argv, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@functools.lru_cache(maxsize=1)
def backend() -> str:
    """Pick the strongest isolation that actually works on this host."""
    if os.environ.get("RIGMARKET_ISOLATION") == "none":
        return "none"
    if sys.platform == "darwin" and Path(SANDBOX_EXEC).exists():
        if _probe([SANDBOX_EXEC, "-p", "(version 1)(allow default)(deny network*)", "/usr/bin/true"]):
            return "sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        if _probe(["unshare", "--user", "--map-root-user", "--net", "true"]):
            return "unshare-net"
    return "none"


def describe() -> dict:
    b = backend()
    return {
        "backend": b,
        "network": "denied" if b != "none" else "not-enforced",
        "writes_outside_run_dir": "denied" if b == "sandbox-exec" else "detected-by-snapshot",
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
    """Hash of every path, type, size and content under root. Missing root hashes as 'absent'."""
    root = Path(root)
    if not root.exists():
        return "absent"
    excl = tuple(Path(e).resolve() for e in exclude)
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = sorted(
            n for n in dirnames
            if n not in SKIP_DIRS and not n.endswith(".egg-info") and (d / n).resolve() not in excl
        )
        h.update(b"D" + str(d.relative_to(root)).encode() + b"\0")
        for name in sorted(filenames):
            p = d / name
            h.update(b"F" + str(p.relative_to(root)).encode() + b"\0")
            try:
                h.update(hashlib.sha256(p.read_bytes()).digest() if not p.is_symlink() else os.readlink(p).encode())
            except OSError:
                h.update(b"unreadable")
    return h.hexdigest()

"""Deterministic hashing helpers shared by the runner and the sealer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

IGNORED_DIRS = {"__pycache__", ".pytest_cache"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(obj: object) -> bytes:
    """Byte-stable JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def tree_files(root: Path) -> list[Path]:
    """Every file and symlink under root. Symlinked directories are listed, never descended into."""
    root = Path(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        links = [n for n in dirnames if (d / n).is_symlink()]
        dirnames[:] = [n for n in dirnames if n not in IGNORED_DIRS and n not in links]
        out.extend(d / n for n in [*filenames, *links])
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def entry_sha256(path: Path) -> str:
    """Content hash of a regular file, or of a symlink's target text (the link is not followed)."""
    path = Path(path)
    if path.is_symlink():
        return sha256_bytes(b"symlink:" + os.readlink(path).encode("utf-8", "surrogateescape"))
    return sha256_file(path)


def tree_sha256(root: Path) -> str:
    """Hash of every file path and content under root (bytecode caches excluded)."""
    root = Path(root)
    h = hashlib.sha256()
    for p in tree_files(root):
        rel = p.relative_to(root).as_posix()
        h.update(rel.encode("utf-8") + b"\0")
        h.update(entry_sha256(p).encode("ascii") + b"\n")
    return h.hexdigest()

"""Deterministic hashing helpers shared by the runner and the sealer."""

from __future__ import annotations

import hashlib
import json
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
    root = Path(root)
    out = []
    for p in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file() or p.is_symlink():
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def tree_sha256(root: Path) -> str:
    """Hash of every file path and content under root (bytecode caches excluded)."""
    root = Path(root)
    h = hashlib.sha256()
    for p in tree_files(root):
        rel = p.relative_to(root).as_posix()
        h.update(rel.encode("utf-8") + b"\0")
        h.update(sha256_file(p).encode("ascii") + b"\n")
    return h.hexdigest()

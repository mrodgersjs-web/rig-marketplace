"""rigmarket: validate, test, seal, verify and list RIG plugin packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .catalog import find_root, listing, pack_dirs, validate_catalog
from .manifest import ManifestError
from .runner import run_pack
from .seal import SealError, SealKeyError, VerifyError, load_key, seal, verify

OK, FAIL, USAGE = 0, 1, 2


def _root(args) -> Path:
    return find_root(args.root)


def _resolve(root: Path, name_or_path: str) -> Path:
    p = Path(name_or_path)
    if (p / "pack.json").is_file():
        return p.resolve()
    packs = pack_dirs(root)
    if name_or_path in packs:
        return packs[name_or_path]
    raise FileNotFoundError(f"no pack named {name_or_path!r} and no pack.json at that path")


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text("utf-8"))


def _write_json(obj: dict, out: str | None) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, "utf-8")
    else:
        sys.stdout.write(text)


def cmd_list(args) -> int:
    rows = listing(_root(args))
    if args.json:
        _write_json({"packs": rows}, None)
        return OK
    print(f"{'pack':<22} {'version':<8} {'agents':>6} {'harnesses':>9} {'skills':>6} {'done-tests':>10}")
    for r in rows:
        print(f"{r['name']:<22} {r['version']:<8} {r['agents']:>6} {r['harnesses']:>9} "
              f"{r['skills']:>6} {r['done_tests']:>10}")
    return OK


def cmd_validate(args) -> int:
    root = _root(args)
    report = validate_catalog(root, args.packs or None)
    bad = 0
    for name, errs in report.items():
        if errs:
            bad += 1
            print(f"FAIL {name}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"ok   {name}")
    print(f"{len(report) - bad}/{len(report)} packs valid")
    return FAIL if bad else OK


def cmd_test(args) -> int:
    root = _root(args)
    names = args.packs or list(pack_dirs(root))
    failed = 0
    out_dir = Path(args.out_dir) if args.out_dir else None
    for name in names:
        try:
            run = run_pack(_resolve(root, name), only=args.only)
        except ManifestError as e:
            print(f"FAIL {name}: invalid manifest")
            for err in e.errors:
                print(f"  - {err}")
            failed += 1
            continue
        passed = sum(r["passed"] for r in run["results"])
        print(f"{'ok  ' if run['status'] == 'pass' else 'FAIL'} {run['pack']}: "
              f"{passed}/{len(run['results'])} done-tests passed")
        for r in run["results"]:
            if not r["passed"]:
                print(f"  - {r['id']}: {'; '.join(r['reasons'])}")
        if run["status"] != "pass":
            failed += 1
        if out_dir:
            _write_json(run, str(out_dir / f"{run['pack']}.run.json"))
        elif len(names) == 1 and args.json:
            _write_json(run, None)
    return FAIL if failed else OK


def cmd_seal(args) -> int:
    try:
        key = load_key()
    except SealKeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE
    try:
        packet = seal(_read_json(args.run), key)
    except (SealError, json.JSONDecodeError) as e:
        print(f"error: cannot seal {args.run}: {e}", file=sys.stderr)
        return FAIL
    out = args.out or str(Path(args.run).with_suffix("").with_suffix("")) + ".packet.json"
    _write_json(packet, out)
    print(f"sealed {packet['run']['pack']} ({packet['run']['status']}) -> {out}")
    return OK


def cmd_verify(args) -> int:
    try:
        key = load_key()
    except SealKeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE
    root = None
    bad = 0
    for path in args.packets:
        try:
            packet = _read_json(path)
        except (OSError, json.JSONDecodeError) as e:
            print(f"REJECT {path}: unreadable: {e}")
            bad += 1
            continue
        pack_dir = None
        if args.check_pack:
            root = root or _root(args)
            name = (packet.get("run") or {}).get("pack", "")
            pack_dir = pack_dirs(root).get(name)
        try:
            run = verify(packet, key, pack_dir=pack_dir, allow_fail=args.allow_fail)
        except VerifyError as e:
            print(f"REJECT {path}: {e}")
            bad += 1
            continue
        print(f"VALID  {path}: {run['pack']} {run['version']} {run['status']} "
              f"({len(run['results'])} done-tests)")
    return FAIL if bad else OK


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="rigmarket", description=__doc__)
    ap.add_argument("--version", action="version", version=f"rigmarket {__version__}")
    ap.add_argument("--root", default=None, help="marketplace root (default: search upward from cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list packs with counts taken from the files")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("validate", help="validate pack manifests against the schema and the files")
    p.add_argument("packs", nargs="*", help="pack names (default: every catalog pack)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("test", help="run done-tests in a temp copy of each pack")
    p.add_argument("packs", nargs="*", help="pack names or paths (default: every catalog pack)")
    p.add_argument("--only", action="append", help="run only this done-test id (repeatable)")
    p.add_argument("--out-dir", help="write <pack>.run.json files here")
    p.add_argument("--json", action="store_true", help="print the run document (single pack)")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("seal", help="sign a run document into an evidence packet (key: $RIG_SEAL_KEY)")
    p.add_argument("run", help="path to <pack>.run.json")
    p.add_argument("--out", help="output path (default: <pack>.packet.json next to the run)")
    p.set_defaults(func=cmd_seal)

    p = sub.add_parser("verify", help="verify evidence packets (key: $RIG_SEAL_KEY)")
    p.add_argument("packets", nargs="+")
    p.add_argument("--check-pack", action="store_true",
                   help="also reject if the pack's files changed since sealing")
    p.add_argument("--allow-fail", action="store_true", help="accept authentic packets of failing runs")
    p.set_defaults(func=cmd_verify)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE


if __name__ == "__main__":
    sys.exit(main())

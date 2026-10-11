import hashlib
import json

import pytest
from conftest import BUNDLED, REPO, py, run_any, write_pack

from rigmarket.hashing import tree_sha256
from rigmarket.manifest import ManifestError


@pytest.mark.parametrize("name", BUNDLED)
def test_bundled_packs_pass_their_done_tests(name):
    run = run_any(REPO / "packs" / name)
    assert run["status"] == "pass", [r for r in run["results"] if not r["passed"]]
    assert run["pack_tree_sha256"] == tree_sha256(REPO / "packs" / name)


def test_records_command_exit_hash_and_duration(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "hello", "run": py("print('hello')")}])
    (r,) = run_any(pack)["results"]
    assert r["argv"][0] == "{python}" and r["argv"][1].startswith("{pack}/_t_")
    assert r["exit_code"] == 0 and r["passed"] and r["reasons"] == []
    assert r["stdout_sha256"] == hashlib.sha256(b"hello\n").hexdigest()
    assert isinstance(r["duration_ms"], int) and r["duration_ms"] >= 0


def test_wrong_exit_code_fails(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": py("raise SystemExit(3)")}])
    run = run_any(pack)
    assert run["status"] == "fail"
    assert run["results"][0]["exit_code"] == 3
    assert run["results"][0]["reasons"] == ["exit code 3, expected 0"]


def test_expected_nonzero_exit_passes(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": py("raise SystemExit(1)"), "expect_exit": 1}])
    assert run_any(pack)["status"] == "pass"


def test_missing_stdout_fails(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": py("print('no')"), "expect_stdout_contains": ["yes"]}])
    assert run_any(pack)["results"][0]["reasons"] == ["stdout lacks 'yes'"]


def test_timeout_fails(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": py("import time; time.sleep(5)"), "timeout_s": 0.5}])
    r = run_any(pack)["results"][0]
    assert r["exit_code"] is None and r["reasons"] == ["timed out after 0.5s"]


def test_runs_in_temp_copy_with_scrubbed_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "do-not-leak")
    monkeypatch.setenv("ALLOWED_VAR", "visible")
    code = ("import os, json, pathlib; print(json.dumps({'cwd': os.getcwd(), 'home': os.environ['HOME'], "
            "'secret': os.environ.get('SECRET_TOKEN'), 'allowed': os.environ.get('ALLOWED_VAR')}))")
    pack = write_pack(tmp_path, tests=[{"id": "env", "run": py(code)}])
    m = json.loads((pack / "pack.json").read_text())
    m["permissions"]["env"] = ["ALLOWED_VAR"]
    (pack / "pack.json").write_text(json.dumps(m))
    seen = json.loads(run_any(pack)["results"][0]["output_tail"])
    assert seen["secret"] is None and seen["allowed"] == "visible"
    assert seen["cwd"] != str(pack.resolve()) and seen["cwd"].endswith("demo-pack")
    assert "rigpack-" in seen["home"]


def test_write_to_pack_is_caught_and_not_carried_forward(tmp_path):
    write = py("open('agents/injected.md', 'w').write('x')")
    check = py("import os; raise SystemExit(1 if os.path.exists('agents/injected.md') else 0)")
    pack = write_pack(tmp_path, tests=[{"id": "writer", "run": write}, {"id": "after", "run": check}])
    before = tree_sha256(pack)
    run = run_any(pack)
    assert run["results"][0]["reasons"] == ["modified pack files but permissions.writes_pack is false"]
    assert run["results"][1]["passed"]
    assert tree_sha256(pack) == before  # the source pack is never touched


def test_invalid_manifest_is_not_run(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": ["sh", "-c", "touch /tmp/should-not-run"]}])
    with pytest.raises(ManifestError):
        run_any(pack)


def test_only_filters_and_rejects_unknown_ids(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "a", "run": py("pass")}, {"id": "b", "run": py("pass")}])
    assert [r["id"] for r in run_any(pack, only=["b"])["results"]] == ["b"]
    with pytest.raises(ValueError):
        run_any(pack, only=["zzz"])

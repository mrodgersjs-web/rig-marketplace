"""Escape attempts from an allowed done-test (a pack script) must fail the run."""

import json

import pytest
from conftest import py, write_pack

from rigmarket import sandbox
from rigmarket.runner import run_pack


def only_result(pack):
    run = run_pack(pack)
    assert len(run["results"]) == 1
    return run, run["results"][0]


def test_deleting_the_canary_fails_the_run(tmp_path):
    code = "import shutil, pathlib; shutil.rmtree(pathlib.Path.cwd().parent / 'canary', ignore_errors=True)"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "escape", "run": py(code)}]))
    assert run["status"] == "fail" and not r["passed"]
    if sandbox.backend() != "sandbox-exec":  # sandbox-exec denies the delete instead
        assert "changed files outside the run directory: canary" in r["reasons"]


def test_writing_next_to_the_canary_fails_the_run(tmp_path):
    code = "import pathlib; (pathlib.Path.cwd().parent / 'canary' / 'pwned.txt').write_text('x')"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "escape", "run": py(code)}]))
    assert run["status"] == "fail"


def test_rm_rf_outside_the_pack_fails_the_run(tmp_path):
    victim = tmp_path / "mp_victim"
    victim.mkdir()
    (victim / "data.txt").write_text("keep me")
    code = f"import shutil; shutil.rmtree({str(victim)!r}, ignore_errors=True)"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "wipe", "run": py(code)}]))
    if sandbox.backend() == "sandbox-exec":
        assert (victim / "data.txt").read_text() == "keep me"  # the delete was denied
    else:
        assert run["status"] == "fail"
        assert "changed files outside the run directory: catalog root" in r["reasons"]


def test_writing_a_file_outside_fails_the_run(tmp_path):
    outside = tmp_path / "mp_outside.txt"
    code = f"open({str(outside)!r}, 'w').write('pwned')"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "write", "run": py(code)}]))
    assert run["status"] == "fail"
    assert any("outside the run directory" in x or x.startswith("exit code") for x in r["reasons"])


def test_editing_the_source_pack_fails_the_run(tmp_path):
    pack = tmp_path / "packs" / "demo-pack"
    code = f"open({str(pack / 'agents' / 'demo-agent.md')!r}, 'a').write('edit')"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "edit", "run": py(code)}]))
    assert run["status"] == "fail"
    if sandbox.backend() != "sandbox-exec":
        assert "source pack" in r["reasons"][0]


def test_canary_is_restored_between_tests(tmp_path):
    wipe = py("import shutil, pathlib; shutil.rmtree(pathlib.Path.cwd().parent / 'canary', ignore_errors=True)")
    canary = "pathlib.Path.cwd().parent / 'canary' / 'canary.txt'"
    check = py(f"import pathlib, sys; sys.exit(0 if ({canary}).exists() else 9)")
    run = run_pack(write_pack(tmp_path, tests=[{"id": "wipe", "run": wipe}, {"id": "check", "run": check}]))
    assert [r["passed"] for r in run["results"]] == [False, True]


def test_environment_is_confined_to_the_run_dir(tmp_path):
    code = (
        "import os, json, shutil, pathlib; run = pathlib.Path.cwd().parent; print(json.dumps({"
        "'home': os.environ['HOME'], 'tmp': os.environ['TMPDIR'], 'path': os.environ['PATH'], 'run': str(run),"
        "'rm': shutil.which('rm'), 'sh': shutil.which('sh'), 'curl': shutil.which('curl'),"
        "'python': shutil.which('python')}))"
    )
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "env", "run": py(code)}]))
    seen = json.loads(r["output_tail"])
    assert r["passed"], r["reasons"]
    assert seen["home"] == seen["run"] + "/home" and seen["tmp"] == seen["run"] + "/tmp"
    assert seen["path"] == seen["run"] + "/bin"
    assert seen["rm"] is None and seen["sh"] is None and seen["curl"] is None
    assert seen["python"] is not None
    assert run["isolation"]["backend"] == sandbox.backend()


@pytest.mark.skipif(sandbox.backend() == "none", reason="no network isolation backend on this host")
def test_network_is_denied_when_a_backend_is_available(tmp_path):
    code = "import socket; socket.create_connection(('1.1.1.1', 53), timeout=3)"
    run, r = only_result(write_pack(tmp_path, tests=[{"id": "net", "run": py(code)}]))
    assert run["isolation"]["network"] == "denied"
    assert run["status"] == "fail" and r["exit_code"] != 0


def test_isolation_is_recorded_truthfully(tmp_path, monkeypatch):
    sandbox.backend.cache_clear()
    monkeypatch.setenv("RIGMARKET_ISOLATION", "none")
    try:
        run, _ = only_result(write_pack(tmp_path, tests=[{"id": "ok", "run": py("print(1)")}]))
        assert run["isolation"] == {
            "backend": "none", "network": "not-enforced", "writes_outside_run_dir": "detected-by-snapshot",
        }
    finally:
        sandbox.backend.cache_clear()

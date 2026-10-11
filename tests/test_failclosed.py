"""Default runs fail closed without enforced OS containment; receipts say what was enforced.

Reviewer finding (PR #2): with no sandbox backend, an in-pack script wrote by absolute path, started
/bin/sh and still sealed as a pass, and the receipt claimed writes were 'detected-by-snapshot'.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from conftest import ENFORCED, UNCONTAINED_FLAG, py, write_pack

from rigmarket import sandbox
from rigmarket.cli import main
from rigmarket.hashing import tree_sha256
from rigmarket.manifest import ManifestError, validate_pack
from rigmarket.runner import ContainmentUnavailable, run_pack
from rigmarket.seal import VerifyError, seal, verify


@pytest.fixture
def no_backend(monkeypatch):
    """Force backend 'none' the documented way (RIGMARKET_ISOLATION=none)."""
    sandbox.probe.cache_clear()
    monkeypatch.setenv("RIGMARKET_ISOLATION", "none")
    yield
    sandbox.probe.cache_clear()


def escape_code(marker: Path) -> str:
    # The reviewer's escape: absolute-path write plus /bin/sh through subprocess (bypasses PATH and
    # the argv[0] command policy).
    return (
        "import subprocess\n"
        f"open({str(marker) + '.abs'!r}, 'w').write('escaped')\n"
        f"subprocess.run(['/bin/sh', '-c', 'echo shell > {marker}.sh'])\n"
    )


def markers(marker: Path) -> list[Path]:
    return [p for p in (Path(str(marker) + ".abs"), Path(str(marker) + ".sh")) if p.exists()]


# --- fail closed --------------------------------------------------------------------------------

def test_default_run_refuses_without_backend_and_runs_nothing(tmp_path, no_backend):
    marker = tmp_path / "outside" / "pwned"
    marker.parent.mkdir()
    pack = write_pack(tmp_path, tests=[{"id": "esc", "run": py(escape_code(marker))}])
    with pytest.raises(ContainmentUnavailable) as e:
        run_pack(pack)
    assert "'none'" in str(e.value) and "not enforced" in str(e.value)
    assert markers(marker) == []  # the script never started


def test_cli_default_refuses_with_exit_3_and_reports_backend(tmp_path, no_backend, capsys):
    marker = tmp_path / "outside" / "pwned"
    marker.parent.mkdir()
    write_pack(tmp_path, tests=[{"id": "esc", "run": py(escape_code(marker))}])
    assert main(["--root", str(tmp_path), "test", "--out-dir", str(tmp_path / "ev")]) == 3
    out = capsys.readouterr().out
    assert "isolation: backend=none enforced=false network=not-enforced writes_outside_run_dir=not-enforced" in out
    assert "REFUSED demo-pack" in out
    assert markers(marker) == [] and not (tmp_path / "ev").exists()


def test_nested_sandbox_probe_failure_means_none(monkeypatch):
    """Inside another sandbox sandbox-exec cannot start; simulated here by failing every probe run.

    This only simulates the probe result; it says nothing about any real host's sandbox.
    """
    sandbox.probe.cache_clear()
    monkeypatch.delenv("RIGMARKET_ISOLATION", raising=False)
    monkeypatch.setattr(sandbox, "_run_ok", lambda argv: False)
    try:
        iso = sandbox.describe()
        assert iso["backend"] == "none" and iso["enforced"] is False
        assert iso["network"] == "not-enforced" and iso["writes_outside_run_dir"] == "not-enforced"
    finally:
        sandbox.probe.cache_clear()


def test_probe_rejects_a_sandbox_that_does_not_deny_writes(monkeypatch):
    """A sandbox-exec that starts but lets writes through must not count as enforced."""
    if not Path("/usr/bin/touch").exists():
        pytest.skip("needs /usr/bin/touch")
    import subprocess

    def fake_sandbox(argv):  # drop `sandbox-exec -p <profile>` and run the command unsandboxed
        return subprocess.run(argv[3:], capture_output=True).returncode == 0

    monkeypatch.setattr(sandbox, "_run_ok", fake_sandbox)
    ok, why = sandbox._probe_sandbox_exec()
    assert ok is False and "did not deny" in why


def test_unshare_network_only_is_not_enforced(monkeypatch):
    sandbox.probe.cache_clear()
    monkeypatch.delenv("RIGMARKET_ISOLATION", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "/usr/bin/unshare")
    monkeypatch.setattr(sandbox, "_run_ok", lambda argv: True)
    try:
        iso = sandbox.describe()
        assert iso["backend"] == "unshare-net" and iso["network"] == "denied"
        assert iso["enforced"] is False and iso["writes_outside_run_dir"] == "not-enforced"
    finally:
        sandbox.probe.cache_clear()


# --- explicit opt-in: still honest, still rejected by default at verify ---------------------------

def test_opt_in_run_is_marked_and_verify_rejects_it_by_default(tmp_path, no_backend, key):
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    run = run_pack(pack, allow_uncontained=True)
    assert run["status"] == "pass" and run["isolation"]["enforced"] is False
    assert "detected-by-snapshot" not in json.dumps(run)
    packet = seal(run, key)
    with pytest.raises(VerifyError) as e:
        verify(packet, key)
    assert e.value.code == "uncontained"
    assert verify(packet, key, allow_uncontained=True)["status"] == "pass"


def test_packet_without_enforced_field_is_rejected(tmp_path, key):
    """Packets sealed by older versions (no 'enforced') are not trusted as contained."""
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    run = run_pack(pack, allow_uncontained=True)
    run["isolation"] = {"backend": "none", "network": "not-enforced", "writes_outside_run_dir": "detected-by-snapshot"}
    with pytest.raises(VerifyError) as e:
        verify(seal(run, key), key)
    assert e.value.code == "uncontained"


def test_cli_verify_rejects_uncontained_packet(tmp_path, no_backend, key, capsys):
    write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    root = ["--root", str(tmp_path)]
    assert main([*root, "test", "--allow-uncontained", "--out-dir", str(tmp_path / "ev")]) == 0
    assert main(["seal", str(tmp_path / "ev" / "demo-pack.run.json")]) == 0
    packet = str(tmp_path / "ev" / "demo-pack.packet.json")
    assert main(["verify", packet]) == 1
    assert main(["verify", "--allow-uncontained", packet]) == 0
    out = capsys.readouterr().out
    assert "WARNING: --allow-uncontained" in out and "REJECT" in out and "uncontained" in out and "VALID" in out


# --- real enforcement (only where the OS sandbox is actually available) ---------------------------

@pytest.mark.skipif(not ENFORCED, reason="no enforced OS sandbox on this host (default runs refuse here)")
def test_default_flow_contains_policy_bypass_via_subprocess(tmp_path):
    """Allowed {python} script starts /bin/sh (bypassing the argv[0] policy): the OS denies its writes."""
    marker = tmp_path / "outside" / "pwned"
    marker.parent.mkdir()
    pack = write_pack(tmp_path, tests=[{"id": "esc", "run": py(escape_code(marker))}])
    run = run_pack(pack)  # default flow, no opt-in
    assert run["isolation"]["enforced"] is True and run["isolation"]["backend"] == "sandbox-exec"
    assert run["status"] == "fail"
    assert markers(marker) == []


@pytest.mark.skipif(not ENFORCED, reason="no enforced OS sandbox on this host (default runs refuse here)")
def test_default_flow_runs_and_verifies_where_enforced(tmp_path, key):
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    run = run_pack(pack)
    assert run["status"] == "pass" and run["isolation"]["enforced"] is True
    assert verify(seal(run, key), key, pack_dir=pack)["status"] == "pass"


# --- symlinks -------------------------------------------------------------------------------------

def _symlink_pack(tmp_path, link_name="link", to_dir=True):
    outside = tmp_path / "outside_secret"
    outside.mkdir()
    (outside / "s.txt").write_text("secret")
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    target = outside if to_dir else outside / "s.txt"
    (pack / link_name).symlink_to(target)
    return pack


@pytest.mark.parametrize("to_dir", [True, False])
def test_symlink_in_pack_is_rejected_cleanly(tmp_path, capsys, to_dir):
    pack = _symlink_pack(tmp_path, to_dir=to_dir)
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    assert e.value.errors == ["symlinks are not allowed in a pack: link"]
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert main(["--root", str(tmp_path), "test", *UNCONTAINED_FLAG]) == 1
    out = capsys.readouterr().out
    assert "symlinks are not allowed in a pack: link" in out and "invalid manifest" in out
    with pytest.raises(ManifestError):
        run_pack(pack, allow_uncontained=True)


def test_nested_symlink_and_script_symlink_are_rejected(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": ["{python}", "{pack}/tool.py"]}])
    (tmp_path / "evil.py").write_text("print('outside code')\n")
    (pack / "tool.py").symlink_to(tmp_path / "evil.py")
    (pack / "agents" / "deep").mkdir()
    (pack / "agents" / "deep" / "up").symlink_to(tmp_path)
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    assert sorted(e.value.errors) == [
        "symlinks are not allowed in a pack: agents/deep/up",
        "symlinks are not allowed in a pack: tool.py",
    ]


def test_tree_hash_does_not_follow_or_crash_on_symlinked_dirs(tmp_path):
    pack = _symlink_pack(tmp_path)
    h1 = tree_sha256(pack)  # previously IsADirectoryError
    (tmp_path / "outside_secret" / "s.txt").write_text("changed")
    assert tree_sha256(pack) == h1  # content behind the link is not read
    os.remove(pack / "link")
    (pack / "link").symlink_to(tmp_path)
    assert tree_sha256(pack) != h1  # the link target text is hashed


def test_catalog_source_outside_root_or_through_symlink_is_rejected(tmp_path, capsys):
    real = write_pack(tmp_path / "elsewhere")
    root = tmp_path / "market"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "packs").mkdir()
    (root / "packs" / "demo-pack").symlink_to(real)
    cat = {"name": "m", "plugins": [{"name": "demo-pack", "source": "./packs/demo-pack"},
                                    {"name": "far", "source": "../elsewhere/packs/demo-pack"}]}
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(cat))
    assert main(["--root", str(root), "validate"]) == 1
    out = capsys.readouterr().out
    assert "goes through a symlink (demo-pack)" in out
    assert "'../elsewhere/packs/demo-pack' is outside the marketplace root" in out
    assert main(["--root", str(root), "test", "demo-pack", *UNCONTAINED_FLAG]) == 2


# --- command policy bypass attempts ----------------------------------------------------------------

@pytest.mark.parametrize("env", ["PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONBREAKPOINT", "DYLD_FRAMEWORK_PATH",
                                 "LD_AUDIT"])
def test_interpreter_and_loader_env_cannot_be_passed_through(tmp_path, env):
    pack = write_pack(tmp_path, permissions={"commands": ["{python}"], "env": [env], "writes_pack": False})
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    assert any(env in err for err in e.value.errors)


def test_nul_byte_argument_is_rejected_not_crashing(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "nul", "run": ["{python}", "{pack}/x.py\u0000"]}])
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    assert any("NUL" in err for err in e.value.errors)

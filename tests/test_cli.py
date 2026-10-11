import json

from conftest import REPO, UNCONTAINED_FLAG, py, write_pack

from rigmarket.cli import main


def test_full_flow_on_bundled_packs(tmp_path, key, capsys):
    root = ["--root", str(REPO)]
    assert main([*root, "validate"]) == 0
    assert main([*root, "test", "rig-gtm-pack", "rig-content-pack", "rig-engineering-pack",
                 "--out-dir", str(tmp_path), *UNCONTAINED_FLAG]) == 0
    packets = []
    for name in ("rig-gtm-pack", "rig-content-pack", "rig-engineering-pack"):
        assert main(["seal", str(tmp_path / f"{name}.run.json")]) == 0
        packets.append(str(tmp_path / f"{name}.packet.json"))
    assert main([*root, "verify", "--check-pack", *UNCONTAINED_FLAG, *packets]) == 0
    out = capsys.readouterr().out
    assert out.count("VALID ") == 3 and "REJECT" not in out


def test_verify_rejects_tampered_packet_and_exits_1(tmp_path, key, capsys):
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print(1)")}])
    out_dir = str(tmp_path / "out")
    assert main(["--root", str(tmp_path), "test", "demo-pack", "--out-dir", out_dir, *UNCONTAINED_FLAG]) == 0
    assert main(["seal", str(tmp_path / "out" / "demo-pack.run.json")]) == 0
    packet_path = tmp_path / "out" / "demo-pack.packet.json"
    packet = json.loads(packet_path.read_text())
    packet["run"]["results"][0]["output_tail"] = "forged\n"
    packet_path.write_text(json.dumps(packet))
    assert main(["verify", "--allow-uncontained", str(packet_path)]) == 1
    out = capsys.readouterr().out
    assert "REJECT" in out and "bad-signature" in out and pack.exists()


def test_seal_and_verify_without_key_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("RIG_SEAL_KEY", raising=False)
    (tmp_path / "r.run.json").write_text("{}")
    assert main(["seal", str(tmp_path / "r.run.json")]) == 2
    assert main(["verify", str(tmp_path / "r.run.json")]) == 2
    assert "RIG_SEAL_KEY is not set" in capsys.readouterr().err


def test_test_command_reports_failures(tmp_path, capsys):
    write_pack(tmp_path, tests=[{"id": "bad", "run": py("raise SystemExit(4)")}])
    assert main(["--root", str(tmp_path), "test", *UNCONTAINED_FLAG]) == 1
    assert "bad: exit code 4, expected 0" in capsys.readouterr().out


def test_list_counts_come_from_files(capsys):
    assert main(["--root", str(REPO), "list", "--json"]) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out)["packs"]}
    agents = len(list((REPO / "packs" / "rig-prime-fleet" / "agents").glob("*.md")))
    assert rows["rig-prime-fleet"]["agents"] == agents

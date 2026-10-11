import copy
import json

import pytest
from conftest import py, write_pack

from rigmarket.runner import run_pack
from rigmarket.seal import SealError, SealKeyError, VerifyError, load_key, seal, verify


@pytest.fixture
def passing(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "ok", "run": py("print('ok')")}])
    return pack, run_pack(pack)


def rejects(code, packet, key, **kw):
    with pytest.raises(VerifyError) as e:
        verify(packet, key, **kw)
    assert e.value.code == code, str(e.value)


def test_round_trip(passing, key):
    pack, run = passing
    packet = seal(run, key)
    assert packet["signature"]["alg"] == "HMAC-SHA256"
    assert verify(json.loads(json.dumps(packet)), key, pack_dir=pack) == run


def test_key_must_be_set_and_long_enough():
    with pytest.raises(SealKeyError):
        load_key({})
    with pytest.raises(SealKeyError):
        load_key({"RIG_SEAL_KEY": "short"})
    assert load_key({"RIG_SEAL_KEY": "k" * 32}) == b"k" * 32


def test_packet_never_contains_the_key(passing, key):
    assert key.decode() not in json.dumps(seal(passing[1], key))


def test_rejects_edited_result(passing, key):
    packet = seal(passing[1], key)
    packet["run"]["results"][0]["exit_code"] = 0 if packet["run"]["results"][0]["exit_code"] else 1
    rejects("bad-signature", packet, key)


def test_rejects_edit_even_when_digest_is_recomputed(passing, key):
    from rigmarket.hashing import canonical_json, sha256_bytes

    packet = seal(passing[1], key)
    packet["run"]["results"][0]["duration_ms"] = 1
    packet["run_sha256"] = sha256_bytes(canonical_json(packet["run"]))
    rejects("bad-signature", packet, key)


def test_rejects_edited_signature(passing, key):
    packet = seal(passing[1], key)
    packet["signature"]["value"] = "0" * 64
    rejects("bad-signature", packet, key)


def test_rejects_unsigned(passing, key):
    packet = seal(passing[1], key)
    del packet["signature"]
    rejects("unsigned", packet, key)
    packet["signature"] = {"alg": "HMAC-SHA256", "value": ""}
    rejects("unsigned", packet, key)


def test_rejects_other_algorithm(passing, key):
    packet = seal(passing[1], key)
    packet["signature"]["alg"] = "none"
    rejects("bad-alg", packet, key)


def test_rejects_wrong_key(passing, key):
    packet = seal(passing[1], key)
    rejects("wrong-key", packet, b"x" * 64)


def test_rejects_forged_key_id(passing, key):
    other = b"y" * 64
    packet = seal(passing[1], other)
    from rigmarket.seal import key_id

    packet["key_id"] = key_id(key)  # claims our key, signed with another
    rejects("bad-signature", packet, key)


def test_rejects_raw_run_document(passing, key):
    rejects("bad-schema", passing[1], key)
    rejects("bad-schema", [], key)


def test_rejects_failing_run_unless_allowed(tmp_path, key):
    pack = write_pack(tmp_path, tests=[{"id": "bad", "run": py("raise SystemExit(2)")}])
    packet = seal(run_pack(pack), key)
    rejects("failed-tests", packet, key)
    assert verify(packet, key, allow_fail=True)["status"] == "fail"


def test_rejects_pack_changed_after_sealing(passing, key):
    pack, run = passing
    packet = seal(run, key)
    (pack / "agents" / "late-edit.md").write_text("x")
    rejects("pack-changed", packet, key, pack_dir=pack)


def test_rejects_manifest_changed_after_sealing(passing, key):
    pack, run = passing
    packet = seal(run, key)
    (pack / "pack.json").write_text((pack / "pack.json").read_text() + "\n")
    rejects("manifest-changed", packet, key, pack_dir=pack)


def test_seal_refuses_inconsistent_run(passing, key):
    run = copy.deepcopy(passing[1])
    run["results"][0]["passed"] = False  # passed=False but no reasons
    with pytest.raises(SealError):
        seal(run, key)
    run = copy.deepcopy(passing[1])
    run["results"][0].update(passed=False, reasons=["exit code 1, expected 0"])  # status still 'pass'
    with pytest.raises(SealError, match="disagrees with the results"):
        seal(run, key)


def test_seal_refuses_non_run_documents(key):
    for doc in ({}, {"schema": "rig.run.v1"}, {"schema": "rig.run.v1", "pack": "p", "version": "1",
                 "manifest_sha256": "", "pack_tree_sha256": "", "status": "pass", "results": []}):
        with pytest.raises(SealError):
            seal(doc, key)

"""Ledger: tamper-evidence. Break one record, the chain catches it."""
import json

from execution.ledger import Ledger, GENESIS_HASH


def test_chain_verifies(tmp_path):
    led = Ledger(tmp_path / "ledger.jsonl")
    led.append("signal", {"symbol": "AAPL", "expected_return": 0.01})
    led.append("proposal", {"symbol": "AAPL", "qty": 0.1})
    led.append("risk_decision", {"allow": True, "code": "ALLOW"})
    ok, bad = led.verify()
    assert ok and bad is None


def test_genesis_prev_hash(tmp_path):
    led = Ledger(tmp_path / "ledger.jsonl")
    rec = led.append("signal", {"x": 1})
    assert rec["prev_hash"] == GENESIS_HASH
    assert rec["seq"] == 1


def test_tamper_detected_at_right_seq(tmp_path):
    led = Ledger(tmp_path / "ledger.jsonl")
    for i in range(5):
        led.append("signal", {"i": i, "qty": 0.1})
    # Tamper with record seq 3 on disk.
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    rec = json.loads(lines[2])
    rec["data"]["qty"] = 999.0
    lines[2] = json.dumps(rec, sort_keys=True)
    (tmp_path / "ledger.jsonl").write_text("\n".join(lines) + "\n")
    ok, bad = led.verify()
    assert not ok and bad == 3


def test_prev_hash_link_tamper_detected(tmp_path):
    led = Ledger(tmp_path / "ledger.jsonl")
    led.append("signal", {"i": 0})
    led.append("signal", {"i": 1})
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    rec = json.loads(lines[1])
    rec["prev_hash"] = "0" * 64
    lines[1] = json.dumps(rec, sort_keys=True)
    (tmp_path / "ledger.jsonl").write_text("\n".join(lines) + "\n")
    ok, bad = led.verify()
    assert not ok and bad == 2


def test_unknown_record_type_rejected(tmp_path):
    led = Ledger(tmp_path / "ledger.jsonl")
    try:
        led.append("teleport", {"x": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown record type must raise")


def test_full_pipeline_chain(tmp_path):
    """signal -> proposal -> risk_decision -> order -> fill -> position."""
    led = Ledger(tmp_path / "ledger.jsonl")
    for rtype in ("signal", "proposal", "risk_decision", "order", "fill",
                  "position"):
        led.append(rtype, {"symbol": "AAPL"})
    ok, _ = led.verify()
    assert ok
    assert [r["type"] for r in led.tail(6)] == [
        "signal", "proposal", "risk_decision", "order", "fill", "position"]

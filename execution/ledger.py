"""Hash-chained append-only ledger.

Every pipeline step is recorded: signal -> proposal -> risk_decision ->
order -> fill -> position. Each record carries ``prev_hash`` and ``hash``;
``hash = sha256(canonical_json(record_without_hash))``. Tampering with any
record breaks every subsequent link — verified by ``verify()`` and by the
independent C# verifier in tools/LedgerVerify/.

Canonical JSON: ``json.dumps(sort_keys=True, separators=(",", ":"))`` —
byte-stable across Python versions and platforms.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GENESIS_HASH = "0" * 64

RECORD_TYPES = ("signal", "proposal", "risk_decision", "order", "fill",
                "position", "benchmark", "note")


def canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def hash_record(record: dict) -> str:
    return hashlib.sha256(canonical(record)).hexdigest()


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = self._last_seq()
        self._last_hash = self._last_hash_value()

    def _read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _last_seq(self) -> int:
        records = self._read_all()
        return records[-1]["seq"] if records else 0

    def _last_hash_value(self) -> str:
        records = self._read_all()
        return records[-1]["hash"] if records else GENESIS_HASH

    def append(self, record_type: str, data: dict) -> dict:
        if record_type not in RECORD_TYPES:
            raise ValueError(f"unknown record type: {record_type}")
        self._seq += 1
        record = {
            "seq": self._seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": record_type,
            "data": data,
            "prev_hash": self._last_hash,
        }
        record["hash"] = hash_record(record)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        self._last_hash = record["hash"]
        return record

    def verify(self) -> tuple[bool, int | None]:
        """Re-verify the full chain. Returns (ok, bad_seq_or_None)."""
        prev = GENESIS_HASH
        for rec in self._read_all():
            if rec["prev_hash"] != prev:
                return False, rec["seq"]
            check = {k: v for k, v in rec.items() if k != "hash"}
            if hash_record(check) != rec["hash"]:
                return False, rec["seq"]
            prev = rec["hash"]
        return True, None

    def tail(self, n: int = 20) -> list[dict]:
        return self._read_all()[-n:]

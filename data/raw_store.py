"""Append-only raw store: byte-identical API responses, JSONL.

Every API response is persisted BEFORE any processing. Reprocessing must be
reproducible from raw + code hash. Files are append-only: this module never
opens a raw file for writing except in ``'a'`` mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class RawStore:
    def __init__(self, root: str | Path = "data/raw"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, source: str, day: str) -> Path:
        d = self.root / source
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{day}.jsonl"

    def append(self, source: str, payload: dict) -> Path:
        """Persist one API response. Returns the file written."""
        record = {
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            # Canonical serialization: deterministic bytes for the same payload.
            "payload": json.loads(json.dumps(payload, sort_keys=True)),
        }
        day = record["stored_at"][:10]
        path = self._path(source, day)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        return path

    def iter_records(self, source: str):
        """Yield stored records in insertion order."""
        d = self.root / source
        if not d.exists():
            return
        for path in sorted(d.glob("*.jsonl")):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)

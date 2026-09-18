"""Point-in-time feature tables.

Every feature row carries ``as_of`` (the decision timestamp it was valid for)
and ``source_max_ts`` (the newest source timestamp consumed to build it).
Invariant: ``source_max_ts <= as_of``. Always. ``data.integrity`` tests it.

Storage is JSONL (one row per line). Parquet is the documented target format
at scale; JSONL keeps the dependency set at numpy/pandas only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class FeatureTable:
    REQUIRED = ("symbol", "as_of", "source_max_ts", "features")

    def __init__(self, name: str, root: str | Path = "data/features"):
        self.name = name
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / f"{name}.jsonl"
        self._rows: list[dict] = []

    def add_row(self, symbol: str, as_of: str, features: dict,
                source_max_ts: str) -> None:
        if not (source_max_ts <= as_of):
            raise ValueError(
                f"leakage at write time: source_max_ts {source_max_ts} "
                f"is newer than as_of {as_of} for {symbol}"
            )
        self._rows.append({
            "symbol": symbol,
            "as_of": as_of,
            "source_max_ts": source_max_ts,
            "features": dict(features),
        })

    def flush(self) -> Path:
        with open(self.path, "a", encoding="utf-8") as f:
            for row in self._rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")
        n = len(self._rows)
        self._rows.clear()
        return self.path

    def load(self) -> pd.DataFrame:
        rows = []
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rows.append(json.loads(line))
        return pd.DataFrame(rows, columns=list(self.REQUIRED))

    def at_or_before(self, timestamp: str) -> pd.DataFrame:
        """Point-in-time slice: only rows knowable at ``timestamp``."""
        df = self.load()
        if df.empty:
            return df
        return df[df["as_of"] <= timestamp].copy()

"""Validated config loader with frozen-config integrity checks.

Workflow:
    1. Edit YAML configs freely during research.
    2. Before Day 1, run ``python -m config.freeze`` — records SHA-256 of every
       config file in ``config/manifest.json`` and flips their ``status`` to
       ``frozen`` (manual edit, journaled).
    3. After that, ``load_config`` verifies every file against the manifest.
       Any byte-level mutation -> ``ConfigMutatedError``. No silent drift.

Hard constraints (capital == $100, 30 days, long-only, no leverage, ...) are
asserted on load via ``assert_hard_constraints`` — they are code, not comments.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent
MANIFEST = CONFIG_DIR / "manifest.json"

TRACKED = [
    "universe.yaml",
    "costs.yaml",
    "risk.yaml",
    "strategies/strategy_v1.yaml",
]


class ConfigError(Exception):
    """Base config error."""


class ConfigMutatedError(ConfigError):
    """A frozen config file was modified after freezing."""


class ConfigNotFrozenWarning(UserWarning):
    """Raised when loading configs that have never been frozen."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_configs() -> dict:
    """Record hashes of all tracked configs. Run once before Day 1."""
    manifest = {rel: sha256_file(CONFIG_DIR / rel) for rel in TRACKED}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def _verify_against_manifest() -> None:
    if not MANIFEST.exists():
        warnings.warn(
            "configs are not frozen (no manifest.json). "
            "Run `python -m config.freeze` before Day 1.",
            ConfigNotFrozenWarning,
            stacklevel=3,
        )
        return
    manifest = json.loads(MANIFEST.read_text())
    for rel in TRACKED:
        expected = manifest.get(rel)
        actual = sha256_file(CONFIG_DIR / rel)
        if expected != actual:
            raise ConfigMutatedError(
                f"frozen config mutated: {rel} "
                f"(expected {expected[:12]}, got {actual[:12]}). "
                "Config changes after freezing require a new strategy version."
            )


def load_yaml(rel: str) -> dict:
    _verify_against_manifest()
    with open(CONFIG_DIR / rel) as f:
        return yaml.safe_load(f)


def load_all() -> dict:
    """Load every tracked config, verified and hard-constraint checked."""
    cfgs = {rel: load_yaml(rel) for rel in TRACKED}
    assert_hard_constraints(cfgs)
    return cfgs


def assert_hard_constraints(cfgs: dict) -> None:
    """Encode the experiment's non-negotiable constraints as assertions."""
    risk = cfgs["risk.yaml"]
    exp = risk["experiment"]
    pf = risk["portfolio"]
    assert exp["capital"] == 100.0, "capital must be exactly $100"
    assert exp["calendar_days"] == 30, "experiment must be 30 calendar days"
    assert pf["long_only"] is True, "long-only is structural"
    assert pf["leverage_allowed"] is False, "no leverage"
    assert pf["margin_allowed"] is False, "no margin"
    assert pf["derivatives_allowed"] is False, "no derivatives"
    assert risk["liquidity"]["min_price"] == 5.0, "penny-stock floor is $5"
    assert pf["max_gross_exposure_pct"] <= 1.0, "gross exposure cannot exceed 100%"
    universe = cfgs["universe.yaml"]["symbols"]
    assert "SPY" in universe, "SPY (benchmark) must be in the universe"
    assert len(universe) <= 30, "universe capped at 30 symbols (websocket limit)"
    costs = cfgs["costs.yaml"]
    assert costs["slippage_bps_one_way"] >= 0, "slippage assumption must be >= 0"


if __name__ == "__main__":
    manifest = freeze_configs()
    print(f"froze {len(manifest)} configs -> {MANIFEST}")

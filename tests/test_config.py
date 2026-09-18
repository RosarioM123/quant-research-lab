"""Config loader: hard constraints are validated in code, not trusted.

NOTE: these tests monkeypatch config.loader.CONFIG_DIR/MANIFEST onto a temp
copy. The real config tree is never frozen by tests: no manifest.json may be
created there until the documented universe/parameters are frozen for Day 1.
"""
import shutil

import pytest
import yaml

import config.loader as L
from config.loader import ConfigMutatedError, load_all


@pytest.fixture()
def cfg_copy(tmp_path, monkeypatch):
    dst = tmp_path / "config"
    shutil.copytree("/home/hatch/workspace/signal-build/config", dst)
    monkeypatch.setattr(L, "CONFIG_DIR", dst)
    monkeypatch.setattr(L, "MANIFEST", dst / "manifest.json")
    return dst


def test_load_all_validates(cfg_copy):
    cfg = load_all()
    assert cfg["risk.yaml"]["experiment"]["capital"] == 100.0
    assert cfg["risk.yaml"]["portfolio"]["max_gross_exposure_pct"] <= 1.0


def test_freeze_detects_mutation(cfg_copy):
    L.freeze_configs()
    assert (cfg_copy / "manifest.json").exists()
    p = cfg_copy / "risk.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["portfolio"]["max_position_pct"] = 0.99
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(ConfigMutatedError):
        load_all()


def test_unfrozen_load_warns_but_succeeds(cfg_copy):
    with pytest.warns(L.ConfigNotFrozenWarning):
        load_all()  # no manifest: allowed, with an explicit warning


def test_reject_margin_in_config(cfg_copy):
    p = cfg_copy / "risk.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["portfolio"]["margin_allowed"] = True
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(AssertionError):
        load_all()


def test_reject_wrong_capital(cfg_copy):
    p = cfg_copy / "risk.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["experiment"]["capital"] = 1000
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(AssertionError):
        load_all()


def test_reject_leverage(cfg_copy):
    p = cfg_copy / "risk.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["portfolio"]["leverage_allowed"] = True
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(AssertionError):
        load_all()


def test_reject_missing_spy(cfg_copy):
    p = cfg_copy / "universe.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["symbols"] = [s for s in doc["symbols"] if s != "SPY"]
    p.write_text(yaml.safe_dump(doc))
    with pytest.raises(AssertionError):
        load_all()


def test_real_config_dir_has_no_manifest():
    # The experiment is not started: the real tree must stay unfrozen.
    import config.loader as loader  # fresh reference, no fixture active
    assert not loader.MANIFEST.exists(), (
        "manifest.json exists in the real config tree: "
        "freezing happens only when Day-1 parameters are final")

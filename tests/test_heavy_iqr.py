"""Tests for the IQR heavy-selector rule (v0.2.0)."""

from __future__ import annotations

import pandas as pd
import pytest

from overlap_qc.config import ConfigError, HeavySelector, load_config
from overlap_qc.heavy_selector import compute_heavy


def test_iqr_flags_tukey_outlier():
    # 12 respondents pick 1 option; one picks all 5 -> Tukey outlier.
    rows = [{"id": f"R{i}", "Q1": 1, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0}
            for i in range(12)]
    rows.append({"id": "ROUT", "Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1})
    df = pd.DataFrame(rows)
    check = HeavySelector(name="c", columns=["Q1", "Q2", "Q3", "Q4", "Q5"], iqr=1.5)
    result = compute_heavy(df, check, id_col="id")
    assert "ROUT" in result.flagged_ids


def test_iqr_appears_in_describe():
    check = HeavySelector(name="c", columns=["Q1", "Q2"], iqr=1.5)
    assert "IQR" in check.describe()


def test_loader_accepts_iqr(tmp_path):
    text = """
id: id
heavy_selectors:
  - name: blk
    columns: [A1, A2, A3]
    iqr: 1.5
"""
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    cfg = load_config(p)
    assert cfg.heavy_selectors[0].iqr == 1.5


def test_loader_rejects_negative_iqr(tmp_path):
    text = """
id: id
heavy_selectors:
  - name: blk
    columns: [A1, A2]
    iqr: -1
"""
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    with pytest.raises(ConfigError):
        load_config(p)

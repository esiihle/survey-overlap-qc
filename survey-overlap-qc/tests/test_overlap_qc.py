"""Tests for the overlap-qc pipeline.

Run with: pytest -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from overlap_qc import (
    compute_all_heavy,
    compute_group,
    flags_frame,
    load_config,
    render_html,
)
from overlap_qc.config import (
    AnalysisConfig,
    ConfigError,
    HeavySelector,
    OverlapGroup,
    SetDef,
)
from overlap_qc.heavy_selector import compute_heavy
from overlap_qc.overlap import compute_all_groups, slugify


def make_frame() -> pd.DataFrame:
    # 5 respondents, 3 brand indicators + weight.
    return pd.DataFrame(
        {
            "respondent_id": ["R1", "R2", "R3", "R4", "R5"],
            "weight": ["1.0", "1.0", "2.0", "1.0", "1.0"],
            "A": [1, 1, 0, 0, 1],
            "B": [1, 0, 1, 0, 1],
            "C": [0, 0, 1, 0, 1],
        }
    )


def make_group() -> OverlapGroup:
    return OverlapGroup(
        name="Test group",
        sets=[
            SetDef("A", ["A"]),
            SetDef("B", ["B"]),
            SetDef("C", ["C"]),
        ],
    )


# --- overlap ---------------------------------------------------------------

def test_regions_partition_respondents():
    df = make_frame()
    result = compute_group(df, make_group(), weight_col="weight")
    assert sum(r.n for r in result.regions) == len(df)


def test_region_assignment_is_correct():
    df = make_frame()
    result = compute_group(df, make_group(), weight_col="weight")
    by_label = {r.label: r.n for r in result.regions}
    # R1: A&B, R2: A only, R3: B&C, R4: none, R5: A&B&C
    assert by_label["A only"] == 1
    assert by_label["A & B"] == 1
    assert by_label["B & C"] == 1
    assert by_label["A & B & C"] == 1
    assert by_label["None (in no set)"] == 1


def test_weighted_percentages_use_weights():
    df = make_frame()
    result = compute_group(df, make_group(), weight_col="weight")
    total_w = result.total_weight
    assert total_w == pytest.approx(6.0)  # 1+1+2+1+1
    # B&C region is R3 with weight 2 -> 2/6 = 33.3%
    bc = next(r for r in result.regions if r.label == "B & C")
    assert bc.weighted_n == pytest.approx(2.0)
    assert bc.pct == pytest.approx(100 * 2 / 6, abs=0.05)


def test_multi_column_set_uses_or():
    df = pd.DataFrame({"id": ["R1", "R2"], "X1": [1, 0], "X2": [0, 0]})
    group = OverlapGroup(
        name="g", sets=[SetDef("X", ["X1", "X2"]), SetDef("none", ["nonexist_ok"])],
    )
    # Use a column that exists for the second set to keep it valid.
    group = OverlapGroup(
        name="g", sets=[SetDef("X", ["X1", "X2"]), SetDef("Y", ["X2"])],
    )
    result = compute_group(df, group, weight_col=None)
    x_only = next((r for r in result.regions if r.label == "X only"), None)
    assert x_only is not None and x_only.n == 1  # R1 in X via X1


def test_derived_variables_named_and_binary():
    df = make_frame()
    result = compute_group(df, make_group(), weight_col="weight")
    # Set-membership columns exist and are 0/1.
    assert "set__test_group__a" in result.derived.columns
    region_cols = [c for c in result.derived.columns if c.startswith("ovl__")]
    assert region_cols
    for c in region_cols:
        assert set(result.derived[c].dropna().unique()) <= {0, 1}


def test_slugify():
    assert slugify("Premium tier!") == "premium_tier"
    assert slugify("  A & B  ") == "a_b"


# --- heavy selector --------------------------------------------------------

def test_heavy_absolute_threshold():
    df = pd.DataFrame(
        {
            "id": ["R1", "R2", "R3"],
            "Q1": [1, 1, 0], "Q2": [1, 0, 0], "Q3": [1, 0, 0], "Q4": [1, 0, 1],
        }
    )
    check = HeavySelector(name="c", columns=["Q1", "Q2", "Q3", "Q4"], max_absolute=4)
    result = compute_heavy(df, check, id_col="id")
    assert result.flagged_ids == ["R1"]           # only R1 selected all 4
    assert result.counts.loc["R1"] == 4
    assert result.n_flagged == 1


def test_heavy_fraction_threshold():
    df = pd.DataFrame(
        {"id": ["R1", "R2"], "Q1": [1, 1], "Q2": [1, 0], "Q3": [1, 0], "Q4": [1, 0]}
    )
    check = HeavySelector(name="c", columns=["Q1", "Q2", "Q3", "Q4"], fraction=0.9)
    result = compute_heavy(df, check, id_col="id")
    assert set(result.flagged_ids) == {"R1"}       # 4/4 >= 0.9*4


def test_heavy_sd_rule_flags_outlier():
    # 9 respondents pick 1 option, one picks all 5 -> clear outlier.
    rows = []
    for i in range(9):
        rows.append({"id": f"R{i}", "Q1": 1, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0})
    rows.append({"id": "ROUT", "Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1})
    df = pd.DataFrame(rows)
    check = HeavySelector(
        name="c", columns=["Q1", "Q2", "Q3", "Q4", "Q5"], sd_above_mean=2.0
    )
    result = compute_heavy(df, check, id_col="id")
    assert "ROUT" in result.flagged_ids


def test_flags_frame_has_any_column():
    df = pd.DataFrame(
        {"id": ["R1", "R2"], "Q1": [1, 0], "Q2": [1, 0], "Q3": [1, 0], "Q4": [1, 0]}
    )
    checks = [HeavySelector(name="Block A", columns=["Q1", "Q2", "Q3", "Q4"],
                            max_absolute=4)]
    results = compute_all_heavy(df, checks, id_col="id")
    frame = flags_frame(results, "id")
    assert "flag__any" in frame.columns
    assert frame.loc[frame["id"] == "R1", "flag__any"].iloc[0] == 1
    assert frame.loc[frame["id"] == "R2", "flag__any"].iloc[0] == 0


# --- report ----------------------------------------------------------------

def test_html_is_self_contained():
    df = make_frame()
    config = AnalysisConfig(
        id_col="respondent_id", weight_col="weight",
        overlap_groups=[make_group()],
        heavy_selectors=[HeavySelector(name="blk", columns=["A", "B", "C"],
                                       max_absolute=3)],
    )
    groups = compute_all_groups(df, config.overlap_groups, config.weight_col)
    heavy = compute_all_heavy(df, config.heavy_selectors, config.id_col)
    html = render_html(config, groups, heavy)
    # No external resource references of any kind.
    for needle in ["http://", "https://", "src=", "<script", "cdn", "@import"]:
        assert needle not in html.lower(), f"report references external resource: {needle}"
    assert "<svg" in html          # Venn drawn inline
    assert "Synthetic data" in html


# --- config loader ---------------------------------------------------------

def test_loader_reads_example(tmp_path):
    text = """
id: respondent_id
weight: weight
overlap_groups:
  - name: g1
    sets:
      - {label: A, columns: [A1]}
      - {label: B, columns: [B1, B2]}
heavy_selectors:
  - name: blk
    columns: [A1, B1, B2]
    max_absolute: 2
"""
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    cfg = load_config(p)
    assert cfg.weight_col == "weight"
    assert len(cfg.overlap_groups) == 1
    assert cfg.overlap_groups[0].sets[1].columns == ["B1", "B2"]
    assert cfg.heavy_selectors[0].max_absolute == 2


def test_loader_rejects_group_with_one_set(tmp_path):
    text = """
id: id
overlap_groups:
  - name: bad
    sets:
      - {label: A, columns: [A1]}
"""
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    with pytest.raises(ConfigError):
        load_config(p)


def test_loader_rejects_heavy_with_no_rule(tmp_path):
    text = """
id: id
heavy_selectors:
  - name: bad
    columns: [A1, A2]
"""
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    with pytest.raises(ConfigError):
        load_config(p)

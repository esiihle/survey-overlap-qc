"""Report tests for the pairwise section and large-set handling (v0.2.0)."""

from __future__ import annotations

import pandas as pd

from overlap_qc import compute_all_groups, compute_all_heavy, render_html
from overlap_qc.config import AnalysisConfig, OverlapGroup, SetDef


def _four_set_config():
    return AnalysisConfig(
        id_col="id", weight_col=None,
        overlap_groups=[OverlapGroup(name="Big group", sets=[
            SetDef("A", ["A"]), SetDef("B", ["B"]),
            SetDef("C", ["C"]), SetDef("D", ["D"]),
        ])],
        heavy_selectors=[],
    )


def _four_set_frame():
    return pd.DataFrame({
        "id": ["R1", "R2", "R3", "R4"],
        "A": [1, 1, 0, 1], "B": [1, 0, 1, 1],
        "C": [0, 0, 1, 1], "D": [0, 1, 1, 0],
    })


def test_report_has_pairwise_section():
    cfg = _four_set_config()
    groups = compute_all_groups(_four_set_frame(), cfg.overlap_groups, None)
    html = render_html(cfg, groups, [])
    assert "Pairwise overlap" in html
    assert "Jaccard" in html


def test_report_still_self_contained_with_pairwise():
    cfg = _four_set_config()
    groups = compute_all_groups(_four_set_frame(), cfg.overlap_groups, None)
    html = render_html(cfg, groups, []).lower()
    for needle in ["http://", "https://", "src=", "<script", "cdn", "@import"]:
        assert needle not in html, f"pairwise section leaked external ref: {needle}"


def test_four_sets_no_venn_but_has_matrix():
    cfg = _four_set_config()
    groups = compute_all_groups(_four_set_frame(), cfg.overlap_groups, None)
    # 4 sets -> not Venn-drawable, but pairwise matrix must still be present.
    assert not groups[0].can_draw_venn
    html = render_html(cfg, groups, [])
    assert "Pairwise overlap" in html

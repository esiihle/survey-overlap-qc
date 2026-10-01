"""Tests for the pairwise overlap engine (v0.2.0)."""

from __future__ import annotations

import pandas as pd
import pytest

from overlap_qc.config import OverlapGroup, SetDef
from overlap_qc.overlap import compute_group
from overlap_qc.pairwise import compute_pairwise, pairwise_from_group


def _membership():
    # A: R1,R2,R5 ; B: R1,R3,R5 ; C: R3,R5
    return {
        "A": pd.Series([True, True, False, False, True]),
        "B": pd.Series([True, False, True, False, True]),
        "C": pd.Series([False, False, True, False, True]),
    }


def test_intersection_and_diagonal():
    pr = compute_pairwise(_membership())
    # Diagonal is the set size.
    assert pr.n_both.loc["A", "A"] == 3
    assert pr.n_both.loc["B", "B"] == 3
    # A & B = R1, R5 -> 2
    assert pr.n_both.loc["A", "B"] == 2
    # symmetry of the count matrix
    assert pr.n_both.loc["A", "B"] == pr.n_both.loc["B", "A"]


def test_jaccard_values():
    pr = compute_pairwise(_membership())
    # A={R1,R2,R5}, B={R1,R3,R5}: intersection 2, union 4 -> 0.5
    assert pr.jaccard.loc["A", "B"] == pytest.approx(0.5)
    assert pr.jaccard.loc["A", "A"] == pytest.approx(1.0)


def test_conditional_is_asymmetric():
    pr = compute_pairwise(_membership())
    # C={R3,R5} (size 2); A&C = {R5} -> P(A|C)=1/2, P(C|A)=1/3
    assert pr.conditional.loc["A", "C"] == pytest.approx(0.5)
    assert pr.conditional.loc["C", "A"] == pytest.approx(1 / 3)


def test_weighted_intersection():
    m = _membership()
    weights = pd.Series([1.0, 1.0, 2.0, 1.0, 3.0])  # R5 heavy
    pr = compute_pairwise(m, weights)
    # A & B = R1 (1.0) + R5 (3.0) = 4.0
    assert pr.weighted_both.loc["A", "B"] == pytest.approx(4.0)


def test_from_group_matches_direct():
    df = pd.DataFrame({
        "respondent_id": ["R1", "R2", "R3", "R4", "R5"],
        "weight": ["1", "1", "2", "1", "3"],
        "A": [1, 1, 0, 0, 1], "B": [1, 0, 1, 0, 1], "C": [0, 0, 1, 0, 1],
    })
    group = OverlapGroup(name="g", sets=[SetDef("A", ["A"]), SetDef("B", ["B"]),
                                         SetDef("C", ["C"])])
    gr = compute_group(df, group, weight_col="weight")
    pr = pairwise_from_group(gr)
    assert pr.n_both.loc["A", "B"] == 2
    assert pr.weighted_both.loc["A", "B"] == pytest.approx(4.0)


def test_to_long_shape():
    pr = compute_pairwise(_membership())
    long = pr.to_long(group_name="g")
    # 3 sets -> 3 unordered pairs
    assert len(long) == 3
    assert set(["group", "set_a", "set_b", "jaccard", "p_a_given_b"]).issubset(long.columns)

"""Pairwise overlap statistics.

Full Venn regions are the right view for 2-3 sets, but they become unwieldy
fast: k sets have 2^k regions, and a diagram past three circles is unreadable.
For any number of sets, the practical summary is *pairwise*: for every pair of
sets, how much do they overlap?

This module computes, for a group's sets:

* ``n_both``       - intersection counts |i & j| (the diagonal is the set size |i|)
* ``weighted_both``- the same, summing survey weights
* ``jaccard``      - |i & j| / |i | j|, a symmetric 0-1 similarity
* ``conditional``  - P(row | col) = |i & j| / |j|, an asymmetric share
                     (e.g. "of Value-tier buyers, what share are also Premium?")

Everything is derived from set membership (a boolean Series per set), so it
works the same whether a set is one column or several OR-ed columns.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .overlap import GroupResult


@dataclass
class PairwiseResult:
    """Pairwise overlap matrices for one overlap group."""

    labels: list[str]
    n_both: pd.DataFrame          # k x k intersection counts (diagonal = set size)
    weighted_both: pd.DataFrame   # k x k weighted intersection
    jaccard: pd.DataFrame         # k x k Jaccard similarity (0-1)
    conditional: pd.DataFrame     # k x k P(row | col), asymmetric
    total_n: int
    total_weight: float

    def to_long(self, group_name: str | None = None) -> pd.DataFrame:
        """Flatten the off-diagonal pairs into a tidy table for export.

        One row per unordered pair {a, b}, with both conditional directions.
        """
        rows: list[dict[str, object]] = []
        labels = self.labels
        for i, a in enumerate(labels):
            for j in range(i + 1, len(labels)):
                b = labels[j]
                row: dict[str, object] = {}
                if group_name is not None:
                    row["group"] = group_name
                row.update({
                    "set_a": a,
                    "set_b": b,
                    "n_both": int(self.n_both.loc[a, b]),
                    "weighted_both": round(float(self.weighted_both.loc[a, b]), 2),
                    "jaccard": round(float(self.jaccard.loc[a, b]), 4),
                    "p_a_given_b": round(float(self.conditional.loc[a, b]), 4),
                    "p_b_given_a": round(float(self.conditional.loc[b, a]), 4),
                })
                rows.append(row)
        return pd.DataFrame(rows)


def compute_pairwise(
    membership: dict[str, "pd.Series"],
    weights: "pd.Series | None" = None,
) -> PairwiseResult:
    """Compute pairwise overlap matrices from per-set boolean membership.

    Args:
        membership: mapping of set label -> boolean Series (aligned index).
        weights: optional per-respondent weights (defaults to 1 each).
    """
    labels = list(membership)
    # Align everything on a common index and coerce to clean booleans.
    mat = pd.DataFrame({lbl: membership[lbl].astype(bool) for lbl in labels})
    if weights is None:
        weights = pd.Series(1.0, index=mat.index)
    else:
        weights = pd.to_numeric(weights, errors="coerce").fillna(0.0).reindex(mat.index)

    total_n = len(mat)
    total_weight = float(weights.sum())

    def _empty() -> pd.DataFrame:
        return pd.DataFrame(0.0, index=labels, columns=labels)

    n_both, w_both = _empty(), _empty()
    jaccard, conditional = _empty(), _empty()

    for a in labels:
        col_a = mat[a]
        size_a = int(col_a.sum())
        for b in labels:
            col_b = mat[b]
            both = col_a & col_b
            inter = int(both.sum())
            union = int((col_a | col_b).sum())

            n_both.loc[a, b] = inter
            w_both.loc[a, b] = float(weights[both].sum())
            jaccard.loc[a, b] = (inter / union) if union else 0.0
            # P(a | b): of those in b, how many are also in a.
            size_b = int(col_b.sum())
            conditional.loc[a, b] = (inter / size_b) if size_b else 0.0

    # Cast the plain count matrix to ints for clean display/export.
    n_both = n_both.astype(int)

    return PairwiseResult(
        labels=labels,
        n_both=n_both,
        weighted_both=w_both,
        jaccard=jaccard,
        conditional=conditional,
        total_n=total_n,
        total_weight=total_weight,
    )


def pairwise_from_group(result: GroupResult) -> PairwiseResult:
    """Convenience wrapper: compute pairwise overlap for a computed group."""
    return compute_pairwise(result.set_membership, result.weights)

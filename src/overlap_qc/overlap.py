"""Overlap / Venn region computation.

For an overlap group of *k* sets, every respondent falls into exactly one of
the 2^k mutually exclusive regions, identified by which sets they belong to
(the empty region = "in none of the sets"). This module:

* computes each set's membership (OR across its columns),
* assigns every respondent to their region,
* produces a region summary (counts, weighted counts, percentages), and
* emits derived binary variables — one per region, plus one per set — so the
  overlaps can be used directly in downstream tabulation.

A partition invariant is asserted: region counts must sum back to the total
number of respondents. If they don't, something is wrong and we want to know.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from .config import OverlapGroup


def slugify(text: str) -> str:
    """Lower-case ASCII slug safe for use in a column name."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", text.strip().lower())
    return s.strip("_") or "x"


@dataclass
class Region:
    """One mutually exclusive Venn region."""

    members: frozenset[str]      # set labels the region belongs to
    n: int                       # unweighted respondent count
    weighted_n: float            # sum of weights (== n if unweighted)
    pct: float                   # % of total (weighted if weights present)

    @property
    def label(self) -> str:
        if not self.members:
            return "None (in no set)"
        # Preserve a stable, readable ordering of member labels.
        ordered = sorted(self.members)
        joined = " & ".join(ordered)
        return joined if len(self.members) >= 2 else f"{ordered[0]} only"

    def var_suffix(self) -> str:
        if not self.members:
            return "none"
        return "_".join(slugify(m) for m in sorted(self.members))


@dataclass
class GroupResult:
    group: OverlapGroup
    regions: list[Region]
    derived: pd.DataFrame              # respondent-level derived indicators
    total_n: int
    total_weight: float
    set_membership: dict[str, "pd.Series"] = field(default_factory=dict)
    weights: "pd.Series | None" = None

    @property
    def can_draw_venn(self) -> bool:
        return 2 <= len(self.group.sets) <= 3


def _membership(df: pd.DataFrame, columns: list[str]) -> "pd.Series":
    """Boolean membership: True where any of the given indicators is 1."""
    block = df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    return (block > 0).any(axis=1)


def compute_group(
    df: pd.DataFrame,
    group: OverlapGroup,
    weight_col: str | None,
    output_prefix: str = "ovl",
) -> GroupResult:
    """Compute Venn regions and derived variables for one overlap group."""
    labels = [s.label for s in group.sets]
    membership = {s.label: _membership(df, s.columns) for s in group.sets}

    if weight_col and weight_col in df.columns:
        weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0)
    else:
        weights = pd.Series(1.0, index=df.index)

    total_n = len(df)
    total_weight = float(weights.sum())

    # Assign each respondent to their region (frozenset of member labels).
    member_lists: list[frozenset[str]] = []
    for idx in df.index:
        present = frozenset(lbl for lbl in labels if bool(membership[lbl].loc[idx]))
        member_lists.append(present)
    region_series = pd.Series(member_lists, index=df.index)

    # Build the region summary over every region that actually occurs, plus the
    # empty region so "None" is always represented.
    occurring = set(region_series)
    occurring.add(frozenset())

    group_slug = slugify(group.name)
    regions: list[Region] = []
    derived = pd.DataFrame(index=df.index)

    # Emit per-set membership indicators too (handy downstream).
    for lbl in labels:
        col = f"set__{group_slug}__{slugify(lbl)}"
        derived[col] = membership[lbl].astype("Int8")

    # Sort regions: by number of members, then alphabetically, empty last.
    def sort_key(members: frozenset[str]) -> tuple[int, str]:
        return (len(members) if members else 99, " ".join(sorted(members)))

    for members in sorted(occurring, key=sort_key):
        mask = region_series == members
        n = int(mask.sum())
        w = float(weights[mask].sum())
        pct = (w / total_weight * 100.0) if total_weight else 0.0
        region = Region(members=members, n=n, weighted_n=w, pct=pct)
        regions.append(region)
        col = f"{output_prefix}__{group_slug}__{region.var_suffix()}"
        derived[col] = mask.astype("Int8")

    # Partition invariant: exclusive regions must sum back to the total.
    summed = sum(r.n for r in regions)
    if summed != total_n:
        raise AssertionError(
            f"overlap group '{group.name}': regions sum to {summed}, "
            f"expected {total_n} (regions are not a clean partition)"
        )

    return GroupResult(
        group=group,
        regions=regions,
        derived=derived,
        total_n=total_n,
        total_weight=total_weight,
        set_membership=membership,
        weights=weights,
    )


def compute_all_groups(
    df: pd.DataFrame,
    groups: list[OverlapGroup],
    weight_col: str | None,
) -> list[GroupResult]:
    return [compute_group(df, g, weight_col) for g in groups]

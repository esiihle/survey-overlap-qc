"""Heavy-selector QC.

"Heavy selectors" are respondents who tick an implausibly large number of
options in a select-all-that-apply block. They're a classic data-quality
signal: sometimes genuine, often a satisficing respondent clicking everything.
This module counts selections per respondent for a configured column block and
flags those meeting any enabled rule, returning a structured result for both
reporting and export.

Nothing is deleted here — heavy selectors are *flagged for review*. Whether to
exclude them is an analyst decision, not the tool's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .config import HeavySelector


@dataclass
class HeavyResult:
    check: HeavySelector
    counts: "pd.Series"                 # selection count per respondent (indexed by id)
    flagged_ids: list                   # ids meeting any rule
    threshold_absolute: int | None      # effective absolute threshold applied
    mean: float
    sd: float
    n_respondents: int
    distribution: dict[int, int] = field(default_factory=dict)  # count -> n respondents

    @property
    def n_flagged(self) -> int:
        return len(self.flagged_ids)

    @property
    def pct_flagged(self) -> float:
        return (self.n_flagged / self.n_respondents * 100.0) if self.n_respondents else 0.0


def compute_heavy(
    df: pd.DataFrame,
    check: HeavySelector,
    id_col: str,
) -> HeavyResult:
    """Run one heavy-selector check over its column block."""
    block = df[check.columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    counts = (block > 0).sum(axis=1).astype(int)
    counts.index = df[id_col].values

    n = len(counts)
    mean = float(counts.mean()) if n else 0.0
    sd = float(counts.std(ddof=0)) if n else 0.0
    n_cols = len(check.columns)

    # Build the set of flagged ids as the union across enabled rules.
    flagged = pd.Series(False, index=counts.index)
    effective_abs: int | None = None

    if check.max_absolute is not None:
        flagged |= counts >= check.max_absolute
        effective_abs = check.max_absolute

    if check.fraction is not None:
        thr = check.fraction * n_cols
        flagged |= counts >= thr
        # Track the tightest absolute-equivalent threshold for reporting.
        frac_abs = int(-(-thr // 1))  # ceil
        effective_abs = frac_abs if effective_abs is None else min(effective_abs, frac_abs)

    if check.sd_above_mean is not None:
        thr = mean + check.sd_above_mean * sd
        flagged |= counts > thr

    if check.iqr is not None:
        q1 = float(counts.quantile(0.25)) if n else 0.0
        q3 = float(counts.quantile(0.75)) if n else 0.0
        thr = q3 + check.iqr * (q3 - q1)
        flagged |= counts > thr

    distribution = {int(k): int(v) for k, v in counts.value_counts().sort_index().items()}

    return HeavyResult(
        check=check,
        counts=counts,
        flagged_ids=list(counts.index[flagged]),
        threshold_absolute=effective_abs,
        mean=mean,
        sd=sd,
        n_respondents=n,
        distribution=distribution,
    )


def compute_all_heavy(
    df: pd.DataFrame,
    checks: list[HeavySelector],
    id_col: str,
) -> list[HeavyResult]:
    return [compute_heavy(df, c, id_col) for c in checks]


def flags_frame(results: list[HeavyResult], id_col: str) -> pd.DataFrame:
    """Combine all heavy-selector results into one respondent-level flag table."""
    if not results:
        return pd.DataFrame()
    ids = results[0].counts.index
    out = pd.DataFrame({id_col: ids})
    for r in results:
        slug = r.check.name.strip().lower().replace(" ", "_")
        out[f"count__{slug}"] = r.counts.values
        flagged_set = set(r.flagged_ids)
        out[f"flag__{slug}"] = [1 if i in flagged_set else 0 for i in ids]
    flag_cols = [c for c in out.columns if c.startswith("flag__")]
    out["flag__any"] = out[flag_cols].max(axis=1)
    return out

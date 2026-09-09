"""Analysis configuration: overlap groups and heavy-selector rules.

Like the codeframe in the compact2binary tool, this is the single place where
survey specifics live. The analysis code reads only this config; nothing about
a particular study is hard-coded.

An analysis config has three parts:

* ``id`` / ``weight`` - which column identifies a respondent, and (optionally)
  which column holds the survey weight. Weighting is applied throughout when a
  weight column is given.
* ``overlap_groups`` - named groups of *sets*, where each set is one or more
  binary indicator columns OR-ed together. The tool computes the mutually
  exclusive Venn regions for each group.
* ``heavy_selectors`` - named checks that flag respondents selecting an
  implausibly high number of options across a block of columns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when an analysis config file is structurally invalid."""


@dataclass
class SetDef:
    """One set within an overlap group.

    Membership is the logical OR across ``columns``: a respondent is "in" the
    set if any listed indicator is 1. A single-column set is the common case;
    multi-column sets let you collapse several codes into one concept
    (e.g. "Premium" = any premium brand).
    """

    label: str
    columns: list[str]


@dataclass
class OverlapGroup:
    name: str
    sets: list[SetDef]

    @property
    def all_columns(self) -> list[str]:
        cols: list[str] = []
        for s in self.sets:
            cols.extend(s.columns)
        return cols


@dataclass
class HeavySelector:
    """A heavy-selector QC check over a block of binary columns.

    A respondent is flagged if they satisfy ANY of the enabled rules:

    * ``max_absolute``  - selection count >= this integer.
    * ``fraction``      - selection count / len(columns) >= this fraction.
    * ``sd_above_mean`` - selection count > mean + k * standard deviation,
                          with the mean/sd computed across all respondents.
    """

    name: str
    columns: list[str]
    max_absolute: int | None = None
    fraction: float | None = None
    sd_above_mean: float | None = None

    def describe(self) -> str:
        parts = []
        if self.max_absolute is not None:
            parts.append(f"count >= {self.max_absolute}")
        if self.fraction is not None:
            parts.append(f"count/{len(self.columns)} >= {self.fraction:g}")
        if self.sd_above_mean is not None:
            parts.append(f"count > mean + {self.sd_above_mean:g}*sd")
        return " OR ".join(parts) if parts else "(no rule)"


@dataclass
class AnalysisConfig:
    id_col: str
    weight_col: str | None
    overlap_groups: list[OverlapGroup] = field(default_factory=list)
    heavy_selectors: list[HeavySelector] = field(default_factory=list)

    @property
    def referenced_columns(self) -> set[str]:
        cols: set[str] = {self.id_col}
        if self.weight_col:
            cols.add(self.weight_col)
        for g in self.overlap_groups:
            cols.update(g.all_columns)
        for h in self.heavy_selectors:
            cols.update(h.columns)
        return cols


def _require(mapping: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"{ctx}: missing required key '{key}'")
    return mapping[key]


def _parse_set(raw: dict[str, Any], ctx: str) -> SetDef:
    label = str(_require(raw, "label", ctx))
    cols = _require(raw, "columns", ctx)
    if not isinstance(cols, list) or not cols:
        raise ConfigError(f"{ctx} '{label}': 'columns' must be a non-empty list")
    return SetDef(label=label, columns=[str(c) for c in cols])


def _parse_overlap_group(raw: dict[str, Any], index: int) -> OverlapGroup:
    ctx = f"overlap_groups[{index}]"
    name = str(_require(raw, "name", ctx))
    ctx = f"overlap group '{name}'"
    raw_sets = _require(raw, "sets", ctx)
    if not isinstance(raw_sets, list) or len(raw_sets) < 2:
        raise ConfigError(f"{ctx}: needs at least 2 sets")
    sets = [_parse_set(s, ctx) for s in raw_sets]
    labels = [s.label for s in sets]
    if len(set(labels)) != len(labels):
        raise ConfigError(f"{ctx}: duplicate set labels {labels}")
    return OverlapGroup(name=name, sets=sets)


def _parse_heavy(raw: dict[str, Any], index: int) -> HeavySelector:
    ctx = f"heavy_selectors[{index}]"
    name = str(_require(raw, "name", ctx))
    ctx = f"heavy selector '{name}'"
    cols = _require(raw, "columns", ctx)
    if not isinstance(cols, list) or not cols:
        raise ConfigError(f"{ctx}: 'columns' must be a non-empty list")

    max_absolute = raw.get("max_absolute")
    fraction = raw.get("fraction")
    sd_above_mean = raw.get("sd_above_mean")
    if max_absolute is None and fraction is None and sd_above_mean is None:
        raise ConfigError(
            f"{ctx}: at least one rule "
            "(max_absolute / fraction / sd_above_mean) is required"
        )
    if fraction is not None and not (0 < float(fraction) <= 1):
        raise ConfigError(f"{ctx}: 'fraction' must be in (0, 1]")

    return HeavySelector(
        name=name,
        columns=[str(c) for c in cols],
        max_absolute=int(max_absolute) if max_absolute is not None else None,
        fraction=float(fraction) if fraction is not None else None,
        sd_above_mean=float(sd_above_mean) if sd_above_mean is not None else None,
    )


def load_config(path: str | Path) -> AnalysisConfig:
    """Load and validate an analysis config from YAML."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ConfigError("top level of config must be a mapping")

    id_col = str(_require(raw, "id", "config"))
    weight_col = raw.get("weight")
    weight_col = str(weight_col) if weight_col else None

    raw_groups = raw.get("overlap_groups", []) or []
    raw_heavy = raw.get("heavy_selectors", []) or []
    if not raw_groups and not raw_heavy:
        raise ConfigError("config must define overlap_groups and/or heavy_selectors")

    groups = [_parse_overlap_group(g, i) for i, g in enumerate(raw_groups)]
    heavy = [_parse_heavy(h, i) for i, h in enumerate(raw_heavy)]

    return AnalysisConfig(
        id_col=id_col, weight_col=weight_col,
        overlap_groups=groups, heavy_selectors=heavy,
    )

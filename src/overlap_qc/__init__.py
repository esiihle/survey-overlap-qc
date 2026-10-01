"""overlap_qc — overlap/Venn variable generation and heavy-selector QC.

Consumes a binary survey indicator matrix (e.g. the output of the
compact2binary tool) and:

* generates mutually exclusive Venn-region variables for configured sets, and
* flags heavy selectors (respondents ticking implausibly many options).

Public API::

    from overlap_qc import load_config, compute_all_groups, compute_all_heavy, render_html
"""

from __future__ import annotations

from .config import (
    AnalysisConfig,
    ConfigError,
    HeavySelector,
    OverlapGroup,
    SetDef,
    load_config,
)
from .heavy_selector import (
    HeavyResult,
    compute_all_heavy,
    compute_heavy,
    flags_frame,
)
from .overlap import (
    GroupResult,
    Region,
    compute_all_groups,
    compute_group,
    slugify,
)
from .pairwise import PairwiseResult, compute_pairwise, pairwise_from_group
from .report import render_html
from .tables import read_table, write_table

__version__ = "0.2.0"

__all__ = [
    "AnalysisConfig",
    "ConfigError",
    "HeavySelector",
    "OverlapGroup",
    "SetDef",
    "load_config",
    "GroupResult",
    "Region",
    "compute_group",
    "compute_all_groups",
    "slugify",
    "HeavyResult",
    "compute_heavy",
    "compute_all_heavy",
    "flags_frame",
    "PairwiseResult",
    "compute_pairwise",
    "pairwise_from_group",
    "read_table",
    "write_table",
    "render_html",
    "__version__",
]

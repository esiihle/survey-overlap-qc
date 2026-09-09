"""Command-line interface.

Example::

    overlap-qc run \
        --input data/synthetic_binary.csv \
        --config config/analysis.example.yaml \
        --out-html data/report.html \
        --out-vars data/derived_variables.csv \
        --out-flags data/heavy_flags.csv
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .config import load_config
from .heavy_selector import compute_all_heavy, flags_frame
from .overlap import compute_all_groups
from .report import render_html


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    df = pd.read_csv(args.input, dtype=str)

    # Confirm every referenced column exists before doing work.
    missing = sorted(config.referenced_columns - set(df.columns))
    if missing:
        print(f"error: input is missing columns referenced by config: {missing}",
              file=sys.stderr)
        return 2

    group_results = compute_all_groups(df, config.overlap_groups, config.weight_col)
    heavy_results = compute_all_heavy(df, config.heavy_selectors, config.id_col)

    # Console summary.
    for gr in group_results:
        print(f"[overlap] {gr.group.name}: {len(gr.regions)} regions "
              f"over {len(gr.group.sets)} sets")
    for hr in heavy_results:
        print(f"[heavy]   {hr.check.name}: {hr.n_flagged} flagged "
              f"({hr.pct_flagged:.1f}%)")

    if args.out_html:
        html = render_html(config, group_results, heavy_results)
        with open(args.out_html, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"Wrote HTML report -> {args.out_html}")

    if args.out_vars and group_results:
        derived = pd.concat(
            [df[[config.id_col]]] + [gr.derived for gr in group_results], axis=1
        )
        derived.to_csv(args.out_vars, index=False)
        print(f"Wrote {derived.shape[1] - 1} derived variables -> {args.out_vars}")

    if args.out_flags and heavy_results:
        flags = flags_frame(heavy_results, config.id_col)
        flags.to_csv(args.out_flags, index=False)
        print(f"Wrote heavy-selector flags -> {args.out_flags}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="overlap-qc",
        description="Overlap/Venn variable generation and heavy-selector QC.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="run overlap + heavy-selector analysis")
    p.add_argument("-i", "--input", required=True, help="binary matrix CSV")
    p.add_argument("-c", "--config", required=True, help="analysis config YAML")
    p.add_argument("--out-html", help="path for the self-contained HTML report")
    p.add_argument("--out-vars", help="path for derived overlap-variable CSV")
    p.add_argument("--out-flags", help="path for heavy-selector flag CSV")
    p.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

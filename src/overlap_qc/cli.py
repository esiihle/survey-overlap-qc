"""Command-line interface.

Input and output may be CSV, TSV, or Parquet; the format is chosen from the
file extension, so this chains directly with compact2binary's Parquet output.

Example::

    overlap-qc run \
        --input data/synthetic_binary.parquet \
        --config config/analysis.example.yaml \
        --out-html data/report.html \
        --out-vars data/derived_variables.csv \
        --out-flags data/heavy_flags.csv \
        --out-pairwise data/pairwise_overlap.csv
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .config import load_config
from .heavy_selector import compute_all_heavy, flags_frame
from .logging_setup import configure_logging
from .overlap import compute_all_groups
from .pairwise import pairwise_from_group
from .report import render_html
from .tables import read_table, write_table


def _cmd_run(args: argparse.Namespace, log) -> int:
    config = load_config(args.config)
    df = read_table(args.input, as_str=True)

    # Confirm every referenced column exists before doing work.
    missing = sorted(config.referenced_columns - set(df.columns))
    if missing:
        log.error(f"error: input is missing columns referenced by config: {missing}")
        return 2

    group_results = compute_all_groups(df, config.overlap_groups, config.weight_col)
    heavy_results = compute_all_heavy(df, config.heavy_selectors, config.id_col)

    # Console summary (stderr via logging).
    for gr in group_results:
        log.info(f"[overlap] {gr.group.name}: {len(gr.regions)} regions "
                 f"over {len(gr.group.sets)} sets")
    for hr in heavy_results:
        log.info(f"[heavy]   {hr.check.name}: {hr.n_flagged} flagged "
                 f"({hr.pct_flagged:.1f}%)")

    if args.out_html:
        html = render_html(config, group_results, heavy_results)
        with open(args.out_html, "w", encoding="utf-8") as fh:
            fh.write(html)
        log.info(f"Wrote HTML report -> {args.out_html}")

    if args.out_vars and group_results:
        derived = pd.concat(
            [df[[config.id_col]]] + [gr.derived for gr in group_results], axis=1
        )
        write_table(derived, args.out_vars)
        log.info(f"Wrote {derived.shape[1] - 1} derived variables -> {args.out_vars}")

    if args.out_flags and heavy_results:
        flags = flags_frame(heavy_results, config.id_col)
        write_table(flags, args.out_flags)
        log.info(f"Wrote heavy-selector flags -> {args.out_flags}")

    if args.out_pairwise and group_results:
        long = pd.concat(
            [pairwise_from_group(gr).to_long(gr.group.name) for gr in group_results],
            ignore_index=True,
        )
        write_table(long, args.out_pairwise)
        log.info(f"Wrote pairwise overlap ({len(long)} pairs) -> {args.out_pairwise}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="overlap-qc",
        description="Overlap/Venn variable generation and heavy-selector QC.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="run overlap + heavy-selector analysis")
    p.add_argument("-i", "--input", required=True,
                   help="binary matrix (.csv/.tsv/.parquet)")
    p.add_argument("-c", "--config", required=True, help="analysis config YAML")
    p.add_argument("--out-html", help="path for the self-contained HTML report")
    p.add_argument("--out-vars", help="path for derived overlap-variable table")
    p.add_argument("--out-flags", help="path for heavy-selector flag table")
    p.add_argument("--out-pairwise", help="path for the pairwise-overlap table")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="verbose (debug-level) logging")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="quiet: warnings and errors only")
    p.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log = configure_logging(verbose=getattr(args, "verbose", False),
                            quiet=getattr(args, "quiet", False))
    return args.func(args, log)


if __name__ == "__main__":
    sys.exit(main())

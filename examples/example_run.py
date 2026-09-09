"""End-to-end example using the Python API (no CLI).

Run from the repo root:

    python examples/example_run.py

Generates (if needed) a small synthetic binary matrix, computes overlap regions
and heavy-selector flags, writes a self-contained HTML report next to this
script, and prints a short summary.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from overlap_qc import (
    compute_all_groups,
    compute_all_heavy,
    flags_frame,
    load_config,
    render_html,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    data_path = ROOT / "examples" / "sample_data" / "sample_binary.csv"
    config_path = ROOT / "config" / "analysis.example.yaml"

    if not data_path.exists():
        data_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py"),
             "--rows", "120", "--seed", "5", "--out", str(data_path)],
            check=True,
        )

    config = load_config(config_path)
    df = pd.read_csv(data_path, dtype=str)

    groups = compute_all_groups(df, config.overlap_groups, config.weight_col)
    heavy = compute_all_heavy(df, config.heavy_selectors, config.id_col)

    print("=== OVERLAP REGIONS ===")
    for gr in groups:
        print(f"\n{gr.group.name}")
        for region in gr.regions:
            print(f"  {region.label:<28} n={region.n:<4} {region.pct:5.1f}%")

    print("\n=== HEAVY SELECTORS ===")
    for hr in heavy:
        print(f"  {hr.check.name}: {hr.n_flagged} flagged "
              f"({hr.pct_flagged:.1f}%), rule = {hr.check.describe()}")

    out_html = ROOT / "examples" / "sample_data" / "sample_report.html"
    out_html.write_text(render_html(config, groups, heavy), encoding="utf-8")
    print(f"\nWrote HTML report -> {out_html.relative_to(ROOT)}")

    flags = flags_frame(heavy, config.id_col)
    print(f"Combined flag table: {flags.shape[0]} rows x {flags.shape[1]} cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

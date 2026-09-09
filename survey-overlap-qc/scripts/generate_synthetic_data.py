"""Generate a synthetic binary survey matrix.

Everything emitted here is fake. The output matches config/analysis.example.yaml:

    respondent_id, weight, Q3_1..Q3_8, Q4_1..Q4_8

* Q3_* are purchase indicators, Q4_* are awareness indicators (0/1).
* Brand preferences are correlated so overlap regions are non-trivial, and
  awareness is a superset of purchase (as in real trackers).
* A configurable share of respondents are injected "heavy selectors" who tick
  most options, so the QC has something to flag.
* weight is a passthrough survey weight.

This is the same shape the compact2binary tool produces, so the two tools chain.

Usage::

    python scripts/generate_synthetic_data.py --rows 600 --seed 42 \
        --out data/synthetic_binary.csv
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

try:
    from faker import Faker
except ImportError:  # pragma: no cover
    raise SystemExit("faker is required: pip install -r requirements.txt")

N_BRANDS = 8
PURCHASE_COLS = [f"Q3_{i}" for i in range(1, N_BRANDS + 1)]
AWARE_COLS = [f"Q4_{i}" for i in range(1, N_BRANDS + 1)]

# Baseline purchase propensity per brand (index 0 == brand code 1).
BASE_PURCHASE = [0.42, 0.36, 0.30, 0.24, 0.20, 0.16, 0.12, 0.09]
# Two loose "affinity clusters" so overlaps aren't just independent noise.
CLUSTERS = [[0, 2, 4], [1, 3, 5]]


def _draw_purchase(rng: random.Random) -> list[int]:
    # Give each respondent a slight lean toward one affinity cluster.
    lean = rng.choice(CLUSTERS)
    flags = [0] * N_BRANDS
    for i in range(N_BRANDS):
        p = BASE_PURCHASE[i] + (0.18 if i in lean else 0.0)
        flags[i] = 1 if rng.random() < p else 0
    if not any(flags):  # everyone bought at least one
        flags[rng.randrange(N_BRANDS)] = 1
    return flags


def _draw_awareness(purchase: list[int], rng: random.Random) -> list[int]:
    aware = list(purchase)  # aware of everything you bought
    for i in range(N_BRANDS):
        if not aware[i] and rng.random() < 0.4:
            aware[i] = 1
    return aware


def build_rows(n: int, seed: int, heavy_rate: float) -> list[dict[str, str]]:
    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)

    rows: list[dict[str, str]] = []
    for i in range(1, n + 1):
        is_heavy = rng.random() < heavy_rate
        if is_heavy:
            # Heavy selector: ticks most options in both blocks.
            purchase = [1 if rng.random() < 0.85 else 0 for _ in range(N_BRANDS)]
            aware = [1 if rng.random() < 0.92 else 0 for _ in range(N_BRANDS)]
        else:
            purchase = _draw_purchase(rng)
            aware = _draw_awareness(purchase, rng)

        row: dict[str, str] = {
            "respondent_id": f"R{i:05d}",
            "weight": f"{rng.uniform(0.5, 1.8):.4f}",
        }
        for col, v in zip(PURCHASE_COLS, purchase):
            row[col] = str(v)
        for col, v in zip(AWARE_COLS, aware):
            row[col] = str(v)
        row["_note"] = fake.word()  # generator-only; never written out
        rows.append(row)
    return rows


def write_csv(rows: list[dict[str, str]], out: Path) -> None:
    if not rows:
        raise SystemExit("no rows generated")
    fieldnames = [k for k in rows[0].keys() if k != "_note"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=600, help="number of respondents")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible)")
    parser.add_argument("--heavy-rate", type=float, default=0.06,
                        help="share of injected heavy selectors (0-1)")
    parser.add_argument("--out", type=Path, default=Path("data/synthetic_binary.csv"))
    args = parser.parse_args(argv)

    rows = build_rows(args.rows, args.seed, args.heavy_rate)
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} synthetic respondents "
          f"(~{args.heavy_rate:.0%} heavy selectors) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

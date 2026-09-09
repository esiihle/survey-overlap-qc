# overlap-qc

**Generate overlap/Venn variables and flag heavy selectors from a binary survey matrix — with a self-contained HTML report.**

![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![tests](https://img.shields.io/badge/tests-pytest-brightgreen)

Two everyday survey-processing jobs, automated and QC'd:

1. **Overlap / Venn variables.** For any group of answer *sets* (e.g. which brands a respondent bought), compute the mutually exclusive Venn regions — "A only", "A & B", "A & B & C", "None" — as counts, weighted counts, and percentages, and emit them as derived 0/1 variables ready for tabulation.
2. **Heavy-selector QC.** Flag respondents who tick an implausibly high number of options in a select-all block — a classic satisficing/data-quality signal — using absolute, fractional, or statistical-outlier rules.

Both feed a single **self-contained HTML report** (inline SVG Venns, no external assets) you can open in any browser or hand to a colleague.

> **Note on data:** this is a clean-room implementation. Every dataset here is **synthetic** (`scripts/generate_synthetic_data.py`, built on `faker`) and the report is generated programmatically from it at run time — there is no data or branding baked into the HTML. Nothing here refers to any real survey, client, or brand.

It consumes the same binary matrix the companion [compact2binary](../survey-compact-to-binary) tool produces, so the two chain together: **compact2binary → overlap-qc**.

---

## What it produces

**Inline Venn (from the demo run — schematic, with per-region counts and %):**

```
            Crispa
         104  (16.5%)
      72          79
   (12.1%)  59  (14.1%)
           (9.0%)
   79        52        71
 Muncho   (8.4%)     Snaxi
```

**Region summary table** (per overlap group): region, n, weighted n, % of total.

**Heavy-selector summary**: rule applied, count distribution, and a table of flagged respondents — plus a combined per-respondent flag CSV (`flag__any` across all checks).

## Features

- **Config-driven.** All survey specifics live in one YAML file; the analysis code is generic.
- **Sets are OR-groups of columns.** A set can be a single indicator or several codes collapsed into one concept (e.g. "Premium tier" = any premium brand).
- **Weighting throughout.** Give a weight column and every region size and percentage is weighted; omit it for an unweighted run.
- **Three heavy-selector rules**, combined with OR: `max_absolute`, `fraction` (of options), and `sd_above_mean` (statistical outlier).
- **Partition invariant enforced.** Venn regions are asserted to sum back to the respondent total — a silent miscount fails loudly.
- **Self-contained HTML.** Inline CSS + inline SVG, every value escaped and sourced at run time. No external fonts, scripts, logos, or embedded datasets.
- **Runs out of the box** on synthetic data with injected heavy selectors so the QC has something to catch.

## Quickstart

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Generate a synthetic binary matrix (600 respondents, ~6% heavy selectors)
python scripts/generate_synthetic_data.py --rows 600 --seed 42 \
    --out data/synthetic_binary.csv

# 3. Run overlap + heavy-selector analysis, emit report + derived vars + flags
overlap-qc run \
    -i data/synthetic_binary.csv \
    -c config/analysis.example.yaml \
    --out-html data/report.html \
    --out-vars data/derived_variables.csv \
    --out-flags data/heavy_flags.csv
```

Expected console output:

```
[overlap] Purchase overlap: top 3 brands: 8 regions over 3 sets
[overlap] Awareness: premium vs value tiers: 4 regions over 2 sets
[heavy]   Brands bought (Q3): 17 flagged (2.8%)
[heavy]   Brands aware of (Q4): 17 flagged (2.8%)
```

Open `data/report.html` in any browser. Or run the illustrated demo: `python examples/example_run.py`.

Python API:

```python
from overlap_qc import (load_config, compute_all_groups,
                        compute_all_heavy, render_html)
import pandas as pd

config = load_config("config/analysis.example.yaml")
df     = pd.read_csv("data/synthetic_binary.csv", dtype=str)

groups = compute_all_groups(df, config.overlap_groups, config.weight_col)
heavy  = compute_all_heavy(df, config.heavy_selectors, config.id_col)
html   = render_html(config, groups, heavy)
```

## Configuration

```yaml
id: respondent_id
weight: weight            # optional; omit for an unweighted analysis

overlap_groups:
  - name: "Purchase overlap: top 3 brands"      # 3 sets -> Venn-eligible
    sets:
      - { label: "Crispa", columns: [Q3_1] }
      - { label: "Muncho", columns: [Q3_2] }
      - { label: "Snaxi",  columns: [Q3_3] }

  - name: "Awareness: premium vs value tiers"   # sets can OR several codes
    sets:
      - { label: "Premium tier", columns: [Q4_1, Q4_3, Q4_7] }
      - { label: "Value tier",   columns: [Q4_2, Q4_4, Q4_6] }

heavy_selectors:
  - name: "Brands bought (Q3)"
    columns: [Q3_1, Q3_2, Q3_3, Q3_4, Q3_5, Q3_6, Q3_7, Q3_8]
    max_absolute: 7          # flag if >= 7 of 8 selected
    sd_above_mean: 2.5       # ...or a statistical outlier (OR of rules)
```

A Venn diagram is drawn for groups of 2–3 sets; larger groups still get a full region table.

## Outputs

| File | Contents |
|------|----------|
| `--out-html` | Self-contained report: Venn diagrams, region tables, heavy-selector summaries + flagged lists. |
| `--out-vars` | Derived variables per respondent: one 0/1 column per Venn region and per set membership. |
| `--out-flags`| Per-respondent selection counts and flags for each check, plus `flag__any`. |

## Project structure

```
survey-overlap-qc/
├── src/overlap_qc/
│   ├── config.py          # analysis config model + YAML loader
│   ├── overlap.py         # Venn region computation + derived variables
│   ├── heavy_selector.py  # selection counts + flagging rules
│   ├── report.py          # self-contained HTML (inline SVG Venns)
│   └── cli.py
├── scripts/generate_synthetic_data.py
├── config/analysis.example.yaml
├── examples/{example_run.py, sample_data/}
├── tests/test_overlap_qc.py
├── docs/OVERVIEW.md
└── .github/workflows/ci.yml
```

## Development

```bash
pip install -e ".[dev]"
pytest -q                 # test suite (overlap, heavy-selector, report, config)
pre-commit install        # gitleaks + notebook-output stripping
```

A dedicated test asserts the HTML report contains **no external references** (`http`, `src=`, `<script>`, CDNs, `@import`) — the self-containment guarantee is enforced, not just intended.

## License

MIT — see [LICENSE](LICENSE).

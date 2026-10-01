#!/usr/bin/env bash
#
# build_history_v2.sh — turn the v0.2.0 changes into a clean sequence of
# feature commits ON TOP OF your existing v0.1.0 commit.
#
# This is a local helper, NOT part of the repo. It stages specific files per
# commit (never itself), so each commit is a coherent, self-contained change
# with a real diff. Every commit is buildable and green. All commits are dated
# now — which is exactly how a portfolio project built over a weekend looks.
# Do NOT backdate commits to fake a longer timeline; that is the thing that
# reads as dishonest if anyone checks.
#
# Prerequisite: you are in the repo root, the v0.1.0 commit is already made
# (git log shows it), and these v0.2.0 files are in place (unstaged).
#
# Usage:
#   bash build_history_v2.sh
#
# Afterwards:
#   git log --oneline        # review the history
#   git push -u origin main  # publish (see COMMIT_GUIDE.md for the force case)
#   rm build_history_v2.sh COMMIT_GUIDE.md   # remove the helpers

set -euo pipefail

# --- sanity checks ---------------------------------------------------------
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not inside a git repository."
  echo "  First lay down v0.1.0 and commit it (see COMMIT_GUIDE.md), then re-run."
  exit 1
fi
if git diff --quiet && git diff --cached --quiet; then
  echo "error: no changes to commit. Are the v0.2.0 files in place?"
  exit 1
fi

commit () {
  local msg="$1"; shift
  git add -- "$@"
  git commit -m "$msg" >/dev/null
  echo "  committed: $msg"
}

echo "Building v0.2.0 commit sequence..."

commit "feat: pairwise overlap & Jaccard matrix

Add a pairwise engine computing, per overlap group, set-by-set intersection
counts, weighted overlap, Jaccard similarity and conditional shares P(a|b).
This is the readable overlap view when a group has more sets than a Venn can
show. GroupResult now carries per-respondent weights so the statistics can be
derived from a computed group." \
  src/overlap_qc/pairwise.py \
  src/overlap_qc/overlap.py \
  tests/test_pairwise.py

commit "feat: IQR heavy-selector rule

Add a robust Tukey-style outlier rule (count > Q3 + k*IQR) that, unlike
sd_above_mean, does not assume a normal count distribution. Available in the
config and demonstrated in the example analysis." \
  src/overlap_qc/config.py \
  src/overlap_qc/heavy_selector.py \
  config/analysis.example.yaml \
  tests/test_heavy_iqr.py

commit "feat: CSV, TSV and Parquet table I/O

Dispatch reads/writes on file extension so the pipeline handles .csv, .tsv and
.parquet interchangeably, keeping it in step with compact2binary's Parquet
output. Parquet is an optional extra (pyarrow)." \
  src/overlap_qc/tables.py \
  tests/test_tables.py

commit "feat: pairwise matrix and large-set handling in the HTML report

Render a pairwise overlap matrix for every group, and use it as the primary
overlap view when a group has more than three sets. The report stays fully
self-contained (no external references)." \
  src/overlap_qc/report.py \
  tests/test_report_pairwise.py

commit "feat: logging and CLI surface for the new capabilities

Route status through logging with --verbose/--quiet, wire input/output through
read_table/write_table (CSV/TSV/Parquet), and add an --out-pairwise export." \
  src/overlap_qc/logging_setup.py \
  src/overlap_qc/cli.py

commit "docs: release v0.2.0

Export the new pairwise and table-I/O API, bump the version to 0.2.0, add a
CHANGELOG, refresh the sample report, and update the README, overview and CI
smoke test for the new features." \
  src/overlap_qc/__init__.py \
  pyproject.toml \
  CHANGELOG.md \
  README.md \
  docs/OVERVIEW.md \
  .github/workflows/ci.yml \
  examples/sample_data/sample_report.html

echo ""
echo "Done. Recent history:"
git log --oneline | head -8

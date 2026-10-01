# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0]

### Added
- **Pairwise overlap matrix.** New `pairwise` engine and `compute_pairwise` /
  `pairwise_from_group` API compute, for each overlap group, set-by-set
  intersection counts, weighted overlap, Jaccard similarity, and conditional
  shares P(a|b). This is the readable overlap view when there are more sets
  than a Venn can show.
- **Pairwise section in the HTML report**, shown for every group and used as
  the primary overlap view when a group has more than three sets.
- **IQR heavy-selector rule.** A robust Tukey-style outlier rule
  (`count > Q3 + k*IQR`) that, unlike `sd_above_mean`, doesn't assume a normal
  count distribution.
- **New `--out-pairwise` export** writing a tidy pairwise-overlap table.
- **CSV, TSV & Parquet I/O.** Inputs and every output are chosen by file
  extension. Parquet needs the `parquet` extra (`pip install '.[parquet]'`),
  and this keeps the tool in step with compact2binary's Parquet output.
- **Logging with `--verbose` / `--quiet`**; status now goes to stderr so any
  data on stdout stays clean.

### Changed
- `GroupResult` now carries the per-respondent weights, so pairwise statistics
  can be derived from a computed group without re-reading the data.

## [0.1.0]

### Added
- Initial release: config-driven overlap/Venn region variables (mutually
  exclusive regions for 2^k sets, weighted, partition invariant asserted),
  heavy-selector QC (`max_absolute` / `fraction` / `sd_above_mean`), a
  self-contained HTML report with inline SVG Venn diagrams, derived-variable
  and flag exports, a synthetic data generator, tests, and CI.

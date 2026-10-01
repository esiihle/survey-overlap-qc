# Overview & design notes

This document explains *why* the tool exists, the context it came from, and the design decisions behind it. The [README](../README.md) covers *how* to use it.

## Background

Two recurring tasks in survey processing sit close together and are easy to get subtly wrong:

**Overlap / Venn analysis.** Multi-response questions invite "how many bought *both* A and B?" style questions. The answer is a set of mutually exclusive regions — A only, B only, A∩B, and so on — that must partition the respondents cleanly and, in market research, are almost always reported *weighted*. Done by hand across several brands and waves, it's fiddly and error-prone: an off-by-one in an intersection, or a percentage taken over the wrong base, quietly corrupts a chart.

**Heavy-selector QC.** In select-all-that-apply grids, a respondent who ticks nearly everything is a data-quality signal worth reviewing — often a satisficer clicking down the list. Spotting them consistently, with a defensible rule, is exactly the kind of check that should be automated rather than eyeballed.

This tool is a generalised, clean-room version of an automation originally built to do both in a production workflow and emit a shareable HTML report. The techniques are standard practice; this implementation was rebuilt from the concept against synthetic data so it could be shared publicly.

## Input contract

The tool consumes a **binary indicator matrix**: respondent rows, an id column, an optional weight column, and 0/1 indicator columns. That is precisely the shape the companion `compact2binary` tool produces, so the two chain end to end — compact survey export → `compact2binary` → binary matrix → `overlap-qc`. Keeping the two tools as separate repos with a shared, boring interface (a CSV of 0/1 columns) is deliberate: each stands alone in a portfolio, and neither has to know the other's internals.

## Design principles

**1. Config is the only place survey specifics live.** Set definitions, weighting, and QC rules all come from one YAML file. The analysis code never names a brand or a question.

**2. Sets are OR-groups, not single columns.** A "set" is one or more indicator columns combined with logical OR. This small choice covers both the simple case (one code = one set) and the useful case (collapse several codes into a concept like "Premium tier") without special-casing.

**3. Regions must partition — and that's asserted.** For *k* sets there are 2^k mutually exclusive regions; every respondent lands in exactly one. The code asserts the region counts sum back to the respondent total, so a miscount can't slip through as a plausible-looking table.

**4. Weighting is first-class.** If a weight column is supplied, every region size and percentage is weighted, because that's how these figures are actually reported. Percentages are always taken over the correct total (weighted total when weighted).

**5. QC flags, it does not delete.** Heavy selectors are surfaced for an analyst to judge. Rules combine with OR so you can layer an absolute cutoff, a fractional one, and a statistical-outlier test; the tool reports who tripped which threshold and never silently drops a respondent.

**6. The report has nowhere to hide data.** An HTML report is a classic leakage vector — a dataset or a client logo baked into the markup. This generator builds the whole file programmatically from the input at run time, inline CSS and inline SVG only, every value HTML-escaped, no external fonts/scripts/images. A test asserts the output contains no external references, so self-containment is enforced rather than hoped for.

## Key decisions and trade-offs

**Schematic, not area-proportional, Venns.** Area-proportional Venn diagrams are genuinely hard for three sets and impossible to guarantee for arbitrary data. The report draws a clean schematic Venn with the true count and percentage labelled in each region — unambiguous and honest — and says so in the legend. Region tables carry the exact figures regardless.

**Venn drawn for 2–3 sets only.** Beyond three sets a Venn becomes unreadable, so larger groups get the full region table and a note, rather than a misleading diagram.

**Derived-variable naming.** Region and set-membership variables are emitted with slugged, ASCII-safe names (`ovl__<group>__<members>`, `set__<group>__<label>`) so they drop straight into downstream tooling without quoting headaches.

**Flag table shape.** One row per respondent, a `count__*` and `flag__*` pair per check, and a roll-up `flag__any`, so the QC output joins back to the main dataset on the id column with no reshaping.

## Clean-room / confidentiality approach

This repo was produced by **reimplementing the technique against synthetic data**, not by sanitising a real working file — the same discipline used across the toolset:

- The synthetic generator injects a configurable share of heavy selectors, so the QC path is demonstrable without a single real respondent.
- The HTML report is assembled at run time from that synthetic input; there is no authored-in dataset or branding to leak.
- Pre-commit hooks (`gitleaks`, `nbstripout`) enforce the no-secrets / no-notebook-output rules on every commit.

## Shipped since 0.1.0

See [CHANGELOG.md](../CHANGELOG.md) for detail. In brief, 0.2.0 added a pairwise
overlap matrix (Jaccard + conditional shares) that scales past three sets, an
IQR heavy-selector rule, CSV/TSV/Parquet I/O, a pairwise export and report
section, and logging.

## Possible extensions

- Area-proportional 2-set Venns (exact) as an opt-in.
- Additional QC signals alongside heavy selection: straight-lining, speeding, and near-duplicate response patterns.
- Direct SPSS (`.sav`) input/output.

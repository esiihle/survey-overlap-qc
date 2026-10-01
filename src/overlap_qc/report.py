"""HTML report generation.

The report is a single self-contained ``.html`` file: inline CSS, inline SVG,
no external fonts, scripts, logos, or stylesheets. Every value shown is drawn
from the (synthetic) input at run time and HTML-escaped — nothing is baked in
at authoring time. That is deliberate: an HTML report is a classic place for a
dataset or client branding to hide, so this generator is built so there is
simply nowhere for that to happen.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from .config import AnalysisConfig
from .heavy_selector import HeavyResult
from .overlap import GroupResult, Region
from .pairwise import pairwise_from_group

_MAX_FLAGGED_ROWS = 100  # cap the flagged table so reports stay readable

_CSS = """
:root { --ink:#1a1a1a; --muted:#666; --line:#e2e2e2; --accent:#2b6cb0;
        --warn:#b7791f; --bg:#ffffff; --band:#f7f7f8; }
* { box-sizing: border-box; }
body { margin:0; padding:0; background:var(--bg); color:var(--ink);
       font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
       Helvetica, Arial, sans-serif; line-height:1.5; }
.wrap { max-width: 960px; margin: 0 auto; padding: 32px 24px 64px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.2rem; margin: 40px 0 12px; padding-top: 16px;
     border-top: 1px solid var(--line); }
h3 { font-size: 1.02rem; margin: 24px 0 8px; }
.sub { color: var(--muted); font-size: .9rem; margin: 0 0 8px; }
.banner { background: #fffbea; border: 1px solid #f6e05e; color: #744210;
          padding: 10px 14px; border-radius: 8px; font-size: .9rem; margin: 16px 0 8px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 4px; font-size: .92rem; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); }
th { background: var(--band); font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:.8rem;
        background:#eef2f7; color:var(--accent); }
.flag { color: var(--warn); font-weight: 600; }
.venn-wrap { display:flex; gap:24px; flex-wrap:wrap; align-items:flex-start; }
.venn { flex: 0 0 auto; }
.legend { font-size:.85rem; color:var(--muted); margin-top:6px; }
.foot { margin-top: 48px; color: var(--muted); font-size: .82rem;
        border-top: 1px solid var(--line); padding-top: 12px; }
"""

# Region centroid geometry for schematic (non-proportional) Venn diagrams,
# keyed by the frozenset of set indices in the region.
_VENN2 = {
    "viewBox": "0 0 460 300",
    "circles": [(185, 150, 95), (275, 150, 95)],
    "labels": [(150, 40), (310, 40)],
    "regions": {
        frozenset({0}): (130, 155),
        frozenset({1}): (330, 155),
        frozenset({0, 1}): (230, 155),
    },
}
_VENN3 = {
    "viewBox": "0 0 460 350",
    "circles": [(230, 135, 100), (180, 225, 100), (280, 225, 100)],
    "labels": [(230, 20), (70, 315), (390, 315)],
    "regions": {
        frozenset({0}): (230, 95),
        frozenset({1}): (145, 265),
        frozenset({2}): (315, 265),
        frozenset({0, 1}): (165, 180),
        frozenset({0, 2}): (295, 180),
        frozenset({1, 2}): (230, 270),
        frozenset({0, 1, 2}): (230, 195),
    },
}
_CIRCLE_FILLS = ["#2b6cb0", "#38a169", "#dd6b20"]


def _esc(value: object) -> str:
    return html.escape(str(value))


def _venn_svg(result: GroupResult) -> str:
    labels = [s.label for s in result.group.sets]
    k = len(labels)
    geom = _VENN2 if k == 2 else _VENN3
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}

    parts = [f'<svg class="venn" viewBox="{geom["viewBox"]}" width="380" '
             f'role="img" aria-label="Venn diagram">']
    for (cx, cy, r), fill in zip(geom["circles"], _CIRCLE_FILLS):
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
            f'fill-opacity="0.16" stroke="{fill}" stroke-width="2"/>'
        )
    for (lx, ly), lbl, fill in zip(geom["labels"], labels, _CIRCLE_FILLS):
        parts.append(
            f'<text x="{lx}" y="{ly}" text-anchor="middle" '
            f'font-size="14" font-weight="700" fill="{fill}">{_esc(lbl)}</text>'
        )
    # Place each region's count at its centroid.
    for region in result.regions:
        if not region.members:
            continue  # "None" shown outside the diagram
        idx_set = frozenset(label_to_idx[m] for m in region.members)
        pos = geom["regions"].get(idx_set)
        if pos is None:
            continue
        x, y = pos
        parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" font-size="15" '
            f'font-weight="700" fill="#1a1a1a">{region.n}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y + 16}" text-anchor="middle" font-size="11" '
            f'fill="#666">{region.pct:.1f}%</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _region_table(result: GroupResult, weighted: bool) -> str:
    rows = []
    for region in result.regions:
        weighted_cell = (
            f'<td class="num">{region.weighted_n:.1f}</td>' if weighted else ""
        )
        rows.append(
            f"<tr><td>{_esc(region.label)}</td>"
            f'<td class="num">{region.n}</td>'
            f"{weighted_cell}"
            f'<td class="num">{region.pct:.1f}%</td></tr>'
        )
    wt_head = '<th class="num">Weighted n</th>' if weighted else ""
    pct_head = "% (weighted)" if weighted else "%"
    return (
        "<table><thead><tr><th>Region (mutually exclusive)</th>"
        f'<th class="num">n</th>{wt_head}<th class="num">{pct_head}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _overlap_section(result: GroupResult, weighted: bool) -> str:
    parts = [f"<h2>Overlap &mdash; {_esc(result.group.name)}</h2>"]
    parts.append(
        f'<p class="sub">{len(result.group.sets)} sets &middot; '
        f"{result.total_n} respondents"
        + (f" &middot; total weight {result.total_weight:.1f}" if weighted else "")
        + "</p>"
    )
    parts.append('<div class="venn-wrap">')
    if result.can_draw_venn:
        parts.append(
            '<div><div class="venn">' + _venn_svg(result) + "</div>"
            '<div class="legend">Counts shown per region; '
            'diagram is schematic, not area-proportional.</div></div>'
        )
    else:
        parts.append(
            '<div class="legend">A Venn diagram is drawn for 2&ndash;3 sets; '
            "this group has more, so the pairwise overlap matrix below is the "
            "clearer summary.</div>"
        )
    parts.append('<div style="flex:1; min-width:280px;">'
                 + _region_table(result, weighted) + "</div>")
    parts.append("</div>")
    parts.append(_pairwise_section(result))
    return "".join(parts)


def _pairwise_matrix_table(result: GroupResult) -> str:
    """A k x k matrix: diagonal = set size, off-diagonal = intersection + Jaccard."""
    pr = pairwise_from_group(result)
    labels = pr.labels
    head = "".join(f'<th class="num">{_esc(lbl)}</th>' for lbl in labels)
    rows = []
    for a in labels:
        cells = []
        for b in labels:
            n = int(pr.n_both.loc[a, b])
            if a == b:
                cells.append(f'<td class="num"><strong>{n}</strong></td>')
            else:
                j = pr.jaccard.loc[a, b] * 100.0
                cells.append(
                    f'<td class="num">{n}<br>'
                    f'<span class="sub">J {j:.0f}%</span></td>'
                )
        rows.append(f"<tr><th>{_esc(a)}</th>{''.join(cells)}</tr>")
    return (
        f'<table><thead><tr><th></th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _pairwise_section(result: GroupResult) -> str:
    parts = ["<h3>Pairwise overlap</h3>"]
    parts.append(
        '<p class="sub">Diagonal = set size (n). Off-diagonal = respondents in '
        "both sets, with the Jaccard similarity J (shared &divide; combined). "
        "This view scales to any number of sets.</p>"
    )
    parts.append(_pairwise_matrix_table(result))
    return "".join(parts)


def _heavy_section(result: HeavyResult) -> str:
    check = result.check
    parts = [f"<h2>Heavy selectors &mdash; {_esc(check.name)}</h2>"]
    parts.append(
        f'<p class="sub">Rule: {_esc(check.describe())} '
        f"&middot; {len(check.columns)} option columns "
        f"&middot; mean {result.mean:.2f}, sd {result.sd:.2f}</p>"
    )
    parts.append(
        f'<p><span class="pill">Flagged: {result.n_flagged} '
        f"({result.pct_flagged:.1f}%)</span></p>"
    )

    # Selection-count distribution.
    dist_rows = "".join(
        f'<tr><td class="num">{count}</td><td class="num">{n}</td></tr>'
        for count, n in sorted(result.distribution.items())
    )
    parts.append("<h3>Selection-count distribution</h3>")
    parts.append(
        '<table><thead><tr><th class="num">Options selected</th>'
        '<th class="num">Respondents</th></tr></thead><tbody>'
        + dist_rows + "</tbody></table>"
    )

    # Flagged respondents (capped).
    if result.flagged_ids:
        counts = result.counts
        flagged_sorted = sorted(
            result.flagged_ids, key=lambda i: int(counts.loc[i]), reverse=True
        )
        shown = flagged_sorted[:_MAX_FLAGGED_ROWS]
        rows = "".join(
            f"<tr><td>{_esc(i)}</td>"
            f'<td class="num flag">{int(counts.loc[i])}</td></tr>'
            for i in shown
        )
        parts.append("<h3>Flagged respondents</h3>")
        parts.append(
            '<table><thead><tr><th>Respondent</th>'
            '<th class="num">Options selected</th></tr></thead><tbody>'
            + rows + "</tbody></table>"
        )
        if len(flagged_sorted) > _MAX_FLAGGED_ROWS:
            parts.append(
                f'<p class="sub">Showing top {_MAX_FLAGGED_ROWS} of '
                f"{len(flagged_sorted)} flagged; full list is in the exported CSV.</p>"
            )
    return "".join(parts)


def render_html(
    config: AnalysisConfig,
    group_results: list[GroupResult],
    heavy_results: list[HeavyResult],
    *,
    title: str = "Overlap & heavy-selector QC report",
) -> str:
    """Render the full self-contained HTML report as a string."""
    weighted = bool(config.weight_col)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = [f"<h1>{_esc(title)}</h1>"]
    body.append(f'<p class="sub">Generated {generated}'
                + (" &middot; weighted analysis" if weighted else " &middot; unweighted")
                + "</p>")
    body.append(
        '<div class="banner"><strong>Synthetic data.</strong> This report was '
        "generated from a fake dataset for demonstration. It contains no real "
        "respondents, clients, or proprietary content.</div>"
    )

    for gr in group_results:
        body.append(_overlap_section(gr, weighted))
    for hr in heavy_results:
        body.append(_heavy_section(hr))

    body.append(
        '<div class="foot">Generated by overlap-qc &middot; self-contained HTML '
        "(no external assets) &middot; all figures derived from the input at run time.</div>"
    )

    return (
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)}</title><style>{_CSS}</style></head>"
        f'<body><div class="wrap">{"".join(body)}</div></body></html>\n'
    )

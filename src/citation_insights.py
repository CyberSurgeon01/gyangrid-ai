"""
citation_insights.py

Additional citation-analysis views that build on top of the graph dict
produced by `src.citation_graph.build_citation_graph()`. Kept as a
separate module (rather than growing citation_graph.py) so the core
graph-building logic stays untouched and these can evolve independently.

Public API:
    citations_per_section(graph) -> dict[str, int]
    citation_frequency_histogram(graph) -> dict[str, int]
    citation_density_by_section(graph, section_word_counts) -> list[dict]
    self_citation_ratio(graph, paper_authors) -> dict | None

All functions take the `graph` dict returned by build_citation_graph()
(keys: "paper_title", "nodes", "edges", "warnings") and return plain
Python data structures ready to hand to Plotly — no Streamlit or Plotly
imports in this file, so it stays easy to unit-test.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional


# ── 1. Citation count per section ────────────────────────────────────────

def citations_per_section(graph: Dict[str, Any]) -> Dict[str, int]:
    """Returns {section_name: total_in_text_citation_count}, counting every
    edge weight (an edge's weight is how many times that reference was
    cited within that section). Sections are returned in descending order
    of citation count. The synthetic 'unmatched' section (used for
    references never matched to an in-text marker) is excluded here since
    it doesn't represent a real paper section.
    """
    counts: Dict[str, int] = defaultdict(int)
    for e in graph.get("edges", []):
        section = e.get("section")
        weight = e.get("weight", 0)
        if not section or section == "unmatched" or weight <= 0:
            continue
        counts[section] += weight

    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


# ── 2. In-text citation frequency histogram ──────────────────────────────

def citation_frequency_histogram(graph: Dict[str, Any]) -> Dict[str, int]:
    """Returns {"cited 1x": n, "cited 2x": n, ..., "cited 6+x": n} — how many
    references fall into each citation-count bucket. References with
    times_cited == 0 (in the reference list but never matched to an
    in-text marker) are reported separately under 'never cited' rather
    than silently folded into 'cited 1x'.
    """
    buckets: Dict[str, int] = defaultdict(int)
    for n in graph.get("nodes", []):
        if n.get("type") != "reference":
            continue
        times = n.get("times_cited") or 0
        if times <= 0:
            buckets["never cited"] += 1
        elif times >= 6:
            buckets["cited 6+x"] += 1
        else:
            buckets[f"cited {times}x"] += 1

    # Fixed, readable ordering rather than relying on dict insertion order.
    order = ["never cited", "cited 1x", "cited 2x", "cited 3x", "cited 4x", "cited 5x", "cited 6+x"]
    return {label: buckets[label] for label in order if buckets.get(label)}


# ── 3. Citation density over paper length (per section) ─────────────────

def citation_density_by_section(
    graph: Dict[str, Any],
    section_word_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Returns a list of
        {"section": str, "citations": int, "words": int, "density": float}
    sorted by density ascending, so the most under-cited sections surface
    first — useful for flagging "Discussion has almost no citations
    relative to its length."

    `section_word_counts` should be {section_name: word_count}, e.g. built
    by the caller from `parsed["sections"]` with `len(text.split())`. This
    function intentionally doesn't compute word counts itself, since
    tokenization choices belong with the parser, not with a chart helper.

    Sections with zero words are skipped (density would be undefined).
    Density is citations per 1,000 words, which reads more naturally than
    a tiny per-word fraction.
    """
    per_section_citations = citations_per_section(graph)

    rows: List[Dict[str, Any]] = []
    for section, words in section_word_counts.items():
        if not words:
            continue
        citations = per_section_citations.get(section, 0)
        density = (citations / words) * 1000
        rows.append({
            "section": section,
            "citations": citations,
            "words": words,
            "density": round(density, 2),
        })

    rows.sort(key=lambda r: r["density"])
    return rows


# ── 4. Self-citation vs external ratio ───────────────────────────────────

def _normalize_author_surname(name: str) -> str:
    return name.strip().lower()


def self_citation_ratio(
    graph: Dict[str, Any],
    paper_authors: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """Returns {"self": int, "external": int, "self_pct": float} — how many
    *citation instances* (edge weights, not distinct references) point to
    a reference whose raw text contains one of the paper's own author
    surnames, vs. references that don't.

    Returns None if `paper_authors` is falsy (empty list or None), since
    self-citation detection is only meaningful once the paper's own
    author list is available. GyanGrid's current `parsed` dict does not
    yet include an "authors" field — this function is written to activate
    automatically the moment the parser adds one, without needing any
    changes here. Until then, callers should treat None as "not available"
    and show an explanatory message rather than a fake 0/0 chart.
    """
    if not paper_authors:
        return None

    surnames = {_normalize_author_surname(a) for a in paper_authors if a and a.strip()}
    if not surnames:
        return None

    # Map ref_id -> raw_text isn't stored on the graph node today (only
    # label/year), so we match on the label text as a best-effort proxy.
    # This will under-detect self-citations where the surname isn't the
    # first author shown in the label, which is a known limitation until
    # raw_text is threaded through into the graph nodes.
    self_count = 0
    external_count = 0

    for n in graph.get("nodes", []):
        if n.get("type") != "reference":
            continue
        weight = n.get("times_cited") or 0
        if weight <= 0:
            continue
        label = (n.get("label") or "").lower()
        is_self = any(surname in label for surname in surnames)
        if is_self:
            self_count += weight
        else:
            external_count += weight

    total = self_count + external_count
    if total == 0:
        return {"self": 0, "external": 0, "self_pct": 0.0}

    return {
        "self": self_count,
        "external": external_count,
        "self_pct": round((self_count / total) * 100, 1),
    }
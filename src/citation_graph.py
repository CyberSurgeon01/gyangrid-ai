"""
citation_graph.py

Builds a citation graph from a parsed research paper: which references are
cited, how often, and in which sections. Designed to plug into GyanGrid's
existing pipeline (the `parsed` dict produced by `src.parser.parse_document`
and the `section_chunks` produced by `src.chunker.chunk_sections`).

Public API:
    build_citation_graph(parsed, section_chunks=None) -> dict
    graph_to_vis_json(graph) -> dict   # ready for a frontend force-graph lib

No external dependencies beyond the standard library, so this file is safe
to drop into src/ without touching requirements.txt.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ── Citation marker patterns ─────────────────────────────────────────────
# Covers the common in-text citation styles seen in CS/ML papers:
#   [3]        [3, 7]        [3-5]        [3,7,9]
#   (Smith et al., 2020)     (Smith, 2020; Jones, 2019)
_NUMERIC_CITATION_RE = re.compile(r"\[([0-9]+(?:\s*[-,]\s*[0-9]+)*)\]")
_AUTHOR_YEAR_RE = re.compile(
    r"\(([A-Z][A-Za-z\-']+(?:\s+et al\.)?,?\s*\d{4}[a-z]?(?:\s*;\s*[A-Z][A-Za-z\-']+(?:\s+et al\.)?,?\s*\d{4}[a-z]?)*)\)"
)


def _expand_numeric_group(group: str) -> List[int]:
    """Turns '3, 7-9' into [3, 7, 8, 9]. Silently skips anything malformed
    rather than raising, since citation text in the wild is messy."""
    ids: List[int] = []
    for part in group.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and all(b.strip().isdigit() for b in bounds):
                lo, hi = int(bounds[0]), int(bounds[1])
                if lo <= hi and (hi - lo) < 50:  # sanity cap, avoid runaway ranges
                    ids.extend(range(lo, hi + 1))
        elif part.isdigit():
            ids.append(int(part))
    return ids


def _split_author_year_group(group: str) -> List[str]:
    """Turns 'Smith, 2020; Jones, 2019' into ['Smith, 2020', 'Jones, 2019'].
    Keys are normalized (whitespace-collapsed) so they can be matched against
    reference-list entries later."""
    parts = [p.strip() for p in group.split(";") if p.strip()]
    return [re.sub(r"\s+", " ", p) for p in parts]


# A reference entry shorter than this (after stripping bracket numbers and
# whitespace) is almost certainly a PDF-extraction artifact (a stray line
# break, a lone page-footer character, etc.) rather than a real citation.
_MIN_VALID_REFERENCE_CHARS = 8
_MIN_VALID_REFERENCE_WORDS = 3

# Common leading words that indicate the "author" position was actually a
# sentence fragment (extraction artifact), not a real bibliography entry.
_NON_AUTHOR_LEAD_WORDS = {
    "the", "a", "an", "this", "these", "those", "in", "on", "for", "of",
    "and", "or", "with", "from", "using", "based",
}


def _is_junk_reference_text(text: str) -> bool:
    """Returns True if `text` is too short/sparse/malformed to plausibly be
    a real bibliography entry (e.g. a single stray character from PDF
    line-break extraction, or a sentence fragment with no real author)."""
    stripped = re.sub(r"^\s*\[?\d+\]?\.?\s*", "", text).strip()

    letters = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]", stripped)
    if len(stripped) < _MIN_VALID_REFERENCE_CHARS or len(letters) < 4:
        return True

    words = stripped.split()
    if len(words) < _MIN_VALID_REFERENCE_WORDS:
        return True

    # A real bibliography entry starts with an author surname/initials
    # (capitalized) or a bracketed number, not a generic sentence-leading
    # word — "The 2025 ..." is a giveaway that the actual author text was
    # lost during parsing/extraction.
    first_word = re.sub(r"[^\w]", "", words[0]).lower()
    if first_word in _NON_AUTHOR_LEAD_WORDS:
        return True

    return False


def _normalize_reference_entry(entry: Any, index: int) -> Optional[Dict[str, Any]]:
    """Normalizes a single reference-list entry into a consistent shape,
    regardless of whether parse_document stored it as a plain string or a
    dict with fields. Returns None if the entry looks like a junk/garbage
    artifact rather than a real reference, so callers can drop it instead
    of surfacing a broken label like "s"."""
    if isinstance(entry, dict):
        text = entry.get("text") or entry.get("raw") or entry.get("citation") or ""
        ref_id = entry.get("id") or entry.get("number") or index
    else:
        text = str(entry)
        ref_id = index

    text = text.strip()

    if _is_junk_reference_text(text):
        return None

    # Try to pull a short display label: first author's surname + year if
    # present, else the first several words of the entry (for organizational
    # / institutional references like "National Curriculum and Textbook
    # Board, 2026" where there's no single personal-author surname).
    year_match = re.search(r"\b(19|20)\d{2}[a-z]?\b", text)
    year = year_match.group(0) if year_match else None

    first_author = None
    author_match = re.match(r"^\s*\[?\d*\]?\.?\s*([A-Z][A-Za-z\-'À-ÖØ-öø-ÿ]+)", text)
    if author_match:
        candidate = author_match.group(1)
        # Reject candidates that are all-caps acronyms (NCTB, SSC, IEEE) or
        # generic institutional words — these aren't personal surnames, so
        # "NCTB 2026" / "Board 2026" is a misleading label. Fall through to
        # the multi-word fallback instead, which reads better for orgs.
        is_acronym = candidate.isupper() and len(candidate) <= 6
        is_generic_org_word = candidate.lower() in {
            "board", "national", "ministry", "department", "committee",
            "association", "society", "institute", "organization",
            "organisation", "council", "commission", "bureau",
        }
        if not is_acronym and not is_generic_org_word:
            first_author = candidate

    if first_author and year:
        label = f"{first_author} {year}"
    elif first_author:
        label = first_author
    else:
        words = text.split()
        label = " ".join(words[:6]) + ("…" if len(words) > 6 else "")

    return {
        "ref_id": ref_id,
        "label": label or f"Reference {index}",
        "raw_text": text,
        "year": year,
    }


def _reference_lookup_keys(ref: Dict[str, Any]) -> List[str]:
    """Builds the set of strings that could plausibly match this reference
    against an author-year in-text citation, e.g. 'Smith 2020', 'Smith, 2020'."""
    keys = []
    if ref.get("label"):
        keys.append(ref["label"])
        keys.append(ref["label"].replace(" ", ", ", 1))
    return keys


def _guess_section_for_offset(offset: int, section_spans: List[Tuple[str, int, int]]) -> str:
    """Returns the section name whose (start, end) character span contains
    the given offset, or 'unknown' if none match."""
    for name, start, end in section_spans:
        if start <= offset < end:
            return name
    return "unknown"


def _build_section_spans(sections: Dict[str, str], full_text: str) -> List[Tuple[str, int, int]]:
    """Best-effort reconstruction of where each section starts/ends inside
    the full cleaned text, by locating each section's own text as a
    substring. Sections that can't be located are simply skipped (their
    citations will fall back to 'unknown') rather than raising."""
    spans: List[Tuple[str, int, int]] = []
    for name, section_text in sections.items():
        if not section_text:
            continue
        needle = section_text[:200].strip()
        if not needle:
            continue
        start = full_text.find(needle)
        if start == -1:
            continue
        end = start + len(section_text)
        spans.append((name, start, end))
    spans.sort(key=lambda s: s[1])
    return spans


def build_citation_graph(
    parsed: Dict[str, Any],
    section_chunks: Optional[List[Dict[str, Any]]] = None,
    full_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a citation graph from GyanGrid's `parsed` document dict.

    Parameters
    ----------
    parsed : dict
        Output of src.parser.parse_document. Expected (but not strictly
        required) keys: "title", "sections" (dict of section_name -> text),
        "references" (list of strings or dicts).
    section_chunks : list, optional
        Output of src.chunker.chunk_sections. Used as a fallback source of
        section text if `parsed["sections"]` text spans can't be located
        inside `full_text`.
    full_text : str, optional
        The full cleaned document text. If not provided, falls back to
        concatenating parsed["sections"].values() in order.

    Returns
    -------
    dict with keys:
        "paper_title": str
        "nodes": list of {id, label, type, section, times_cited}
        "edges": list of {source, target, section}
        "warnings": list of str  (non-fatal issues, e.g. unmatched citations)
    """
    warnings: List[str] = []

    title = (parsed.get("title") or "Untitled paper").strip()
    sections: Dict[str, str] = parsed.get("sections") or {}
    references_raw: List[Any] = parsed.get("references") or []

    if not references_raw:
        warnings.append("No references found in parsed document; graph will only contain the paper node.")

    if full_text is None:
        full_text = "\n".join(sections.values()) if sections else ""

    raw_normalized = [
        _normalize_reference_entry(entry, i + 1) for i, entry in enumerate(references_raw)
    ]
    dropped_count = sum(1 for r in raw_normalized if r is None)
    if dropped_count:
        warnings.append(
            f"{dropped_count} reference-list entry(ies) looked like extraction artifacts "
            f"(too short/garbled) and were skipped."
        )
    normalized_refs = [r for r in raw_normalized if r is not None]
    ref_by_number = {r["ref_id"]: r for r in normalized_refs if isinstance(r["ref_id"], int)}

    # Build a lookup for author-year style citations -> ref entry
    author_year_lookup: Dict[str, Dict[str, Any]] = {}
    for ref in normalized_refs:
        for key in _reference_lookup_keys(ref):
            author_year_lookup[key.lower()] = ref

    section_spans = _build_section_spans(sections, full_text) if full_text else []

    # cited_in[ref_key] -> Counter-like dict of section -> count
    cited_in: Dict[Any, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unmatched_numeric: set = set()
    unmatched_author_year: set = set()

    if full_text:
        for match in _NUMERIC_CITATION_RE.finditer(full_text):
            offset = match.start()
            section_name = _guess_section_for_offset(offset, section_spans)
            for num in _expand_numeric_group(match.group(1)):
                if num in ref_by_number:
                    cited_in[num][section_name] += 1
                else:
                    unmatched_numeric.add(num)

        for match in _AUTHOR_YEAR_RE.finditer(full_text):
            offset = match.start()
            section_name = _guess_section_for_offset(offset, section_spans)
            for entry in _split_author_year_group(match.group(1)):
                key = entry.lower()
                ref = author_year_lookup.get(key)
                if not ref:
                    # try matching just on surname (drop the year) as a softer fallback
                    surname = entry.split(",")[0].strip().lower()
                    ref = next(
                        (r for r in normalized_refs if r["label"].lower().startswith(surname)),
                        None,
                    )
                if ref:
                    cited_in[ref["ref_id"]][section_name] += 1
                else:
                    unmatched_author_year.add(entry)

    if unmatched_numeric:
        warnings.append(
            f"{len(unmatched_numeric)} numeric citation marker(s) had no matching entry "
            f"in the reference list (e.g. {sorted(list(unmatched_numeric))[:5]})."
        )
    if unmatched_author_year:
        sample = list(unmatched_author_year)[:3]
        warnings.append(
            f"{len(unmatched_author_year)} author-year citation(s) could not be matched "
            f"to the reference list (e.g. {sample})."
        )

    # ── Assemble nodes ────────────────────────────────────────────────
    nodes: List[Dict[str, Any]] = [
        {
            "id": "paper",
            "label": title[:60],
            "type": "paper",
            "section": None,
            "times_cited": None,
        }
    ]

    edges: List[Dict[str, Any]] = []

    for ref in normalized_refs:
        ref_id = ref["ref_id"]
        sections_hit = cited_in.get(ref_id, {})
        total = sum(sections_hit.values())

        nodes.append(
            {
                "id": f"ref_{ref_id}",
                "label": ref["label"],
                "type": "reference",
                "section": None,
                "times_cited": total,
                "year": ref.get("year"),
            }
        )

        if sections_hit:
            for section_name, count in sections_hit.items():
                edges.append(
                    {
                        "source": "paper",
                        "target": f"ref_{ref_id}",
                        "section": section_name,
                        "weight": count,
                    }
                )
        else:
            # Reference exists in the list but was never matched to an
            # in-text marker (common with noisy OCR/parsing) — still show
            # it as a zero-weight edge so nothing silently disappears.
            edges.append(
                {
                    "source": "paper",
                    "target": f"ref_{ref_id}",
                    "section": "unmatched",
                    "weight": 0,
                }
            )

    return {
        "paper_title": title,
        "nodes": nodes,
        "edges": edges,
        "warnings": warnings,
    }


def graph_to_vis_json(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts the graph dict from build_citation_graph() into the shape
    expected by common JS force-graph libraries (e.g. react-force-graph,
    d3-force): {"nodes": [{id, ...}], "links": [{source, target, ...}]}.

    Kept as a separate function so the internal graph representation can
    evolve without breaking the frontend contract.
    """
    return {
        "nodes": [
            {
                "id": n["id"],
                "label": n["label"],
                "type": n["type"],
                "timesCited": n["times_cited"],
            }
            for n in graph["nodes"]
        ],
        "links": [
            {
                "source": e["source"],
                "target": e["target"],
                "section": e["section"],
                "weight": e["weight"],
            }
            for e in graph["edges"]
        ],
        "paperTitle": graph["paper_title"],
        "warnings": graph["warnings"],
    }


def reference_year_distribution(graph: Dict[str, Any]) -> Dict[str, int]:
    """Returns a {year_string: count} dict of how many references were
    published in each year, sorted by year ascending. References with no
    detectable year are grouped under 'unknown'. Useful for a timeline
    chart showing how recent the paper's literature base is."""
    counts: Dict[str, int] = defaultdict(int)
    for n in graph["nodes"]:
        if n["type"] != "reference":
            continue
        year = n.get("year") or "unknown"
        counts[year] += 1

    def _sort_key(item):
        y = item[0]
        return (0, int(y)) if y.isdigit() else (1, y)

    return dict(sorted(counts.items(), key=_sort_key))


def most_cited_references(graph: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    """Convenience helper: returns the top_n most-cited reference nodes,
    sorted descending by citation count. Useful for a quick summary above
    the full graph (e.g. 'Top 5 most-cited references')."""
    ref_nodes = [n for n in graph["nodes"] if n["type"] == "reference"]
    ref_nodes.sort(key=lambda n: n["times_cited"] or 0, reverse=True)
    return ref_nodes[:top_n]


if __name__ == "__main__":
    # Minimal smoke test using a tiny synthetic paper, so this file can be
    # sanity-checked directly with `python -m src.citation_graph` without
    # needing a real uploaded PDF. This sample is entirely fictional and
    # not derived from any real paper.
    sample_parsed = {
        "title": "Example Paper Title for Testing",
        "sections": {
            "introduction": "Prior work has explored this general area [1]. A common baseline approach was proposed [2].",
            "methodology": "We build on the baseline approach [2] and a related technique [3] for our experiments. See also (Doe, 2019).",
            "conclusion": "Future work will explore an alternative method [4].",
        },
        "references": [
            "Example Reference One: A General Survey, 2022.",
            "Author, A. Baseline Approach for Example Tasks, 2020.",
            "Author, B. Related Technique for Example Domain, 2021.",
            "Author, C. Alternative Method Overview, 2019.",
            "Doe, J. Example Named Entity Method, 2019.",
        ],
    }
    g = build_citation_graph(sample_parsed)
    import json

    print(json.dumps(g, indent=2))
    print("\nTop cited:", [n["label"] for n in most_cited_references(g)])
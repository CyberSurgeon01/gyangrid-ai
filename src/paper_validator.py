"""
paper_validator.py
Decides whether an uploaded document looks like a research paper before
spending time/tokens on embedding + AI analysis.

No detector is 100% accurate — this module scores structural signals
(abstract, references, section headers, in-text citations, length) and
optionally escalates borderline cases to an LLM semantic check. The result
always includes `reasons` so the UI can explain *why*, and callers should
let the user override with "Analyze anyway" rather than hard-blocking,
since false positives/negatives are unavoidable with any method.
"""

import re

from src.parser import SECTION_HEADINGS

# parser.py's detect_sections() already normalizes headings via
# _normalize() (lowercase, spaces -> underscores) and *pops* abstract /
# references / reference / bibliography out of the sections dict before
# parse_document() returns — those are checked separately below via
# parsed["abstract"] / parsed["references"], not via this list. So this is
# SECTION_HEADINGS minus the ones parser.py removes, normalized the same way.
_POPPED_BY_PARSER = {"abstract", "references", "reference", "bibliography"}
_ACADEMIC_SECTION_KEYS = {
    h.strip().lower().replace(" ", "_")
    for h in SECTION_HEADINGS
    if h not in _POPPED_BY_PARSER
}

# Phrases common in academic writing, rare in resumes/invoices/reports.
_ACADEMIC_PHRASES = [
    "this paper", "this study", "we propose", "we present", "our approach",
    "the results show", "experimental results", "dataset", "prior work",
    "state of the art", "we evaluate", "in this work", "our method",
    "significant difference", "hypothesis",
]

# [1]  [1,2]  [1-3]  (Smith, 2020)  (Smith et al., 2020)
_NUMERIC_CITATION_RE = re.compile(r"\[\d+(?:[,\-–]\s*\d+)*\]")
_AUTHOR_YEAR_CITATION_RE = re.compile(r"\([A-Z][a-zA-Z\-]+(?:\s+et al\.)?,?\s+\d{4}[a-z]?\)")


def _section_keyword_score(parsed: dict) -> tuple[int, list[str]]:
    """Up to 20 points for recognizable academic section headers, matched
    directly against parsed["sections"] keys (already normalized by
    parser.py's detect_sections()) rather than re-scanning raw text —
    the parser already did that work, so trust its output."""
    found = set((parsed or {}).get("sections", {}).keys()) & _ACADEMIC_SECTION_KEYS
    score = min(20, len(found) * 4)
    if found:
        readable = ", ".join(sorted(f.replace("_", " ") for f in found))
        reasons = [f"found {len(found)} academic section header(s): {readable}"]
    else:
        reasons = ["no academic section headers found"]
    return score, reasons


def _abstract_score(parsed: dict) -> tuple[int, list[str]]:
    """Up to 15 points for a real (non-trivial) abstract."""
    abstract = (parsed or {}).get("abstract", "") or ""
    if len(abstract.strip()) >= 150:
        return 15, ["has a substantive abstract"]
    if len(abstract.strip()) > 0:
        return 6, ["has a short/weak abstract"]
    return 0, ["no abstract detected"]


def _references_score(parsed: dict) -> tuple[int, list[str]]:
    """Up to 20 points for a reference list of reasonable size."""
    refs = (parsed or {}).get("references", []) or []
    n = len(refs)
    if n >= 8:
        return 20, [f"has {n} references"]
    if n >= 3:
        return 12, [f"has only {n} references"]
    if n >= 1:
        return 5, [f"has only {n} reference(s)"]
    return 0, ["no reference list detected"]


def _citation_pattern_score(cleaned_text: str) -> tuple[int, list[str]]:
    """Up to 15 points for in-text citation markers actually appearing in
    the body text (not just a reference list existing)."""
    numeric_hits = len(_NUMERIC_CITATION_RE.findall(cleaned_text))
    author_year_hits = len(_AUTHOR_YEAR_CITATION_RE.findall(cleaned_text))
    total = numeric_hits + author_year_hits
    if total >= 5:
        return 15, [f"found {total} in-text citation markers"]
    if total >= 1:
        return 7, [f"found only {total} in-text citation marker(s)"]
    return 0, ["no in-text citation markers found"]


def _phrase_score(cleaned_text: str) -> tuple[int, list[str]]:
    """Up to 15 points for academic-register phrasing."""
    lower = cleaned_text.lower()
    hits = sum(1 for p in _ACADEMIC_PHRASES if p in lower)
    score = min(15, hits * 3)
    reasons = [f"matched {hits} academic phrase(s)"] if hits else ["no academic phrasing detected"]
    return score, reasons


def _length_score(cleaned_text: str) -> tuple[int, list[str]]:
    """Up to 10 points — rules out short notes/single-page docs. Also caps
    out (rather than rewarding indefinitely) so a huge non-paper doc
    doesn't score well just from length."""
    n = len(cleaned_text)
    if n >= 8000:
        return 10, [f"document length ok ({n:,} chars)"]
    if n >= 3000:
        return 5, [f"document is on the short side ({n:,} chars)"]
    return 0, [f"document is very short ({n:,} chars)"]


def _title_score(parsed: dict) -> tuple[int, list[str]]:
    """Up to 5 points for a plausible, non-empty title."""
    title = ((parsed or {}).get("title") or "").strip()
    if len(title) >= 8:
        return 5, ["has a plausible title"]
    return 0, ["no usable title detected"]


def score_paper(cleaned_text: str, parsed: dict) -> dict:
    """Returns {score: 0-100, reasons: [...], breakdown: {...}}.
    Does NOT make the network call for Layer 2 — see maybe_llm_check()."""
    checks = {
        "abstract": _abstract_score(parsed),
        "references": _references_score(parsed),
        "sections": _section_keyword_score(parsed),
        "citations": _citation_pattern_score(cleaned_text),
        "phrasing": _phrase_score(cleaned_text),
        "length": _length_score(cleaned_text),
        "title": _title_score(parsed),
    }
    score = sum(v[0] for v in checks.values())
    reasons = [r for v in checks.values() for r in v[1]]
    breakdown = {k: v[0] for k, v in checks.items()}
    return {"score": score, "reasons": reasons, "breakdown": breakdown}


def maybe_llm_check(cleaned_text: str, llm_classify_fn=None) -> dict | None:
    """Optional Layer 2 for borderline scores (see is_research_paper()).
    `llm_classify_fn` should be a callable(text: str) -> dict with at least
    {"is_paper": bool, "reason": str} — wire this to your existing Gemini
    client in src/llm_pipeline.py. Returns None if no fn is supplied, so
    callers can skip the network call entirely (e.g. in tests or when the
    heuristic score is already decisive).
    """
    if llm_classify_fn is None:
        return None
    try:
        # Cap input size — we only need enough text for the model to judge
        # register/structure, not the whole paper.
        sample = cleaned_text[:4000]
        return llm_classify_fn(sample)
    except Exception as e:
        # Fail open to the heuristic result rather than blocking upload on
        # a transient API error.
        return {"is_paper": None, "reason": f"LLM check unavailable: {e}"}


def is_research_paper(
    cleaned_text: str,
    parsed: dict,
    threshold: int = 55,
    borderline_band: tuple[int, int] = (35, 65),
    llm_classify_fn=None,
) -> dict:
    """
    Main entry point. Returns:
        {
            "verdict": bool,          # final decision
            "score": int,             # 0-100 heuristic score
            "reasons": [str, ...],    # human-readable explanation
            "used_llm": bool,
            "confidence": "high" | "medium" | "low",
        }

    Only escalates to the LLM (if llm_classify_fn is provided) when the
    heuristic score falls in `borderline_band` — clear-cut cases are
    resolved without a network call.
    """
    result = score_paper(cleaned_text, parsed)
    score = result["score"]
    reasons = result["reasons"]
    used_llm = False
    confidence = "high"

    verdict = score >= threshold

    lo, hi = borderline_band
    if lo <= score <= hi and llm_classify_fn is not None:
        llm_result = maybe_llm_check(cleaned_text, llm_classify_fn)
        used_llm = True
        if llm_result and llm_result.get("is_paper") is not None:
            verdict = bool(llm_result["is_paper"])
            reasons = reasons + [f"LLM check: {llm_result.get('reason', '')}"]
            confidence = "medium"
        else:
            confidence = "low"
            reasons = reasons + [
                (llm_result or {}).get("reason", "LLM check unavailable — falling back to heuristic score")
            ]
    elif lo <= score <= hi:
        confidence = "low"

    return {
        "verdict": verdict,
        "score": score,
        "reasons": reasons,
        "used_llm": used_llm,
        "confidence": confidence,
    }
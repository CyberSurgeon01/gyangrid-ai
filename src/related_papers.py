"""
src/related_papers.py
Fetches top 10 related papers using Semantic Scholar + OpenAlex fallback.
Reads title and abstract directly from parsed dict (as produced by parser.py).
"""

from __future__ import annotations
import re
import time
import streamlit as st
import requests

from src.ui_theme import card_open, card_close, empty_state, theme_colors

_SS_SEARCH   = "https://api.semanticscholar.org/graph/v1/paper/search"
_SS_FIELDS   = "title,authors,year,externalIds,openAccessPdf,venue,citationCount"
_OA_SEARCH   = "https://api.openalex.org/works"
_OA_SELECT   = "id,display_name,authorships,doi,open_access,publication_year,primary_location,cited_by_count"
_HEADERS_SS  = {"User-Agent": "gyangrid-ai/1.0"}
_HEADERS_OA  = {"User-Agent": "gyangrid-ai/1.0 (mailto:contact@gyangrid.ai)"}
_MAX         = 10
_MAX_RETRIES = 3


# ── query builder ─────────────────────────────────────────────────────────────

_STOPWORDS = {
    "a", "an", "the", "of", "for", "and", "or", "in", "on", "to", "with",
    "using", "based", "via", "towards", "toward", "study", "approach",
    "analysis", "system", "systems", "framework", "method", "methods",
    "dataset", "data", "new", "novel", "improved", "efficient",
}


def _clean(text: str) -> str:
    """Strip punctuation/dashes that hurt relevance search on both APIs."""
    text = re.sub(r"[\u2010-\u2015]", " ", text)   # unicode hyphen/dash variants
    text = re.sub(r"[():,;]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_query(parsed: dict, file_name: str) -> str:
    """
    Primary query: title only, cleaned. Titles alone perform far better on
    Semantic Scholar / OpenAlex relevance search than title+raw-abstract blobs,
    which dilute the match and often return zero results.
    """
    title = (parsed.get("title") or file_name or "").strip()
    title = re.sub(r"\.(pdf|docx?)$", "", title, flags=re.IGNORECASE)
    return _clean(title)[:300]


def _build_keyword_query(parsed: dict, file_name: str) -> str:
    """
    Secondary/fallback query: title + a short, cleaned abstract snippet.
    Used only if the title-only query comes back thin.
    """
    title    = (parsed.get("title") or file_name or "").strip()
    abstract = (parsed.get("abstract") or "").strip()
    abstract_snippet = " ".join(abstract.split()[:20]) if abstract else ""
    query = f"{title} {abstract_snippet}".strip()
    return _clean(query)[:300]


def _build_broad_queries(parsed: dict, file_name: str) -> list[str]:
    """
    A hyper-specific/novel title (e.g. a coined dataset name like
    "SSC-BanglaTutor") will rarely have 10 papers that literally match it —
    exact-title search is the wrong tool for "related papers" recall.
    Instead, build several short topical keyword queries (3-5 significant
    words each) from the title and abstract, so different subsets of the
    real topic surface different, genuinely related papers.
    """
    title    = _clean((parsed.get("title") or file_name or ""))
    abstract = _clean((parsed.get("abstract") or ""))

    def _keywords(text: str, n: int) -> list[str]:
        words = [w for w in text.split() if w.lower().strip("-") not in _STOPWORDS and len(w) > 2]
        return words[:n]

    title_kw    = _keywords(title, 6)
    abstract_kw = _keywords(abstract, 12)

    queries = []
    if title_kw:
        queries.append(" ".join(title_kw))
    if len(title_kw) > 3:
        queries.append(" ".join(title_kw[:3]))
    if abstract_kw:
        queries.append(" ".join(abstract_kw[:6]))
        if len(abstract_kw) > 6:
            queries.append(" ".join(abstract_kw[6:12]))

    # de-dupe while preserving order
    seen, out = set(), []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


# ── normalizers ───────────────────────────────────────────────────────────────

def _authors_str(names: list[str]) -> str:
    if not names:
        return "Unknown authors"
    if len(names) > 3:
        return ", ".join(names[:3]) + " et al."
    return ", ".join(names)


def _normalize_ss(item: dict) -> dict:
    names    = [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")]
    ext      = item.get("externalIds") or {}
    doi      = ext.get("DOI")
    oa       = item.get("openAccessPdf") or {}
    return {
        "title":    item.get("title") or "Untitled",
        "authors":  _authors_str(names),
        "year":     item.get("year"),
        "venue":    item.get("venue") or "Unknown venue",
        "doi":      doi,
        "doi_link": f"https://doi.org/{doi}" if doi else None,
        "pdf_link": oa.get("url"),
        "cited_by": item.get("citationCount"),
    }


def _normalize_oa(item: dict) -> dict:
    names    = [
        a["author"]["display_name"]
        for a in (item.get("authorships") or [])
        if a.get("author") and a["author"].get("display_name")
    ]
    doi_raw  = (item.get("doi") or "").replace("https://doi.org/", "").strip()
    oa       = item.get("open_access") or {}
    src      = ((item.get("primary_location") or {}).get("source") or {})
    return {
        "title":    item.get("display_name") or "Untitled",
        "authors":  _authors_str(names),
        "year":     item.get("publication_year"),
        "venue":    src.get("display_name") or "Unknown venue",
        "doi":      doi_raw or None,
        "doi_link": f"https://doi.org/{doi_raw}" if doi_raw else None,
        "pdf_link": oa.get("oa_url"),
        "cited_by": item.get("cited_by_count"),
    }


# ── fetchers ──────────────────────────────────────────────────────────────────

def _get_with_retry(url: str, params: dict, headers: dict, label: str):
    """
    GET with retry-with-backoff on 429/5xx. A single transient rate-limit
    should not silently kill the whole source for the session.
    """
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=12)
            if r.status_code == 429:
                # Respect Retry-After if provided, else exponential backoff
                wait = float(r.headers.get("Retry-After", 0)) or (1.5 * (attempt + 1))
                last_err = f"{label}: rate limited (429), retrying in {wait:.1f}s…"
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                last_err = f"{label}: server error {r.status_code}"
                time.sleep(1.0 * (attempt + 1))
                continue
            r.raise_for_status()
            return r, None
        except requests.RequestException as e:
            last_err = f"{label}: {e}"
            time.sleep(1.0 * (attempt + 1))
    return None, last_err


def _get_with_retry(url: str, params: dict, headers: dict, label: str):
    """GET with retry-with-backoff on 429/5xx."""
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=12)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 0)) or (1.5 * (attempt + 1))
                last_err = f"{label}: rate limited (429), retrying in {wait:.1f}s…"
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                last_err = f"{label}: server error {r.status_code}"
                time.sleep(1.0 * (attempt + 1))
                continue
            r.raise_for_status()
            return r, None
        except requests.RequestException as e:
            last_err = f"{label}: {e}"
            time.sleep(1.0 * (attempt + 1))
    return None, last_err


def _fetch_ss(query: str) -> list[dict]:
    if not query:
        return []
    r, err = _get_with_retry(
        _SS_SEARCH,
        {"query": query, "limit": _MAX, "fields": _SS_FIELDS},
        _HEADERS_SS,
        "SemanticScholar",
    )
    if err:
        st.session_state["_rp_last_error"] = err
    if r is None:
        return []
    try:
        return [_normalize_ss(x) for x in r.json().get("data", [])]
    except Exception as e:
        st.session_state["_rp_last_error"] = f"SemanticScholar: bad response ({e})"
        return []


def _fetch_oa(query: str) -> list[dict]:
    """
    Single OpenAlex query attempt (no internal shortening — callers now sweep
    across multiple pre-built broad queries instead, so we don't need to
    silently bail into ever-shorter versions of one query here).
    """
    if not query:
        return []
    r, err = _get_with_retry(
        _OA_SEARCH,
        {"search": query, "per-page": _MAX,
         "sort": "relevance_score:desc", "select": _OA_SELECT},
        _HEADERS_OA,
        "OpenAlex",
    )
    if err:
        st.session_state["_rp_last_error"] = err
    if r is None:
        return []
    try:
        return [_normalize_oa(x) for x in r.json().get("results", [])]
    except Exception as e:
        st.session_state["_rp_last_error"] = f"OpenAlex: bad response ({e})"
        return []


def _is_self_match(paper_title: str, source_title: str) -> bool:
    """True if a search result is essentially the user's own uploaded paper."""
    def _norm(t: str) -> str:
        t = re.sub(r"[^a-z0-9 ]", "", t.lower())
        return re.sub(r"\s+", " ", t).strip()
    a, b = _norm(paper_title), _norm(source_title)
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) > 15 and shorter in longer


def fetch_related_papers(exact_query: str, broad_queries: list[str], source_title: str = "") -> list[dict]:
    """
    Strategy: try the exact title query first (best precision), then sweep
    across several broad topical keyword queries (built from title+abstract)
    and keep accumulating unique, non-self papers from BOTH Semantic Scholar
    and OpenAlex until we reach _MAX or run out of queries to try. An exact
    title match alone rarely yields 10 results for a specific/novel title —
    broad queries are what actually fill out a real top-10.
    """
    cache_key = f"rp_{exact_query[:80]}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    st.session_state.pop("_rp_last_error", None)
    papers: list[dict] = []
    seen: set[str] = set()

    def _add_all(new: list[dict]):
        for p in new:
            if source_title and _is_self_match(p["title"], source_title):
                continue
            key = p["title"].lower()
            if key not in seen:
                papers.append(p)
                seen.add(key)

    all_queries = [exact_query] + [q for q in broad_queries if q and q != exact_query]

    for q in all_queries:
        if len(papers) >= _MAX:
            break
        _add_all(_fetch_ss(q))
        if len(papers) >= _MAX:
            break
        _add_all(_fetch_oa(q))

    papers = papers[:_MAX]
    st.session_state[cache_key] = papers
    return papers


def _clear_cache():
    for k in [k for k in st.session_state if k.startswith("rp_")]:
        del st.session_state[k]
    st.session_state.pop("_rp_last_error", None)


# ── UI ────────────────────────────────────────────────────────────────────────

def _paper_card(paper: dict, index: int, c: dict):
    badge = lambda label, color: (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:12px;'
        f'font-size:11px;font-weight:600;margin-right:6px;'
        f'background:{color}22;color:{color};">{label}</span>'
    )
    year_badge = badge(str(paper["year"] or "n/a"), c["accent"])
    oa_badge   = badge("Open Access", "#1D9E75") if paper["pdf_link"] else ""

    st.markdown(
        f"""<div style="border:1px solid {c['border']};border-radius:12px;
            padding:16px 20px;margin-bottom:8px;background:{c['surface']};">
            <div style="margin-bottom:6px;">{year_badge}{oa_badge}</div>
            <div style="font-weight:700;font-size:15px;color:{c['text_primary']};
                line-height:1.4;margin-bottom:4px;">{index}. {paper['title']}</div>
            <div style="font-size:12px;color:{c['text_secondary']};margin-bottom:2px;">
                👤 {paper['authors']}</div>
            <div style="font-size:12px;color:{c['text_secondary']};">
                📰 {paper['venue']}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    col_doi, col_link, col_pdf = st.columns([2, 1, 1])
    with col_doi:
        st.caption(f"🆔 `{paper['doi']}`" if paper["doi"] else "🆔 No DOI")
    with col_link:
        if paper["doi_link"]:
            st.link_button("Open DOI", paper["doi_link"], use_container_width=True)
    with col_pdf:
        if paper["pdf_link"]:
            st.link_button("📄 Free PDF", paper["pdf_link"], use_container_width=True)
        elif paper["cited_by"] is not None:
            st.caption(f"📊 Cited {paper['cited_by']}×")

    st.markdown("<hr style='margin:4px 0 12px 0;opacity:0.15;'>", unsafe_allow_html=True)


def render_related_papers_page():
    c = theme_colors()

    if "processed_file_name" not in st.session_state:
        empty_state("link", "No paper loaded",
                    "Upload a research paper first, then come back here.")
        if st.button("Go to Upload paper"):
            st.session_state.nav_page = "Upload paper"
            st.rerun()
        return

    parsed         = st.session_state.get("parsed") or {}
    if st.session_state.get("_rp_debug", False):
        with st.expander("🐞 Debug: parsed paper data", expanded=False):
            st.write({
                "title": parsed.get("title"),
                "abstract_len": len(parsed.get("abstract") or ""),
                "abstract_preview": (parsed.get("abstract") or "")[:200],
                "section_keys": list((parsed.get("sections") or {}).keys()),
            })
    file_name      = st.session_state.get("processed_file_name", "")
    title          = parsed.get("title") or file_name
    query          = _build_query(parsed, file_name)
    broad_queries  = _build_broad_queries(parsed, file_name)

    display_title = title[:70] + ("…" if len(title) > 70 else "")
    card_open("Related Papers", "link",
              caption=f'Searching for: "{display_title}"')

    col_r, col_i = st.columns([1, 5])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            _clear_cache()
            st.rerun()
    with col_i:
        st.caption("Powered by [Semantic Scholar](https://www.semanticscholar.org) + [OpenAlex](https://openalex.org)")
    card_close()

    # Show query used (helps debug)
    with st.expander("🔍 Queries used", expanded=False):
        st.caption("Exact title match (tried first):")
        st.code(query, language=None)
        if broad_queries:
            st.caption("Broad topical sweeps (used to fill out the top 10):")
            for q in broad_queries:
                st.code(q, language=None)

    with st.spinner("Fetching related papers…"):
        papers = fetch_related_papers(query, broad_queries, source_title=title)

    # Show last API error if any (after fetch, so it reflects this run)
    err = st.session_state.get("_rp_last_error")
    if err and not papers:
        st.warning(f"API note: {err}", icon="⚠️")

    if not papers:
        empty_state("search", "No results found",
                    "Both APIs returned no results. Check the query above and try 🔄 Refresh.")
        return

    card_open(f"Top {len(papers)} Related Papers", "book-open")
    for i, paper in enumerate(papers, start=1):
        _paper_card(paper, i, c)
    card_close()
from src.llm_pipeline import answer_question, _expand_query, classify_is_research_paper, extract_retry_seconds, is_zero_quota_exception
from src.background_analysis import get_analysis_status
from src.paper_validator import is_research_paper
from src.report_export import generate_docx_report, generate_pdf_report
from src.citation_graph import build_citation_graph, most_cited_references, reference_year_distribution
import time
from datetime import datetime, timezone
import streamlit as st
from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_text, chunk_sections
from src.parser import parse_document
from src.embeddings import embed_chunks, embed_query
from src.vector_store import VectorStore
from src.paper_cache import hash_file_bytes, save_paper, load_paper, save_analysis, load_analysis
from src.audio_player import render_audio_player
from src.login_page import render_login_page
from src.signup_page import render_signup_page
from src.supabase_client import get_supabase
from src.profile import render_profile_menu, register_paper, get_current_user_id, list_papers, open_paper, _load_index
from src.compare_page import render_compare_page
from src.related_papers import render_related_papers_page
from src.ui_theme import (
    inject_base_css,
    render_sidebar_nav,
    render_dark_mode_toggle,
    render_logout_button,
    card_open,
    card_close,
    metric_tile,
    structure_row,
    result_card,
    tag_pills,
    page_header,
    empty_state,
    feature_preview_card,
    history_table,
    json_block,
    theme_colors,
    icon_svg,
    history_row_open,
    history_row_close,
)

st.set_page_config(page_title="GyanGrid AI", layout="wide")


def _is_quota_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def _quota_warning(e: Exception = None):
    if e is not None and is_zero_quota_exception(e):
        st.error(
            "This Gemini API key has **no quota at all** (limit: 0) for this "
            "model — that's not a temporary traffic spike, it's a billing/plan "
            "issue, so retrying won't help. Check "
            "[Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) "
            "and make sure billing is enabled on the linked Google Cloud project.",
            icon="🚫",
        )
    else:
        wait_s = extract_retry_seconds(e) if e is not None else None
        if wait_s:
            wait_str = f"{int(wait_s)} seconds" if wait_s < 90 else f"{int(wait_s // 60)} minutes"
            msg = f"We're processing a lot of requests right now and hit our limit. Please try again in about {wait_str}."
        else:
            msg = "We're processing a lot of requests right now and hit our limit. Please try again shortly."
        st.warning(msg, icon="⏳")
    if e is not None:
        with st.expander("Show raw error (source material)"):
            st.code(str(e), language=None)

# ── Restore dark-mode preference after a page refresh ───────────────────
# st.session_state resets on refresh (new browser session), but
# st.query_params survives it — same trick used below for the loaded
# paper. Without this, the toggle "wins" only within the current
# session and silently falls back to light on the next refresh.
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = st.query_params.get("theme") == "dark"

inject_base_css()

# ── Auth gate: login/sign-up is the landing page ────────────────────────
if "auth_status" not in st.session_state:
    st.session_state.auth_status = None

# After a Google OAuth redirect, Supabase (using the auth-code / PKCE
# flow, its current default) sends the user back with a plain query
# param — http://localhost:8501/?code=xxxx — not a URL hash. Streamlit
# can read query params directly via st.query_params, so this just
# exchanges that code for a real session, no client-side JS needed.
if "code" in st.query_params and st.session_state.auth_status is None:
    try:
        sb = get_supabase()
        sb.auth.exchange_code_for_session({"auth_code": st.query_params["code"]})
        session = sb.auth.get_session()
        if session and session.user:
            st.session_state.auth_status = "user"
            st.session_state.user_email = session.user.email
            st.session_state.user_id = session.user.id
    except Exception as e:
        st.session_state.oauth_error = str(e)
    finally:
        st.query_params.pop("code", None)

# Restore Supabase session after an ordinary page refresh (same-tab
# reload, not a fresh OAuth redirect) — Supabase's Python client persists
# the session locally, so get_session() alone is enough for that case.
if st.session_state.auth_status is None:
    try:
        sb = get_supabase()
        session = sb.auth.get_session()
        if session and session.user:
            st.session_state.auth_status = "user"
            st.session_state.user_email = session.user.email
            st.session_state.user_id = session.user.id
    except Exception:
        pass

if st.session_state.auth_status is None:
    _oauth_err = st.session_state.pop("oauth_error", None)
    if _oauth_err:
        st.error(f"Google sign-in failed: {_oauth_err}")
    if st.session_state.get("auth_view") == "signup":
        render_signup_page()
    else:
        render_login_page()
    st.stop()

page = render_sidebar_nav(default="Dashboard")

# ── Restore a previously-processed paper after a page refresh ───────────
# st.session_state resets on refresh (new browser session), but
# st.query_params survives it — so a hash in the URL is what lets us find
# the cached pipeline output (and, if present, the AI analysis) on disk.
#
# Authorization check: paper_cache.py keys purely by file-content hash
# with no per-user boundary, so the hash in ?paper=... could belong to
# any user (e.g. a shared/leaked link, or simply two users uploading the
# same PDF and colliding on the same cache key). Only restore it if the
# hash is in the current user's own paper index — guests (no user_id)
# never have an index, so this always blocks them, which is correct.
_paper_param = st.query_params.get("paper")
_uid_for_restore = st.session_state.get("user_id")
_owns_paper = bool(
    _uid_for_restore and _paper_param
    and _paper_param in {e["file_hash"] for e in _load_index(_uid_for_restore)}
)
if "processed_file_name" not in st.session_state and _paper_param and _owns_paper:
    _cached = load_paper(_paper_param)
    if _cached:
        _data, _store = _cached
        st.session_state.processed_file_name = _data["file_name"]
        st.session_state.cleaned_text = _data["cleaned_text"]
        st.session_state.chunks = _data["chunks"]
        st.session_state.parsed = _data["parsed"]
        st.session_state.section_chunks = _data["section_chunks"]
        st.session_state.vector_store = _store

        _cached_analysis = load_analysis(_paper_param)
        if _cached_analysis:
            st.session_state.last_analysis = _cached_analysis["analysis"]
            st.session_state.last_analysis_lang = _cached_analysis["lang_code"]

_HAS_PAPER = "processed_file_name" in st.session_state
_PAGE_COPY = {
    "Dashboard": ("Dashboard", "Overview of your uploaded paper's structure and extracted content."),
    "Upload paper": ("Upload paper", "Upload a research paper and prepare it for AI analysis."),
    "History": ("History", "All papers you've uploaded — open any of them to pick up right where you left off."),
    "Q&A (RAG)": ("Q&A (RAG)", "Ask grounded questions and get answers sourced directly from the paper."),
    "AI analysis": ("AI Analysis", "Upload a research paper to generate summaries, insights, questions, and citation support."),
    "Compare": ("Compare", "Compare sections between two research papers side by side."),
    "Citation graph": ("Citation graph", "Visualize how this paper's citations map to its reference list."),
    "Related Papers": ("Related Papers", "Discover the top 10 papers most related to your uploaded paper, powered by OpenAlex."),
    "Settings": ("Settings", "Configure output language and workspace preferences."),
}
_title, _subtitle = _PAGE_COPY.get(page, ("GyanGrid AI", ""))
render_profile_menu()
page_header(
    _title,
    _subtitle,
    crumb=["GyanGrid AI", page],
    status_label=(
        f"Paper loaded: {st.session_state.get('processed_file_name', '')[:28]}"
        if _HAS_PAPER else "No paper loaded"
    ),
    status_active=_HAS_PAPER,
)


MAX_SAVED_PAPERS = 3


def process_uploaded_file(uploaded_file):
    """Runs the load -> clean -> parse -> chunk -> embed pipeline once per
    new file, or restores it from disk cache if this exact file was
    processed before (this is what survives a page refresh, via the hash
    stored in st.query_params)."""
    if st.session_state.get("processed_file_name") == uploaded_file.name:
        return

    # Guest users can analyze but cannot save papers
    is_guest = st.session_state.get("auth_status") == "guest"

    file_bytes = uploaded_file.getvalue()  # safe: doesn't disturb the read position load_document() uses
    file_hash = hash_file_bytes(file_bytes)

    # Logged-in users: enforce 3-paper cap before doing any work
    if not is_guest:
        user_id = get_current_user_id()
        existing_papers = list_papers(user_id)
        already_saved = any(e["file_hash"] == file_hash for e in existing_papers)
        if not already_saved and len(existing_papers) >= MAX_SAVED_PAPERS:
            st.warning(
                f"\u26a0\ufe0f You can only save up to {MAX_SAVED_PAPERS} papers. "
                "Please remove one from your History before uploading a new one.",
                icon="\U0001f4c4",
            )
            return

    cached = load_paper(file_hash)
    if cached:
        data, store = cached
        st.session_state.processed_file_name = data["file_name"]
        st.session_state.cleaned_text = data["cleaned_text"]
        st.session_state.chunks = data["chunks"]
        st.session_state.parsed = data["parsed"]
        st.session_state.section_chunks = data["section_chunks"]
        st.session_state.vector_store = store
        st.query_params["paper"] = file_hash

        cached_analysis = load_analysis(file_hash)
        if cached_analysis:
            st.session_state.last_analysis = cached_analysis["analysis"]
            st.session_state.last_analysis_lang = cached_analysis["lang_code"]

        if not is_guest:
            register_paper(get_current_user_id(), file_hash, data["file_name"])
        st.session_state.pop(f"audio_paper_{uploaded_file.name}", None)
        st.session_state.pop("audio_analysis", None)
        return

    with st.spinner("Reading and preparing document..."):
        raw_text = load_document(uploaded_file)
        cleaned_text = clean_text(raw_text)
        chunks = chunk_text(cleaned_text)
        parsed = parse_document(cleaned_text)
        section_chunks = chunk_sections(parsed)

    # Gate before embedding — no point spending embedding time/tokens on a
    # document that isn't a research paper. Heuristic score resolves clear
    # cases instantly; only borderline scores trigger the Gemini call.
    force_key = f"force_analyze_{uploaded_file.name}"
    if not st.session_state.get(force_key):
        check = is_research_paper(cleaned_text, parsed, llm_classify_fn=classify_is_research_paper)
        if not check["verdict"]:
            st.session_state.pending_reject = {
                "file_name": uploaded_file.name,
                "reasons": check["reasons"],
                "score": check["score"],
            }
            return
    st.session_state.pop("pending_reject", None)

    with st.spinner("Generating embeddings (first run may take a minute to load the model)..."):
        embedded_chunks = embed_chunks(section_chunks)
        store = VectorStore(dimension=384)
        store.add_chunks(embedded_chunks)

    save_paper(file_hash, uploaded_file.name, cleaned_text, chunks, parsed, section_chunks, store)
    if not is_guest:
        register_paper(get_current_user_id(), file_hash, uploaded_file.name)

    st.session_state.processed_file_name = uploaded_file.name
    st.session_state.cleaned_text = cleaned_text
    st.session_state.chunks = chunks
    st.session_state.parsed = parsed
    st.session_state.section_chunks = section_chunks
    st.session_state.vector_store = store
    st.query_params["paper"] = file_hash
    st.session_state.pop(f"audio_paper_{uploaded_file.name}", None)
    st.session_state.pop("audio_analysis", None)


def require_document():
    """Returns True and does nothing if a document is already processed.
    Otherwise shows a prompt and returns False so the caller can stop rendering."""
    if "processed_file_name" in st.session_state:
        return True
    card_open("No paper loaded yet", "file-text")
    st.write("Upload a research paper first, then come back here.")
    if st.button("Go to Upload paper"):
        st.session_state.nav_page = "Upload paper"
        st.rerun()
    card_close()
    return False


# ── History page ─────────────────────────────────────────────────────────
if page == "History":
    _papers = list_papers(get_current_user_id())
    if not _papers:
        empty_state(
            "clock",
            "No papers yet",
            "Papers you upload will show up here so you can reopen them anytime.",
        )
    else:
        c = theme_colors()
        border_color = "#3d5a80" if st.session_state.get("dark_mode") else "#94a3b8"
        bg_color = c["surface"]

        for _idx, _entry in enumerate(_papers):
            _marker_id = f"gg-history-marker-{_idx}"
            with st.container():
                st.markdown(
                    f'<span id="{_marker_id}" style="display:none;"></span>',
                    unsafe_allow_html=True,
                )
                _info_col, _open_col, _remove_col = st.columns([6, 1, 1])
                with _info_col:
                    _date_label = _entry["uploaded_at"][:16].replace("T", " ")
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;">'
                        f'{icon_svg("file-text", 18, c["text_secondary"])}'
                        f'<span style="font-weight:600;color:{c["text_primary"]};">{_entry["file_name"]}</span>'
                        f'<span style="color:{c["text_secondary"]};font-size:12px;">{_date_label}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with _open_col:
                    if st.button(
                        "Open",
                        key=f"history_open_{_entry['file_hash']}",
                        type="primary",
                        use_container_width=True,
                        help="Analyze, ask questions, view graph",
                    ):
                        if open_paper(_entry["file_hash"]):
                            st.rerun()
                        else:
                            st.error("That paper's cache is gone — it may need to be re-uploaded.")
                with _remove_col:
                    if st.button(
                        "🗑",
                        key=f"history_remove_{_entry['file_hash']}",
                        use_container_width=True,
                        help="Remove from history",
                    ):
                        from src.profile import remove_paper
                        remove_paper(get_current_user_id(), _entry["file_hash"])
                        st.rerun()

                st.components.v1.html(
                    f"""<script>
                    (function() {{
                        function applyBorder() {{
                            var marker = window.parent.document.getElementById('{_marker_id}');
                            if (!marker) {{ setTimeout(applyBorder, 50); return; }}
                            var el = marker;
                            while (el && el !== window.parent.document.body) {{
                                el = el.parentElement;
                                if (el && el.getAttribute('data-testid') === 'stVerticalBlock') {{
                                    el.style.setProperty('border', '2px solid {border_color}', 'important');
                                    el.style.setProperty('border-radius', '12px', 'important');
                                    el.style.setProperty('padding', '10px 16px', 'important');
                                    el.style.setProperty('margin-bottom', '12px', 'important');
                                    el.style.setProperty('background', '{bg_color}', 'important');
                                    break;
                                }}
                            }}
                        }}
                        applyBorder();
                    }})();
                    </script>""",
                    height=0,
                )

# ── Upload paper page ───────────────────────────────────────────────────
if page in ("Dashboard", "Upload paper"):
    card_open("Upload a research paper", "upload")

    # Guest notice
    if st.session_state.get("auth_status") == "guest":
        st.info(
            "You're browsing as a guest — you can analyze papers but they won't be saved. "
            "Sign in to save up to 3 papers to your account.",
            icon="ℹ️",
        )
    else:
        # Show remaining slots for logged-in users
        _saved_count = len(list_papers(get_current_user_id()))
        _remaining = MAX_SAVED_PAPERS - _saved_count
        if _remaining <= 0:
            st.warning(
                f"📄 You've used all {MAX_SAVED_PAPERS} paper slots. "
                "Remove a paper from History to upload a new one.",
            )
        else:
            st.caption(f"📄 {_saved_count}/{MAX_SAVED_PAPERS} papers saved — {_remaining} slot(s) remaining.")

    uploaded_file = st.file_uploader(
        "Upload PDF or DOCX", type=["pdf", "docx"], label_visibility="collapsed"
    )
    card_close()
    if uploaded_file:
        process_uploaded_file(uploaded_file)
        if st.session_state.get("processed_file_name") == uploaded_file.name:
            st.success("Document processed and embedded successfully.")

    _reject = st.session_state.get("pending_reject")
    if uploaded_file and _reject and _reject["file_name"] == uploaded_file.name:
        card_open("", "")
        st.error(
            f"This doesn't look like a research paper (confidence score: "
            f"{_reject['score']}/100). Please upload a research paper — one "
            "with an abstract, sections like Introduction/Methodology/"
            "Conclusion, and a reference list."
        )
        with st.expander("Why was this flagged?"):
            for reason in _reject["reasons"]:
                st.write(f"- {reason}")
        if st.button("Analyze anyway", key=f"force_analyze_btn_{uploaded_file.name}"):
            st.session_state[f"force_analyze_{uploaded_file.name}"] = True
            st.rerun()
        card_close()

# ── Dashboard page ───────────────────────────────────────────────────────
if page == "Dashboard":
    if require_document():
        cleaned_text = st.session_state.cleaned_text
        chunks = st.session_state.chunks
        parsed = st.session_state.parsed
        section_chunks = st.session_state.section_chunks

        card_open("Document overview", "list")
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            metric_tile("Characters", f"{len(cleaned_text):,}", icon="file-text", color="accent")
        with m2:
            metric_tile("Chunks", len(chunks), icon="grid", color="success")
        with m3:
            metric_tile("Sections found", len(parsed["sections"]), icon="layers", color="pro")
        with m4:
            metric_tile("Section-aware chunks", len(section_chunks), icon="layers", color="warning")
        with m5:
            metric_tile("References", len(parsed["references"]), icon="quote", color="teal")
        card_close()

        col_preview, col_structure = st.columns([1.2, 1])
        with col_preview:
            card_open("Extracted text preview", "file-text")
            st.text_area("Preview", cleaned_text[:5000], height=260, label_visibility="collapsed")
            render_audio_player(
                text=cleaned_text,
                lang_code="en",
                label="Listen to this paper",
                player_id="paper",
                session_key=f"audio_paper_{st.session_state.processed_file_name}",
            )
            card_close()

        with col_structure:
            card_open("Detected structure", "grid")
            for i, section_name in enumerate(parsed["sections"].keys(), start=1):
                structure_row(section_name.title(), i)
            card_close()

            card_open("Paper details", "help")
            json_block({
                "title": parsed["title"],
                "abstract_preview": parsed["abstract"][:300],
                "num_references": len(parsed["references"]),
            })
            card_close()

# ── Q&A (RAG) page ──────────────────────────────────────────────────────
if page == "Q&A (RAG)":
    if require_document():
        parsed = st.session_state.parsed
        store = st.session_state.vector_store
        lang_code = st.session_state.get("lang_code", "en")

        card_open(
            "Ask a question about this paper",
            "message",
            caption="Try: 'What is the novelty of this paper?' or 'What is the future work?'",
        )
        query = st.text_input("Your question", label_visibility="collapsed", placeholder="What is the future work?")
        top_k = st.slider("Number of chunks to retrieve", min_value=1, max_value=10, value=5)

        if query:
            with st.spinner("Searching..."):
                expanded_query = _expand_query(query)
                effective_k = max(top_k, 4)
                query_vector = embed_query(expanded_query)
                results = store.search(query_vector, top_k=effective_k)

            if not results:
                st.warning("No relevant chunks found.")
            else:
                with st.spinner("Synthesizing answer..."):
                    try:
                        answer = answer_question(query, results, language=lang_code)
                        st.markdown("**Answer**")
                        st.write(answer)
                    except Exception as e:
                        if _is_quota_error(e):
                            _quota_warning(e)
                        else:
                            st.error(f"Could not generate an answer: {e}")

                with st.expander("Show retrieved excerpts (source material)"):
                    for i, r in enumerate(results, start=1):
                        st.markdown(
                            f"**Result {i}** — section: `{r['section']}` — similarity: `{r['score']:.3f}`"
                        )
                        st.text_area(
                            f"result_{i}",
                            r["text"],
                            height=150,
                            label_visibility="collapsed",
                        )
        card_close()

# ── AI analysis page ─────────────────────────────────────────────────────
if page == "AI analysis":
    if "processed_file_name" not in st.session_state:
        card_open("", "")
        empty_state(
            "sparkles",
            "No paper loaded yet",
            "Upload a research paper to generate an AI-powered summary, "
            "key topics, research gaps, likely reviewer questions, and "
            "citation support — all grounded in the paper's own text.",
        )
        _, btn_col, _ = st.columns([1, 1, 1])
        with btn_col:
            if st.button("Upload paper", type="primary", use_container_width=True, key="ai_empty_upload_btn"):
                st.session_state.nav_page = "Upload paper"
                st.rerun()
        card_close()

        card_open("What you'll get", "grid", caption="These panels populate automatically once a paper is processed.")
        f1, f2, f3 = st.columns(3)
        with f1:
            feature_preview_card(
                "file-text", "Paper Summary",
                "A concise, plain-language digest of the paper's core contribution.",
                color="accent", badge="Supported",
            )
        with f2:
            feature_preview_card(
                "layers", "Key Topics",
                "The main themes and technical concepts the paper covers.",
                color="pro", badge="Supported",
            )
        with f3:
            feature_preview_card(
                "alert-triangle", "Research Gaps",
                "Limitations and open problems the authors call out or imply.",
                color="warning", badge="Supported",
            )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        f4, f5, f6 = st.columns(3)
        with f4:
            feature_preview_card(
                "help-circle-q", "Generated Questions",
                "Likely reviewer or exam questions drawn from the paper's content.",
                color="teal", badge="Supported",
            )
        with f5:
            feature_preview_card(
                "quote", "Citation Support",
                "Verified in-text citations cross-checked against source references.",
                color="success",
            )
        with f6:
            feature_preview_card(
                "gauge", "AI Readiness Score",
                "How well-structured the paper is for automated analysis.",
                color="accent",
            )
        card_close()

        card_open("Analysis history", "clock", caption="Papers you've previously run through AI analysis.")
        history_table(
            rows=[],
            columns=["Paper", "Date", "Status", "Novelty score"],
            empty_message="No analyses yet — your processed papers will appear here.",
        )
        card_close()

    else:
        parsed = st.session_state.parsed
        store = st.session_state.vector_store
        lang_code = st.session_state.get("lang_code", "en")
        file_hash = st.query_params.get("paper", "")
        user_id = st.session_state.get("user_id", "")
        is_guest = st.session_state.get("auth_status") == "guest"

        card_open(
            "Full AI analysis",
            "sparkles",
            caption="Analysis runs inline and finishes before the page continues.",
        )
        word_limit = st.slider("Conclusion summary word limit", min_value=50, max_value=300, value=120)

        # Previously-saved result (if any) — used only to decide the
        # button label ("Generate" vs "Re-run"). No background polling:
        # analysis now runs synchronously, so there's no in-between state
        # to track.
        saved_status_row = None if is_guest else get_analysis_status(user_id, file_hash)
        has_saved_result = bool(saved_status_row and saved_status_row.get("result"))

        # Restore a previously-completed analysis after a refresh, even if
        # the disk cache (loaded near the top of this file) missed it.
        if has_saved_result and "last_analysis" not in st.session_state:
            st.session_state.last_analysis = saved_status_row["result"]
            st.session_state.last_analysis_lang = saved_status_row.get("lang_code", "en")
            st.session_state.last_analysis_hash = file_hash

        btn_label = "Re-run AI analysis" if has_saved_result else "Generate AI analysis"
        if st.button(btn_label, type="primary", key="ai_generate_btn"):
            # Clear any previous results first — if THIS attempt fails, we
            # don't want stale results from an earlier run rendering below
            # the error, which makes the error look bogus/contradictory.
            st.session_state.pop("last_analysis", None)
            st.session_state.pop("last_analysis_lang", None)
            st.session_state.pop("last_analysis_hash", None)
            st.session_state.pop("audio_analysis", None)

            with st.spinner("Brewing insights from your paper..."):
                try:
                    from src.llm_pipeline import analyze_paper
                    novelty_chunks = store.search(embed_query("novelty original contribution of this paper"), top_k=5)
                    gap_chunks = store.search(embed_query("research gap limitation prior work"), top_k=5)
                    future_chunks = store.search(embed_query("future work directions recommendations"), top_k=5)
                    general_chunks = [
                        {"section": "title", "text": parsed["title"]},
                        {"section": "abstract", "text": parsed["abstract"][:1000]},
                    ]
                    analysis = analyze_paper(
                        {"novelty": novelty_chunks, "research_gap": gap_chunks,
                         "future_work": future_chunks, "general": general_chunks},
                        language=lang_code, word_limit=word_limit,
                    )
                    st.session_state.last_analysis = analysis
                    st.session_state.last_analysis_lang = lang_code
                    st.session_state.last_analysis_hash = file_hash
                    st.session_state.pop("audio_analysis", None)

                    if not is_guest:
                        # Persist for History / page-refresh restore. This
                        # runs in the main Streamlit thread — no threading
                        # involved, so no ScriptRunContext issues, no stuck
                        # 'pending' rows possible.
                        try:
                            from src.background_analysis import _upsert_row
                            from src.supabase_client import get_supabase
                            _upsert_row(
                                get_supabase(), user_id, file_hash,
                                status="done", result=analysis,
                                lang_code=lang_code,
                                file_name=st.session_state.get("processed_file_name", ""),
                            )
                        except Exception:
                            pass  # non-fatal — result still shows this session
                        try:
                            from src.paper_cache import save_analysis
                            save_analysis(file_hash, analysis, lang_code)
                        except Exception:
                            pass

                except Exception as e:
                    if _is_quota_error(e):
                        _quota_warning(e)
                    else:
                        st.error(f"Analysis failed: {e}")

        card_close()


        if "last_analysis" in st.session_state:
            analysis = st.session_state.last_analysis
            paper_title = parsed.get("title") or "Research Paper Analysis"

            card_open("AI analysis results", "sparkles")

            key_points = analysis.get("key_points", [])
            if key_points:
                st.markdown("**Key points**")
                for p in key_points:
                    st.markdown(f"- {p}")
                st.markdown("<br>", unsafe_allow_html=True)

            r1, r2, r3 = st.columns(3)
            with r1:
                result_card("success", "Novelty", analysis.get("novelty", ""))
            with r2:
                result_card("warning", "Research gap", analysis.get("research_gap", ""))
            with r3:
                result_card("pro", "Future work", analysis.get("future_work", ""))

            result_card("accent", "Conclusion summary", analysis.get("conclusion_summary", ""))

            st.markdown("**Core technologies**")
            tag_pills(analysis.get("core_tech_tags", []))

            with st.expander("Raw JSON"):
                json_block(analysis)
            card_close()

            analysis_audio_text = "\n\n".join([
                "Key Points: " + ". ".join(analysis.get("key_points", [])),
                "Novelty: " + analysis.get("novelty", ""),
                "Research Gap: " + analysis.get("research_gap", ""),
                "Future Work: " + analysis.get("future_work", ""),
                "Conclusion: " + analysis.get("conclusion_summary", ""),
            ])
            render_audio_player(
                text=analysis_audio_text,
                lang_code=st.session_state.get("last_analysis_lang", "en"),
                label="Listen to analysis",
                player_id="analysis",
                session_key="audio_analysis",
            )

            card_open("Export report", "download")
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                docx_buffer = generate_docx_report(analysis, paper_title)
                st.download_button(
                    label="Download as DOCX",
                    data=docx_buffer,
                    file_name=f"{paper_title[:50].strip().replace(' ', '_')}_analysis.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            with exp_col2:
                pdf_buffer = generate_pdf_report(analysis, paper_title)
                st.download_button(
                    label="Download as PDF",
                    data=pdf_buffer,
                    file_name=f"{paper_title[:50].strip().replace(' ', '_')}_analysis.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            card_close()

# ── Compare page ─────────────────────────────────────────────────────────
# No require_document() gate here — Compare works off saved History, not
# the currently-loaded paper. Guest handling (no saved papers) lives
# inside render_compare_page() itself, since the exact "log back in"
# behavior is specific to that page.
if page == "Compare":
    render_compare_page()

# ── Citation graph page ─────────────────────────────────────────────────
if page == "Citation graph":
    if require_document():
        parsed = st.session_state.parsed

        graph = build_citation_graph(parsed)
        for w in graph["warnings"]:
            st.warning(w)

        if len(graph["nodes"]) <= 1:
            st.info("No citations could be matched in this paper yet.")
        else:
            try:
                from pyvis.network import Network

                c = theme_colors()
                section_colors = {}
                palette = ["#6C8EF5", "#1D9E75", "#D85A30", "#D4537E", "#BA7517", "#7F77DD"]

                def _color_for_section(section_name):
                    if section_name not in section_colors:
                        section_colors[section_name] = palette[len(section_colors) % len(palette)]
                    return section_colors[section_name]

                def _truncate_label(label, max_chars=18):
                    return label if len(label) <= max_chars else label[: max_chars - 1] + "…"

                num_ref_nodes = max(len(graph["nodes"]) - 1, 1)
                canvas_height = min(900, max(560, 60 + num_ref_nodes * 34))

                net = Network(
                    height=f"{canvas_height}px",
                    width="100%",
                    bgcolor=c["surface"],
                    font_color=c["text_primary"],
                    directed=True,
                    cdn_resources="in_line",  # embed JS/CSS so it works offline too
                )
                net.barnes_hut(
                    gravity=-6000, central_gravity=0.3,
                    spring_length=180, spring_strength=0.04,
                )

                for n in graph["nodes"]:
                    if n["type"] == "paper":
                        net.add_node(
                            n["id"],
                            label=_truncate_label(n["label"], max_chars=20),
                            title=n["label"],
                            size=30,
                            color="#2C2C2A",
                            shape="dot",
                            font={"size": 14, "color": c["text_primary"]},
                        )
                    else:
                        weight = n["times_cited"] or 0
                        # Full reference text for the hover tooltip (falls
                        # back to the short label if raw_text is missing,
                        # e.g. on graphs built before this field existed).
                        full_text = n.get("raw_text") or n["label"]
                        tooltip = f"{full_text} — cited {weight}x"
                        node_url = n.get("url")
                        net.add_node(
                            n["id"],
                            label=_truncate_label(n["label"]),
                            title=tooltip,
                            size=10 + min(weight, 6) * 2,
                            color="#378ADD",
                            shape="dot",
                            font={"size": 11, "color": c["text_primary"]},
                            # Stashed on the node's own data so we can wire
                            # click-to-open below, only for references that
                            # actually have a detected URL/DOI.
                            url=node_url or "",
                        )

                for e in graph["edges"]:
                    if e["weight"] > 0:
                        net.add_edge(
                            e["source"], e["target"],
                            color=_color_for_section(e["section"]),
                        )

                graph_html = net.generate_html(notebook=False)

                # pyvis has no built-in "open URL on click" option, so we
                # append a small script that reads the `url` field we
                # stashed on each node (see net.add_node(..., url=...)
                # above) and opens it in a new tab on double-click. Nodes
                # with no detected URL (url == "") intentionally do
                # nothing rather than guessing a link.
                click_script = """
                <script type="text/javascript">
                  network.on("doubleClick", function (params) {
                    if (params.nodes.length > 0) {
                      var nodeId = params.nodes[0];
                      var nodeData = network.body.data.nodes.get(nodeId);
                      if (nodeData && nodeData.url) {
                        window.open(nodeData.url, "_blank");
                      }
                    }
                  });
                </script>
                """
                graph_html = graph_html.replace("</body>", click_script + "</body>")

                st.components.v1.html(graph_html, height=canvas_height + 20, scrolling=True)
                st.caption(
                    "Hover a node to see its full reference. Double-click a node to open its "
                    "source link (if one was found in the reference). Drag nodes to spread them out further."
                )

                if section_colors:
                    legend_html = "".join(
                        f'<span style="display:inline-flex;align-items:center;gap:6px;'
                        f'margin-right:16px;font-size:13px;">'
                        f'<span style="width:10px;height:10px;border-radius:50%;'
                        f'background:{color};display:inline-block;"></span>{section}</span>'
                        for section, color in section_colors.items()
                    )
                    st.caption("Edge colors by section:")
                    st.markdown(
                        f'<div style="margin-top:-8px;">{legend_html}</div>',
                        unsafe_allow_html=True,
                    )
            except ImportError:
                st.warning(
                    "The interactive graph view needs the `pyvis` package "
                    "(add it to requirements.txt: `pyvis`). Showing a plain "
                    "ranked list instead."
                )
                top_refs = most_cited_references(graph, top_n=10)
                for ref in top_refs:
                    st.write(f"- {ref['label']} — cited {ref['times_cited']}x")

            import plotly.graph_objects as go
            from src.citation_insights import (
                citations_per_section,
                citation_frequency_histogram,
                citation_density_by_section,
                self_citation_ratio,
                orphan_citations,
            )

            c = theme_colors()

            def _themed_bar(x_vals, y_vals, color, y_title=None):
                fig = go.Figure(go.Bar(x=x_vals, y=y_vals, marker_color=color))
                fig.update_layout(
                    paper_bgcolor=c["surface"], plot_bgcolor=c["surface"],
                    font_color=c["text_primary"], margin=dict(l=10, r=10, t=10, b=10),
                    height=280,
                    xaxis=dict(gridcolor=c["border"], color=c["text_primary"]),
                    yaxis=dict(gridcolor=c["border"], color=c["text_primary"], title=y_title),
                )
                return fig

            # ── Row 1: Reference publication years | Citation count per section
            row1_col1, row1_col2 = st.columns(2)

            with row1_col1:
                card_open(
                    "Reference publication years",
                    "calendar",
                    caption="How recent the literature this paper cites actually is.",
                )
                year_dist = reference_year_distribution(graph)
                if year_dist:
                    fig = _themed_bar(list(year_dist.keys()), list(year_dist.values()), "#378ADD")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    if "unknown" in year_dist:
                        st.caption(
                            f"{year_dist['unknown']} reference(s) had no detectable publication year."
                        )
                else:
                    st.caption("No reference years could be detected.")
                card_close()

            with row1_col2:
                card_open(
                    "Citation count per section",
                    "bar-chart",
                    caption="How many in-text citations appear in each section.",
                )
                sec_counts = citations_per_section(graph)
                if sec_counts:
                    fig = _themed_bar(list(sec_counts.keys()), list(sec_counts.values()), "#1D9E75")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("No section-tagged citations were found.")
                card_close()

            # ── Row 2: In-text citation frequency | Citation density by section
            st.markdown("<br>", unsafe_allow_html=True)
            row2_col1, row2_col2 = st.columns(2)

            with row2_col1:
                card_open(
                    "In-text citation frequency",
                    "hash",
                    caption="How many references get cited once vs. repeatedly.",
                )
                freq = citation_frequency_histogram(graph)
                if freq:
                    fig = _themed_bar(list(freq.keys()), list(freq.values()), "#D4537E")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("No citation frequency data available.")
                card_close()

            with row2_col2:
                card_open(
                    "Citation density by section",
                    "activity",
                    caption="Citations per 1,000 words — flags under-cited sections.",
                )
                section_word_counts = {
                    name: len(text.split())
                    for name, text in (parsed.get("sections") or {}).items()
                }
                density_rows = citation_density_by_section(graph, section_word_counts)
                if density_rows:
                    fig = _themed_bar(
                        [r["section"] for r in density_rows],
                        [r["density"] for r in density_rows],
                        "#BA7517",
                        y_title="citations / 1k words",
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("Not enough section text to compute density.")
                card_close()

            # ── Row 3: Self-citation vs external | Isolated/orphan citations
            st.markdown("<br>", unsafe_allow_html=True)
            row3_col1, row3_col2 = st.columns(2)

            with row3_col1:
                card_open(
                    "Self-citation vs external",
                    "users",
                    caption="Share of citations pointing to the paper's own prior work.",
                )
                ratio = self_citation_ratio(graph, parsed.get("authors"))
                if ratio is None:
                    st.caption(
                        "Not available yet — the parser doesn't currently extract the "
                        "paper's author list, which is needed to detect self-citations."
                    )
                else:
                    fig = go.Figure(go.Pie(
                        labels=["Self-citations", "External"],
                        values=[ratio["self"], ratio["external"]],
                        marker_colors=["#7F77DD", "#378ADD"],
                        hole=0.5,
                    ))
                    fig.update_layout(
                        paper_bgcolor=c["surface"], font_color=c["text_primary"],
                        margin=dict(l=10, r=10, t=10, b=10), height=280,
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    st.caption(f"{ratio['self_pct']}% of citations are self-citations.")
                card_close()

            with row3_col2:
                card_open(
                    "Isolated / orphan citations",
                    "alert-triangle",
                    caption="References never cited in text, and in-text markers with no matching reference.",
                )
                orphans = orphan_citations(graph)
                uncited = orphans["uncited_references"]
                unmatched = orphans["unmatched_markers"]

                if not uncited and not unmatched["numeric"] and not unmatched["author_year"]:
                    st.caption("No orphan citations found — every reference is cited, and every in-text marker resolved.")
                else:
                    if uncited:
                        st.markdown(f"**{len(uncited)} reference(s) never cited in text:**")
                        for ref in uncited:
                            year_part = f" ({ref['year']})" if ref.get("year") else ""
                            st.write(f"- {ref['label']}{year_part}")
                    else:
                        st.caption("Every reference in the list was cited at least once.")

                    total_unmatched = len(unmatched["numeric"]) + len(unmatched["author_year"])
                    if total_unmatched:
                        st.markdown(f"**{total_unmatched} in-text marker(s) with no matching reference:**")
                        if unmatched["numeric"]:
                            st.write("- Numeric: " + ", ".join(f"[{n}]" for n in unmatched["numeric"]))
                        if unmatched["author_year"]:
                            st.write("- Author-year: " + ", ".join(unmatched["author_year"]))
                    else:
                        st.caption("Every in-text citation marker matched a reference.")
                card_close()

# ── Related Papers page ──────────────────────────────────────────────────
if page == "Related Papers":
    render_related_papers_page()

# ── Settings page ────────────────────────────────────────────────────────
if page == "Settings":
    render_dark_mode_toggle()

    card_open("Output language", "settings")
    st.caption("Applies to Q&A answers and the full AI analysis.")
    lang_choice = st.radio(
        "Output language",
        ["English", "বাংলা (Bangla)"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state.get("lang_code", "en") == "en" else 1,
    )
    st.session_state.lang_code = "bn" if lang_choice and "বাংলা" in lang_choice else "en"
    card_close()
    #completed.
    #need to review this
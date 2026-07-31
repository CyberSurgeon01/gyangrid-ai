from src.llm_pipeline import analyze_paper, answer_question, _expand_query, classify_is_research_paper
from src.paper_validator import is_research_paper
from src.report_export import generate_docx_report, generate_pdf_report
from src.citation_graph import build_citation_graph, most_cited_references, reference_year_distribution
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
)

st.set_page_config(page_title="GyanGrid AI", layout="wide")

# ── Restore dark-mode preference after a page refresh ───────────────────
# st.session_state resets on refresh (new browser session), but
# st.query_params survives it — same trick used below for the loaded
# paper. Without this, the toggle "wins" only within the current
# session and silently falls back to light on the next refresh.
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = st.query_params.get("theme") == "dark"

inject_base_css()

# ── Auth gate: login/sign-up is the landing page ────────────────────────
# Guests can proceed without an account (auth_status = "guest"), but
# nothing they upload gets persisted — see save_paper/load_paper calls
# below, which should be made conditional on auth_status == "user" once
# real per-user storage (e.g. Supabase) is wired in.
if "auth_status" not in st.session_state:
    st.session_state.auth_status = None

if st.session_state.auth_status is None:
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
if "processed_file_name" not in st.session_state and "paper" in st.query_params:
    _cached = load_paper(st.query_params["paper"])
    if _cached:
        _data, _store = _cached
        st.session_state.processed_file_name = _data["file_name"]
        st.session_state.cleaned_text = _data["cleaned_text"]
        st.session_state.chunks = _data["chunks"]
        st.session_state.parsed = _data["parsed"]
        st.session_state.section_chunks = _data["section_chunks"]
        st.session_state.vector_store = _store

        _cached_analysis = load_analysis(st.query_params["paper"])
        if _cached_analysis:
            st.session_state.last_analysis = _cached_analysis["analysis"]
            st.session_state.last_analysis_lang = _cached_analysis["lang_code"]

_HAS_PAPER = "processed_file_name" in st.session_state
_PAGE_COPY = {
    "Dashboard": ("Dashboard", "Overview of your uploaded paper's structure and extracted content."),
    "Upload paper": ("Upload paper", "Upload a research paper and prepare it for AI analysis."),
    "Q&A (RAG)": ("Q&A (RAG)", "Ask grounded questions and get answers sourced directly from the paper."),
    "AI analysis": ("AI Analysis", "Upload a research paper to generate summaries, insights, questions, and citation support."),
    "Citation graph": ("Citation graph", "Visualize how this paper's citations map to its reference list."),
    "Settings": ("Settings", "Configure output language and workspace preferences."),
}
_title, _subtitle = _PAGE_COPY.get(page, ("GyanGrid AI", ""))
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


def process_uploaded_file(uploaded_file):
    """Runs the load -> clean -> parse -> chunk -> embed pipeline once per
    new file, or restores it from disk cache if this exact file was
    processed before (this is what survives a page refresh, via the hash
    stored in st.query_params)."""
    if st.session_state.get("processed_file_name") == uploaded_file.name:
        return

    file_bytes = uploaded_file.getvalue()  # safe: doesn't disturb the read position load_document() uses
    file_hash = hash_file_bytes(file_bytes)

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


# ── Upload paper page ───────────────────────────────────────────────────
if page in ("Dashboard", "Upload paper"):
    card_open("Upload a research paper", "upload")
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
            st.json({
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

        card_open(
            "Full AI analysis",
            "sparkles",
            caption="Generates novelty, research gap, future work, and a conclusion summary.",
        )
        word_limit = st.slider("Conclusion summary word limit", min_value=50, max_value=300, value=120)

        if st.button("Generate AI analysis", type="primary"):
            with st.spinner("Retrieving relevant chunks..."):
                novelty_chunks = store.search(
                    embed_query("novelty original contribution of this paper"), top_k=5
                )
                gap_chunks = store.search(
                    embed_query("research gap limitation prior work"), top_k=5
                )
                future_chunks = store.search(
                    embed_query("future work directions recommendations"), top_k=5
                )
                general_chunks = [
                    {"section": "title", "text": parsed["title"]},
                    {"section": "abstract", "text": parsed["abstract"][:1000]},
                ]
                chunks_by_type = {
                    "novelty": novelty_chunks,
                    "research_gap": gap_chunks,
                    "future_work": future_chunks,
                    "general": general_chunks,
                }

            with st.spinner("Brewing insights from your paper..."):
                try:
                    analysis = analyze_paper(
                        chunks_by_type, language=lang_code, word_limit=word_limit
                    )
                    st.session_state.last_analysis = analysis
                    st.session_state.last_analysis_lang = lang_code
                    st.session_state.pop("audio_analysis", None)

                    # Cache the analysis too, so it survives a refresh
                    # alongside the paper itself (keyed off the same hash
                    # that's already sitting in st.query_params).
                    if "paper" in st.query_params:
                        save_analysis(st.query_params["paper"], analysis, lang_code)
                except Exception as e:
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
                st.json(analysis)
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
                from streamlit_agraph import agraph, Node, Edge, Config

                section_colors = {}
                palette = ["#6C8EF5", "#1D9E75", "#D85A30", "#D4537E", "#BA7517", "#7F77DD"]

                def _color_for_section(section_name):
                    if section_name not in section_colors:
                        section_colors[section_name] = palette[len(section_colors) % len(palette)]
                    return section_colors[section_name]

                def _truncate_label(label, max_chars=18):
                    return label if len(label) <= max_chars else label[: max_chars - 1] + "…"

                agraph_nodes = []
                for n in graph["nodes"]:
                    if n["type"] == "paper":
                        agraph_nodes.append(
                            Node(
                                id=n["id"],
                                label=_truncate_label(n["label"], max_chars=20),
                                title=n["label"],
                                size=30,
                                color="#2C2C2A",
                                shape="dot",
                                font={"size": 14, "color": "#ffffff", "strokeWidth": 0},
                            )
                        )
                    else:
                        weight = n["times_cited"] or 0
                        agraph_nodes.append(
                            Node(
                                id=n["id"],
                                label=_truncate_label(n["label"]),
                                title=f"{n['label']} — cited {weight}x",
                                size=10 + min(weight, 6) * 2,
                                color="#378ADD",
                                shape="dot",
                                font={"size": 11, "color": "#1a1d24", "strokeWidth": 3, "strokeColor": "#ffffff"},
                            )
                        )

                agraph_edges = [
                    Edge(
                        source=e["source"],
                        target=e["target"],
                        color=_color_for_section(e["section"]),
                    )
                    for e in graph["edges"]
                    if e["weight"] > 0
                ]

                num_ref_nodes = max(len(agraph_nodes) - 1, 1)
                canvas_height = min(900, max(560, 60 + num_ref_nodes * 34))

                config = Config(
                    width="100%",
                    height=canvas_height,
                    directed=True,
                    physics=True,
                    hierarchical=False,
                    collapsible=False,
                    nodeHighlightBehavior=True,
                    highlightColor="#F2A623",
                    node={"labelProperty": "label"},
                    link={"renderLabel": False},
                    d3={"gravity": -600, "linkLength": 180, "linkStrength": 0.4},
                )
                agraph(nodes=agraph_nodes, edges=agraph_edges, config=config)
                st.caption("Hover a node to see its full title. Drag nodes to spread them out further.")

                if section_colors:
                    st.caption(
                        "Edge colors by section: "
                        + ", ".join(f"{sec}" for sec in section_colors.keys())
                    )
            except ImportError:
                st.warning(
                    "The interactive graph view needs the `streamlit-agraph` package "
                    "(add it to requirements.txt: `streamlit-agraph`). Showing a plain "
                    "ranked list instead."
                )
                top_refs = most_cited_references(graph, top_n=10)
                for ref in top_refs:
                    st.write(f"- {ref['label']} — cited {ref['times_cited']}x")

            st.markdown("<br>", unsafe_allow_html=True)
            card_open(
                "Reference publication years",
                "calendar",
                caption="How recent the literature this paper cites actually is.",
            )
            year_dist = reference_year_distribution(graph)
            if year_dist:
                import pandas as pd

                year_df = pd.DataFrame(
                    {"Year": list(year_dist.keys()), "References": list(year_dist.values())}
                ).set_index("Year")
                st.bar_chart(year_df, color="#378ADD")
                if "unknown" in year_dist:
                    st.caption(
                        f"{year_dist['unknown']} reference(s) had no detectable publication year."
                    )
            else:
                st.caption("No reference years could be detected.")
            card_close()

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
from src.llm_pipeline import analyze_paper, answer_question, _expand_query
from src.report_export import generate_docx_report, generate_pdf_report
import streamlit as st
from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_text, chunk_sections
from src.parser import parse_document
from src.embeddings import embed_chunks, embed_query
from src.vector_store import VectorStore
from src.audio_player import render_audio_player
from src.ui_theme import (
    inject_base_css,
    render_topbar,
    render_sidebar_nav,
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
inject_base_css()
page = render_sidebar_nav(default="Dashboard")
render_topbar()

_HAS_PAPER = "processed_file_name" in st.session_state
_PAGE_COPY = {
    "Dashboard": ("Dashboard", "Overview of your uploaded paper's structure and extracted content."),
    "Upload paper": ("Upload paper", "Upload a research paper and prepare it for AI analysis."),
    "Q&A (RAG)": ("Q&A (RAG)", "Ask grounded questions and get answers sourced directly from the paper."),
    "AI analysis": ("AI Analysis", "Upload a research paper to generate summaries, insights, questions, and citation support."),
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
    """Runs the load -> clean -> parse -> chunk -> embed pipeline once per new file."""
    if st.session_state.get("processed_file_name") == uploaded_file.name:
        return
    with st.spinner("Reading and preparing document..."):
        raw_text = load_document(uploaded_file)
        cleaned_text = clean_text(raw_text)
        chunks = chunk_text(cleaned_text)
        parsed = parse_document(cleaned_text)
        section_chunks = chunk_sections(parsed)

    with st.spinner("Generating embeddings (first run may take a minute to load the model)..."):
        embedded_chunks = embed_chunks(section_chunks)
        store = VectorStore(dimension=384)
        store.add_chunks(embedded_chunks)

    st.session_state.processed_file_name = uploaded_file.name
    st.session_state.cleaned_text = cleaned_text
    st.session_state.chunks = chunks
    st.session_state.parsed = parsed
    st.session_state.section_chunks = section_chunks
    st.session_state.vector_store = store
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
        st.success("Document processed and embedded successfully.")

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
                color="accent",
            )
        with f2:
            feature_preview_card(
                "layers", "Key Topics",
                "The main themes and technical concepts the paper covers.",
                color="pro",
            )
        with f3:
            feature_preview_card(
                "alert-triangle", "Research Gaps",
                "Limitations and open problems the authors call out or imply.",
                color="warning",
            )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        f4, f5, f6 = st.columns(3)
        with f4:
            feature_preview_card(
                "help-circle-q", "Generated Questions",
                "Likely reviewer or exam questions drawn from the paper's content.",
                color="teal",
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

# ── Settings page ────────────────────────────────────────────────────────
if page == "Settings":
    card_open("Output language", "settings")
    st.caption("Applies to Q&A answers and the full AI analysis.")
    lang_choice = st.radio(
        "Output language",
        ["English", "বাংলা (Bangla)"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state.get("lang_code", "en") == "en" else 1,
    )
    st.session_state.lang_code = "bn" if "বাংলা" in lang_choice else "en"
    card_close()
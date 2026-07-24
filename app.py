from src.llm_pipeline import analyze_paper, answer_question, _expand_query
from src.report_export import generate_docx_report, generate_pdf_report
import streamlit as st
from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_text, chunk_sections
from src.parser import parse_document
from src.embeddings import embed_chunks, embed_query
from src.vector_store import VectorStore

st.set_page_config(page_title="GyanGrid AI", layout="wide")

st.title("GyanGrid AI")
st.write("Upload a research paper and prepare it for AI analysis.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

if uploaded_file:
    # Only reprocess if a new file was uploaded (avoid re-embedding on every rerun)
    if "processed_file_name" not in st.session_state or st.session_state.processed_file_name != uploaded_file.name:
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

    cleaned_text = st.session_state.cleaned_text
    chunks = st.session_state.chunks
    parsed = st.session_state.parsed
    section_chunks = st.session_state.section_chunks
    store = st.session_state.vector_store

    st.success("Document processed and embedded successfully.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Characters", len(cleaned_text))
    col2.metric("Chunks", len(chunks))
    col3.metric("Sections Found", len(parsed["sections"]))
    col4.metric("Section-Aware Chunks", len(section_chunks))

    st.subheader("Extracted Text Preview")
    st.text_area("Preview", cleaned_text[:5000], height=300)

    st.subheader("Detected Structure")
    st.json({
        "title": parsed["title"],
        "abstract_preview": parsed["abstract"][:300],
        "sections_found": list(parsed["sections"].keys()),
        "num_references": len(parsed["references"]),
    })

    st.divider()

    # ── Shared language selector (used by both RAG Q&A and Full Analysis) ──
    analysis_lang = st.radio(
        "Output language",
        ["English", "বাংলা (Bangla)"],
        horizontal=True,
        key="lang_radio",
    )
    lang_code = "bn" if "বাংলা" in analysis_lang else "en"

    # ── RAG Q&A ────────────────────────────────────────────────────────────
    st.subheader("Ask a question about this paper (RAG search)")
    st.caption("Try: 'What is the novelty of this paper?' or 'What is the future work?'")

    query = st.text_input("Your question")
    top_k = st.slider("Number of chunks to retrieve", min_value=1, max_value=10, value=5)

    if query:
        with st.spinner("Searching..."):
            # Expand vague/short queries so FAISS hits the right sections
            expanded_query = _expand_query(query)
            effective_k = max(top_k, 4)  # enforce a minimum of 4 chunks

            query_vector = embed_query(expanded_query)
            results = store.search(query_vector, top_k=effective_k)

        if not results:
            st.warning("No relevant chunks found.")
        else:
            with st.spinner("Synthesizing answer..."):
                try:
                    answer = answer_question(query, results, language=lang_code)
                    st.markdown("### Answer")
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

    st.divider()

    # ── Full AI Analysis ────────────────────────────────────────────────────
    st.subheader("Full AI Analysis")
    st.caption("Generates novelty, research gap, future work, and a conclusion summary using Gemini.")

    word_limit = st.slider("Conclusion summary word limit", min_value=50, max_value=300, value=120)

    if st.button("Generate AI Analysis"):
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
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    if "last_analysis" in st.session_state:
        analysis = st.session_state.last_analysis
        paper_title = parsed.get("title") or "Research Paper Analysis"

        st.markdown(
            """
            <style>
            .analysis-card {
                background-color: #1a1d24;
                border: 1px solid #2d323d;
                border-left: 4px solid #3d8b9e;
                border-radius: 6px;
                padding: 18px 22px;
                margin-bottom: 14px;
            }
            .analysis-card h4 {
                margin-top: 0;
                margin-bottom: 10px;
                color: #6fb8c9;
                font-size: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .analysis-card p, .analysis-card li {
                font-size: 15px;
                line-height: 1.6;
                color: #e6e6e6;
            }
            .tag-pill {
                display: inline-block;
                background-color: #2d323d;
                color: #6fb8c9;
                padding: 4px 12px;
                border-radius: 14px;
                font-size: 13px;
                margin: 3px 6px 3px 0;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        def card(title, body_html):
            st.markdown(
                f'<div class="analysis-card"><h4>{title}</h4>{body_html}</div>',
                unsafe_allow_html=True,
            )

        key_points_html = (
            "<ul>"
            + "".join(f"<li>{p}</li>" for p in analysis.get("key_points", []))
            + "</ul>"
        )
        card("Key Points", key_points_html)
        card("Novelty", f"<p>{analysis.get('novelty', '')}</p>")
        card("Research Gap", f"<p>{analysis.get('research_gap', '')}</p>")
        card("Future Work", f"<p>{analysis.get('future_work', '')}</p>")
        card("Conclusion Summary", f"<p>{analysis.get('conclusion_summary', '')}</p>")

        tags_html = "".join(
            f'<span class="tag-pill">{t}</span>'
            for t in analysis.get("core_tech_tags", [])
        )
        card("Core Technologies", tags_html)

        with st.expander("Raw JSON"):
            st.json(analysis)

        st.markdown("#### Export Report")
        exp_col1, exp_col2 = st.columns(2)

        with exp_col1:
            docx_buffer = generate_docx_report(analysis, paper_title)
            st.download_button(
                label="Download as DOCX",
                data=docx_buffer,
                file_name=f"{paper_title[:50].strip().replace(' ', '_')}_analysis.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        with exp_col2:
            pdf_buffer = generate_pdf_report(analysis, paper_title)
            st.download_button(
                label="Download as PDF",
                data=pdf_buffer,
                file_name=f"{paper_title[:50].strip().replace(' ', '_')}_analysis.pdf",
                mime="application/pdf",
            )
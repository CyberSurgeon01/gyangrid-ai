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
    st.subheader("🔍 Ask a question about this paper (RAG search)")
    st.caption("Try: 'What is the novelty of this paper?' or 'What is the future work?'")

    query = st.text_input("Your question")
    top_k = st.slider("Number of chunks to retrieve", min_value=1, max_value=10, value=3)

    if query:
        with st.spinner("Searching..."):
            query_vector = embed_query(query)
            results = store.search(query_vector, top_k=top_k)

        if not results:
            st.warning("No relevant chunks found.")
        else:
            for i, r in enumerate(results, start=1):
                st.markdown(f"**Result {i}** — section: `{r['section']}` — similarity: `{r['score']:.3f}`")
                st.text_area(f"result_{i}", r["text"], height=150, label_visibility="collapsed")

import streamlit as st

from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_text, chunk_sections
from src.parser import parse_document

st.set_page_config(page_title="GyanGrid AI", layout="wide")

st.title("GyanGrid AI")
st.write("Upload a research paper and prepare it for AI analysis.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

if uploaded_file:
    with st.spinner("Reading and preparing document..."):
        raw_text = load_document(uploaded_file)
        cleaned_text = clean_text(raw_text)
        chunks = chunk_text(cleaned_text)
        parsed = parse_document(cleaned_text)
        section_chunks = chunk_sections(parsed)

    st.success("Document processed successfully.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Characters", len(cleaned_text))
    col2.metric("Chunks", len(chunks))
    col3.metric("Sections Found", len(parsed["sections"]))
    col4.metric("Section-Aware Chunks", len(section_chunks))

    st.subheader("Extracted Text Preview")
    st.text_area("Preview", cleaned_text[:5000], height=300)

    st.subheader("First Chunk Preview")
    if chunks:
        st.text_area("Chunk 1", chunks[0], height=250)

    st.subheader("Detected Structure")
    st.json({
        "title": parsed["title"],
        "abstract_preview": parsed["abstract"][:300],
        "sections_found": list(parsed["sections"].keys()),
        "num_references": len(parsed["references"]),
    })

    st.subheader("Section-Aware Chunks")
    if section_chunks:
        for c in section_chunks[:5]:
            st.markdown(f"**[{c['section']}] chunk {c['chunk_index']}**")
            st.text_area(f"{c['section']}_{c['chunk_index']}", c["text"], height=120, label_visibility="collapsed")
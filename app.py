import streamlit as st

from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_text

st.set_page_config(page_title="GyanGrid AI", layout="wide")

st.title("GyanGrid AI")
st.write("Upload a research paper and prepare it for AI analysis.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

if uploaded_file:
    with st.spinner("Reading and preparing document..."):
        raw_text = load_document(uploaded_file)
        cleaned_text = clean_text(raw_text)
        chunks = chunk_text(cleaned_text)

    st.success("Document processed successfully.")

    col1, col2 = st.columns(2)
    col1.metric("Characters", len(cleaned_text))
    col2.metric("Chunks", len(chunks))

    st.subheader("Extracted Text Preview")
    st.text_area("Preview", cleaned_text[:5000], height=300)

    st.subheader("First Chunk Preview")
    if chunks:
        st.text_area("Chunk 1", chunks[0], height=250)
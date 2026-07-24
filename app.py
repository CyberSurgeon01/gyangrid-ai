import streamlit as st
from src.document_loader import load_document

st.set_page_config(page_title="GyanGrid AI", layout="wide")

st.title("GyanGrid AI")
st.write("Upload a research paper and extract its text.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

if uploaded_file:
    with st.spinner("Extracting text..."):
        text = load_document(uploaded_file)

    st.success("Text extracted successfully!")

    st.subheader("Extracted Text Preview")
    st.text_area("Preview", text[:5000], height=400)

    st.info(f"Total characters extracted: {len(text)}")
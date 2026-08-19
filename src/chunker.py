"""
chunker.py
Section-aware chunking: splits each detected section into ~500-800 token
chunks (word-based approximation) with slight overlap, tagging each chunk
with its source section for RAG retrieval routing.
"""

def _chunk_words(text: str, chunk_size: int = 600, overlap: int = 80) -> list:
    """Split a block of text into overlapping word-count chunks."""
    words = text.split()
    if not words:
        return [] 

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap  # overlap for context continuity

    return chunks


def chunk_text(cleaned_text: str, chunk_size: int = 600, overlap: int = 80) -> list:
    """
    Backwards-compatible flat chunker (no section awareness).
    Kept so existing calls in app.py still work unchanged.
    """
    return _chunk_words(cleaned_text, chunk_size, overlap)


def chunk_sections(parsed_doc: dict, chunk_size: int = 600, overlap: int = 80) -> list:
    """
    Section-aware chunker. Takes the dict returned by parser.parse_document()
    and returns a list of chunk dicts:
        {"section": "introduction", "text": "...", "chunk_index": 0}

    This is what rag_pipeline.py should consume for retrieval routing.
    """
    all_chunks = []

    # Abstract gets its own pass since it's pulled out separately in parser.py
    if parsed_doc.get("abstract"):
        for i, chunk in enumerate(_chunk_words(parsed_doc["abstract"], chunk_size, overlap)):
            all_chunks.append({"section": "abstract", "text": chunk, "chunk_index": i})

    for section_name, section_text in parsed_doc.get("sections", {}).items():
        if not section_text.strip():
            continue
        for i, chunk in enumerate(_chunk_words(section_text, chunk_size, overlap)):
            all_chunks.append({"section": section_name, "text": chunk, "chunk_index": i})

    return all_chunks
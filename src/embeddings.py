"""
embeddings.py
Loads a multilingual sentence-embedding model and converts text chunks
into vector embeddings for use with the RAG vector store.
"""

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "intfloat/multilingual-e5-small"
_model = None


def get_model():
    """Lazily load the embedding model (only once per session)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list) -> list:
    """
    Embed a list of raw strings.
    Note: e5 models expect a "query: " or "passage: " prefix for best results.
    We use "passage: " since we're embedding document chunks, not search queries.
    """
    model = get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(query: str) -> list:
    """Embed a single search query string (uses the 'query: ' prefix)."""
    model = get_model()
    embedding = model.encode([f"query: {query}"], normalize_embeddings=True, show_progress_bar=False)
    return embedding[0].tolist()


def embed_chunks(section_chunks: list) -> list:
    """
    Takes chunk_sections() output ([{section, text, chunk_index}, ...])
    and returns the same list with an added "embedding" key per chunk.
    """
    texts = [c["text"] for c in section_chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(section_chunks, vectors):
        chunk["embedding"] = vector
    return section_chunks

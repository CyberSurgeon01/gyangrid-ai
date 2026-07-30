"""
paper_cache.py
Disk cache so a processed paper survives a page refresh. Streamlit's
st.session_state is tied to the browser session and is wiped on refresh,
but a hash of the uploaded file's bytes can live in st.query_params
(which *does* survive a refresh) and point at a cache folder on disk.
"""

import hashlib
import pickle
from pathlib import Path

from src.vector_store import VectorStore

CACHE_DIR = Path(".cache/papers")


def hash_file_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()[:16]


def _paths(file_hash: str):
    base = CACHE_DIR / file_hash
    return base, base / "data.pkl", base / "store"


def save_paper(file_hash: str, file_name: str, cleaned_text, chunks, parsed, section_chunks, store: VectorStore):
    base, data_path, store_path = _paths(file_hash)
    base.mkdir(parents=True, exist_ok=True)
    with open(data_path, "wb") as f:
        pickle.dump({
            "file_name": file_name,
            "cleaned_text": cleaned_text,
            "chunks": chunks,
            "parsed": parsed,
            "section_chunks": section_chunks,
        }, f)
    store.save(store_path)


def load_paper(file_hash: str):
    """Returns (data_dict, VectorStore) or None if nothing cached / cache
    is corrupt (e.g. a previous save was interrupted)."""
    base, data_path, store_path = _paths(file_hash)
    if not data_path.exists():
        return None
    try:
        with open(data_path, "rb") as f:
            data = pickle.load(f)
        store = VectorStore.load(store_path)
        return data, store
    except (FileNotFoundError, pickle.UnpicklingError, EOFError):
        return None


def save_analysis(file_hash: str, analysis: dict, lang_code: str):
    """Optional: cache the AI analysis result (novelty/gap/future work/etc.)
    alongside the paper data so it also survives a refresh."""
    base, _, _ = _paths(file_hash)
    base.mkdir(parents=True, exist_ok=True)
    with open(base / "analysis.pkl", "wb") as f:
        pickle.dump({"analysis": analysis, "lang_code": lang_code}, f)


def load_analysis(file_hash: str):
    base, _, _ = _paths(file_hash)
    analysis_path = base / "analysis.pkl"
    if not analysis_path.exists():
        return None
    try:
        with open(analysis_path, "rb") as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, EOFError):
        return None
"""
src/background_analysis.py

Runs the Gemini AI analysis in a background thread so the user can
navigate to other pages while it completes. Progress and results are
stored in the Supabase `analyses` table, which acts as the shared
message bus between the thread and the Streamlit UI.

Flow
----
1. UI calls start_analysis() → inserts a 'pending' row, spawns a thread.
2. Thread calls _run_analysis() → updates row to 'running', runs Gemini,
   updates row to 'done' (with result) or 'error' (with error_msg).
3. UI calls get_analysis_status() on every rerun to poll the row and
   render the appropriate state (spinner / results / error).

Thread safety
-------------
The Supabase client is re-created inside the thread (get_supabase() is
cached per *process*, but supabase-py's PostgREST client is not
thread-safe for concurrent writes, so we build a fresh one). The thread
never touches st.session_state — all communication is via Supabase.
"""

import threading
from datetime import datetime, timezone

from supabase import create_client
import streamlit as st


# ── Internal helpers ─────────────────────────────────────────────────────

def _thread_supabase():
    """Fresh client for use inside the worker thread."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def _upsert_row(sb, user_id: str, file_hash: str, **fields):
    """Insert or update the analyses row for (user_id, file_hash)."""
    sb.table("analyses").upsert({
        "user_id": user_id,
        "file_hash": file_hash,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }, on_conflict="user_id,file_hash").execute()


def _run_analysis(user_id: str, file_hash: str, file_name: str,
                  chunks_by_type: dict, lang_code: str, word_limit: int):
    """Worker function — runs in a daemon thread."""
    sb = _thread_supabase()
    try:
        _upsert_row(sb, user_id, file_hash, status="running", file_name=file_name)

        # Import here so the thread picks up the same installed package
        from src.llm_pipeline import analyze_paper
        result = analyze_paper(chunks_by_type, language=lang_code, word_limit=word_limit)

        _upsert_row(sb, user_id, file_hash,
                    status="done",
                    result=result,
                    lang_code=lang_code,
                    file_name=file_name)

        # Also write to disk cache so offline / guest fallback still works
        try:
            from src.paper_cache import save_analysis
            save_analysis(file_hash, result, lang_code)
        except Exception:
            pass

    except Exception as exc:
        try:
            _upsert_row(sb, user_id, file_hash,
                        status="error",
                        error_msg=str(exc),
                        file_name=file_name)
        except Exception:
            pass


# ── Public API ───────────────────────────────────────────────────────────

def start_analysis(user_id: str, file_hash: str, file_name: str,
                   chunks_by_type: dict, lang_code: str = "en",
                   word_limit: int = 120) -> bool:
    """
    Kick off a background analysis for (user_id, file_hash).
    Returns False immediately if one is already running.
    """
    from src.supabase_client import get_supabase
    sb = get_supabase()

    # Check if already running / done
    try:
        existing = (
            sb.table("analyses")
            .select("status")
            .eq("user_id", user_id)
            .eq("file_hash", file_hash)
            .maybe_single()
            .execute()
        )
        if existing and existing.data and existing.data.get("status") in ("pending", "running"):
            return False  # already in progress
    except Exception:
        pass  # no existing row — safe to proceed

    # Insert pending row immediately so the UI can show a spinner right away
    _upsert_row(sb, user_id, file_hash,
                status="pending",
                file_name=file_name,
                result=None,
                error_msg=None)

    t = threading.Thread(
        target=_run_analysis,
        args=(user_id, file_hash, file_name,
              chunks_by_type, lang_code, word_limit),
        daemon=True,
    )
    t.start()
    return True


def get_analysis_status(user_id: str, file_hash: str) -> dict | None:
    """
    Poll Supabase for the current analysis row.
    Returns the row dict or None if no analysis has been started.

    Keys: status ('pending'|'running'|'done'|'error'),
          result (dict|None), lang_code, error_msg, updated_at
    """
    if not user_id or not file_hash:
        return None
    try:
        from src.supabase_client import get_supabase
        sb = get_supabase()
        row = (
            sb.table("analyses")
            .select("status,result,lang_code,error_msg,updated_at,file_name")
            .eq("user_id", user_id)
            .eq("file_hash", file_hash)
            .maybe_single()
            .execute()
        )
        return row.data if row else None
    except Exception:
        return None


def clear_analysis(user_id: str, file_hash: str):
    """Delete the analysis row so the user can re-run it."""
    try:
        from src.supabase_client import get_supabase
        get_supabase().table("analyses") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("file_hash", file_hash) \
            .execute()
    except Exception:
        pass
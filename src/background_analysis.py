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

Critically, the worker thread must never call ANY st.* API directly
(st.secrets, st.cache_resource-wrapped get_supabase(), etc.) — Streamlit
only attaches a ScriptRunContext to the main script thread, and a raw
threading.Thread has none. Touching st.* from inside the thread can
raise or hang before the row is ever updated, which looks exactly like
a job stuck at 'pending' forever with no error logged. All Streamlit-
dependent values (Supabase URL/key) are resolved in start_analysis(),
which runs in the main thread, and passed into the worker as plain
strings.
"""

import logging
import threading
from datetime import datetime, timezone

from supabase import create_client
import streamlit as st

logger = logging.getLogger(__name__)


# ── Internal helpers ─────────────────────────────────────────────────────

def _thread_supabase(url: str, key: str):
    """Fresh client for use inside the worker thread.

    IMPORTANT: takes url/key as plain strings, resolved by the caller in
    the main Streamlit script thread. Do NOT call st.secrets (or any
    st.* API, including cached get_supabase()) from inside the worker
    thread itself — Streamlit's ScriptRunContext is only attached to the
    main script thread, and touching st.* from a raw threading.Thread can
    silently raise (or hang, depending on Streamlit version) before any
    status row is ever written, which looks identical to a job stuck at
    'pending' forever with zero logged trace.
    """
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
                  chunks_by_type: dict, lang_code: str, word_limit: int,
                  supabase_url: str, supabase_key: str):
    """Worker function — runs in a daemon thread.

    Never touches st.* directly (see _thread_supabase docstring) — all
    Streamlit-dependent values must be resolved by the caller and passed
    in as plain arguments.
    """
    # First thing that happens in the thread, before anything can go
    # wrong — if this line is missing from the terminal, the thread
    # never started at all (problem is in start_analysis/threading, not
    # here). If it's present but nothing after it logs, the thread died
    # before reaching the try block below.
    logger.info(
        "Background analysis thread started for user_id=%s file_hash=%s", user_id, file_hash
    )
    sb = None
    try:
        sb = _thread_supabase(supabase_url, supabase_key)
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
        logger.exception(
            "Background analysis failed for user_id=%s file_hash=%s", user_id, file_hash
        )
        msg = str(exc)
        # Give users a friendlier message for quota errors
        if "429" in msg or "resource_exhausted" in msg.lower() or "quota" in msg.lower():
            from src.llm_pipeline import extract_retry_seconds
            wait_s = extract_retry_seconds(exc)
            if wait_s:
                wait_str = f"{int(wait_s)} seconds" if wait_s < 90 else f"{int(wait_s // 60)} minutes"
                friendly = f"We're processing a lot of requests right now and hit our limit. Please try again in about {wait_str}."
            else:
                friendly = "We're processing a lot of requests right now and hit our limit. Please try again shortly."
        else:
            friendly = msg
        try:
            if sb is None:
                # Client creation itself failed — retry with the same
                # plain url/key (never call get_supabase()/st.secrets
                # here; both touch st.* and this is still the worker
                # thread, which has no ScriptRunContext).
                sb = create_client(supabase_url, supabase_key)
            _upsert_row(sb, user_id, file_hash,
                        status="error",
                        error_msg=friendly,
                        file_name=file_name)
        except Exception:
            logger.exception(
                "Also failed to write error status for user_id=%s file_hash=%s — "
                "row will be stuck at its last status until manually cleared.",
                user_id, file_hash,
            )


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

    # Resolve secrets HERE, in the main script thread — this is the only
    # place in this whole flow where touching st.secrets is safe. The
    # thread itself must receive plain strings, never call st.* directly.
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    t = threading.Thread(
        target=_run_analysis,
        args=(user_id, file_hash, file_name,
              chunks_by_type, lang_code, word_limit,
              supabase_url, supabase_key),
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
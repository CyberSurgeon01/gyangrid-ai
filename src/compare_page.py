"""
src/compare_page.py

Side-by-side comparison of two papers: retrieves section-relevant chunks
from each paper's vector store, sends both to Gemini via
llm_pipeline.compare_papers(), and renders the result as tabs (Novelty /
Research Gap / Methodology / Results / Future Work / Conclusion) plus an
AI Verdict summary.

Each slot (A / B) can be filled either by picking a saved paper from
History, or by uploading a one-off file right there in the slot. An
ad-hoc upload runs the full parse/chunk/embed pipeline in memory so
retrieval works exactly the same as a saved paper, but it is never
written to paper_cache or the user's paper index — closing the tab
loses it, by design.

Guest gating
------------
Compare requires an account (both for History-backed papers and for
the usage limit below), and guest sessions never authenticate against
Supabase. Rather than let a guest hit a broken picker, render_compare_page()
shows a short explanation + a "Log in" button. That button does NOT
render the login form inline — it resets st.session_state.auth_status
to None and reruns, handing control back to app.py's own top-level auth
gate (the same one every other page already funnels through), so there
is only ever one login code path in the app.

Rate limiting
-------------
Each user gets 3 comparisons per rolling 3-hour window, tracked in a
small Supabase table (`compare_usage`: user_id, run_at). This survives
restarts/redeploys, unlike an in-process counter. See
_check_and_record_usage() for the exact query. Requires creating that
table once in Supabase (see the note at the bottom of this file).

Widget-state note
------------------
The Streamlit rule "st.session_state.<key> cannot be written after the
widget with that key has rendered this run" means the swap button can't
write directly into compare_pick_a/compare_pick_b's own keys after the
selectboxes exist. Instead the swap button sets a `compare_swap_pending`
flag and reruns; the flag is consumed and applied *before* the
selectboxes are instantiated on the next run.
"""

from datetime import datetime, timedelta, timezone

import streamlit as st

from src.document_loader import load_document
from src.text_cleaner import clean_text
from src.chunker import chunk_sections
from src.parser import parse_document
from src.embeddings import embed_chunks, embed_query
from src.vector_store import VectorStore
from src.paper_cache import hash_file_bytes, load_paper
from src.llm_pipeline import compare_papers, COMPARE_SECTIONS, extract_retry_seconds, is_zero_quota_exception
from src.profile import get_current_user_id, list_papers
from src.ui_theme import card_open, card_close, result_card

MAX_COMPARES_PER_WINDOW = 3
RATE_WINDOW = timedelta(hours=3)

_UPLOAD_LABEL = "📤 Upload a paper (not saved)"

_SECTION_META = {
    "novelty": ("novelty original contribution of this paper", "success"),
    "research_gap": ("research gap limitation prior work", "warning"),
    "methodology": ("methodology approach proposed model architecture", "accent"),
    "results": ("results evaluation performance accuracy experiment", "pro"),
    "future_work": ("future work directions recommendations", "pro"),
    "conclusion": ("conclusion summary findings key takeaways", "accent"),
}

_SECTION_LABELS = {
    "novelty": "Novelty",
    "research_gap": "Research Gap",
    "methodology": "Methodology",
    "results": "Results",
    "future_work": "Future Work",
    "conclusion": "Conclusion",
}


# ── Guest gate ───────────────────────────────────────────────────────────

def _prompt_login():
    card_open("Sign in to compare papers", "layers")
    st.write(
        "Comparing papers works from your account (saved History plus a "
        "usage limit), and guest sessions don't have one. Log in or create "
        "a free account to unlock it."
    )
    if st.button("Log in", type="primary", key="compare_goto_login"):
        for key in ("auth_status", "user_name", "user_email", "user_id"):
            st.session_state.pop(key, None)
        st.rerun()
    card_close()


# ── Rate limiting (Supabase) ────────────────────────────────────────────
#
# Requires a table in Supabase, created once:
#
#   create table compare_usage (
#     id bigint generated always as identity primary key,
#     user_id text not null,
#     run_at timestamptz not null default now()
#   );
#   create index compare_usage_user_time_idx on compare_usage (user_id, run_at);
#
# No RLS policy is assumed here beyond what the rest of the app already
# uses for its Supabase client (service key server-side, or matching
# policies if using the anon key) — match whatever `analyses` uses today.

def _check_and_record_usage(user_id: str) -> tuple:
    """Returns (allowed: bool, remaining: int, reset_at: datetime|None).
    Records a usage row only when a comparison is actually about to run
    (call this right before kicking off the Gemini call, not on page
    load) so merely viewing the page never burns a slot."""
    from src.supabase_client import get_supabase
    sb = get_supabase()
    window_start = (datetime.now(timezone.utc) - RATE_WINDOW).isoformat()

    try:
        rows = (
            sb.table("compare_usage")
            .select("run_at")
            .eq("user_id", user_id)
            .gte("run_at", window_start)
            .execute()
        )
        used = len(rows.data or [])
    except Exception as e:
        # Fail open rather than blocking the feature entirely — but make
        # the failure visible instead of silently always reporting full
        # quota, since that's indistinguishable from "the limit doesn't
        # work" otherwise. Most likely cause: the compare_usage table
        # hasn't been created in Supabase yet (see the SQL note above).
        st.session_state["_compare_usage_error"] = str(e)
        return True, MAX_COMPARES_PER_WINDOW, None

    st.session_state.pop("_compare_usage_error", None)

    if used >= MAX_COMPARES_PER_WINDOW:
        oldest = min(r["run_at"] for r in rows.data)
        oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        reset_at = oldest_dt + RATE_WINDOW
        return False, 0, reset_at

    try:
        sb.table("compare_usage").insert({
            "user_id": user_id,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        st.session_state["_compare_usage_error"] = str(e)

    return True, MAX_COMPARES_PER_WINDOW - used - 1, None


def _usage_remaining(user_id: str) -> tuple:
    """Read-only peek at remaining quota, for display before running
    anything. Returns (allowed_now, remaining, next_reset_at) where
    next_reset_at is when the OLDEST used slot in the current window
    frees up — i.e. the next moment `remaining` ticks up by one. None
    if no slots have been used yet in this window."""
    from src.supabase_client import get_supabase
    sb = get_supabase()
    window_start = (datetime.now(timezone.utc) - RATE_WINDOW).isoformat()
    try:
        rows = (
            sb.table("compare_usage")
            .select("run_at")
            .eq("user_id", user_id)
            .gte("run_at", window_start)
            .order("run_at")
            .execute()
        )
        used_rows = rows.data or []
    except Exception as e:
        st.session_state["_compare_usage_error"] = str(e)
        return True, MAX_COMPARES_PER_WINDOW, None

    st.session_state.pop("_compare_usage_error", None)
    used = len(used_rows)
    remaining = max(MAX_COMPARES_PER_WINDOW - used, 0)

    next_reset_at = None
    if used_rows:
        oldest = used_rows[0]["run_at"]
        oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        next_reset_at = oldest_dt + RATE_WINDOW

    return remaining > 0, remaining, next_reset_at


def _format_wait(reset_at) -> str:
    """'in 42 minutes' / 'in 2h 10m' style string for a future timestamp."""
    if not reset_at:
        return ""
    delta = reset_at - datetime.now(timezone.utc)
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m" if minutes else "less than a minute"


def _render_usage_banner(user_id: str):
    allowed, remaining, next_reset_at = _usage_remaining(user_id)

    usage_error = st.session_state.get("_compare_usage_error")
    if usage_error:
        st.warning(
            "Couldn't check your comparison usage limit — showing full quota for now. "
            f"(Likely cause: the `compare_usage` table doesn't exist in Supabase yet. Details: {usage_error})",
            icon="⚠️",
        )

    if remaining == MAX_COMPARES_PER_WINDOW:
        # Nothing used yet in this window — nothing to count down to.
        st.caption(f"🔋 {remaining}/{MAX_COMPARES_PER_WINDOW} comparisons available.")
        return

    if allowed:
        # Some slots used, but at least one still free — no countdown yet.
        # The 3-hour timer is only meaningful once quota is exhausted, so
        # don't show "next slot frees up" until remaining hits 0.
        st.caption(
            f"🔋 {remaining}/{MAX_COMPARES_PER_WINDOW} comparisons left in this 3-hour window."
        )
    else:
        wait_str = _format_wait(next_reset_at)
        wait_for = f" You'll get a new slot in {wait_str}." if wait_str else ""
        st.warning(
            f"You've used all {MAX_COMPARES_PER_WINDOW} comparisons for this 3-hour window.{wait_for}",
            icon="⏳",
        )


# ── Ad-hoc (unsaved) upload pipeline ────────────────────────────────────

def _process_adhoc_file(uploaded_file, slot_key: str):
    """Runs the full parse/chunk/embed pipeline for a one-off uploaded
    file, entirely in session_state — never touches paper_cache or the
    user's paper index. Cached in session_state by file hash so re-runs
    (e.g. switching tabs) don't reprocess the same bytes."""
    file_bytes = uploaded_file.getvalue()
    file_hash = hash_file_bytes(file_bytes)

    cache_key = f"compare_adhoc_{slot_key}"
    cached = st.session_state.get(cache_key)
    if cached and cached.get("file_hash") == file_hash:
        return cached["parsed"], cached["store"], cached["name"]

    with st.spinner(f"Processing {uploaded_file.name} (not saved)..."):
        raw_text = load_document(uploaded_file)
        cleaned_text = clean_text(raw_text)
        parsed = parse_document(cleaned_text)
        section_chunks = chunk_sections(parsed)
        embedded_chunks = embed_chunks(section_chunks)
        store = VectorStore(dimension=384)
        store.add_chunks(embedded_chunks)

    st.session_state[cache_key] = {
        "file_hash": file_hash, "parsed": parsed, "store": store,
        "name": uploaded_file.name,
    }
    return parsed, store, uploaded_file.name


# ── Retrieval / comparison ──────────────────────────────────────────────

def _retrieve_sections(store, parsed: dict) -> dict:
    sections = {}
    for key, (query, _role) in _SECTION_META.items():
        sections[key] = store.search(embed_query(query), top_k=5)
    sections["general"] = [
        {"section": "title", "text": parsed.get("title", "")},
        {"section": "abstract", "text": (parsed.get("abstract") or "")[:1000]},
    ]
    return sections


def _load_saved(file_hash: str):
    cached = load_paper(file_hash)
    if not cached:
        return None
    data, store = cached
    return data.get("parsed", {}), store, data.get("file_name", "")


def _resolve_slot(slot_key: str, pick_label: str, hash_by_label: dict):
    """Returns (parsed, store, display_name) for a slot, whether it's a
    saved-paper pick or the ad-hoc uploader, or None if nothing is ready
    yet (e.g. uploader slot with no file chosen)."""
    if not pick_label:
        return None
    if pick_label == _UPLOAD_LABEL:
        uploaded = st.session_state.get(f"compare_upload_widget_{slot_key}")
        if uploaded is None:
            return None
        return _process_adhoc_file(uploaded, slot_key)
    if pick_label not in hash_by_label:
        return None
    loaded = _load_saved(hash_by_label[pick_label])
    if not loaded:
        return None
    return loaded


def _refund_usage(user_id: str, since: datetime):
    """Deletes this user's most recent usage row if it was recorded at
    or after `since` — used to give back the slot _check_and_record_usage
    just spent when the actual Gemini call then fails for a reason that
    isn't the user's fault (rate limit, transient outage, etc.)."""
    from src.supabase_client import get_supabase
    try:
        sb = get_supabase()
        sb.table("compare_usage") \
            .delete() \
            .eq("user_id", user_id) \
            .gte("run_at", since.isoformat()) \
            .execute()
    except Exception:
        pass  # best-effort — worst case the user loses one slot to a fluke


def _friendly_compare_error(e: Exception) -> str:
    """Maps common Gemini failure modes to a clear, non-technical message
    instead of surfacing a raw exception/JSON blob to the user."""
    msg = str(e).lower()
    if is_zero_quota_exception(e):
        return (
            "This Gemini API key has no quota at all (limit: 0) for this model — "
            "that's a billing/plan issue, not a temporary traffic spike, so "
            "retrying won't help. Check the Gemini API rate-limits page and make "
            "sure billing is enabled on the linked Google Cloud project."
        )
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg:
        wait_s = extract_retry_seconds(e)
        if wait_s:
            wait_str = f"{int(wait_s)} seconds" if wait_s < 90 else f"{int(wait_s // 60)} minutes"
            return f"We're comparing a lot of papers right now and hit our processing limit. Please try again in about {wait_str}."
        return "We're comparing a lot of papers right now and hit our processing limit. Please try again shortly."
    if "503" in msg or "unavailable" in msg or "overloaded" in msg:
        return "The AI model is experiencing high demand right now. This is usually temporary — please try again in a minute."
    if "timeout" in msg or "timed out" in msg or "deadline" in msg:
        return "The comparison took too long and timed out. Please try again."
    return "Something went wrong while comparing these papers. Please try again in a moment."


def _run_comparison(slot_a, slot_b, lang_code: str, user_id: str):
    allowed, remaining, reset_at = _check_and_record_usage(user_id)
    if not allowed:
        wait_str = _format_wait(reset_at)
        wait_for = f" You'll get a new slot in {wait_str}." if wait_str else ""
        st.warning(
            f"You've used all {MAX_COMPARES_PER_WINDOW} comparisons for this 3-hour window.{wait_for}",
            icon="⏳",
        )
        return

    usage_recorded_at = datetime.now(timezone.utc)
    parsed_a, store_a, name_a = slot_a
    parsed_b, store_b, name_b = slot_b

    try:
        with st.spinner("Retrieving relevant sections from both papers..."):
            sections_a = _retrieve_sections(store_a, parsed_a)
            sections_b = _retrieve_sections(store_b, parsed_b)

        with st.spinner("Comparing papers with AI..."):
            result = compare_papers(
                paper_a_title=parsed_a.get("title") or name_a,
                paper_a_sections=sections_a,
                paper_b_title=parsed_b.get("title") or name_b,
                paper_b_sections=sections_b,
                language=lang_code,
            )
    except Exception as e:
        # The call failed after the slot was already recorded — give it
        # back, since this wasn't the user hitting their own limit.
        _refund_usage(user_id, since=usage_recorded_at - timedelta(seconds=5))
        st.error(_friendly_compare_error(e))
        with st.expander("Show raw error (source material)"):
            st.code(str(e), language=None)
        return

    st.session_state.compare_result = result
    st.session_state.compare_meta = {
        "name_a": name_a, "name_b": name_b,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ── Rendering ────────────────────────────────────────────────────────────

def _truncate(name: str, max_chars: int = 30) -> str:
    return name if len(name) <= max_chars else name[: max_chars - 1] + "…"


def _render_verdict(verdict: dict):
    card_open("AI Verdict Summary", "sparkles")

    cols = st.columns(6)
    with cols[0]:
        st.metric("Overall Similarity", f"{verdict.get('overall_similarity', 0)}%")
    with cols[1]:
        st.metric("Better Novelty", verdict.get("better_novelty", "Tie"))
    with cols[2]:
        st.metric("Better Methodology", verdict.get("better_methodology", "Tie"))
    with cols[3]:
        st.metric("Better Results", verdict.get("better_results", "Tie"))
    with cols[4]:
        st.metric("Future Potential", verdict.get("future_potential", "Tie"))
    with cols[5]:
        st.metric("Overall Winner", verdict.get("overall_winner", "Tie"))

    reason = verdict.get("overall_winner_reason", "")
    if reason:
        st.caption(reason)
    st.caption("AI comparison is generated based on content analysis and may have limitations.")
    card_close()


def _render_slot_picker(slot_key: str, labels: list, default_index: int):
    """Renders one slot's selectbox (papers + an 'Upload a paper' option)
    and, if that option is chosen, a compact file uploader right beneath
    it. Returns the chosen label."""
    pick_key = f"compare_pick_{slot_key}"
    all_options = labels + [_UPLOAD_LABEL]
    if pick_key not in st.session_state:
        st.session_state[pick_key] = all_options[default_index] if default_index < len(all_options) else all_options[0]

    pick = st.selectbox(
        f"Paper {slot_key.upper()}", all_options,
        key=pick_key,
        accept_new_options=False,
    )
    if pick is None:
        # The user clicked the selectbox's clear ("x") control. There is
        # no valid "nothing selected" state for a compare slot, so snap
        # straight back to a real option instead of leaving pick_key as
        # None (which would otherwise blow up downstream lookups keyed
        # by label).
        fallback = all_options[default_index] if default_index < len(all_options) else all_options[0]
        st.session_state[pick_key] = fallback
        st.rerun()
    if pick == _UPLOAD_LABEL:
        st.file_uploader(
            "Upload PDF or DOCX", type=["pdf", "docx"],
            key=f"compare_upload_widget_{slot_key}",
            label_visibility="collapsed",
        )
        st.caption("Not saved to your account or History — used for this comparison only.")
    return pick


def render_compare_page():
    """Entry point — call this from app.py when page == 'Compare'."""
    is_guest = st.session_state.get("auth_status") == "guest"
    if is_guest:
        _prompt_login()
        return

    user_id = get_current_user_id()

    # Apply a pending swap BEFORE the selectboxes below are instantiated —
    # writing to their session_state keys after instantiation raises
    # StreamlitAPIException.
    if st.session_state.pop("compare_swap_pending", False):
        a = st.session_state.get("compare_pick_a")
        b = st.session_state.get("compare_pick_b")
        st.session_state["compare_pick_a"] = b
        st.session_state["compare_pick_b"] = a

    saved_options = [(e["file_name"], e["file_hash"]) for e in list_papers(user_id)]
    labels = [label for label, _hash in saved_options]
    hash_by_label = dict(saved_options)

    card_open("Compare Research Papers", "layers", caption="Compare sections between two research papers side by side.")
    _render_usage_banner(user_id)

    col_a, col_swap, col_b, col_btn = st.columns([5, 1, 5, 3])
    with col_a:
        pick_a = _render_slot_picker("a", labels, default_index=0)
    with col_swap:
        st.write("")
        st.write("")
        if st.button("⇄", key="compare_swap", help="Swap Paper A and Paper B"):
            st.session_state.compare_swap_pending = True
            st.rerun()
    with col_b:
        default_b = 1 if len(labels) > 1 else 0
        pick_b = _render_slot_picker("b", labels, default_index=default_b)
    with col_btn:
        st.write("")
        st.write("")
        run_clicked = st.button("Compare", type="primary", use_container_width=True, key="compare_run_btn")
    card_close()

    if run_clicked:
        if pick_a == pick_b and pick_a != _UPLOAD_LABEL:
            st.warning("Choose two different papers to compare.")
        else:
            slot_a = _resolve_slot("a", pick_a, hash_by_label)
            slot_b = _resolve_slot("b", pick_b, hash_by_label)
            if not slot_a:
                st.error("Paper A isn't ready — pick a saved paper or upload a file first.")
            elif not slot_b:
                st.error("Paper B isn't ready — pick a saved paper or upload a file first.")
            else:
                lang_code = st.session_state.get("lang_code", "en")
                _run_comparison(slot_a, slot_b, lang_code, user_id)

    result = st.session_state.get("compare_result")
    meta = st.session_state.get("compare_meta")
    if not result or not meta:
        return

    name_a, name_b = meta["name_a"], meta["name_b"]

    tabs = st.tabs([_SECTION_LABELS[s] for s in COMPARE_SECTIONS])
    for tab, section in zip(tabs, COMPARE_SECTIONS):
        with tab:
            role = _SECTION_META[section][1]
            col_left, col_right, col_insight = st.columns([4, 4, 4])
            with col_left:
                card_open("Paper A", "file-text", caption=_truncate(name_a, max_chars=42))
                for bullet in result["paper_a"].get(section, []):
                    st.markdown(f"- {bullet}")
                card_close()
            with col_right:
                card_open("Paper B", "file-text", caption=_truncate(name_b, max_chars=42))
                for bullet in result["paper_b"].get(section, []):
                    st.markdown(f"- {bullet}")
                card_close()
            with col_insight:
                insight_text = result["insight"].get(section, "")
                result_card(role, "AI Insight", insight_text or "No insight available for this section.")

    st.markdown("<br>", unsafe_allow_html=True)
    _render_verdict(result.get("verdict", {}))
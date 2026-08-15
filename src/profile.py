"""
profile.py
Everything related to "who is logged in": the top-right profile menu,
editable account details, password change, and a per-user list of
previously uploaded papers ("My papers").

Design notes
------------
- Auth/session data (user_id, user_email) already lives in
  st.session_state, set by app.py after Supabase login/OAuth. This module
  reads it rather than re-implementing auth.
- Supabase is the source of truth for the account itself (email, password,
  display name via user_metadata). change_password() re-verifies the
  current password via sign_in_with_password() before calling
  auth.update_user() — Supabase's API will happily change a password for
  an already-authenticated session without the old one, so this extra
  check is what actually stops someone at an unlocked laptop from
  changing it.
- "My papers" has no natural home yet: paper_cache.py caches by file
  hash only, with no notion of *which user* uploaded a given paper. This
  module adds a small per-user index (one pickle per user_id) that just
  records (file_hash, file_name, uploaded_at) pairs, so the profile menu
  can list and re-open a user's own papers. It does not duplicate the
  actual paper cache — it only points at it.
"""

import pickle
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.paper_cache import CACHE_DIR, load_paper, load_analysis
from src.ui_theme import icon_svg, theme_colors

INDEX_DIR = CACHE_DIR.parent / "user_papers"


# ── Per-user paper index ─────────────────────────────────────────────────

def _index_path(user_id: str) -> Path:
    return INDEX_DIR / f"{user_id}.pkl"


def _load_index(user_id: str) -> list:
    path = _index_path(user_id)
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, EOFError, FileNotFoundError):
        return []


def _save_index(user_id: str, entries: list):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(_index_path(user_id), "wb") as f:
        pickle.dump(entries, f)


def get_current_user_id() -> str:
    """Robust user_id lookup for anything that needs to be tied to the
    logged-in user (e.g. registering an uploaded paper). session_state
    is the fast path, but if it's ever empty/stale while a real Supabase
    session exists — e.g. a timing quirk right after login/OAuth, or a
    rerun that lost it — this falls back to asking Supabase directly,
    instead of register_paper() silently doing nothing (which is what
    was causing uploaded papers to never show up under 'My papers')."""
    user_id = st.session_state.get("user_id")
    if user_id:
        return user_id
    try:
        from src.supabase_client import get_supabase
        sb_user = get_supabase().auth.get_user()
        if sb_user and sb_user.user:
            st.session_state.user_id = sb_user.user.id
            st.session_state.user_email = sb_user.user.email
            return sb_user.user.id
    except Exception:
        pass
    return ""


def register_paper(user_id: str, file_hash: str, file_name: str):
    """Call this right after paper_cache.save_paper() succeeds, so the
    paper shows up under this user's 'My papers' list. Safe to call
    repeatedly for the same file (re-uploads just bump it to the top).
    Falls back to get_current_user_id() if the caller passed nothing
    usable, so a stale/empty session_state.user_id can't silently drop
    the upload."""
    user_id = user_id or get_current_user_id()
    if not user_id:
        st.toast("Couldn't link this paper to your account — try refreshing and re-uploading.", icon="⚠️")
        return
    entries = [e for e in _load_index(user_id) if e["file_hash"] != file_hash]
    entries.insert(0, {
        "file_hash": file_hash,
        "file_name": file_name,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
    })
    _save_index(user_id, entries[:50])  # cap history so the pickle can't grow unbounded


def list_papers(user_id: str) -> list:
    """Returns this user's papers, most recent first. Silently drops any
    entry whose underlying cache has since been deleted from disk."""
    if not user_id:
        return []
    entries = _load_index(user_id)
    valid = [e for e in entries if load_paper(e["file_hash"]) is not None]
    if len(valid) != len(entries):
        _save_index(user_id, valid)
    return valid


def remove_paper(user_id: str, file_hash: str):
    """Removes a paper from this user's list only — does not touch the
    shared on-disk cache, since another user (or a query param link) may
    still be pointing at it."""
    entries = [e for e in _load_index(user_id) if e["file_hash"] != file_hash]
    _save_index(user_id, entries)


def open_paper(file_hash: str) -> bool:
    """Loads a cached paper (and its cached analysis, if any) straight
    into session_state and points the URL at it — mirrors the refresh-
    restore logic in app.py. Returns False if the cache is gone."""
    cached = load_paper(file_hash)
    if not cached:
        return False
    data, store = cached
    st.session_state.processed_file_name = data["file_name"]
    st.session_state.cleaned_text = data["cleaned_text"]
    st.session_state.chunks = data["chunks"]
    st.session_state.parsed = data["parsed"]
    st.session_state.section_chunks = data["section_chunks"]
    st.session_state.vector_store = store
    st.query_params["paper"] = file_hash

    cached_analysis = load_analysis(file_hash)
    if cached_analysis:
        st.session_state.last_analysis = cached_analysis["analysis"]
        st.session_state.last_analysis_lang = cached_analysis["lang_code"]
    else:
        st.session_state.pop("last_analysis", None)

    st.session_state.nav_page = "Dashboard"
    return True


# ── Account details ──────────────────────────────────────────────────────

def _current_user():
    """Best-effort snapshot of the logged-in user for display purposes."""
    user_id = get_current_user_id()

    # If user_id resolved but user_email is still missing/stale (e.g. a
    # rerun that lost session_state), refresh it from Supabase too.
    if user_id and not st.session_state.get("user_email"):
        try:
            from src.supabase_client import get_supabase
            sb_user = get_supabase().auth.get_user()
            if sb_user and sb_user.user:
                st.session_state.user_email = sb_user.user.email
        except Exception:
            pass

    email = st.session_state.get("user_email", "")
    name = st.session_state.get("user_display_name")
    if name is None:
        try:
            from src.supabase_client import get_supabase
            sb_user = get_supabase().auth.get_user()
            name = (sb_user.user.user_metadata or {}).get("full_name") if sb_user and sb_user.user else None
        except Exception:
            name = None
        st.session_state.user_display_name = name or ""
    return {"email": email, "user_id": user_id, "name": name or ""}


def _initials(name: str, email: str) -> str:
    source = name.strip() if name and name.strip() else email
    if not source:
        return "?"
    return source[0].upper()


def update_display_name(new_name: str) -> tuple:
    """Returns (ok, message)."""
    new_name = new_name.strip()
    if not new_name:
        return False, "Name can't be empty."
    try:
        from src.supabase_client import get_supabase
        get_supabase().auth.update_user({"data": {"full_name": new_name}})
        st.session_state.user_display_name = new_name
        return True, "Profile updated."
    except Exception as e:
        return False, f"Couldn't update profile: {e}"


def change_password(current_password: str, new_password: str, confirm_password: str) -> tuple:
    """Returns (ok, message). Re-verifies current_password by attempting
    a fresh sign-in before allowing the change."""
    email = st.session_state.get("user_email", "")
    if not current_password or not new_password:
        return False, "Fill in both password fields."
    if new_password != confirm_password:
        return False, "New password and confirmation don't match."
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters."
    if new_password == current_password:
        return False, "New password must be different from the current one."

    try:
        from src.supabase_client import get_supabase
        sb = get_supabase()
        # Re-verify identity before allowing the change.
        sb.auth.sign_in_with_password({"email": email, "password": current_password})
        sb.auth.update_user({"password": new_password})
        return True, "Password updated. Use it next time you log in."
    except Exception:
        return False, "Current password is incorrect, or the update failed. Please try again."


# ── Top-right profile menu ───────────────────────────────────────────────

def render_profile_menu():
    """Renders the top-right avatar + dropdown (profile details, change
    password, my papers, log out). Call this once near the top of
    app.py, alongside page_header(). Renders nothing at all for guest
    sessions (no user_email) — there's no account to manage, so the
    trigger button is hidden rather than shown in a permanently
    "Not signed in" state."""
    user = _current_user()
    if not user["email"]:
        return

    c = theme_colors()
    initials = _initials(user["name"], user["email"])

    # Inject CSS using the exact data-testid Streamlit 1.52 assigns to the
    # popover trigger button: "stPopoverButton". We also zero out the
    # container width override that Streamlit forces on it so the circle
    # doesn't stretch to fill the column.
    st.markdown(
        f"""
        <style>
        /* Popover button container — prevent Streamlit's width:100% override */
        [data-testid="stPopover"] {{
            width: 40px !important;
            min-width: 40px !important;
        }}
        /* The actual button */
        [data-testid="stPopoverButton"] {{
            width: 40px !important;
            height: 40px !important;
            min-width: 40px !important;
            max-width: 40px !important;
            padding: 0 !important;
            border-radius: 50% !important;
            background-color: #2563eb !important;
            color: #ffffff !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            border: none !important;
            box-shadow: 0 2px 8px rgba(37,99,235,0.30) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
        }}
        [data-testid="stPopoverButton"]:hover {{
            background-color: #1d4ed8 !important;
            box-shadow: 0 4px 14px rgba(37,99,235,0.45) !important;
        }}
        [data-testid="stPopoverButton"]:focus {{
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.35) !important;
        }}
        /* Label container inside the button */
        [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
        [data-testid="stPopoverButton"] p {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    spacer, menu_col = st.columns([14, 1])
    with menu_col:
        with st.popover(initials, use_container_width=False):
            st.markdown(f"**{user['name'] or 'Unnamed user'}**")
            st.caption(user["email"] or "Not signed in")
            st.caption("Personal account")
            st.divider()

            tab_profile, tab_password, tab_papers = st.tabs(
                ["Profile", "Password", "My papers"]
            )

            with tab_profile:
                if not user["email"]:
                    st.caption("You're browsing as a guest. Sign in to set a display name and save your profile.")
                else:
                    new_name = st.text_input(
                        "Display name", value=user["name"], key="profile_name_input"
                    )
                    if st.button("Save name", key="profile_save_name_btn"):
                        ok, msg = update_display_name(new_name)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
                    st.caption(f"Email: {user['email'] or '—'}")

            with tab_password:
                if not user["email"]:
                    st.caption("You're browsing as a guest. Sign in to change your password.")
                else:
                    cur_pw = st.text_input("Current password", type="password", key="profile_cur_pw")
                    new_pw = st.text_input("New password", type="password", key="profile_new_pw")
                    confirm_pw = st.text_input("Confirm new password", type="password", key="profile_confirm_pw")
                    if st.button("Update password", key="profile_update_pw_btn"):
                        ok, msg = change_password(cur_pw, new_pw, confirm_pw)
                        (st.success if ok else st.error)(msg)

            with tab_papers:
                papers = list_papers(user["user_id"])
                if not papers:
                    st.caption("No papers uploaded yet.")
                else:
                    st.caption("Tap a paper to load it as your current paper.")
                    for entry in papers:
                        uploaded_label = entry["uploaded_at"][:16].replace("T", " ")
                        if st.button(
                            f"📄 {entry['file_name']}\n\n{uploaded_label}",
                            key=f"profile_open_{entry['file_hash']}",
                            use_container_width=True,
                        ):
                            if open_paper(entry["file_hash"]):
                                st.rerun()
                            else:
                                st.error("That paper's cache is gone.")
                        if st.button(
                            "Remove from my papers",
                            key=f"profile_remove_{entry['file_hash']}",
                            use_container_width=True,
                        ):
                            remove_paper(user["user_id"], entry["file_hash"])
                            st.rerun()
                        st.divider()

            st.divider()
            if st.button("Log out", use_container_width=True, key="profile_logout_btn"):
                try:
                    from src.supabase_client import get_supabase
                    get_supabase().auth.sign_out()
                except Exception:
                    pass
                for key in ("auth_status", "user_name", "user_email", "user_id", "user_display_name"):
                    st.session_state.pop(key, None)
                st.rerun() 
                #complete rerun to clear any cached paper/analysis data from session_state, since the next user may not have access to it.
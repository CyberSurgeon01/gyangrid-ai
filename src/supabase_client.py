"""
src/supabase_client.py

Single Supabase client per browser session for GyanGrid AI.

⚠️  CRITICAL SECURITY FIX (was: @st.cache_resource)
------------------------------------------------------
The previous version used @st.cache_resource, which caches at the
**server-process** level — one shared instance across ALL users on
Streamlit Cloud.  Because the Supabase Python client stores auth tokens
on the client object itself, User A's login session was visible to every
other browser that called get_session() on the same shared client.

The fix: cache on st.session_state instead.  st.session_state is isolated
per WebSocket connection (i.e. per browser tab), so no session data ever
leaks between users.
"""

import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client:
    """Return a Supabase client bound to the current browser session.

    The client is created once per session and stored in
    st.session_state["_supabase"] so it is never shared across users.
    """
    if "_supabase" not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state["_supabase"] = create_client(url, key)
    return st.session_state["_supabase"]
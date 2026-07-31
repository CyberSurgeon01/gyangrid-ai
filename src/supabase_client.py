"""
src/supabase_client.py

Single shared Supabase client for GyanGrid AI. Reads credentials from
Streamlit secrets (.streamlit/secrets.toml) so the same code works both
locally and on Streamlit Cloud (where secrets are injected the same way).

Cached with st.cache_resource so every part of the app (app.py,
login_page.py, signup_page.py) reuses one client instance instead of
opening a new connection per rerun.
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
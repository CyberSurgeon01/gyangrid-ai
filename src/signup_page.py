"""
Sign-up page for GyanGrid AI — redesigned auth experience.

Same CSS strategy as login_page.py: st.markdown(unsafe_allow_html=True)
injects global styles (not iframes), and we style Streamlit's own
block-container to act as the centered white card.

Sets, on success:
    st.session_state.auth_status = "user"
    st.session_state.user_name / user_email

NOTE: UI + session-state only — wire up Supabase once ready.
"""

import streamlit as st
from src.ui_theme import icon_svg, theme_colors


def _inject_signup_css(c: dict):
    st.markdown(f"""
    <style>
    /* ── Page background ───────────────────────────────────── */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {{
        background: #F7F9FC !important;
    }}
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stSidebar"],
    #MainMenu, footer {{ display: none !important; }}

    /* ── Center the block container ─────────────────────────── */
    [data-testid="stMainBlockContainer"],
    .block-container {{
        max-width: 420px !important;
        margin: 0 auto !important;
        padding: 48px 0 40px 0 !important;
        background: transparent !important;
    }}

    /* ── Auth card shell ────────────────────────────────────── */
    .gg-auth-card-shell {{
        background: #ffffff;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(15,23,42,.07), 0 0 1px rgba(15,23,42,.04);
        padding: 36px 36px 30px 36px;
        width: 100%;
        box-sizing: border-box;
    }}

    /* ── Brand header ───────────────────────────────────────── */
    .gg-auth-brand {{
        display: flex; align-items: center;
        justify-content: center; gap: 9px; margin-bottom: 3px;
    }}
    .gg-auth-brand-name {{
        font-size: 22px; font-weight: 700;
        color: {c['text_primary']}; letter-spacing: -.3px;
    }}
    .gg-auth-subtitle {{
        text-align: center; color: {c['text_secondary']};
        font-size: 13px; margin-bottom: 22px;
    }}
    .gg-auth-page-title {{
        font-size: 19px; font-weight: 600;
        color: {c['text_primary']}; margin-bottom: 18px;
        letter-spacing: -.2px;
    }}

    /* ── Field labels ───────────────────────────────────────── */
    .gg-field-label {{
        display: block; font-size: 12.5px; font-weight: 500;
        color: {c['text_primary']}; margin-bottom: 5px; margin-top: 12px;
    }}
    .gg-field-label:first-child {{ margin-top: 0; }}
    .gg-pw-hint {{
        font-size: 11.5px; color: #9CA3AF; margin-top: 3px; margin-bottom: 0;
    }}

    /* ── Streamlit input override ────────────────────────────── */
    [data-testid="stTextInput"] > div > div {{
        border: 1px solid #D1D5DB !important;
        border-radius: 6px !important;
        background: #ffffff !important;
        box-shadow: none !important;
        height: 40px !important;
        transition: border-color .15s, box-shadow .15s !important;
    }}
    [data-testid="stTextInput"] > div > div:focus-within {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,.10) !important;
    }}
    [data-testid="stTextInput"] input {{
        font-size: 13.5px !important;
        color: {c['text_primary']} !important;
        padding: 0 12px !important;
        height: 38px !important;
        background: transparent !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: #9CA3AF !important;
    }}
    [data-testid="stTextInput"] label {{ display: none !important; }}

    /* ── Password row: input + eye toggle ────────────────────── */
    .gg-pw-row [data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        align-items: flex-end !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:first-child
        [data-testid="stTextInput"] > div > div {{
        border-radius: 6px 0 0 6px !important;
        border-right: none !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:last-child button {{
        height: 40px !important;
        width: 40px !important;
        border: 1px solid #D1D5DB !important;
        border-left: none !important;
        border-radius: 0 6px 6px 0 !important;
        background: #ffffff !important;
        color: #6B7280 !important;
        padding: 0 !important;
        font-size: 18px !important;
        box-shadow: none !important;
        transition: background .12s, color .12s !important;
        margin-top: 0 !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:last-child button:hover {{
        background: #F9FAFB !important;
        color: {c['text_primary']} !important;
    }}

    /* ── Primary submit button ────────────────────────────────── */
    [data-testid="stFormSubmitButton"] > button,
    div.stButton > button[kind="primary"] {{
        background: {c['accent']} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        height: 42px !important;
        width: 100% !important;
        box-shadow: 0 1px 3px rgba(37,99,235,.22) !important;
        transition: background .15s, box-shadow .15s !important;
        margin-top: 10px !important;
    }}
    [data-testid="stFormSubmitButton"] > button:hover,
    div.stButton > button[kind="primary"]:hover {{
        background: #1d4ed8 !important;
        box-shadow: 0 3px 10px rgba(37,99,235,.30) !important;
    }}

    /* ── Secondary / outline buttons ──────────────────────────── */
    div.stButton > button[kind="secondary"] {{
        background: #ffffff !important;
        color: {c['text_primary']} !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 6px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        height: 42px !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: border-color .15s, background .15s !important;
    }}
    div.stButton > button[kind="secondary"]:hover {{
        border-color: #9CA3AF !important;
        background: #F9FAFB !important;
    }}

    /* ── Divider ─────────────────────────────────────────────── */
    .gg-auth-divider {{
        display: flex; align-items: center;
        gap: 10px; margin: 14px 0;
    }}
    .gg-div-line {{ flex: 1; height: 1px; background: #E5E7EB; }}
    .gg-div-text {{ font-size: 12px; color: #9CA3AF; }}

    /* ── Switch-view footer ─────────────────────────────────── */
    .gg-auth-switch {{
        text-align: center; margin-top: 20px;
        padding-top: 16px; border-top: 1px solid #F1F5F9;
        font-size: 13px; color: {c['text_secondary']};
    }}

    /* ── Form / layout cleanup ───────────────────────────────── */
    [data-testid="stForm"] {{
        border: none !important; padding: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }}
    .gg-pw-row [data-testid="column"] {{
        padding: 0 !important; gap: 0 !important;
    }}
    [data-testid="stVerticalBlock"] > div {{ gap: 0 !important; }}
    [data-testid="stAlert"] {{
        border-radius: 6px !important;
        font-size: 13.5px !important;
        margin-bottom: 10px !important;
        margin-top: 4px !important;
    }}

    @media (max-width: 460px) {{
        .gg-auth-card-shell {{ padding: 28px 18px 24px 18px; border-radius: 6px; }}
        [data-testid="stMainBlockContainer"], .block-container {{
            padding: 24px 16px 32px 16px !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def render_signup_page():
    c = theme_colors()
    _inject_signup_css(c)

    if "signup_show_pw" not in st.session_state:
        st.session_state.signup_show_pw = False
    if "signup_show_confirm" not in st.session_state:
        st.session_state.signup_show_confirm = False

    brain_svg = icon_svg("brain", 26, c["accent"])

    # ── Card open ──────────────────────────────────────────────
    st.markdown('<div class="gg-auth-card-shell">', unsafe_allow_html=True)

    st.markdown(f"""
        <div class="gg-auth-brand">
            {brain_svg}
            <span class="gg-auth-brand-name">GyanGrid AI</span>
        </div>
        <div class="gg-auth-subtitle">AI Research Assistant</div>
        <div class="gg-auth-page-title">Create your account</div>
    """, unsafe_allow_html=True)

    # ── Signup form ────────────────────────────────────────────
    with st.form("gg_signup_form", border=False):
        st.markdown('<span class="gg-field-label">Full name</span>', unsafe_allow_html=True)
        name = st.text_input(
            "Full name", key="signup_name",
            placeholder="Your name", label_visibility="collapsed"
        )

        st.markdown('<span class="gg-field-label">Email</span>', unsafe_allow_html=True)
        email = st.text_input(
            "Email", key="signup_email",
            placeholder="you@example.com", label_visibility="collapsed"
        )

        st.markdown('<span class="gg-field-label">Password</span>', unsafe_allow_html=True)
        pw_type = "text" if st.session_state.signup_show_pw else "password"
        st.markdown('<div class="gg-pw-row">', unsafe_allow_html=True)
        pw_col, eye_col = st.columns([9, 1], gap="small")
        with pw_col:
            password = st.text_input(
                "Password", key="signup_password", type=pw_type,
                placeholder="••••••••", label_visibility="collapsed"
            )
        with eye_col:
            eye1 = "🙈" if st.session_state.signup_show_pw else "👁"
            if st.form_submit_button(eye1):
                st.session_state.signup_show_pw = not st.session_state.signup_show_pw
                st.rerun()
        st.markdown('</div><p class="gg-pw-hint">Minimum 6 characters.</p>',
                    unsafe_allow_html=True)

        st.markdown('<span class="gg-field-label">Confirm password</span>',
                    unsafe_allow_html=True)
        cpw_type = "text" if st.session_state.signup_show_confirm else "password"
        st.markdown('<div class="gg-pw-row">', unsafe_allow_html=True)
        cpw_col, ceye_col = st.columns([9, 1], gap="small")
        with cpw_col:
            confirm = st.text_input(
                "Confirm password", key="signup_confirm", type=cpw_type,
                placeholder="••••••••", label_visibility="collapsed"
            )
        with ceye_col:
            eye2 = "🙈" if st.session_state.signup_show_confirm else "👁"
            if st.form_submit_button(eye2):
                st.session_state.signup_show_confirm = not st.session_state.signup_show_confirm
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "Create account", use_container_width=True, type="primary"
        )

    if submitted:
        if not name or not email or not password:
            st.error("Please fill in all fields.")
        elif password != confirm:
            st.error("Passwords don't match.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            # TODO: replace with real Supabase auth.sign_up()
            st.session_state.auth_status = "user"
            st.session_state.user_email = email
            st.session_state.user_name = name
            st.rerun()

    # ── Divider ──────────────────────────────────────────────
    st.markdown("""
        <div class="gg-auth-divider">
            <div class="gg-div-line"></div>
            <span class="gg-div-text">or</span>
            <div class="gg-div-line"></div>
        </div>
    """, unsafe_allow_html=True)

    # ── Google ────────────────────────────────────────────────
    if st.button("🔵  Continue with Google", key="signup_google_btn",
                 use_container_width=True):
        if "auth" in st.secrets:
            st.login()
        else:
            st.info("Google login isn't configured yet — add [auth] to .streamlit/secrets.toml.")

    # ── Switch to login ───────────────────────────────────────
    st.markdown('<div class="gg-auth-switch">Already have an account?</div>',
                unsafe_allow_html=True)
    if st.button("Log in →", key="go_to_login_btn", use_container_width=True):
        st.session_state.auth_view = "login"
        st.rerun()

    # ── Card close ────────────────────────────────────────────
    st.markdown('</div>', unsafe_allow_html=True)
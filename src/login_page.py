"""
Login page for GyanGrid AI — rebuilt to match exact target screenshot.

Layout (single column, not side-by-side):
  1. A full-width dark navy/blue gradient hero BANNER at the top:
     logo mark + wordmark, 3-line headline (middle line accent blue),
     description paragraph, 3-item checklist with check icons, a thin
     divider, and a trust line.
  2. Below the banner, on the plain page background: "Welcome back"
     heading + subtitle, then a standard stacked form — Email, Password
     (with a small eye toggle glyph inset at the right edge of the
     input, not a separate button box), Forgot password link,
     full-width blue Log in button, an "OR CONTINUE WITH" divider,
     full-width outlined Google button, full-width outlined Continue
     as Guest button, a small guest-mode caption, a Don't-have-an-account
     line, and a full-width outlined Create account button.

Strategy: st.markdown(unsafe_allow_html=True) injects global CSS.
All interactive elements stay native Streamlit widgets (st.text_input,
st.button, st.form) so session-state + reruns keep working.

Sets, on success:
    st.session_state.auth_status = "user" | "guest"
    st.session_state.user_name / user_email  (only when auth_status == "user")
"""

import streamlit as st
from src.ui_theme import icon_svg, theme_colors


def _inject_login_css(c: dict):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    section.main {{
        background: #F4F6FB !important;
        font-family: 'Inter', -apple-system, 'SF Pro Display', BlinkMacSystemFont, sans-serif !important;
    }}
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stSidebar"],
    #MainMenu, footer {{ display: none !important; }}

    * {{ font-family: 'Inter', -apple-system, 'SF Pro Display', BlinkMacSystemFont, sans-serif !important; }}

    [data-testid="stMainBlockContainer"],
    .block-container {{
        max-width: 720px !important;
        margin: 0 auto !important;
        padding: 32px 20px 56px 20px !important;
        background: transparent !important;
    }}

    /* ── Hero banner ───────────────────────────────────────────────────── */
    .gg-hero-banner {{
        position: relative;
        background:
            radial-gradient(700px 420px at 15% 10%, rgba(96,150,255,.28), transparent 60%),
            linear-gradient(160deg, #0E1B33 0%, #14294E 55%, #1A3868 100%);
        border-radius: 16px;
        padding: 36px 40px 32px 40px;
        color: #ffffff;
        overflow: hidden;
        margin-bottom: 40px;
    }}
    .gg-hero-banner::before {{
        content: "";
        position: absolute; inset: 0;
        background-image:
            linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
        background-size: 30px 30px;
        mask-image: radial-gradient(circle at 20% 15%, black, transparent 70%);
        pointer-events: none;
    }}

    .gg-hero-brand {{
        display: flex; align-items: center; gap: 9px;
        position: relative; z-index: 1;
    }}
    .gg-hero-brand-name {{
        font-size: 15px; font-weight: 600; color: #ffffff; letter-spacing: -.1px;
    }}

    .gg-hero-headline {{
        position: relative; z-index: 1;
        font-size: 26px; font-weight: 800; letter-spacing: -.6px;
        line-height: 1.28; color: #E8ECF5;
        margin-top: 28px;
    }}
    .gg-hero-headline .gg-accent-line {{ color: #7FB2FF; }}

    .gg-hero-desc {{
        position: relative; z-index: 1;
        font-size: 13.5px; line-height: 1.6; color: #9FADC7;
        margin-top: 14px; max-width: 480px;
    }}

    .gg-hero-checklist {{
        position: relative; z-index: 1;
        margin-top: 22px; display: flex; flex-direction: column; gap: 12px;
    }}
    .gg-hero-check-item {{
        display: flex; align-items: center; gap: 10px;
        font-size: 13.5px; color: #C7D1E6;
    }}
    .gg-hero-check-icon {{
        flex-shrink: 0; width: 18px; height: 18px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 5px;
        background: rgba(127,178,255,.14);
        border: 1px solid rgba(127,178,255,.35);
    }}

    .gg-hero-divider {{
        position: relative; z-index: 1;
        height: 1px; background: rgba(255,255,255,.10);
        margin: 22px 0 16px 0;
    }}
    .gg-hero-trust {{
        position: relative; z-index: 1;
        font-size: 12px; color: #7C8AAC;
    }}

    /* ── Welcome section ──────────────────────────────────────────────── */
    .gg-welcome-title {{
        font-size: 24px; font-weight: 800; color: #0B1220;
        letter-spacing: -.5px; margin-bottom: 6px;
    }}
    .gg-welcome-sub {{
        font-size: 14px; color: #64748B; margin-bottom: 28px;
    }}

    /* ── Field labels ──────────────────────────────────────────────────── */
    .gg-field-label {{
        display: block; font-size: 13px; font-weight: 600;
        color: #1E293B; margin-bottom: 8px; margin-top: 20px;
    }}
    .gg-field-label:first-child {{ margin-top: 0; }}

    /* ── Text inputs — full width, clean ──────────────────────────────── */
    [data-testid="stTextInput"] > div > div {{
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        box-shadow: none !important;
        height: 48px !important;
        transition: border-color .15s ease, box-shadow .15s ease !important;
    }}
    [data-testid="stTextInput"] > div > div:focus-within {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
    }}
    [data-testid="stTextInput"] input {{
        font-size: 14px !important;
        color: #0F172A !important;
        padding: 0 14px !important;
        height: 46px !important;
        background: transparent !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: #94A3B8 !important;
    }}
    [data-testid="stTextInput"] label {{ display: none !important; }}

    /* ── Password row: input + eye toggle as adjacent columns ─────────── */
    /* Streamlit renders each st.* call as its own sibling block, so a
       <div> wrapper from st.markdown can never actually contain a
       widget that comes after it — absolute-positioning the eye button
       "inside" the input that way silently fails. Using st.columns()
       to place input + button side-by-side is the reliable approach,
       and this CSS just makes the pair read as one seamless control. */
    .gg-pw-row [data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        align-items: flex-end !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:first-child {{
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:last-child {{
        flex: 0 0 44px !important;
        width: 44px !important;
        min-width: 44px !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:first-child
        [data-testid="stTextInput"] > div > div {{
        border-radius: 10px 0 0 10px !important;
        border-right: none !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:last-child button {{
        height: 48px !important;
        width: 44px !important;
        min-height: 0 !important;
        border: 1px solid #E2E8F0 !important;
        border-left: none !important;
        border-radius: 0 10px 10px 0 !important;
        background: #ffffff !important;
        color: #94A3B8 !important;
        padding: 0 !important;
        font-size: 16px !important;
        display: flex; align-items: center; justify-content: center;
        box-shadow: none !important;
        transition: background .12s, color .12s !important;
        margin: 0 !important;
    }}
    .gg-pw-row [data-testid="stHorizontalBlock"] > div:last-child button:hover {{
        background: #F1F5F9 !important;
        color: #1E293B !important;
    }}
    .gg-pw-row [data-testid="column"] {{
        padding: 0 !important; gap: 0 !important;
    }}

    /* ── Forgot password link — sits directly under the password row ──── */
    .gg-forgot {{
        display: block; text-align: right;
        font-size: 13px; font-weight: 500; color: {c['accent']};
        margin-top: 10px; margin-bottom: 4px;
        text-decoration: underline; text-underline-offset: 2px;
        cursor: pointer;
    }}

    /* ── Primary button: solid blue, full width ───────────────────────── */
    [data-testid="stFormSubmitButton"] > button,
    div.stButton > button[kind="primary"] {{
        background: {c['accent']} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 14.5px !important;
        font-weight: 650 !important;
        height: 50px !important;
        width: 100% !important;
        box-shadow: 0 6px 16px -4px rgba(37,99,235,.45) !important;
        transition: filter .15s ease, transform .12s ease !important;
        margin-top: 18px !important;
    }}
    [data-testid="stFormSubmitButton"] > button:hover,
    div.stButton > button[kind="primary"]:hover {{
        filter: brightness(1.08);
        transform: translateY(-1px);
    }}
    [data-testid="stFormSubmitButton"] > button:focus-visible,
    div.stButton > button:focus-visible {{
        outline: 2px solid {c['accent']} !important;
        outline-offset: 2px !important;
    }}

    /* ── Divider ───────────────────────────────────────────────────────── */
    .gg-auth-divider {{
        display: flex; align-items: center;
        gap: 12px; margin: 26px 0 18px 0;
    }}
    .gg-div-line {{ flex: 1; height: 1px; background: #E5E9F0; }}
    .gg-div-text {{
        font-size: 11.5px; font-weight: 700; color: #94A3B8;
        letter-spacing: .05em; white-space: nowrap;
    }}

    /* ── Outlined full-width buttons (Google, Guest, Create account) ──── */
    div.stButton > button[kind="secondary"] {{
        background: #ffffff !important;
        color: #1E293B !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        height: 50px !important;
        width: 100% !important;
        box-shadow: 0 1px 2px rgba(15,23,42,.03) !important;
        transition: border-color .15s, background .15s, transform .12s !important;
        margin-top: 12px !important;
    }}
    div.stButton > button[kind="secondary"]:hover {{
        border-color: #94A3B8 !important;
        background: #F8FAFC !important;
        transform: translateY(-1px);
    }}
    div.stButton > button[kind="secondary"]:first-of-type {{ margin-top: 0 !important; }}

    /* ── Guest note + switch text ──────────────────────────────────────── */
    .gg-guest-note {{
        text-align: center; font-size: 12.5px;
        color: #94A3B8; margin-top: 12px; margin-bottom: 24px;
    }}
    .gg-auth-switch {{
        text-align: center; font-size: 13.5px; color: #64748B;
        margin-bottom: 12px;
    }}

    /* ── Streamlit cleanup ─────────────────────────────────────────────── */
    [data-testid="stForm"] {{
        border: none !important; padding: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }}
    [data-testid="stVerticalBlock"] > div {{ gap: 0 !important; }}
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        font-size: 13.5px !important;
        margin-bottom: 12px !important;
        margin-top: 6px !important;
    }}

    @media (prefers-reduced-motion: reduce) {{
        * {{ transition: none !important; animation: none !important; }}
    }}

    @media (max-width: 620px) {{
        [data-testid="stMainBlockContainer"], .block-container {{
            padding: 20px 14px 40px 14px !important;
        }}
        .gg-hero-banner {{ padding: 26px 22px 22px 22px; }}
        .gg-hero-headline {{ font-size: 21px; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def _hero_banner(c: dict):
    try:
        mark_svg = icon_svg("brain", 18, "#ffffff")
    except Exception:
        mark_svg = '<span style="color:#ffffff;font-size:16px;">◆</span>'
    try:
        check_svg = icon_svg("check", 11, "#7FB2FF")
    except Exception:
        check_svg = '<span style="color:#7FB2FF;font-size:10px;line-height:18px;">✓</span>'

    st.markdown(f"""
        <div class="gg-hero-banner">
            <div class="gg-hero-brand">
                {mark_svg}
                <span class="gg-hero-brand-name">GyanGrid AI</span>
            </div>
            <div class="gg-hero-headline">
                Understand any<br><span class="gg-accent-line">research paper</span><br>in minutes, not hours.
            </div>
            <div class="gg-hero-desc">
                Upload a paper and get grounded summaries, sourced Q&amp;A, and citation
                insight — in English or বাংলা.
            </div>
            <div class="gg-hero-checklist">
                <div class="gg-hero-check-item">
                    <span class="gg-hero-check-icon">{check_svg}</span>
                    Grounded Q&amp;A, cited directly from the source paper
                </div>
                <div class="gg-hero-check-item">
                    <span class="gg-hero-check-icon">{check_svg}</span>
                    Structured analysis: novelty, gaps, future work
                </div>
                <div class="gg-hero-check-item">
                    <span class="gg-hero-check-icon">{check_svg}</span>
                    Bilingual output — English and Bangla
                </div>
            </div>
            <div class="gg-hero-divider"></div>
            <div class="gg-hero-trust">Trusted by researchers working in low-resource NLP.</div>
        </div>
    """, unsafe_allow_html=True)


def render_login_page():
    c = theme_colors()
    _inject_login_css(c)

    if "login_show_pw" not in st.session_state:
        st.session_state.login_show_pw = False

    _hero_banner(c)

    st.markdown("""
        <div class="gg-welcome-title">Welcome back</div>
        <div class="gg-welcome-sub">Log in to continue analyzing your research papers.</div>
    """, unsafe_allow_html=True)

    # ── Login form ────────────────────────────────────────────────────────
    with st.form("gg_login_form", border=False):
        st.markdown('<span class="gg-field-label">Email</span>', unsafe_allow_html=True)
        email = st.text_input(
            "Email", key="login_email",
            placeholder="you@example.com",
            label_visibility="collapsed"
        )

        st.markdown('<span class="gg-field-label">Password</span>', unsafe_allow_html=True)
        pw_type = "text" if st.session_state.login_show_pw else "password"

        st.markdown('<div class="gg-pw-row">', unsafe_allow_html=True)
        pw_col, eye_col = st.columns([9, 1], gap="small")
        with pw_col:
            password = st.text_input(
                "Password", key="login_password", type=pw_type,
                placeholder="••••••••", label_visibility="collapsed"
            )
        with eye_col:
            eye_label = "🙈" if st.session_state.login_show_pw else "👁"
            if st.form_submit_button(eye_label):
                st.session_state.login_show_pw = not st.session_state.login_show_pw
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<a class="gg-forgot">Forgot password?</a>', unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "Log in", use_container_width=True, type="primary"
        )

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            # TODO: replace with real Supabase auth.sign_in_with_password()
            st.session_state.auth_status = "user"
            st.session_state.user_email = email
            st.session_state.user_name = email.split("@")[0]
            st.rerun()

    # ── Divider ───────────────────────────────────────────────────────────
    st.markdown("""
        <div class="gg-auth-divider">
            <div class="gg-div-line"></div>
            <span class="gg-div-text">OR CONTINUE WITH</span>
            <div class="gg-div-line"></div>
        </div>
    """, unsafe_allow_html=True)

    # ── Google ────────────────────────────────────────────────────────────
    if st.button("🔵  Continue with Google", key="login_google_btn",
                 use_container_width=True):
        if "auth" in st.secrets:
            st.login()
        else:
            st.info("Google login isn't configured yet — add [auth] to .streamlit/secrets.toml.")

    # ── Guest ─────────────────────────────────────────────────────────────
    if st.button("Continue as Guest", key="login_guest_btn",
                 use_container_width=True):
        st.session_state.auth_status = "guest"
        st.rerun()
    st.markdown('<p class="gg-guest-note">Guest mode — uploads won\'t be saved between sessions.</p>',
                unsafe_allow_html=True)

    # ── Switch to sign-up ─────────────────────────────────────────────────
    st.markdown('<div class="gg-auth-switch">Don\'t have an account?</div>',
                unsafe_allow_html=True)
    if st.button("Create account →", key="go_to_signup_btn",
                 use_container_width=True):
        st.session_state.auth_view = "signup"
        st.rerun()
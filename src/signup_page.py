"""
Sign-up page for GyanGrid AI.

Renders the same centered auth card style as login_page.py, but for new
account creation: email, password, confirm password, a sign-up button,
social sign-up buttons with real Google/Apple marks, and a link back to
Log In.

--------------------------------------------------------------------------
v2 audit / rebuild notes — kept in lockstep with login_page.py
--------------------------------------------------------------------------
Same 8px spacing scale and shared control tokens as the login page:
  - CARD_MAX_WIDTH = 840px, CARD_PADDING = 56px 64px
  - CONTROL_HEIGHT = 56px for every input AND every button
  - RADIUS_CARD = 20px, RADIUS_CONTROL = 14px, RADIUS_PILL = 12px

Fixes applied: vertical + horizontal centering of the card, unified
input/button sizing (email, password, confirm-password, Sign Up, Google,
Apple, Guest are all identical height/radius/typography), a balanced OR
divider, room reserved for the native password reveal-icon on both
password fields, and a footer where "Already have an account?" and the
"Log In" button sit on one aligned line via st.columns instead of a tiny
floating link.

Note on approach: same as login_page.py — the card look is applied
directly to Streamlit's own `div.block-container` rather than a separate
opened/closed `<div>` via st.html, since st.html() renders each call as
its own isolated element and doesn't actually nest later widgets inside
it. The Google/Apple logos are drawn as CSS ::before backgrounds pinned
onto each button by its Streamlit `key`, since st.button() only accepts
a plain text label.

Wiring notes:
- On "Sign Up", this does placeholder validation (valid-ish email,
  password length, passwords match) and then sets
  st.session_state.auth_status = "user". Swap _validate_signup() out for
  real account creation (Supabase, Firebase, etc.) when that's wired in.
- "Continue with Google" / "Continue with Apple" are left as visual
  placeholders (no OAuth wired yet), same as on the login page.
- Clicking "Log In" sets auth_view -> "login" and reruns; app.py reads
  st.session_state.auth_view to decide which page to show.
"""

import base64
import streamlit as st
from src.ui_theme import theme_colors, icon_svg

# ── Google "G" mark (official 4-colour logo) and Apple silhouette ───────
# Kept as an identical copy of login_page.py's versions (rather than a
# shared import) so this file can be styled independently if the two
# pages ever diverge.
_GOOGLE_G_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12
c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24
c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
<path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657
C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
<path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36
c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
<path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571
c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
</svg>"""

_APPLE_SILHOUETTE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
<path d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.57-.12 0-.23-.02-.3-.03
-.014-.11-.032-.23-.032-.36 0-1.09.55-2.2 1.19-2.98.7-.85 1.99-1.51 3.014-1.55.019.087.03.187.03.27z
M20.929 17.14c-.06.13-.32.86-1.02 1.87-.61.89-1.28 1.87-2.14 1.87-.85 0-1.11-.51-2.06-.51-.98 0-1.29.51
-2.08.51-.83 0-1.53-.94-2.14-1.83-1.6-2.3-2.82-6.5-1.18-9.34.81-1.4 2.28-2.28 3.85-2.31.86-.02 1.66.58
2.19.58.51 0 1.5-.72 2.53-.61.43.02 1.65.17 2.43 1.31-.06.04-1.45.85-1.43 2.52.02 2 1.75 2.67 1.77 2.68
-.02.06-.28.96-.94 1.9z"/>
</svg>"""


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _google_icon_uri() -> str:
    return _data_uri(_GOOGLE_G_SVG)


def _apple_icon_uri(color: str) -> str:
    return _data_uri(_APPLE_SILHOUETTE_SVG.format(color=color))


def _inject_auth_css():
    c = theme_colors()
    google_uri = _google_icon_uri()
    apple_uri = _apple_icon_uri(c["text_primary"])

    st.html(f"""
    <style>
    /* ============================================================
       LAYOUT: center the card horizontally AND vertically, and
       kill Streamlit's default top/bottom dead-space.
       ============================================================ */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {{
        min-height: 100vh;
    }}
    [data-testid="stMain"],
    section.main {{
        display: flex !important;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
    }}
    div.block-container {{
        width: 100%;
        max-width: 840px !important;
        margin: 32px auto !important;
        padding: 56px 64px !important;
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 20px;
        box-shadow: 0 24px 56px rgba(15, 23, 42, 0.14);
    }}

    /* ============================================================
       TYPOGRAPHY HIERARCHY
       ============================================================ */
    .gg-auth-logo {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-weight: 700;
        font-size: 26px;
        color: {c['text_primary']};
        margin-bottom: 32px;
    }}
    .gg-auth-title {{
        text-align: center;
        font-size: 40px;
        font-weight: 700;
        line-height: 1.25;
        color: {c['text_primary']};
        margin-bottom: 12px;
    }}
    .gg-auth-subtitle {{
        text-align: center;
        font-size: 19px;
        color: {c['text_secondary']};
        margin-bottom: 40px;
        line-height: 1.55;
        padding: 0 16px;
    }}

    /* ============================================================
       FORM FIELDS — identical width/height/radius across the board
       ============================================================ */
    label, .stTextInput label p, [data-testid="stWidgetLabel"] p {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: {c['text_primary']};
        margin-bottom: 6px !important;
    }}
    div[data-testid="stTextInput"] {{
        margin-bottom: 16px !important;
    }}
    div[data-testid="stTextInput"] > div {{
        border-radius: 14px !important;
        border: 1.5px solid {c['border']} !important;
        background: {c['surface']} !important;
        box-shadow: none !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
        position: relative !important;
        display: flex;
        align-items: center;
    }}
    div[data-testid="stTextInput"] > div > div {{
        border: none !important;
        box-shadow: none !important;
        width: 100%;
    }}
    div[data-testid="stTextInput"] > div:hover {{
        border-color: color-mix(in srgb, {c['text_primary']} 35%, {c['border']}) !important;
    }}
    div[data-testid="stTextInput"] input {{
        font-size: 18px !important;
        height: 64px !important;
        padding: 0 20px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: none !important;
        box-sizing: border-box;
    }}
    /* Leave clear room for Streamlit's native reveal-password icon on
       both the password and confirm-password fields. */
    div[data-testid="stTextInput"] input[type="password"] {{
        padding-right: 56px !important;
    }}
    /* Reveal-password icon: anchor to the bordered box above (its nearest
       positioned ancestor) so top:50% actually centers against the real
       64px-tall field, instead of collapsing to the top edge. */
    div[data-testid="stTextInput"] > div button {{
        position: absolute !important;
        right: 14px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        margin: 0 !important;
        height: auto !important;
        min-height: 0 !important;
        width: auto !important;
        padding: 4px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2;
    }}
    div[data-testid="stTextInput"] > div:focus-within {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 4px color-mix(in srgb, {c['accent']} 22%, transparent) !important;
    }}

    /* ============================================================
       BUTTONS — every button (primary, social, guest) shares the
       same height/radius/typography so nothing looks mismatched.
       ============================================================ */
    div.stButton {{ margin-bottom: 16px !important; }}
    div.stButton > button, div.stDownloadButton > button {{
        width: 100% !important;
        height: 64px !important;
        min-height: 64px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border-radius: 14px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: filter 0.15s ease, box-shadow 0.15s ease, transform 0.05s ease;
    }}
    div.stButton > button:hover {{
        filter: brightness(0.97);
    }}
    div.stButton > button:active {{
        transform: translateY(1px);
    }}
    div.stButton > button:focus-visible {{
        outline: none !important;
        box-shadow: 0 0 0 4px color-mix(in srgb, {c['accent']} 30%, transparent) !important;
    }}

    /* Primary "Sign Up" button gets a touch of elevation on hover to
       read as the premium, primary call to action. */
    .st-key-signup_submit button {{
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }}
    .st-key-signup_submit button:hover {{
        box-shadow: 0 8px 20px color-mix(in srgb, {c['accent']} 35%, transparent);
    }}

    /* Balanced OR divider */
    .gg-auth-divider {{
        display: flex;
        align-items: center;
        text-align: center;
        color: {c['text_muted']};
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin: 32px 0;
    }}
    .gg-auth-divider::before, .gg-auth-divider::after {{
        content: "";
        flex: 1;
        border-bottom: 1px solid {c['border']};
    }}
    .gg-auth-divider:not(:empty)::before {{ margin-right: 12px; }}
    .gg-auth-divider:not(:empty)::after {{ margin-left: 12px; }}

    /* Social buttons: identical size, radius, spacing, icon alignment */
    .st-key-signup_google button,
    .st-key-signup_apple button,
    .st-key-signup_guest button {{
        position: relative !important;
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_primary']} !important;
    }}
    .st-key-signup_google button::before,
    .st-key-signup_apple button::before {{
        content: "";
        position: absolute;
        left: 22px;
        top: 50%;
        transform: translateY(-50%);
        width: 22px;
        height: 22px;
        background-repeat: no-repeat;
        background-size: contain;
    }}
    .st-key-signup_google button::before {{
        background-image: url("{google_uri}");
    }}
    .st-key-signup_apple button::before {{
        background-color: {c['text_primary']};
        -webkit-mask-image: url("{apple_uri}");
        mask-image: url("{apple_uri}");
        -webkit-mask-size: contain;
        mask-size: contain;
        -webkit-mask-repeat: no-repeat;
        mask-repeat: no-repeat;
        -webkit-mask-position: center;
        mask-position: center;
    }}

    /* ============================================================
       FOOTER — text + inline "Log In" link on a single line via
       st.columns(vertical_alignment="center"); columns are sized
       tightly around their content (not 50/50) and the gap is
       collapsed to ~4px so the link starts right after the "?".
       ============================================================ */
    .gg-auth-footer-row [data-testid="stHorizontalBlock"] {{
        align-items: flex-end !important;
        justify-content: center;
        gap: 4px;
        margin-top: 32px;
        width: fit-content !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    .gg-auth-footer-row [data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }}
    .gg-auth-footer-text {{
        font-size: 17px;
        line-height: 1;
        color: {c['text_secondary']};
        text-align: right;
        white-space: nowrap;
        margin: 0;
        padding-bottom: 2px;
    }}
    /* Plain text link: no border, no background, no box — only the
       "Log In" label itself is clickable. Selector specificity is
       intentionally boosted (repeated class + attribute) so this beats
       Streamlit's own default secondary-button border, which otherwise
       has equal-or-higher specificity than a single class selector. */
    div.stButton.st-key-signup_goto_login button,
    .st-key-signup_goto_login button[kind] {{
        height: auto !important;
        min-height: 0 !important;
        padding: 0 !important;
        padding-bottom: 2px !important;
        width: auto !important;
        font-size: 17px !important;
        font-weight: 600 !important;
        border-radius: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: {c['accent']} !important;
        border: 0 !important;
        border-width: 0 !important;
        border-style: none !important;
        border-color: transparent !important;
        box-shadow: none !important;
        outline: none !important;
        text-decoration: underline;
        line-height: 1;
    }}
    div.stButton.st-key-signup_goto_login button:hover,
    .st-key-signup_goto_login button[kind]:hover {{
        filter: brightness(0.9);
        box-shadow: none !important;
        border: 0 !important;
    }}
    .st-key-signup_goto_login button:focus-visible {{
        box-shadow: 0 0 0 3px color-mix(in srgb, {c['accent']} 30%, transparent) !important;
        border-radius: 4px !important;
    }}
    .st-key-signup_goto_login {{
        display: flex;
        justify-content: flex-start;
    }}

    [data-testid="stAlertContentInfo"] p, [data-testid="stAlertContentError"] p {{
        font-size: 16px !important;
    }}
    </style>
    """)


def _validate_signup(email: str, password: str, confirm: str) -> str | None:
    """Placeholder sign-up validation. Returns an error message, or None
    if everything looks acceptable. Replace with real account creation
    (and server-side validation) later."""
    if not email or "@" not in email:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password != confirm:
        return "Passwords do not match."
    return None


def render_signup_page():
    c = theme_colors()
    _inject_auth_css()

    st.html(f"""
    <div class="gg-auth-logo">{icon_svg('brain', 28, c['accent'])}GyanGrid AI</div>
    <div class="gg-auth-title">Create your account</div>
    <div class="gg-auth-subtitle">Sign up to start uploading papers and getting AI-powered research insights.</div>
    """)

    email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
    password = st.text_input(
        "Password", placeholder="Create a password", type="password", key="signup_password"
    )
    confirm = st.text_input(
        "Confirm Password", placeholder="Re-enter your password", type="password", key="signup_confirm"
    )

    if st.button("Sign Up", type="primary", use_container_width=True, key="signup_submit"):
        error = _validate_signup(email, password, confirm)
        if error:
            st.error(error)
        else:
            st.session_state.auth_status = "user"
            st.session_state.user_email = email
            st.rerun()

    st.html('<div class="gg-auth-divider">OR</div>')

    if st.button("Continue with Google", use_container_width=True, key="signup_google"):
        st.info("Google sign-up isn't connected yet — coming soon.")
    if st.button("Continue with Apple", use_container_width=True, key="signup_apple"):
        st.info("Apple sign-up isn't connected yet — coming soon.")
    if st.button("Continue as Guest", use_container_width=True, key="signup_guest"):
        st.session_state.auth_status = "guest"
        st.rerun()

    st.html('<div class="gg-auth-footer-row">')
    col_text, col_btn = st.columns([1, 1], gap="small", vertical_alignment="center")
    with col_text:
        st.html('<p class="gg-auth-footer-text">Already have an account?</p>')
    with col_btn:
        if st.button("Log In", key="signup_goto_login", use_container_width=False):
            st.session_state.auth_view = "login"
            st.rerun()
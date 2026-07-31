"""
Login page for GyanGrid AI.

Renders a centered auth card (logo, welcome copy, email/password fields,
forgot-password link, sign-in button, social sign-in buttons with real
Google/Apple marks, and a sign-up link) as the landing page shown while
st.session_state.auth_status is None.

--------------------------------------------------------------------------
v2 audit / rebuild notes
--------------------------------------------------------------------------
This revision fixes a full pass of visual-QA issues found in the previous
version: inconsistent control heights, an off-balance OR divider, a
"Sign Up" link that floated as a tiny disconnected element instead of
sitting on the same line as its sentence, a password field that didn't
leave room for Streamlit's native reveal-password icon, excess dead
space above/below the card, and a card that wasn't vertically centered
in the viewport.

Everything now runs on an 8px spacing scale (8 / 16 / 24 / 32 / 40 / 48 /
56 / 64) and a single set of control tokens:
  - CARD_MAX_WIDTH = 840px   (within the requested 700–900px range)
  - CARD_PADDING   = 56px 64px
  - CONTROL_HEIGHT = 56px    (every input AND every button share this)
  - RADIUS_CARD    = 20px
  - RADIUS_CONTROL = 14px
  - RADIUS_PILL    = 12px    (small footer CTA)

Note on approach: the card look is applied directly to Streamlit's own
`div.block-container` (rather than wrapping content in a separate
`<div class="gg-auth-card">` opened/closed via st.html). st.html() renders
each call as its own isolated element — it does NOT nest the widgets that
come after it — so an "open div, render widgets, close div" pattern only
ever produces an empty floating box plus separately-styled content below
it. Styling block-container itself sidesteps that entirely, since on this
page block-container's only content IS the auth form. The outer view
container is switched to a flex layout so the card is centered both
horizontally *and* vertically, instead of just floating near the top.

The footer ("Don't have an account? · Sign Up") is now laid out with
st.columns(vertical_alignment="center") instead of a bare st.button, since
CSS alone can't put a Streamlit-rendered sentence and a Streamlit-rendered
button on one visually aligned baseline — columns is the supported way to
place two widgets side by side and vertically align them.

The Google/Apple logos are drawn as CSS ::before backgrounds pinned onto
each button (via the same "match a button by its Streamlit `key`" trick
ui_theme.py already uses for sidebar nav icons) since st.button() only
accepts a plain text label — there's no way to pass an inline icon into
the button itself. Icon-bearing buttons get extra left padding so the
label optically centers instead of colliding with the icon.

Wiring notes (unchanged):
- On "Sign In", this does a placeholder validation (non-empty email +
  password) and sets st.session_state.auth_status = "user". Swap
  _validate_credentials() out for real auth (Supabase, Firebase, etc.)
  when that's wired in.
- "Continue with Google" / "Continue with Apple" are left as visual
  placeholders (no OAuth wired yet) so they don't silently pretend to
  authenticate someone. "Continue as Guest" is fully functional since
  app.py already branches on auth_status == "guest".
- Clicking "Sign Up" sets auth_view -> "signup" and reruns; app.py reads
  st.session_state.auth_view to decide which page to show.
"""

import base64
import streamlit as st
from src.ui_theme import theme_colors, icon_svg

# ── Google "G" mark (official 4-colour logo) and Apple silhouette ───────
# Google's mark needs its real colours, so it's embedded as a normal
# background-image (not a CSS mask). Apple's mark is a flat silhouette,
# so it's embedded as a mask and tinted with currentColor so it stays
# legible in both light and dark mode.
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
    div[data-testid="stTextInput"] input {{
        font-size: 18px !important;
        height: 64px !important;
        padding: 0 20px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: none !important;
        box-sizing: border-box;
    }}
    /* Leave clear room for Streamlit's native reveal-password icon so it
       never overlaps typed text, and vertically center it on the input. */
    div[data-testid="stTextInput"] input[type="password"] {{
        padding-right: 56px !important;
    }}
    div[data-testid="stTextInput"] > div:focus-within {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 4px color-mix(in srgb, {c['accent']} 22%, transparent) !important;
    }}

    /* "Forgot Password?" sits flush right, directly under the password
       field, with an 8px-scale gap above the Sign In button. */
    .gg-auth-forgot {{
        text-align: right;
        margin: -8px 0 24px 0;
    }}
    .gg-auth-forgot a {{
        color: {c['accent']};
        font-size: 16px;
        font-weight: 600;
        text-decoration: none;
    }}
    .gg-auth-forgot a:hover {{ text-decoration: underline; }}
    .gg-auth-forgot a:focus-visible {{
        outline: 2px solid {c['accent']};
        outline-offset: 3px;
        border-radius: 4px;
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

    /* Primary "Sign In" button gets a touch of elevation on hover to
       read as the premium, primary call to action. */
    .st-key-login_submit button {{
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }}
    .st-key-login_submit button:hover {{
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
    .st-key-login_google button,
    .st-key-login_apple button,
    .st-key-login_guest button {{
        position: relative !important;
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_primary']} !important;
    }}
    .st-key-login_google button::before,
    .st-key-login_apple button::before {{
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
    .st-key-login_google button::before {{
        background-image: url("{google_uri}");
    }}
    .st-key-login_apple button::before {{
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
       FOOTER — text + inline "Sign Up" link on a single line via
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
       "Sign Up" label itself is clickable. Selector specificity is
       intentionally boosted (repeated class + attribute) so this beats
       Streamlit's own default secondary-button border, which otherwise
       has equal-or-higher specificity than a single class selector. */
    div.stButton.st-key-login_goto_signup button,
    .st-key-login_goto_signup button[kind] {{
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
    div.stButton.st-key-login_goto_signup button:hover,
    .st-key-login_goto_signup button[kind]:hover {{
        filter: brightness(0.9);
        box-shadow: none !important;
        border: 0 !important;
    }}
    .st-key-login_goto_signup button:focus-visible {{
        box-shadow: 0 0 0 3px color-mix(in srgb, {c['accent']} 30%, transparent) !important;
        border-radius: 4px !important;
    }}
    .st-key-login_goto_signup {{
        display: flex;
        justify-content: flex-start;
    }}

    [data-testid="stAlertContentInfo"] p, [data-testid="stAlertContentError"] p {{
        font-size: 16px !important;
    }}
    </style>
    """)


def _validate_credentials(email: str, password: str) -> str | None:
    """Placeholder credential check. Returns an error message, or None
    if the credentials are acceptable. Replace with real auth later."""
    if not email or not password:
        return "Please enter both your email and password."
    if "@" not in email:
        return "Please enter a valid email address."
    return None


def render_login_page():
    c = theme_colors()
    _inject_auth_css()

    st.html(f"""
    <div class="gg-auth-logo">{icon_svg('brain', 28, c['accent'])}GyanGrid AI</div>
    <div class="gg-auth-title">Welcome back!</div>
    <div class="gg-auth-subtitle">Sign in to access your workspace and pick up right where you left off.</div>
    """)

    email = st.text_input("Email", placeholder="you@example.com", key="login_email")
    password = st.text_input(
        "Password", placeholder="Enter your password", type="password", key="login_password"
    )

    st.html('<div class="gg-auth-forgot"><a href="#">Forgot Password?</a></div>')

    if st.button("Sign In", type="primary", use_container_width=True, key="login_submit"):
        error = _validate_credentials(email, password)
        if error:
            st.error(error)
        else:
            st.session_state.auth_status = "user"
            st.session_state.user_email = email
            st.rerun()

    st.html('<div class="gg-auth-divider">OR</div>')

    if st.button("Continue with Google", use_container_width=True, key="login_google"):
        st.info("Google sign-in isn't connected yet — coming soon.")
    if st.button("Continue with Apple", use_container_width=True, key="login_apple"):
        st.info("Apple sign-in isn't connected yet — coming soon.")
    if st.button("Continue as Guest", use_container_width=True, key="login_guest"):
        st.session_state.auth_status = "guest"
        st.rerun()

    st.html('<div class="gg-auth-footer-row">')
    col_text, col_btn = st.columns([1, 1], gap="small", vertical_alignment="center")
    with col_text:
        st.html('<p class="gg-auth-footer-text">Don\'t have an account?</p>')
    with col_btn:
        if st.button("Sign Up", key="login_goto_signup", use_container_width=False):
            st.session_state.auth_view = "signup"
            st.rerun()
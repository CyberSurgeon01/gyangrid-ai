"""
Sign-up page for GyanGrid AI.

Renders the same centered auth card style as login_page.py, but for new
account creation: email, password, confirm password, a sign-up button,
social sign-up button with real Google mark, and a link back to
Log In.

--------------------------------------------------------------------------
v2 audit / rebuild notes — kept in lockstep with login_page.py
--------------------------------------------------------------------------
Same 8px spacing scale and shared control tokens as the login page:
  - CARD_MAX_WIDTH = 880px, CARD_PADDING = 64px 72px
  - CONTROL_HEIGHT = 64px for every input AND every button
  - RADIUS_CARD = 24px, RADIUS_CONTROL = 14px, RADIUS_PILL = 12px

v3 scale-up: same 30–40% bolder pass as login_page.py — larger logo/
heading/subtitle, 17px labels, 20px button text, and wider section
spacing (field gaps 16→24px, button gaps 16→20px).

Fixes applied: vertical + horizontal centering of the card, unified
input/button sizing (email, password, confirm-password, Sign Up, Google,
Guest are all identical height/radius/typography), a balanced OR
divider, room reserved for the native password reveal-icon on both
password fields, and a footer where "Already have an account?" and the
"Log In" button sit on one aligned line via st.columns instead of a tiny
floating link.

Note on approach: same as login_page.py — the card look is applied
directly to Streamlit's own `div.block-container` rather than a separate
opened/closed `<div>` via st.html, since st.html() renders each call as
its own isolated element and doesn't actually nest later widgets inside
it. The Google logo is drawn as a CSS ::before background pinned
onto the button by its Streamlit `key`, since st.button() only accepts
a plain text label.

Wiring notes:
- On "Sign Up", this validates input then calls Supabase's sign_up() via
  _sign_up(). If Supabase requires email confirmation, the user is
  shown a "check your inbox" message instead of being logged in
  immediately.
- "Continue with Google" is left as a visual placeholder (no OAuth wired
  yet), same as on the login page.
- Clicking "Log In" sets auth_view -> "login" and reruns; app.py reads
  st.session_state.auth_view to decide which page to show.
"""

import base64
import streamlit as st
import streamlit.components.v1 as components
from src.ui_theme import theme_colors, icon_svg
from src.supabase_client import get_supabase

# ── Google "G" mark (official 4-colour logo) ───────
# Kept as an identical copy of login_page.py's version (rather than a
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

def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _google_icon_uri() -> str:
    return _data_uri(_GOOGLE_G_SVG)


def _inject_auth_css():
    c = theme_colors()
    google_uri = _google_icon_uri()

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
        max-width: 880px !important;
        margin: 40px auto !important;
        padding: 64px 72px !important;
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 24px;
        box-shadow: 0 32px 72px rgba(15, 23, 42, 0.16);
    }}

    /* ============================================================
       TYPOGRAPHY HIERARCHY
       ============================================================ */
    .gg-auth-logo {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        font-weight: 700;
        font-size: 34px;
        color: {c['text_primary']};
        margin-bottom: 40px;
    }}
    .gg-auth-title {{
        text-align: center;
        font-size: 60px;
        font-weight: 700;
        line-height: 1.2;
        color: {c['text_primary']};
        margin-bottom: 16px;
    }}
    .gg-auth-subtitle {{
        text-align: center;
        font-size: 21px;
        color: {c['text_secondary']};
        margin-bottom: 48px;
        line-height: 1.55;
        padding: 0 16px;
    }}

    /* ============================================================
       FORM FIELDS — identical width/height/radius across the board
       ============================================================ */
    label, .stTextInput label p, [data-testid="stWidgetLabel"] p {{
        font-size: 17px !important;
        font-weight: 600 !important;
        color: {c['text_primary']};
        margin-bottom: 8px !important;
    }}
    div[data-testid="stTextInput"] {{
        margin-bottom: 24px !important;
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
    div.stButton {{ margin-bottom: 20px !important; }}
    div.stButton > button, div.stDownloadButton > button {{
        width: 100% !important;
        height: 64px !important;
        min-height: 64px !important;
        font-size: 20px !important;
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
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin: 36px 0;
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
    .st-key-signup_guest button {{
        position: relative !important;
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_primary']} !important;
    }}
    .st-key-signup_google button::before {{
        content: "";
        position: absolute;
        left: 26px;
        top: 50%;
        transform: translateY(-50%);
        width: 24px;
        height: 24px;
        background-repeat: no-repeat;
        background-size: contain;
        background-image: url("{google_uri}");
    }}

    /* ============================================================
       FOOTER — text + inline "Log In" link on a single line via
       st.columns(vertical_alignment="center"); columns are sized
       tightly around their content (not 50/50) and the gap is
       collapsed to ~4px so the link starts right after the "?".
       ============================================================ */
    .gg-auth-footer-row [data-testid="stHorizontalBlock"] {{
        align-items: center !important;
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
        font-size: 18px;
        line-height: 1;
        color: {c['text_secondary']};
        text-align: right;
        white-space: nowrap;
        margin: 0;
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
        width: auto !important;
        font-size: 18px !important;
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
    /* Hide Streamlit's own "Press Enter to apply · X/Y" hint that
       appears under a text input while it hasn't been committed yet —
       it reads as stray UI noise on this form. */
    [data-testid="InputInstructions"] {{
        display: none !important;
    }}
    </style>
    """)


def _redirect_url() -> str:
    """URL Supabase should send the user back to after Google auth. See
    the matching helper in login_page.py for the full explanation."""
    return st.secrets.get("APP_URL", "https://gyangrid-ai.streamlit.app")


def _send_signup_otp(email: str, password: str, confirm: str) -> str | None:
    """Step 1: validates input, then creates the account (with the
    user's real, final password already set) and asks Supabase to email
    a verification code. The account exists but stays unconfirmed/
    unusable until the code is verified in step 2."""
    if not email or "@" not in email:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password != confirm:
        return "Passwords do not match."

    try:
        sb = get_supabase()
        result = sb.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            return "An account with this email already exists. Please use a different email or log in instead."
        return f"Couldn't send the code: {msg}"

    # Supabase doesn't raise an error for an already-registered email when
    # email confirmation is on (to avoid leaking which emails are
    # registered) — instead it silently returns a user with an empty
    # `identities` list. That's the signal we check for here.
    identities = getattr(result.user, "identities", None) if result.user else None
    if identities is not None and len(identities) == 0:
        return "An account with this email already exists. Please use a different email or log in instead."

    st.session_state.signup_otp_email = email
    st.session_state.signup_otp_sent = True
    return None


def _verify_signup_otp(email: str, token: str) -> str | None:
    """Step 2: verifies the 6-digit code, which finalizes the account.
    Supabase's verify_otp() call inherently authenticates the user (it
    creates a persisted session as a side effect) — but app.py restores
    that session automatically on the very next rerun and logs the user
    straight into the app, skipping the intended "go log in yourself"
    hand-off. Explicitly signing out right after verifying avoids that:
    the account is confirmed and ready, but no live session is left
    behind for app.py to pick up."""
    if not token or not token.strip():
        return "Please enter the verification code."

    try:
        sb = get_supabase()
        result = sb.auth.verify_otp({
            "email": email,
            "token": token.strip(),
            "type": "signup",
        })
    except Exception as e:
        msg = str(e)
        if "rate limit" in msg.lower():
            return "Too many attempts. Please wait a moment and try again."
        # Supabase returns the same generic error ("Token has expired or
        # is invalid") for both a wrong code and an expired one, so there's
        # no reliable way to tell them apart from the message alone.
        return "Incorrect or expired code. Please double-check it, or resend a new one below."

    if not result.user:
        return "Verification failed. Please try again."

    try:
        sb.auth.sign_out()
    except Exception:
        pass  # best-effort — even if this fails, app.py will just log them in early

    for key in ("signup_otp_email", "signup_otp_sent", "signup_otp", "signup_password", "signup_confirm"):
        st.session_state.pop(key, None)
    st.session_state.signup_complete = True
    return None


def _resend_signup_otp(email: str) -> str | None:
    """Asks Supabase to re-send the sign-up verification code."""
    try:
        sb = get_supabase()
        sb.auth.resend({"type": "signup", "email": email})
    except Exception as e:
        return f"Couldn't resend the code: {e}"
    return None


def _render_signup_header(c, title: str, subtitle: str):
    st.html(f"""
    <div class="gg-auth-logo">{icon_svg('brain', 44, c['accent'])}GyanGrid AI</div>
    <div class="gg-auth-title">{title}</div>
    <div class="gg-auth-subtitle">{subtitle}</div>
    """)


def _render_email_step(c):
    """Step 1 UI: email, password, confirm password, and a Send OTP
    button (this is what actually creates the account)."""
    _render_signup_header(
        c, "Create your account",
        "Sign up to start uploading papers and getting AI-powered research insights.",
    )

    email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
    password = st.text_input(
        "Password", placeholder="Create a password", type="password", key="signup_password"
    )
    confirm = st.text_input(
        "Confirm Password", placeholder="Re-enter your password", type="password", key="signup_confirm"
    )

    if st.button("Send OTP", type="primary", use_container_width=True, key="signup_send_otp"):
        with st.spinner("Sending verification code..."):
            error = _send_signup_otp(email, password, confirm)
        if error:
            st.error(error)
        else:
            st.rerun()

    st.html('<div class="gg-auth-divider">OR</div>')

    if st.button("Continue with Google", use_container_width=True, key="signup_google"):
        try:
            sb = get_supabase()
            result = sb.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {"redirect_to": _redirect_url()},
            })
            components.html(f'<script>window.top.location.href = "{result.url}";</script>', height=0)
        except Exception as e:
            st.error(f"Google sign-up failed to start: {e}")
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


def _render_otp_step(c, email: str):
    """Step 2 UI: shown once a code has been emailed. Verifying here
    finalizes account creation and sends the user to the login page —
    it does not log them in directly (see _verify_signup_otp)."""
    _render_signup_header(
        c, "Enter verification code",
        f"We sent a code to <b>{email}</b>. Verifying it creates your account — you'll log in right after.",
    )

    otp = st.text_input(
        "Verification code", placeholder="000000", max_chars=10, key="signup_otp",
    )

    if st.button("Verify", type="primary", use_container_width=True, key="signup_otp_verify"):
        with st.spinner("Verifying..."):
            error = _verify_signup_otp(email, otp)
        if error:
            st.error(error)
        else:
            st.session_state.auth_view = "login"
            st.rerun()

    st.html('<p class="gg-auth-footer-text" style="text-align:center; margin-top:20px;">Didn\'t receive the code?</p>')
    if st.button("Resend code", use_container_width=True, key="signup_otp_resend"):
        with st.spinner("Resending..."):
            error = _resend_signup_otp(email)
        if error:
            st.error(error)
        else:
            st.success("A new code is on its way.")

    st.html('<div class="gg-auth-footer-row">')
    col_text, col_btn = st.columns([1, 1], gap="small", vertical_alignment="center")
    with col_text:
        st.html('<p class="gg-auth-footer-text">Wrong email?</p>')
    with col_btn:
        if st.button("Change email", key="signup_otp_back", use_container_width=False):
            for key in ("signup_otp_email", "signup_otp_sent"):
                st.session_state.pop(key, None)
            st.rerun()


def render_signup_page():
    c = theme_colors()
    _inject_auth_css()

    otp_email = st.session_state.get("signup_otp_email")
    otp_sent = st.session_state.get("signup_otp_sent")

    if otp_sent and otp_email:
        _render_otp_step(c, otp_email)
    else:
        _render_email_step(c)
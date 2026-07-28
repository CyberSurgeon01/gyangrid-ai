"""
UI theme helpers for GyanGrid AI.

Injects flat, card-based CSS styling + provides render helpers so app.py can
build the dashboard layout without repeating raw HTML everywhere.

Icons are inline SVG (no external CDN) so they can never fail to load.
"""

import base64
import textwrap
import streamlit as st

# ── Design tokens ────────────────────────────────────────────────────────
COLORS = {
    "bg": "#f7f8fa",
    "surface": "#ffffff",
    "surface_muted": "#f1f2f5",
    "border": "#e3e5e9",
    "text_primary": "#1a1d24",
    "text_secondary": "#6b7280",
    "text_muted": "#9aa0aa",

    "accent": "#2f6fed",
    "accent_bg": "#eaf1fe",
    "accent_text": "#1d4fb8",

    "success": "#1d9e75",
    "success_bg": "#e1f5ee",
    "success_text": "#0f6e56",

    "warning": "#ba7517",
    "warning_bg": "#faeeda",
    "warning_text": "#854f0b",

    "pro": "#7f77dd",
    "pro_bg": "#eeedfe",
    "pro_text": "#3c3489",

    # icon tile colors (used on the Document overview metric tiles)
    "icon_blue": "#2f6fed",
    "icon_blue_bg": "#eaf1fe",
    "icon_green": "#1d9e75",
    "icon_green_bg": "#e1f5ee",
    "icon_purple": "#7f77dd",
    "icon_purple_bg": "#eeedfe",
    "icon_orange": "#e08a2c",
    "icon_orange_bg": "#fdf0e2",
    "icon_teal": "#1690a3",
    "icon_teal_bg": "#e2f2f5",
}

# ── Dark palette ──────────────────────────────────────────────────────
DARK_COLORS = {
    "bg": "#12141a",
    "surface": "#1b1e26",
    "surface_muted": "#232733",
    "border": "#2c3040",
    "text_primary": "#eef0f4",
    "text_secondary": "#a8adba",
    "text_muted": "#6f7585",

    "accent": "#5b8def",
    "accent_bg": "#1d2b46",
    "accent_text": "#8fb4f7",

    "success": "#37c495",
    "success_bg": "#12332a",
    "success_text": "#5fe0b8",

    "warning": "#e0a344",
    "warning_bg": "#3a2c14",
    "warning_text": "#f0c479",

    "pro": "#a79cf2",
    "pro_bg": "#241f3d",
    "pro_text": "#c3b8fb",

    "icon_blue": "#5b8def",
    "icon_blue_bg": "#1d2b46",
    "icon_green": "#37c495",
    "icon_green_bg": "#12332a",
    "icon_purple": "#a79cf2",
    "icon_purple_bg": "#241f3d",
    "icon_orange": "#e0a344",
    "icon_orange_bg": "#3a2c14",
    "icon_teal": "#3fb8cc",
    "icon_teal_bg": "#12303a",
}


def _colors() -> dict:
    """Returns the active color palette based on st.session_state.dark_mode."""
    return DARK_COLORS if st.session_state.get("dark_mode", False) else COLORS


# ── Inline SVG icon set (Feather-style, no external dependency) ─────────
_ICON_PATHS = {
    "brain": '<path d="M9 2a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5 3 3 0 0 0 2 5v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M15 2a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5 3 3 0 0 1-2 5v1a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>',
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    "upload": '<path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M4 21h16"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "bookmark": '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "sun": '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7"/><path d="M12 17h.01"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h8"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "sparkles": '<path d="M12 2l1.5 5L19 9l-5.5 2L12 16l-1.5-5L5 9l5.5-2z"/>',
    "quote": '<path d="M4 7c0-2.2 1.8-4 4-4v2c-1.1 0-2 .9-2 2v1h2v4H4V7z"/><path d="M14 7c0-2.2 1.8-4 4-4v2c-1.1 0-2 .9-2 2v1h2v4h-4V7z"/>',
    "download": '<path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M4 21h16"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    "eye": '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
}

_STROKE_ICONS = {
    "brain", "home", "upload", "message", "bookmark", "clock", "settings",
    "sun", "help", "file-text", "list", "layers", "grid", "download",
    "trash", "eye", "check",
}


def icon_svg(name: str, size: int = 20, color: str = "#1a1d24") -> str:
    """Returns a base64-encoded <img> tag for the given icon name. No
    external requests are made, so this can never fail to load — and since
    it's an <img>, not a raw <svg> element, it can't be stripped by any
    HTML sanitizer (unlike inline <svg>, which some Streamlit renderers do
    strip). Note: pass an explicit hex color; "currentColor" won't inherit
    correctly inside a base64 image."""
    path = _ICON_PATHS.get(name, "")
    if not path:
        return ""
    if name in _STROKE_ICONS:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
        )
    else:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="{color}" stroke="none">{path}</svg>'
        )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" '
        f'style="vertical-align:middle;display:inline-block;" />'
    )


TABLER_CDN = ""  # no longer used, kept for backwards compatibility


def inject_base_css():
    """Injects the global stylesheet. Call once, near the top of app.py."""
    c = _colors()
    css = f"""
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            background-color: {c['bg']} !important;
        }}
        [data-testid="stHeader"] {{ background: transparent !important; }}
        [data-testid="stAppViewContainer"] * {{
            color: {c['text_primary']};
        }}
        .block-container {{
            padding-top: 1.5rem;
            max-width: 1200px;
        }}

        .gg-topbar {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 14px;
            margin-bottom: 4px;
        }}
        .gg-topbar-icon {{
            width: 36px; height: 36px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: {c['surface']} !important;
            border: 1px solid {c['border']};
            color: {c['text_secondary']} !important;
        }}
        .gg-avatar {{
            width: 36px; height: 36px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: {c['accent']} !important;
            color: #ffffff !important;
            font-weight: 600;
            font-size: 14px;
        }}

        .gg-title {{
            font-size: 34px;
            font-weight: 600;
            color: {c['text_primary']} !important;
            margin-bottom: 2px;
        }}
        .gg-subtitle {{
            font-size: 17px;
            color: {c['text_secondary']} !important;
            margin-bottom: 24px;
        }}

        .gg-card {{
            background: {c['surface']} !important;
            border: 1px solid {c['border']};
            border-radius: 14px;
            padding: 28px 30px;
            margin-bottom: 20px;
        }}
        .gg-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 4px;
        }}
        .gg-card-header-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .gg-card h4 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: {c['text_primary']} !important;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .gg-card h4 svg {{
            color: {c['accent']} !important;
            flex-shrink: 0;
        }}
        .gg-caption {{
            font-size: 15px;
            color: {c['text_secondary']} !important;
            margin: 6px 0 18px 0;
        }}

        .gg-metric {{
            background: {c['surface_muted']} !important;
            border-radius: 10px;
            padding: 18px 18px;
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .gg-metric-icon {{
            width: 40px; height: 40px;
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }}
        .gg-metric .label {{
            font-size: 13.5px;
            color: {c['text_secondary']} !important;
            margin-bottom: 4px;
        }}
        .gg-metric .value {{
            font-size: 24px;
            font-weight: 600;
            color: {c['text_primary']} !important;
        }}

        .gg-pill {{
            display: inline-block;
            background: {c['surface_muted']} !important;
            color: {c['text_secondary']} !important;
            font-size: 14px;
            padding: 7px 16px;
            border-radius: 16px;
            margin: 0 8px 8px 0;
        }}

        .gg-struct-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 16px;
            padding: 11px 0;
            border-bottom: 1px solid {c['border']};
        }}
        .gg-struct-row:last-child {{ border-bottom: none; }}
        .gg-struct-row .left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .gg-struct-dot {{
            width: 8px; height: 8px;
            border-radius: 50%;
            background: {c['success']} !important;
            flex-shrink: 0;
        }}
        .gg-struct-index {{
            background: {c['surface_muted']} !important;
            color: {c['text_secondary']} !important;
            font-size: 13px;
            padding: 3px 10px;
            border-radius: 6px;
            border: 1px solid {c['border']};
        }}

        .gg-result {{
            border-radius: 10px;
            padding: 20px 22px;
            margin-bottom: 14px;
            min-height: 120px;
        }}
        .gg-result .rtitle {{
            font-size: 14px;
            font-weight: 600;
            margin: 0 0 8px 0;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        .gg-result p {{
            font-size: 15.5px;
            line-height: 1.6;
            margin: 0;
            color: {c['text_primary']} !important;
        }}
        .gg-result.success {{ background: {c['success_bg']} !important; }}
        .gg-result.success .rtitle {{ color: {c['success_text']} !important; }}
        .gg-result.warning {{ background: {c['warning_bg']} !important; }}
        .gg-result.warning .rtitle {{ color: {c['warning_text']} !important; }}
        .gg-result.pro {{ background: {c['pro_bg']} !important; }}
        .gg-result.pro .rtitle {{ color: {c['pro_text']} !important; }}
        .gg-result.accent {{ background: {c['accent_bg']} !important; }}
        .gg-result.accent .rtitle {{ color: {c['accent_text']} !important; }}

        section[data-testid="stSidebar"] {{
            background: {c['surface']} !important;
            border-right: 1px solid {c['border']};
            min-width: 260px !important;
        }}
        section[data-testid="stSidebar"] * {{
            color: {c['text_primary']} !important;
        }}

        .gg-logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 4px 20px 4px;
        }}
        .gg-logo svg {{ color: {c['accent']} !important; flex-shrink: 0; }}
        .gg-logo-text {{ display: flex; flex-direction: column; line-height: 1.2; }}
        .gg-logo-title {{ font-weight: 700; font-size: 17px; color: {c['text_primary']} !important; }}
        .gg-logo-sub {{ font-size: 12px; color: {c['text_muted']} !important; }}

        section[data-testid="stSidebar"] div.stButton > button {{
            justify-content: flex-start !important;
            text-align: left !important;
            border: none !important;
            background: transparent !important;
            font-weight: 500 !important;
            padding: 12px 16px !important;
            color: {c['text_secondary']} !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
            background: {c['accent_bg']} !important;
            color: {c['accent_text']} !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button:hover {{
            background: {c['surface_muted']} !important;
        }}

        div.stButton > button, div.stDownloadButton > button {{
            border-radius: 10px;
            border: 1px solid {c['border']};
            font-size: 16px;
            font-weight: 500;
            padding: 12px 22px;
            height: auto;
            min-height: 48px;
        }}
        div.stButton > button[kind="primary"] {{
            background: {c['accent']} !important;
            border-color: {c['accent']} !important;
            color: #ffffff !important;
        }}

        div[data-testid="stTextInput"] input {{
            font-size: 16px !important;
            padding: 12px 14px !important;
            height: auto !important;
        }}
        div[data-testid="stTextArea"] textarea {{
            font-size: 15px !important;
        }}
        label, .stRadio label, .stSlider label {{
            font-size: 15px !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            padding: 40px 24px !important;
            border-radius: 12px !important;
        }}
        [data-testid="stFileUploaderDropzone"] button {{
            font-size: 16px !important;
            padding: 12px 24px !important;
            min-height: 48px !important;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] span {{
            font-size: 16px !important;
        }}

        button[title*="mode"] {{
            width: 40px !important;
            height: 40px !important;
            min-height: 40px !important;
            padding: 0 !important;
            border-radius: 50% !important;
            font-size: 17px !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        /* Native Streamlit widgets - explicitly recolored so dark mode
           doesn't leave them stuck on a light background */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input {{
            background-color: {c['surface']} !important;
            color: {c['text_primary']} !important;
            border: 1px solid {c['border']} !important;
        }}
        div[data-baseweb="select"] > div {{
            background-color: {c['surface']} !important;
            border-color: {c['border']} !important;
            color: {c['text_primary']} !important;
        }}
        div[data-baseweb="popover"] ul,
        div[data-baseweb="menu"] {{
            background-color: {c['surface']} !important;
        }}
        [data-testid="stFileUploaderDropzone"] {{
            background-color: {c['surface_muted']} !important;
            border: 1px dashed {c['border']} !important;
        }}
        [data-testid="stExpander"] {{
            background-color: {c['surface']} !important;
            border: 1px solid {c['border']} !important;
            border-radius: 10px !important;
        }}
        div[data-testid="stJson"] {{
            background-color: {c['surface_muted']} !important;
        }}
        [data-testid="stAlert"] {{
            background-color: {c['surface_muted']} !important;
            border: 1px solid {c['border']} !important;
        }}
        .stSlider [data-baseweb="slider"] div[role="slider"] {{
            background-color: {c['accent']} !important;
        }}
        .stRadio [role="radiogroup"] label {{
            color: {c['text_primary']} !important;
        }}
        code, .stCodeBlock, pre {{
            background-color: {c['surface_muted']} !important;
            color: {c['text_primary']} !important;
        }}
        </style>
        """
    st.html(textwrap.dedent(css).strip())


def render_topbar():
    """Renders the top-right icon row: a working dark-mode toggle, a
    decorative help icon, and an avatar."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    c = _colors()

    spacer, toggle_col, help_col, avatar_col = st.columns([14, 1, 1, 1])
    with toggle_col:
        label = "🌙" if not st.session_state.dark_mode else "☀️"
        tooltip = "Currently light mode — click for dark" if not st.session_state.dark_mode else "Currently dark mode — click for light"
        if st.button(label, key="theme_toggle_btn", help=tooltip):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with help_col:
        st.html(f'<div class="gg-topbar-icon">{icon_svg("help", 18, c["text_secondary"])}</div>')
    with avatar_col:
        st.html('<div class="gg-avatar">RS</div>')


def render_sidebar_nav(default: str = "Dashboard") -> str:
    """Renders the logo header + clickable nav list in st.sidebar and
    returns the currently active page name."""
    items = [
        ("home", "Dashboard"),
        ("upload", "Upload paper"),
        ("message", "Q&A (RAG)"),
        ("sparkles", "AI analysis"),
        ("settings", "Settings"),
    ]
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = default

    c = _colors()
    with st.sidebar:
        st.html(
            f'<div class="gg-logo">{icon_svg("brain", 30, c["accent"])}'
            f'<div class="gg-logo-text">'
            f'<span class="gg-logo-title">GyanGrid AI</span>'
            f'<span class="gg-logo-sub">AI Research Assistant</span>'
            f'</div></div>'
        )
        for icon_name, label in items:
            is_active = st.session_state.nav_page == label
            if st.button(
                label,
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.nav_page = label
                st.rerun()

    return st.session_state.nav_page


def card_open(title: str, icon: str, caption: str | None = None, action_html: str = ""):
    """Opens a .gg-card div with a heading + optional icon and right-aligned
    action (e.g. a button rendered via action_html). Must be paired with card_close()."""
    icon_html = icon_svg(icon, 20, _colors()["accent"]) if icon else ""
    st.html(
        f'<div class="gg-card">'
        f'<div class="gg-card-header">'
        f'<div class="gg-card-header-left"><h4>{icon_html}{title}</h4></div>'
        f'{action_html}'
        f'</div>'
    )
    if caption:
        st.html(f'<p class="gg-caption">{caption}</p>')


def card_close():
    st.html("</div>")


def metric_tile(label: str, value, icon: str = "file-text", color: str = "accent"):
    """Renders a colored-icon metric tile, e.g. 'Characters: 22,539'."""
    c_all = _colors()
    color_map = {
        "accent": ("icon_blue", "icon_blue_bg"),
        "success": ("icon_green", "icon_green_bg"),
        "pro": ("icon_purple", "icon_purple_bg"),
        "warning": ("icon_orange", "icon_orange_bg"),
        "teal": ("icon_teal", "icon_teal_bg"),
    }
    fg_key, bg_key = color_map.get(color, color_map["accent"])
    fg, bg = c_all[fg_key], c_all[bg_key]
    st.html(
        f'<div class="gg-metric">'
        f'<div class="gg-metric-icon" style="background:{bg};color:{fg};">'
        f'{icon_svg(icon, 20, fg)}</div>'
        f'<div><div class="label">{label}</div><div class="value">{value}</div></div>'
        f'</div>'
    )


def structure_row(label: str, index):
    st.html(
        f'<div class="gg-struct-row">'
        f'<span class="left"><span class="gg-struct-dot"></span>{label}</span>'
        f'<span class="gg-struct-index">{index}</span></div>'
    )


def result_card(role: str, title: str, body: str):
    """role is one of: success, warning, pro, accent"""
    st.html(
        f'<div class="gg-result {role}"><p class="rtitle">{title}</p><p>{body}</p></div>'
    )


def tag_pills(tags):
    html = "".join(f'<span class="gg-pill">{t}</span>' for t in tags)
    st.html(html)  
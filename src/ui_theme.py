"""
UI theme helpers for GyanGrid AI.

Injects flat, card-based CSS styling + provides render helpers so app.py can
build the dashboard layout without repeating raw HTML everywhere.

Icons are inline SVG (no external CDN) so they can never fail to load.
"""

import base64
import textwrap
import streamlit as st

# ── Light palette ────────────────────────────────────────────────────────
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
# Premium research-focused dark mode (deep navy base, electric blue, teal accent).
DARK_COLORS = {
    "bg": "#0B0F14",
    "surface": "#121A23",
    "surface_muted": "#17212B",
    "border": "#243244",
    "text_primary": "#F8FAFC",
    "text_secondary": "#CBD5E1",
    "text_muted": "#94A3B8",

    "accent": "#3B82F6",
    "accent_bg": "rgba(59, 130, 246, 0.14)",
    "accent_text": "#3B82F6",

    "success": "#22C55E",
    "success_bg": "rgba(34, 197, 94, 0.14)",
    "success_text": "#22C55E",

    "warning": "#F59E0B",
    "warning_bg": "rgba(245, 158, 11, 0.14)",
    "warning_text": "#F59E0B",

    "pro": "#14B8A6",
    "pro_bg": "rgba(20, 184, 166, 0.14)",
    "pro_text": "#14B8A6",

    "icon_blue": "#3B82F6",
    "icon_blue_bg": "rgba(59, 130, 246, 0.14)",
    "icon_green": "#22C55E",
    "icon_green_bg": "rgba(34, 197, 94, 0.14)",
    "icon_purple": "#14B8A6",
    "icon_purple_bg": "rgba(20, 184, 166, 0.14)",
    "icon_orange": "#F59E0B",
    "icon_orange_bg": "rgba(245, 158, 11, 0.14)",
    "icon_teal": "#14B8A6",
    "icon_teal_bg": "rgba(20, 184, 166, 0.14)",
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
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
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
    "circle": '<circle cx="12" cy="12" r="9"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "alert-triangle": '<path d="M12 3l10 18H2z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
    "help-circle-q": '<path d="M8 9a4 4 0 1 1 5.5 3.7c-1 .4-1.5 1-1.5 2.3"/><path d="M12 17h.01"/><circle cx="12" cy="12" r="9"/>',
    "book": '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v16H6.5A2.5 2.5 0 0 0 4 20.5v-16z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20"/>',
    "gauge": '<path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 12L18 6"/><path d="M12 2v3"/>',
    "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
}

_STROKE_ICONS = {
    "brain", "home", "upload", "message", "bookmark", "clock", "settings",
    "sun", "help", "file-text", "list", "layers", "grid", "download",
    "trash", "eye", "check", "circle", "target", "alert-triangle",
    "help-circle-q", "book", "gauge", "chevron-right", "arrow-right", "inbox",
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


def _icon_mask_data_uri(name: str) -> str:
    """Base64 SVG (black fill/stroke) used as a CSS mask so a nav icon can
    sit inside a plain st.button — only the shape's alpha matters, actual
    color comes from `background-color: currentColor` on the pseudo-el."""
    path = _ICON_PATHS.get(name, "")
    if not path:
        return ""
    if name in _STROKE_ICONS:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>'
        )
    else:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#000" stroke="none">{path}</svg>'
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _theme_toggle_track_icon_uri(name: str, color: str) -> str:
    """A small bare icon (no knob/background) sized for the exposed half of
    the dark-mode toggle switch track."""
    path = _ICON_PATHS.get(name, "")
    if not path:
        return ""
    if name in _STROKE_ICONS:
        icon = (
            f'<svg x="4" y="4" width="16" height="16" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>'
        )
    else:
        icon = f'<svg x="4" y="4" width="16" height="16" viewBox="0 0 24 24" fill="{color}" stroke="none">{path}</svg>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">{icon}</svg>'
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _theme_toggle_knob_uri(name: str, icon_color: str, knob_bg: str) -> str:
    """A rounded-square knob (matching the reference switch design) with the
    given icon centered inside it, as a single SVG data-URI."""
    path = _ICON_PATHS.get(name, "")
    if not path:
        return ""
    if name in _STROKE_ICONS:
        icon = (
            f'<svg x="6" y="6" width="20" height="20" viewBox="0 0 24 24" fill="none" '
            f'stroke="{icon_color}" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>'
        )
    else:
        icon = f'<svg x="6" y="6" width="20" height="20" viewBox="0 0 24 24" fill="{icon_color}" stroke="none">{path}</svg>'
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
        f'<rect x="1" y="1" width="30" height="30" rx="9" fill="{knob_bg}"/>'
        f'{icon}</svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _sidebar_nav_icon_css(icon_names: list[str]) -> str:
    """Builds CSS that pins an icon (as a ::before mask) onto each sidebar
    nav button, in order. Buttons are matched by position since raw
    st.button() has no way to embed HTML/SVG inside its label."""
    rules = []
    for i, name in enumerate(icon_names, start=1):
        uri = _icon_mask_data_uri(name)
        if not uri:
            continue
        rules.append(f"""
        section[data-testid="stSidebar"] div.stButton:nth-of-type({i}) button::before {{
            content: "";
            width: 18px; height: 18px; flex-shrink: 0;
            display: inline-block;
            background-color: currentColor;
            -webkit-mask-image: url("{uri}");
            mask-image: url("{uri}");
            -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
            -webkit-mask-position: center; mask-position: center;
            -webkit-mask-size: contain; mask-size: contain;
        }}
        """)
    return "".join(rules)


def inject_base_css():
    """Injects the global stylesheet. Call once, near the top of app.py."""
    c = _colors()
    is_dark = st.session_state.get("dark_mode", False)
    
    dark_extra = f"""
        .gg-card {{
            box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset, 0 10px 28px rgba(0,0,0,0.4);
        }}
        .gg-metric, .gg-feature {{
            box-shadow: 0 1px 0 rgba(255,255,255,0.02) inset;
        }}
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {c['surface']} 0%, {c['bg']} 100%) !important;
            box-shadow: 1px 0 0 rgba(255,255,255,0.02) inset;
        }}
        [data-testid="stHeader"], .gg-topbar-icon {{
            background: transparent !important;
        }}
        div.stButton > button[kind="primary"] {{
            box-shadow: 0 4px 14px rgba(108, 142, 245, 0.28);
        }}
    """ if is_dark else ""
    
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

        .gg-nav-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            color: {c['text_muted']} !important;
            padding: 18px 16px 6px 16px;
        }}
        .gg-nav-label:first-of-type {{ padding-top: 4px; }}

        .gg-nav-divider {{
            height: 1px;
            background: {c['border']};
            margin: 10px 4px 4px 4px;
        }}

        section[data-testid="stSidebar"] div.stButton {{
            margin-bottom: 2px !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button {{
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            justify-content: flex-start !important;
            text-align: left !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            background: transparent !important;
            font-weight: 500 !important;
            font-size: 14.5px !important;
            padding: 10px 16px 10px 13px !important;
            color: {c['text_secondary']} !important;
            border-radius: 8px !important;
            transition: background 0.12s ease, color 0.12s ease;
        }}
        section[data-testid="stSidebar"] div.stButton > button p {{
            margin: 0 !important;
            font-size: 14.5px !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
            background: {c['accent_bg']} !important;
            border-left: 3px solid {c['accent']} !important;
            color: {c['accent_text']} !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button:hover {{
            background: {c['surface_muted']} !important;
            color: {c['text_primary']} !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{
            color: {c['accent_text']} !important;
        }}

        .gg-sidebar-footer {{
            margin: 14px 4px 4px 4px;
            padding: 12px 12px;
            border-radius: 10px;
            background: {c['surface_muted']} !important;
            border: 1px solid {c['border']};
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .gg-sidebar-footer .gg-avatar {{
            width: 32px; height: 32px;
            font-size: 12.5px;
            flex-shrink: 0;
        }}
        .gg-sidebar-footer-text {{ display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }}
        .gg-sidebar-footer-name {{
            font-size: 13.5px; font-weight: 600;
            color: {c['text_primary']} !important;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .gg-sidebar-footer-plan {{
            font-size: 12px;
            color: {c['text_muted']} !important;
        }}

        /* Fix applied here to explicitly style background and text colors for secondary buttons */
        div.stButton > button, div.stDownloadButton > button, [data-testid="stFileUploaderDropzone"] button {{
            border-radius: 10px;
            border: 1px solid {c['border']} !important;
            background-color: {c['surface']} !important;
            color: {c['text_primary']} !important;
            font-size: 16px;
            font-weight: 500;
            padding: 12px 22px;
            height: auto;
            min-height: 48px;
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {c['accent']} !important;
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
            background-color: {c['surface']} !important;
            color: {c['text_primary']} !important;
            border: 1px solid {c['border']} !important;
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

        /* ── Header bar (breadcrumb + page title + status) ────────────── */
        .gg-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid {c['border']};
            padding-bottom: 18px;
            margin-bottom: 22px;
        }}
        .gg-crumb {{
            font-size: 13px;
            color: {c['text_muted']} !important;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .gg-crumb svg {{ width: 13px; height: 13px; flex-shrink: 0; }}
        .gg-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-size: 13.5px;
            font-weight: 500;
            padding: 7px 14px;
            border-radius: 20px;
            background: {c['surface_muted']} !important;
            border: 1px solid {c['border']};
            color: {c['text_secondary']} !important;
            white-space: nowrap;
        }}
        .gg-status-pill.active {{
            background: {c['success_bg']} !important;
            color: {c['success_text']} !important;
            border-color: transparent;
        }}
        .gg-status-dot {{
            width: 7px; height: 7px; border-radius: 50%;
            background: {c['text_muted']} !important;
            flex-shrink: 0;
        }}
        .gg-status-pill.active .gg-status-dot {{ background: {c['success']} !important; }}

        /* ── Empty state ────────────────────────────────────────────── */
        .gg-empty {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 56px 24px 48px 24px;
        }}
        .gg-empty-icon {{
            width: 64px; height: 64px;
            border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
            background: {c['accent_bg']} !important;
            margin-bottom: 20px;
        }}
        .gg-empty h3 {{
            font-size: 20px;
            font-weight: 600;
            color: {c['text_primary']} !important;
            margin: 0 0 8px 0;
        }}
        .gg-empty p {{
            font-size: 15px;
            color: {c['text_secondary']} !important;
            max-width: 440px;
            line-height: 1.55;
            margin: 0 0 22px 0;
        }}

        /* ── Feature preview cards (AI analysis capabilities grid) ────── */
        .gg-feature {{
            background: {c['surface']} !important;
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 20px;
            height: 100%;
        }}
        .gg-feature-icon {{
            width: 38px; height: 38px;
            border-radius: 9px;
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 14px;
        }}
        .gg-feature h5 {{
            font-size: 15.5px;
            font-weight: 600;
            color: {c['text_primary']} !important;
            margin: 0 0 6px 0;
        }}
        .gg-feature p {{
            font-size: 13.5px;
            color: {c['text_secondary']} !important;
            line-height: 1.5;
            margin: 0 0 10px 0;
        }}
        .gg-feature-badge {{
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.3px;
            text-transform: uppercase;
            padding: 3px 9px;
            border-radius: 6px;
            background: {c['surface_muted']} !important;
            color: {c['text_muted']} !important;
        }}

        /* ── Simple table (Recent papers / Analysis history) ──────────── */
        .gg-table {{ width: 100%; border-collapse: collapse; }}
        .gg-table th {{
            text-align: left;
            font-size: 12.5px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: {c['text_muted']} !important;
            padding: 0 12px 10px 12px;
            border-bottom: 1px solid {c['border']};
        }}
        .gg-table td {{
            font-size: 14.5px;
            color: {c['text_primary']} !important;
            padding: 13px 12px;
            border-bottom: 1px solid {c['border']};
        }}
        .gg-table tr:last-child td {{ border-bottom: none; }}
        .gg-table-empty {{
            text-align: center;
            padding: 32px 12px;
            color: {c['text_muted']} !important;
            font-size: 14px;
        }}
        {dark_extra}
        </style>
        """
    st.html(textwrap.dedent(css).strip())


def render_topbar():
    """Renders the top-right icon row: a working dark-mode toggle (Streamlit's
    native st.toggle widget), a decorative help icon, and an avatar."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    c = _colors()
    is_dark = st.session_state.dark_mode
    tooltip = (
        "Currently dark mode — click for light"
        if is_dark else
        "Currently light mode — click for dark"
    )

    # Minimal styling only (colors/sizing) — no background-image overlay,
    # no hidden-label tricks, no custom click handling. This is a plain
    # native Streamlit widget, so clicks are guaranteed to register.
    st.html(f"""
        <style>
        .st-key-dark_mode_toggle label {{
            font-size: 20px !important;
        }}
        </style>
    """)

    spacer, toggle_col, help_col, avatar_col = st.columns([12, 2, 1, 1])
    with toggle_col:
        st.toggle(
            "🌙" if is_dark else "☀️",
            key="dark_mode",
            help=tooltip,
        )
    with help_col:
        st.html(f'<div class="gg-topbar-icon">{icon_svg("help", 18, c["text_secondary"])}</div>')
    with avatar_col:
        st.html('<div class="gg-avatar">RS</div>')


def render_sidebar_nav(default: str = "Dashboard") -> str:
    """Renders the logo header + grouped, clickable nav list in
    st.sidebar (plus a footer profile card) and returns the currently
    active page name."""
    sections = [
        ("Workspace", [
            ("home", "Dashboard"),
            ("upload", "Upload paper"),
        ]),
        ("AI Tools", [
            ("message", "Q&A (RAG)"),
            ("sparkles", "AI analysis"),
        ]),
    ]
    footer_item = ("settings", "Settings")

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = default

    c = _colors()

    # Icons are pinned onto buttons via a positional CSS mask, since
    # st.button() can't render HTML/SVG inside its own label.
    icon_order = [icon for _, items in sections for icon, _ in items] + [footer_item[0]]
    st.html(f"<style>{_sidebar_nav_icon_css(icon_order)}</style>")

    with st.sidebar:
        st.html(
            f'<div class="gg-logo">{icon_svg("brain", 30, c["accent"])}'
            f'<div class="gg-logo-text">'
            f'<span class="gg-logo-title">GyanGrid AI</span>'
            f'<span class="gg-logo-sub">AI Research Assistant</span>'
            f'</div></div>'
        )

        for section_label, items in sections:
            st.html(f'<div class="gg-nav-label">{section_label}</div>')
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

        st.html('<div class="gg-nav-divider"></div>')
        icon_name, label = footer_item
        is_active = st.session_state.nav_page == label
        if st.button(
            label,
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.nav_page = label
            st.rerun()

        st.html(
            '<div class="gg-sidebar-footer">'
            '<div class="gg-avatar">RS</div>'
            '<div class="gg-sidebar-footer-text">'
            '<span class="gg-sidebar-footer-name">Research Workspace</span>'
            '<span class="gg-sidebar-footer-plan">Free plan</span>'
            '</div></div>'
        )

    return st.session_state.nav_page


def card_open(title: str, icon: str, caption: str | None = None, action_html: str = ""):
    """Opens a .gg-card div with a heading + optional icon and right-aligned
    action (e.g. a button rendered via action_html). Must be paired with card_close()."""
    icon_html = icon_svg(icon, 20, _colors()["accent"]) if icon else ""
    header_html = ""
    if title:
        header_html = (
            f'<div class="gg-card-header">'
            f'<div class="gg-card-header-left"><h4>{icon_html}{title}</h4></div>'
            f'{action_html}'
            f'</div>'
        )
    st.html(f'<div class="gg-card">{header_html}')
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


def page_header(title: str, subtitle: str, crumb: list[str] | None = None,
                 status_label: str | None = None, status_active: bool = False):
    """Renders a page title block with an optional breadcrumb trail above it
    and an optional status pill (e.g. paper loaded / not loaded) to the
    right. Replaces the old raw .gg-title/.gg-subtitle markdown call."""
    c = _colors()
    crumb_html = ""
    if crumb:
        chevrons = f' {icon_svg("chevron-right", 13, c["text_muted"])} '.join(crumb)
        crumb_html = f'<div class="gg-crumb">{chevrons}</div>'

    status_html = ""
    if status_label:
        active_cls = "active" if status_active else ""
        status_html = (
            f'<div class="gg-status-pill {active_cls}">'
            f'<span class="gg-status-dot"></span>{status_label}</div>'
        )

    st.html(
        f'<div class="gg-header">'
        f'<div>{crumb_html}'
        f'<div class="gg-title" style="margin-bottom:4px;">{title}</div>'
        f'<div class="gg-subtitle" style="margin-bottom:0;">{subtitle}</div>'
        f'</div>'
        f'<div style="padding-top:4px;">{status_html}</div>'
        f'</div>'
    )


def empty_state(icon: str, title: str, body: str):
    """Renders a centered empty-state icon/title/body inside a gg-card.
    Caller is responsible for card_open()/card_close() around this, or it
    can be used standalone — button should be rendered by caller right
    after (Streamlit buttons can't be embedded in raw HTML)."""
    c = _colors()
    st.html(
        f'<div class="gg-empty">'
        f'<div class="gg-empty-icon">{icon_svg(icon, 30, c["accent"])}</div>'
        f'<h3>{title}</h3>'
        f'<p>{body}</p>'
        f'</div>'
    )


def feature_preview_card(icon: str, title: str, body: str, badge: str = "Coming soon", color: str = "accent"):
    """Renders a small preview card describing an upcoming analysis
    capability (e.g. 'Paper Summary', 'Key Topics')."""
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
        f'<div class="gg-feature">'
        f'<div class="gg-feature-icon" style="background:{bg};color:{fg};">'
        f'{icon_svg(icon, 19, fg)}</div>'
        f'<h5>{title}</h5>'
        f'<p>{body}</p>'
        f'<span class="gg-feature-badge">{badge}</span>'
        f'</div>'
    )


def history_table(rows: list[dict], columns: list[str], empty_message: str = "No analyses yet."):
    """Renders a lightweight HTML table for 'Recent papers' / 'Analysis
    history'. rows is a list of dicts keyed by column name; if rows is
    empty, shows a centered placeholder row instead."""
    if not rows:
        st.html(
            f'<table class="gg-table"><thead><tr>'
            + "".join(f"<th>{col}</th>" for col in columns)
            + f'</tr></thead></table>'
            f'<div class="gg-table-empty">{empty_message}</div>'
        )
        return

    header_html = "".join(f"<th>{col}</th>" for col in columns)
    body_html = ""
    for row in rows:
        cells = "".join(f"<td>{row.get(col, '')}</td>" for col in columns)
        body_html += f"<tr>{cells}</tr>"
    st.html(
        f'<table class="gg-table"><thead><tr>{header_html}</tr></thead>'
        f'<tbody>{body_html}</tbody></table>'
    )
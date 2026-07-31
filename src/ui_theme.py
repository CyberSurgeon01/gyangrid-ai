"""
UI theme helpers for GyanGrid AI.

Injects flat, card-based CSS styling + provides render helpers so app.py can
build the dashboard layout without repeating raw HTML everywhere.

Icons are inline SVG (no external CDN) so they can never fail to load.
"""

import base64
import textwrap
import streamlit as st
from streamlit.components.v1 import html as _components_html

# ── Light palette ────────────────────────────────────────────────────────
COLORS = {
    "bg": "#f8fafc",
    "surface": "#ffffff",
    "surface_muted": "#f1f5f9",
    "border": "#e5e7eb",
    "text_primary": "#111827",
    "text_secondary": "#6b7280",
    "text_muted": "#9aa0aa",

    "accent": "#2563eb",
    "accent_bg": "#eff6ff",
    "accent_text": "#1d4ed8",

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


def theme_colors() -> dict:
    """Public accessor for the active color palette — use this from
    outside ui_theme.py (e.g. src/login_page.py, src/signup_page.py)
    instead of reaching into the private _colors()."""
    return _colors()


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
    "layout-dashboard": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "file-up": '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M4.5 22H18a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v3"/><path d="M12 12v6"/><path d="m9 15 3-3 3 3"/>',
    "message-question": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/><path d="M9.09 9a3 3 0 1 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
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
    "layout-dashboard", "file-up", "message-question",
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


def _button_key_css_class(key: str) -> str:
    """Mirrors Streamlit's own key->CSS-class sanitizer (`st-key-<key>`,
    with any char outside [a-zA-Z0-9_-] replaced by '-'), so we can target
    a specific nav button reliably instead of guessing its DOM position."""
    import re
    return "st-key-" + re.sub(r"[^a-zA-Z0-9_-]", "-", key.strip())


def _sidebar_nav_icon_css(icon_keys: list[tuple[str, str]]) -> str:
    """Builds CSS that pins an icon (as a ::before mask) onto each sidebar
    nav button. Each button is matched via its own Streamlit `key` (which
    Streamlit exposes as a stable `st-key-<key>` class on the button's
    wrapper), so icons stay attached to the right button regardless of
    render order — unlike positional matching, which breaks because each
    button gets its own isolated wrapper."""
    rules = []
    for name, key in icon_keys:
        uri = _icon_mask_data_uri(name)
        if not uri:
            continue
        css_class = _button_key_css_class(key)
        rules.append(f"""
        section[data-testid="stSidebar"] .{css_class} button::before {{
            content: "";
            width: 23px; height: 23px; flex-shrink: 0;
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
            min-width: 280px !important;
            max-width: 280px !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            overflow-y: auto !important;
            z-index: 100;
        }}
        /* Force the sidebar to always stay open/visible. If anything still
           flips it to aria-expanded="false" (e.g. a keyboard shortcut),
           this keeps it visually pinned open regardless. */
        section[data-testid="stSidebar"][aria-expanded="false"] {{
            min-width: 280px !important;
            max-width: 280px !important;
            margin-left: 0 !important;
            transform: none !important;
            visibility: visible !important;
        }}
        section[data-testid="stSidebar"] * {{
            color: {c['text_primary']} !important;
        }}
        /* Hide every control Streamlit provides for collapsing/re-expanding
           the sidebar — the header's collapse arrow, and the small
           "re-open" arrow that appears once collapsed. Different testid
           names are covered since this varies by Streamlit version. */
        section[data-testid="stSidebar"] button[kind="header"],
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
        section[data-testid="stSidebar"] [data-testid*="CollapseButton"],
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        /* The sidebar is fixed (out of normal document flow), so the main
           content area needs its own left offset equal to the sidebar's
           width, or it would render underneath it. Since collapsing is now
           disabled, this offset is applied unconditionally. General sibling
           combinator (~) is used rather than the adjacent one (+) since the
           main content div isn't always the sidebar's immediate DOM
           neighbor across Streamlit versions. */
        section[data-testid="stSidebar"] ~ div {{
            margin-left: 280px !important;
        }}
        /* Streamlit renders several nested wrapper elements inside the
           sidebar before our own content — a header strip reserved for
           the collapse control, plus one or more content wrappers that
           carry large default top padding/margin. Exact testid names
           differ across Streamlit versions, so instead of guessing one
           name we neutralize anything whose testid contains "Sidebar",
           then apply our own top spacing on the outermost wrapper only. */
        section[data-testid="stSidebar"] [data-testid*="Sidebar"] {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {{
            height: 0 !important;
            min-height: 0 !important;
        }}
        section[data-testid="stSidebar"] > div:first-child {{
            padding: 30px 14px 16px 14px !important;
        }}

        .gg-logo {{
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 0 4px 24px 4px;
            margin-bottom: 0;
            border-bottom: 1px solid {c['border']};
        }}
        .gg-logo svg {{ color: {c['accent']} !important; flex-shrink: 0; }}
        .gg-logo-text {{ display: flex; flex-direction: column; line-height: 1.25; }}
        .gg-logo-title {{ font-weight: 700; font-size: 19px; letter-spacing: -0.2px; color: {c['text_primary']} !important; }}
        .gg-logo-sub {{ font-size: 13px; color: {c['text_muted']} !important; }}

        .gg-nav-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: {c['text_muted']} !important;
            padding: 18px 10px 8px 10px;
        }}
        .gg-nav-label:first-of-type {{ padding-top: 12px; }}

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
            gap: 11px !important;
            justify-content: flex-start !important;
            text-align: left !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            background: transparent !important;
            font-weight: 500 !important;
            font-size: 15px !important;
            line-height: 1.3 !important;
            padding: 9px 14px 9px 11px !important;
            min-height: 0 !important;
            color: {c['text_secondary']} !important;
            border-radius: 10px !important;
            transition: background 0.12s ease, color 0.12s ease;
        }}
        section[data-testid="stSidebar"] div.stButton > button p {{
            margin: 0 !important;
            font-size: 15px !important;
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
            margin: 16px 2px 2px 2px;
            padding: 10px 11px;
            border-radius: 10px;
            background: {c['surface']} !important;
            border: 1px solid {c['border']};
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            display: flex;
            align-items: center;
            gap: 9px;
        }}
        .gg-sidebar-footer .gg-avatar {{
            width: 30px; height: 30px;
            font-size: 12px;
            flex-shrink: 0;
        }}
        .gg-sidebar-footer-text {{ display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }}
        .gg-sidebar-footer-name {{
            font-size: 13px; font-weight: 600;
            color: {c['text_primary']} !important;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .gg-sidebar-footer-plan {{
            font-size: 11.5px;
            color: {c['text_muted']} !important;
        }}

        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                min-width: 240px !important;
                max-width: 82vw !important;
            }}
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
        [data-testid="stFileUploaderDropzoneInstructions"] small,
        [data-testid="stFileUploaderDropzoneInstructions"] span:nth-of-type(2) {{
            font-size: 0 !important;
            line-height: 0 !important;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] small::after,
        [data-testid="stFileUploaderDropzoneInstructions"] span:nth-of-type(2)::after {{
            content: "Please upload a PDF or DOCX file (maximum size: 20 MB)";
            font-size: 14px !important;
            line-height: 1.4 !important;
            display: inline-block;
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
        .gg-feature-badge-supported {{
            background: {c['icon_green_bg']} !important;
            color: {c['icon_green']} !important;
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

    # Streamlit sets a native HTML `title` attribute on the file-uploader
    # dropzone (for accessibility) containing its own default text — this
    # shows up as a plain browser tooltip on hover and is NOT reachable by
    # CSS, since native title tooltips aren't part of the styleable DOM.
    # We strip it via JS so only our CSS-swapped instructions text shows.
    _components_html(
        """
        <script>
        function stripUploaderTitles() {
            const doc = window.parent.document;
            doc.querySelectorAll(
                '[data-testid="stFileUploaderDropzone"] [title],' +
                '[data-testid="stFileUploaderDropzoneInstructions"] [title]'
            ).forEach(el => el.removeAttribute('title'));
        }
        stripUploaderTitles();
        const _gg_observer = new MutationObserver(stripUploaderTitles);
        _gg_observer.observe(window.parent.document.body, {childList: true, subtree: true});
        </script>
        """,
        height=0,
    )


def render_logout_button():
    """Renders a small 'Log out' control for the sidebar footer — clears
    auth_status so the next rerun falls back to render_auth_page()."""
    if st.button("Log out", use_container_width=True, key="gg_logout_btn"):
        for key in ("auth_status", "user_name", "user_email"):
            st.session_state.pop(key, None)
        st.rerun()


def render_topbar():
    """Renders the top-right icon row: avatar only."""
    spacer, avatar_col = st.columns([15, 1])
    with avatar_col:
        st.html('<div class="gg-avatar">RS</div>')


def render_sidebar_nav(default: str = "Dashboard") -> str:
    """Renders the logo header + grouped, clickable nav list in
    st.sidebar (plus a footer profile card) and returns the currently
    active page name."""
    sections = [
        ("Workspace", [
            ("layout-dashboard", "Dashboard"),
            ("file-up", "Upload paper"),
        ]),
        ("AI Tools", [
            ("message-question", "Q&A (RAG)"),
            ("sparkles", "AI analysis"),
            ("quote", "Citation graph"),
        ]),
        ("System", [
            ("settings", "Settings"),
        ]),
    ]

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = default

    c = _colors()

    # Icons are pinned onto buttons via a CSS mask keyed to each button's
    # own `key`, since st.button() can't render HTML/SVG inside its own
    # label.
    icon_keys = [(icon, f"nav_{label}") for _, items in sections for icon, label in items]
    st.html(f"<style>{_sidebar_nav_icon_css(icon_keys)}</style>")

    with st.sidebar:
        st.html(
            f'<div class="gg-logo" style="pointer-events:none;">'
            f'{icon_svg("brain", 28, c["accent"])}'
            f'<div class="gg-logo-text">'
            f'<span class="gg-logo-title">GyanGrid AI</span>'
            f'<span class="gg-logo-sub">AI Research Assistant</span>'
            f'</div></div>'
        )

        for section_label, items in sections:
            st.html(f'<div class="gg-nav-label">{section_label.upper()}</div>')
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

        st.html(
            '<div class="gg-sidebar-footer">'
            '<div class="gg-avatar">RS</div>'
            '<div class="gg-sidebar-footer-text">'
            '<span class="gg-sidebar-footer-name">Research Workspace</span>'
            '<span class="gg-sidebar-footer-plan">Free plan</span>'
            '</div></div>'
        )

    return st.session_state.nav_page


def render_dark_mode_toggle():
    """Renders a working 'Appearance' card for the Settings page with a
    dark/light mode toggle.

    st.session_state['dark_mode'] is a PLAIN flag, not a widget key. This
    matters: a key that belongs to a widget (e.g. st.toggle(key=...)) is
    only kept alive by Streamlit while that widget is actually rendered
    on the current page — navigate to a page that doesn't render it and
    Streamlit resets it to default. That was the bug: binding "dark_mode"
    directly to the toggle's own key made it revert to light on every
    page except Settings. The toggle now uses its own separate widget key
    ("dark_mode_widget") and this function copies its value into the
    plain "dark_mode" flag, which persists across pages exactly like any
    other ordinary session_state variable.

    The choice is also mirrored into st.query_params (?theme=dark|light)
    so it survives a full browser refresh and applies on every page, not
    just this one — session_state alone resets on refresh, same as the
    loaded-paper restore logic elsewhere in app.py. app.py is expected to
    read that query param back into session_state near the top of the
    script, before inject_base_css() runs.

    IMPORTANT — for this to actually take effect, app.py must call
    inject_base_css() unconditionally on every rerun (near the top of
    the script), the same way it already does for the light theme.
    If inject_base_css() is wrapped in @st.cache_resource / @st.cache_data,
    it will keep returning the FIRST theme it ever computed and dark mode
    will silently never apply — that decorator (if present) must be
    removed from that function.
    """
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = st.query_params.get("theme") == "dark"

    icon = "moon" if st.session_state.dark_mode else "sun"
    card_open("Appearance", icon, caption="Switch between light and dark mode.")
    is_dark = st.toggle("Dark mode", value=st.session_state.dark_mode, key="dark_mode_widget")
    card_close()

    if is_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = is_dark
        st.query_params["theme"] = "dark" if is_dark else "light"
        st.rerun()


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
    badge_class = "gg-feature-badge"
    if badge.strip().lower() == "supported":
        badge_class += " gg-feature-badge-supported"
    st.html(
        f'<div class="gg-feature">'
        f'<div class="gg-feature-icon" style="background:{bg};color:{fg};">'
        f'{icon_svg(icon, 19, fg)}</div>'
        f'<h5>{title}</h5>'
        f'<p>{body}</p>'
        f'<span class="{badge_class}">{badge}</span>'
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
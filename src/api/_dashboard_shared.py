"""Shared HTML, CSS, and JS constants for all dashboard pages."""

from __future__ import annotations

# ---- Color Palette ----
COLORS = {
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "surface2": "#252830",
    "border": "#2e3140",
    "text": "#e1e4ea",
    "text_muted": "#8b8fa3",
    "accent": "#6366f1",
    "accent_hover": "#818cf8",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
}


def nav_bar(active: str = "overview") -> str:
    """Generate navigation bar HTML.

    Args:
        active: Which tab is active — "overview", "logs", or "metrics".
    """
    tabs = [
        ("overview", "Overview", "/dashboard"),
        ("logs", "Logs", "/dashboard/logs"),
        ("metrics", "Metrics", "/dashboard/metrics"),
    ]
    links = ""
    for key, label, href in tabs:
        cls = "nav-tab active" if key == active else "nav-tab"
        links += f'<a href="{href}" class="{cls}">{label}</a>\n'

    return f"""<nav class="nav-bar">
  <div class="nav-brand">Patient Advocacy Agent</div>
  <div class="nav-tabs">{links}</div>
  <div class="nav-status" id="nav-status">
    <span class="status-dot"></span>
    <span id="refresh-indicator">Live</span>
  </div>
</nav>"""


def _build_css() -> str:
    """Build CSS string with color variables substituted."""
    c = COLORS
    return f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
    Roboto, sans-serif;
  background: {c["bg"]}; color: {c["text"]}; line-height: 1.5;
}}
.nav-bar {{
  display: flex; align-items: center;
  justify-content: space-between;
  background: {c["surface"]};
  border-bottom: 1px solid {c["border"]};
  padding: 0 24px; height: 52px;
  position: sticky; top: 0; z-index: 100;
}}
.nav-brand {{
  font-weight: 700; font-size: 15px; color: {c["accent"]};
}}
.nav-tabs {{ display: flex; gap: 4px; }}
.nav-tab {{
  padding: 8px 16px; border-radius: 6px;
  text-decoration: none; color: {c["text_muted"]};
  font-size: 13px; font-weight: 500; transition: all 0.15s;
}}
.nav-tab:hover {{
  color: {c["text"]}; background: {c["surface2"]};
}}
.nav-tab.active {{
  color: {c["text"]}; background: {c["accent"]};
}}
.nav-status {{
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: {c["text_muted"]};
}}
.status-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: {c["success"]}; display: inline-block;
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }}
}}
.container {{
  max-width: 1400px; margin: 0 auto; padding: 20px 24px;
}}
.grid {{ display: grid; gap: 16px; }}
.grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
.grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
.grid-full {{ grid-template-columns: 1fr; }}
.card {{
  background: {c["surface"]};
  border: 1px solid {c["border"]};
  border-radius: 10px; padding: 20px;
}}
.card-title {{
  font-size: 13px; font-weight: 600; color: {c["text_muted"]};
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 12px;
}}
.stat-value {{ font-size: 28px; font-weight: 700; }}
.stat-label {{
  font-size: 12px; color: {c["text_muted"]}; margin-top: 2px;
}}
.badge {{
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600; text-transform: uppercase;
}}
.badge-ok {{ background: #16382a; color: {c["success"]}; }}
.badge-warn {{ background: #3d2e0a; color: {c["warning"]}; }}
.badge-error {{ background: #3d1214; color: {c["error"]}; }}
.badge-info {{ background: #172554; color: {c["info"]}; }}
.badge-debug {{
  background: {c["surface2"]}; color: {c["text_muted"]};
}}
.footer {{
  text-align: center; padding: 20px;
  color: {c["text_muted"]};
  font-size: 11px; border-top: 1px solid {c["border"]};
  margin-top: 24px;
}}
@media (max-width: 900px) {{
  .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
}}
"""


BASE_CSS = _build_css()


COMMON_JS = """
async function fetchJSON(url) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (e) {
    console.error('Fetch failed:', url, e);
    return null;
  }
}

function fmtTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-GB', {
    hour:'2-digit', minute:'2-digit', second:'2-digit'
  });
}

function fmtDuration(seconds) {
  if (seconds < 60) return Math.round(seconds) + 's';
  if (seconds < 3600) return Math.round(seconds / 60) + 'm';
  return (seconds / 3600).toFixed(1) + 'h';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
"""

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.0.min.js"

PLOTLY_LAYOUT_DEFAULTS = {
    "paper_bgcolor": COLORS["surface"],
    "plot_bgcolor": COLORS["surface"],
    "font": {"color": COLORS["text"], "size": 11},
    "margin": {"l": 50, "r": 20, "t": 36, "b": 40},
    "xaxis": {
        "gridcolor": COLORS["border"],
        "zerolinecolor": COLORS["border"],
    },
    "yaxis": {
        "gridcolor": COLORS["border"],
        "zerolinecolor": COLORS["border"],
    },
}

FOOTER_HTML = """<div class="footer">
  Auto-refresh active &middot; Patient Advocacy Agent v0.1.0
  &middot; <strong>This system is NOT a doctor.</strong>
  Always seek professional medical help.
</div>"""


def full_page(
    title: str,
    active_tab: str,
    body: str,
    extra_js: str = "",
) -> str:
    """Wrap body content in a full HTML page with nav, CSS, scripts."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport"
    content="width=device-width, initial-scale=1">
  <title>{title} — Patient Advocacy Agent</title>
  <style>{BASE_CSS}</style>
  <script src="{PLOTLY_CDN}"></script>
</head>
<body>
{nav_bar(active_tab)}
<div class="container">
{body}
</div>
{FOOTER_HTML}
<script>
{COMMON_JS}
{extra_js}
</script>
</body>
</html>"""

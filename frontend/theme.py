"""
frontend/theme.py — AdMitra professional design system
=======================================================
Shared CSS (injected after legacy styles so it overrides them) and small
HTML component helpers: top bar, page header, KPI cards, status pills.
"""

from __future__ import annotations

import streamlit as st

NAV_ITEMS = [
    ("overview", "📊", "Overview"),
    ("diagnostic", "🩺", "Diagnostics"),
    ("performance", "📈", "Performance"),
    ("budget", "💰", "Budget"),
    ("creative", "🎨", "Creative Studio"),
    ("engagement", "💬", "Engagement"),
    ("developer", "🧩", "Developer"),
]

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #0b1220; --surface: #111a2e; --surface-2: #16213a; --border: #22304d;
  --text: #e6ebf5; --muted: #8b9ab8; --accent: #6366f1; --accent-2: #818cf8;
  --ok: #10b981; --warn: #f59e0b; --danger: #ef4444; --radius: 12px;
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }
.stApp, .main { background: var(--bg) !important; color: var(--text); }
header[data-testid="stHeader"] { background: transparent; height: 0; }
.block-container { padding: 1.2rem 2.2rem 3rem 2.2rem !important; max-width: 1500px; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
  background: #080e1b !important; border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1rem !important; }
.am-brand { display:flex; align-items:center; gap:10px; padding: 4px 4px 14px 4px; }
.am-brand-logo {
  width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg,#6366f1,#8b5cf6); font-size:18px; box-shadow:0 6px 16px -6px #6366f1;
}
.am-brand-name { font-weight:800; font-size:1.15rem; letter-spacing:-0.02em; color:#fff; line-height:1.1; }
.am-brand-sub { font-size:0.68rem; color: var(--muted); letter-spacing:.06em; text-transform:uppercase; }
.am-nav-label { font-size:0.68rem; color: var(--muted); letter-spacing:.1em; text-transform:uppercase; margin: 10px 4px 4px; }

/* radio -> nav menu */
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
  padding: 9px 12px; border-radius: 9px; cursor: pointer; transition: all .15s ease;
  border: 1px solid transparent; width: 100%;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background: #111a2e; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display:none; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size: 0.9rem; font-weight: 500; color: #c3cde0; margin: 0; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: linear-gradient(90deg, rgba(99,102,241,.22), rgba(99,102,241,.05));
  border-color: rgba(99,102,241,.45);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p { color:#fff; font-weight:600; }

/* ---------- Top bar ---------- */
.am-topbar {
  display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;
  background: var(--surface); border:1px solid var(--border); border-radius: var(--radius);
  padding: 12px 18px; margin-bottom: 18px;
}
.am-crumb { color: var(--muted); font-size: .8rem; }
.am-crumb b { color: var(--text); font-weight:600; }
.am-top-right { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.am-pill {
  display:inline-flex; align-items:center; gap:7px; font-size:.75rem; font-weight:600;
  padding:5px 11px; border-radius:999px; border:1px solid var(--border); background: var(--surface-2); color: var(--text);
}
.am-pill.ok { color:#34d399; border-color: rgba(16,185,129,.4); background: rgba(16,185,129,.1); }
.am-pill.warn { color:#fbbf24; border-color: rgba(245,158,11,.4); background: rgba(245,158,11,.1); }
.am-pill.bad { color:#f87171; border-color: rgba(239,68,68,.4); background: rgba(239,68,68,.1); }
.am-dot { width:7px; height:7px; border-radius:50%; background: currentColor; animation: am-pulse 1.8s infinite; }
@keyframes am-pulse { 0%,100% { opacity:1; transform:scale(1);} 50% { opacity:.4; transform:scale(1.4);} }
.am-avatar {
  width:32px; height:32px; border-radius:50%; background: linear-gradient(135deg,#6366f1,#ec4899);
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.8rem; color:#fff;
}

/* ---------- Page header ---------- */
.am-page-title { font-size: 1.55rem; font-weight: 800; letter-spacing:-0.02em; margin: 0; color:#fff; }
.am-page-sub { color: var(--muted); font-size: .88rem; margin: 2px 0 18px; }

/* ---------- KPI cards ---------- */
.am-kpi {
  background: var(--surface); border:1px solid var(--border); border-radius: var(--radius);
  padding: 16px 18px; transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
  animation: am-fade .4s ease both;
}
.am-kpi:hover { transform: translateY(-3px); border-color: rgba(99,102,241,.55); box-shadow: 0 12px 26px -14px rgba(99,102,241,.6); }
.am-kpi-top { display:flex; justify-content:space-between; align-items:center; }
.am-kpi-label { color: var(--muted); font-size:.74rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; }
.am-kpi-icon { width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; background: rgba(99,102,241,.15); }
.am-kpi-value { font-size:1.75rem; font-weight:800; letter-spacing:-0.02em; margin-top:8px; color:#fff; font-variant-numeric: tabular-nums; }
.am-kpi-delta { font-size:.78rem; font-weight:600; margin-top:2px; }
.am-kpi-delta.up { color:#34d399; } .am-kpi-delta.down { color:#f87171; } .am-kpi-delta.flat { color: var(--muted); }
@keyframes am-fade { from { opacity:0; transform: translateY(8px);} to { opacity:1; transform:none;} }

/* ---------- Generic cards / widgets (also restyles legacy classes) ---------- */
.glass-card, .am-card {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important; box-shadow: none !important; backdrop-filter:none !important;
}
.am-card { padding: 18px 20px; margin-bottom: 14px; }
.am-card-title { font-weight:700; font-size:1rem; color:#fff; margin-bottom:2px; }
.am-card-sub { color: var(--muted); font-size:.8rem; margin-bottom:10px; }

div[data-testid="stMetric"] {
  background: var(--surface); border:1px solid var(--border); border-radius: var(--radius); padding: 14px 16px;
}
div[data-testid="stMetricLabel"] p { color: var(--muted) !important; font-size:.78rem !important; font-weight:600; }
div[data-testid="stMetricValue"] { font-weight:800 !important; font-variant-numeric: tabular-nums; }

.stButton > button {
  border-radius: 9px; font-weight: 600; border: 1px solid var(--border); transition: all .15s ease;
}
.stButton > button:hover { transform: translateY(-1px); border-color: var(--accent-2); }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg,#6366f1,#7c3aed); border: none; box-shadow: 0 8px 18px -10px #6366f1;
}
div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius: var(--radius); overflow:hidden; }
div[data-testid="stExpander"] { border:1px solid var(--border) !important; border-radius: var(--radius) !important; background: var(--surface); }
hr { border-color: var(--border) !important; }

/* legacy hero banner replaced by top bar */
.admitra-header { display:none !important; }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand() -> None:
    st.markdown(
        """
        <div class="am-brand">
          <div class="am-brand-logo">⚡</div>
          <div><div class="am-brand-name">AdMitra</div><div class="am-brand-sub">AI Marketing Suite</div></div>
        </div>
        <div class="am-nav-label">Workspace</div>
        """,
        unsafe_allow_html=True,
    )


def top_bar(page_label: str, used_mock: bool, meta_live: bool, account_name: str = "AdMitra Workspace") -> None:
    api_pill = (
        '<span class="am-pill warn"><span class="am-dot"></span>Standalone mode</span>'
        if used_mock
        else '<span class="am-pill ok"><span class="am-dot"></span>Orchestrator online</span>'
    )
    meta_pill = (
        '<span class="am-pill ok"><span class="am-dot"></span>Meta API connected</span>'
        if meta_live
        else '<span class="am-pill warn"><span class="am-dot"></span>Meta: mock data</span>'
    )
    initials = "".join(w[0] for w in account_name.split()[:2]).upper() or "AM"
    st.markdown(
        f"""
        <div class="am-topbar">
          <div class="am-crumb">AdMitra &nbsp;/&nbsp; <b>{page_label}</b></div>
          <div class="am-top-right">{api_pill}{meta_pill}
            <span class="am-pill">{account_name}</span><div class="am-avatar">{initials}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<h1 class="am-page-title">{title}</h1><p class="am-page-sub">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", trend: str = "flat", icon: str = "📌") -> str:
    delta_html = f'<div class="am-kpi-delta {trend}">{delta}</div>' if delta else ""
    return (
        f'<div class="am-kpi"><div class="am-kpi-top"><span class="am-kpi-label">{label}</span>'
        f'<span class="am-kpi-icon">{icon}</span></div>'
        f'<div class="am-kpi-value">{value}</div>{delta_html}</div>'
    )


def kpi_row(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for col, html in zip(cols, cards):
        with col:
            st.markdown(html, unsafe_allow_html=True)


def card_open(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="am-card"><div class="am-card-title">{title}</div>'
        f'<div class="am-card-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def to_bullets(text: str, max_items: int = 5, max_chars: int = 120) -> list[str]:
    """Condense LLM output (paragraphs, numbered lists, headings) into short bullet lines."""
    import re

    items: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # bullet / number markers only when followed by whitespace (keeps **bold** intact)
        line = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", line).strip()
        # skip pure titles and section headings such as "**Report**" or "Recommendations:"
        if re.fullmatch(r"\*\*[^*]+\*\*:?", line) or line.endswith(":"):
            continue
        if len(line) < 6:
            continue
        parts = re.split(r"(?<=[.!?])\s+", line) if len(line) > max_chars else [line]
        items.extend(p.strip() for p in parts if len(p.strip()) >= 6)
    out = []
    for it in items[:max_items]:
        if len(it) > max_chars:
            it = it[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"
        out.append(it)
    return out


def briefing_card(label: str, text: str, tone: str = "ok", max_items: int = 5) -> None:
    """Compact AI briefing: pill label + short bullets, full text behind a toggle."""
    bullets = to_bullets(text, max_items=max_items)
    with st.container(border=True):
        st.markdown(f'<span class="am-pill {tone}">{label}</span>', unsafe_allow_html=True)
        if bullets:
            st.markdown("\n".join(f"- {b}" for b in bullets).replace("$", "\\$"))
        else:
            st.caption("No insights available yet.")
        if len(str(text or "")) > 400:
            with st.expander("View full analysis"):
                st.markdown(str(text).replace("$", "\\$"))

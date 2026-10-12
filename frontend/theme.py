"""
frontend/theme.py — AdMitra minimalist monochrome design system
===============================================================
Sleek dark mode (Linear / Vercel style) with generous whitespace,
custom brand logo integration, horizontal top navigation, and clean layout.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import streamlit as st

NAV_ITEMS = [
    ("home", "🏠", "Home"),
    ("overview", "📊", "Overview"),
    ("diagnostic", "🩺", "Diagnostics"),
    ("performance", "📈", "Performance"),
    ("budget", "💰", "Budget"),
    ("creative", "🎨", "Creative Studio"),
    ("engagement", "💬", "Engagement"),
    ("pricing", "💳", "Pricing"),
]

LOGO_PATH = Path(__file__).parent / "assets" / "admitra_logo.jpg"


def get_logo_base64() -> str:
    if LOGO_PATH.exists():
        try:
            return base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        except Exception:
            return ""
    return ""


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #f8fafc;
  --surface: rgba(255, 255, 255, 0.85);
  --surface-hover: rgba(0, 0, 0, 0.04);
  --surface-card: #ffffff;
  --glass-bg: rgba(255, 255, 255, 0.75);
  --glass-border: rgba(0, 0, 0, 0.08);
  --glass-highlight: rgba(255, 255, 255, 0.9);
  --border: #e2e8f0;
  --border-light: #cbd5e1;
  --text: #0f172a;
  --text-muted: #64748b;
  --text-sub: #94a3b8;
  --accent: #0284c7;
  --ok: #16a34a;
  --warn: #d97706;
  --danger: #dc2626;
  --radius: 16px;
}

/* Base resets & typography */
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
  color: var(--text) !important;
  -webkit-font-smoothing: antialiased;
}

code, pre {
  font-family: 'JetBrains Mono', monospace !important;
}

.stApp, .main {
  background-color: var(--bg) !important;
  background-image: 
    radial-gradient(at 15% 10%, rgba(2, 132, 199, 0.03) 0px, transparent 40%),
    radial-gradient(at 85% 85%, rgba(0, 0, 0, 0.02) 0px, transparent 50%) !important;
  color: var(--text) !important;
}

header[data-testid="stHeader"] {
  background: transparent !important;
  height: 0 !important;
}

/* Generous breathing room and maximum reading comfort */
.block-container {
  padding: 1.5rem 3.5rem 4rem 3.5rem !important;
  max-width: 1560px !important;
}

/* Sidebar: Completely hidden for clean full-width canvas */
section[data-testid="stSidebar"] {
  display: none !important;
}

button[data-testid="stSidebarCollapseButton"] {
  display: none !important;
}

/* Brand Display */
.am-brand-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 4px 18px 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 18px;
}

.am-brand-logo-img {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  object-fit: cover;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.16);
}

.am-brand-title {
  font-weight: 800;
  font-size: 1.15rem;
  letter-spacing: -0.02em;
  color: #0f172a;
  line-height: 1.1;
}

.am-brand-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-top: 2px;
}

/* Sidebar navigation buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] {
  gap: 4px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label {
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  border: 1px solid transparent;
  width: 100%;
  background: transparent;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
  background: var(--surface-hover);
  border-color: var(--border);
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
  display: none;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label p {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-muted);
  margin: 0;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: #0f172a;
  border-color: #0f172a;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.15);
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
  color: #ffffff;
  font-weight: 700;
}

/* Apple Liquid Glassmorphism Header Bar (White / Light Mode) */
.am-apple-glass-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(28px) saturate(190%) !important;
  -webkit-backdrop-filter: blur(28px) saturate(190%) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: var(--radius);
  padding: 12px 24px;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
}

.am-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(28px) saturate(190%);
  -webkit-backdrop-filter: blur(28px) saturate(190%);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius);
  padding: 14px 24px;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
}

.am-top-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.am-top-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.am-crumb {
  color: var(--text-muted);
  font-size: 0.88rem;
}

.am-crumb b {
  color: #0f172a;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.am-top-right {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

/* Segmented Pill Bar (Horizontal Radio) */
div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-orientation="horizontal"]) {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 999px !important;
  padding: 6px 10px !important;
  display: inline-flex !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
  margin-bottom: 22px !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] {
  gap: 6px !important;
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label {
  background: transparent !important;
  border-radius: 999px !important;
  padding: 8px 18px !important;
  border: 1px solid transparent !important;
  cursor: pointer !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label:hover {
  background: rgba(0, 0, 0, 0.04) !important;
  border-color: #cbd5e1 !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label > div:first-child {
  display: none !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label p {
  color: #475569 !important;
  font-size: 0.86rem !important;
  font-weight: 600 !important;
  margin: 0 !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label:has(input:checked) {
  background: #0f172a !important;
  border-color: #0f172a !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.2) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > label:has(input:checked) p {
  color: #ffffff !important;
  font-weight: 700 !important;
}

/* Pill Badges */
.am-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.76rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #ffffff;
  color: #475569;
}

.am-pill.ok {
  color: #16a34a;
  border-color: rgba(22, 163, 74, 0.3);
  background: rgba(22, 163, 74, 0.08);
}

.am-pill.warn {
  color: #d97706;
  border-color: rgba(217, 119, 6, 0.3);
  background: rgba(217, 119, 6, 0.08);
}

.am-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}

/* Modern Minimalist Page Header */
.am-page-header {
  margin-bottom: 24px;
}

.am-page-title {
  font-size: 1.85rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0;
  color: #0f172a !important;
}

.am-page-sub {
  color: var(--text-muted);
  font-size: 0.92rem;
  margin: 4px 0 0 0;
  line-height: 1.5;
}

/* Minimalist KPI Cards (Apple Crisp White Style) */
.am-kpi {
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.04) 0%, rgba(255, 255, 255, 0.95) 100%), #ffffff !important;
  border: 1px solid rgba(2, 132, 199, 0.16) !important;
  border-radius: var(--radius);
  padding: 20px 22px;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 2px 12px rgba(2, 132, 199, 0.04);
}

.am-kpi:hover {
  border-color: rgba(2, 132, 199, 0.35) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(2, 132, 199, 0.09);
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.07) 0%, rgba(255, 255, 255, 0.98) 100%), #ffffff !important;
}

.am-kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.am-kpi-label {
  color: var(--text-muted);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.am-kpi-icon {
  font-size: 1.1rem;
}

.am-kpi-value {
  font-size: 1.95rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-top: 10px;
  color: #0f172a !important;
  font-variant-numeric: tabular-nums;
}

.am-kpi-delta {
  font-size: 0.78rem;
  font-weight: 600;
  margin-top: 4px;
}

.am-kpi-delta.up { color: #16a34a; }
.am-kpi-delta.down { color: #dc2626; }
.am-kpi-delta.flat { color: var(--text-muted); }

/* General Cards & Streamlit Elements */
.glass-card, .am-card {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: var(--radius) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03) !important;
  padding: 22px 24px;
  margin-bottom: 20px;
}

.am-card-title {
  font-weight: 700;
  font-size: 1.05rem;
  color: #0f172a !important;
  letter-spacing: -0.01em;
  margin-bottom: 3px;
}

.am-card-sub {
  color: var(--text-muted);
  font-size: 0.84rem;
  margin-bottom: 14px;
}

/* Buttons & Nav Pills (Apple Light Mode) */
.stButton > button {
  border-radius: 999px !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  border: 1px solid #e2e8f0 !important;
  background-color: #ffffff !important;
  color: #475569 !important;
  padding: 8px 14px !important;
  white-space: nowrap !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stButton > button:hover {
  background-color: #f1f5f9 !important;
  border-color: #cbd5e1 !important;
  color: #0f172a !important;
  transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
  background: #0f172a !important;
  color: #ffffff !important;
  border: 1px solid #0f172a !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15) !important;
}

.stButton > button[kind="primary"]:hover {
  background: #1e293b !important;
  border-color: #1e293b !important;
  color: #ffffff !important;
  transform: translateY(-1px);
}

/* Header Trigger Button Specific Styling */
button[data-testid="baseButton-secondary"]:has(span:contains("Linked Accounts")),
div:has(> button[data-testid*="btn_trigger_oauth_modal"]) > button {
  height: 48px !important;
  margin-top: 10px !important;
  background: #0f172a !important;
  color: #ffffff !important;
  border: 1px solid #0f172a !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12) !important;
}

div:has(> button[data-testid*="btn_trigger_oauth_modal"]) > button:hover {
  background: #1e293b !important;
  border-color: #1e293b !important;
  color: #ffffff !important;
  transform: translateY(-1px);
}

/* Inputs & Selectboxes */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
  background-color: #ffffff !important;
  border-color: var(--border) !important;
  border-radius: 10px !important;
  color: #0f172a !important;
}

div[data-baseweb="textarea"] {
  background-color: #ffffff !important;
  border-color: var(--border) !important;
  border-radius: 10px !important;
  color: #0f172a !important;
}

/* DataFrame styling */
div[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--surface-card) !important;
}

div[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--surface-card) !important;
}

hr {
  border-color: var(--border) !important;
  margin: 24px 0 !important;
}

/* Clean Minimal Footer */
.am-footer {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--text-sub);
  font-size: 0.8rem;
}

.am-footer b {
  color: var(--text-muted);
}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand() -> None:
    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="am-brand-logo-img" alt="AdMitra Logo" />'
    else:
        logo_html = '<div style="width:44px; height:44px; border-radius:12px; background:#18181b; display:flex; align-items:center; justify-content:center; font-size:22px; border:1px solid rgba(255,255,255,0.12);">⚡</div>'

    st.markdown(
        f"""
        <div class="am-brand-box">
          {logo_html}
          <div>
            <div class="am-brand-title">AdMitra</div>
            <div class="am-brand-sub">AI Marketing Suite</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_apple_nav_header(current_page: str, used_mock: bool, meta_live: bool, account_name: str = "AdMitra Workspace") -> str:
    """
    Renders a unified, single-line Apple Frosted Glass Header Bar.
    Left: Brand Logo & Title
    Center: Horizontal Navigation Tabs (Previous names, generous spacing)
    Right: Live Status & Account Badge
    """
    logo_b64 = get_logo_base64()
    logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="am-top-logo" alt="AdMitra" />' if logo_b64 else '⚡'

    api_pill = (
        '<span class="am-pill warn" style="padding:4px 10px; font-size:0.72rem;"><span class="am-dot"></span>Standalone</span>'
        if used_mock
        else '<span class="am-pill ok" style="padding:4px 10px; font-size:0.72rem;"><span class="am-dot"></span>Online</span>'
    )
    meta_pill = (
        '<span class="am-pill ok" style="padding:4px 10px; font-size:0.72rem;"><span class="am-dot"></span>Meta Live</span>'
        if meta_live
        else '<span class="am-pill warn" style="padding:4px 10px; font-size:0.72rem;"><span class="am-dot"></span>Sandbox</span>'
    )

    if "active_nav_page" not in st.session_state:
        st.session_state["active_nav_page"] = current_page or "home"

    # State for connected accounts
    if "linked_social_accounts" not in st.session_state:
        st.session_state["linked_social_accounts"] = {
            "meta_fb": True,
            "instagram": True,
            "tiktok": False,
            "youtube": False,
        }
    if "selected_oauth_channel" not in st.session_state:
        st.session_state["selected_oauth_channel"] = None

    @st.dialog("🔗 Connect Social & Ad Channels", width="large")
    def show_connect_channels_dialog():
        selected = st.session_state.get("selected_oauth_channel")
        
        # Channel metadata & OAuth configs
        channels = {
            "meta_fb": {
                "name": "Facebook Pages & Meta Ads",
                "tagline": "Meta Marketing Graph API v19.0",
                "color": "#1877F2",
                "bg_tint": "rgba(24, 119, 242, 0.06)",
                "border": "rgba(24, 119, 242, 0.25)",
                "svg_logo": """<svg width="34" height="34" viewBox="0 0 48 48"><circle cx="24" cy="24" r="24" fill="#1877F2"/><path d="M29 24.3h-3.6V37h-5.4V24.3h-2.6v-4.6h2.6v-3c0-3.6 1.7-5.7 5.7-5.7h3.5v4.5h-2.2c-1.8 0-2.1.8-2.1 2v2.2h4.5l-.5 4.6z" fill="#ffffff"/></svg>""",
                "scopes": ["ads_management", "ads_read", "pages_manage_posts", "pages_read_engagement", "leads_retrieval"],
                "account_handle": "Achintha Kaushalya (ID: act_8923419024)",
            },
            "instagram": {
                "name": "Instagram Professional",
                "tagline": "Instagram Graph API Business Suite",
                "color": "#E1306C",
                "bg_tint": "rgba(225, 48, 108, 0.06)",
                "border": "rgba(225, 48, 108, 0.25)",
                "svg_logo": """<svg width="34" height="34" viewBox="0 0 48 48"><defs><radialGradient id="igG" cx="0.2" cy="1" r="1.3"><stop offset="0%" stop-color="#FFDD55"/><stop offset="50%" stop-color="#FF543E"/><stop offset="100%" stop-color="#C837AB"/></radialGradient></defs><rect width="48" height="48" rx="12" fill="url(#igG)"/><path d="M24 16c-4.4 0-8 3.6-8 8s3.6 8 8 8 8-3.6 8-8-3.6-8-8-8zm0 13c-2.8 0-5-2.2-5-5s2.2-5 5-5 5 2.2 5 5-2.2 5-5 5zm9.5-13.8c-.9 0-1.7.8-1.7 1.7s.8 1.7 1.7 1.7 1.7-.8 1.7-1.7-.8-1.7-1.7-1.7z" fill="#ffffff"/></svg>""",
                "scopes": ["instagram_basic", "instagram_manage_comments", "instagram_content_publish", "instagram_manage_insights"],
                "account_handle": "@admitra.lk (Professional Creator)",
            },
            "tiktok": {
                "name": "TikTok for Business",
                "tagline": "TikTok Commercial Content & Spark Ads API",
                "color": "#000000",
                "bg_tint": "rgba(0, 0, 0, 0.05)",
                "border": "rgba(0, 0, 0, 0.2)",
                "svg_logo": """<svg width="34" height="34" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#000000"/><path d="M33 18.5a7.5 7.5 0 0 1-5-1.9v11.6a7.2 7.2 0 1 1-7.2-7.2c.4 0 .9 0 1.3.1v4a3.3 3.3 0 1 0 2 3.1V10h4a7.5 7.5 0 0 0 4.9 4v4.5z" fill="#25F4EE"/><path d="M32.5 18a7.5 7.5 0 0 1-5-1.9v11.6a7.2 7.2 0 1 1-7.2-7.2c.4 0 .9 0 1.3.1v4a3.3 3.3 0 1 0 2 3.1V10h4a7.5 7.5 0 0 0 4.9 4v4z" fill="#FE2C55"/></svg>""",
                "scopes": ["video.publish", "video.insights", "user.info.basic", "ad.management", "spark_ads.read"],
                "account_handle": "@admitra_official (Business ID: tt_98231)",
            },
            "youtube": {
                "name": "YouTube Brand Channel",
                "tagline": "Google Data API v3 & Video Ads Partner",
                "color": "#FF0000",
                "bg_tint": "rgba(255, 0, 0, 0.06)",
                "border": "rgba(255, 0, 0, 0.25)",
                "svg_logo": """<svg width="34" height="34" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#FF0000"/><path d="M34 24l-14 8V16l14 8z" fill="#ffffff"/></svg>""",
                "scopes": ["youtube.readonly", "youtube.upload", "yt-analytics.readonly", "adwords.partner"],
                "account_handle": "AdMitra Studios (Channel ID: UC8x192k)",
            },
        }

        # Sub-view: If user clicked to authorize a specific channel, show realistic OAuth screen
        if selected:
            cfg = channels[selected]
            is_connected = st.session_state["linked_social_accounts"].get(selected, False)
            
            st.markdown(
                f"""
                <div style="background: {cfg['bg_tint']}; border: 1.5px solid {cfg['border']}; border-radius: 16px; padding: 22px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 14px;">
                        {cfg['svg_logo']}
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; color: {cfg['color']};">OAuth 2.0 Authorization Gateway</div>
                            <h3 style="margin: 2px 0 0 0; color: #0f172a; font-size: 1.3rem; font-weight: 800;">{cfg['name']}</h3>
                            <div style="color: #64748b; font-size: 0.82rem;">{cfg['tagline']}</div>
                        </div>
                    </div>
                    
                    <div style="background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 16px; margin-top: 14px;">
                        <div style="font-size: 0.86rem; color: #0f172a; font-weight: 700; margin-bottom: 8px;">
                            AdMitra AI Suite is requesting access to:
                        </div>
                        <div style="font-size: 0.82rem; color: #334155; margin-bottom: 12px; padding: 8px 12px; background: #f8fafc; border-radius: 8px; border-left: 3px solid {cfg['color']};">
                            <b>Account:</b> {cfg['account_handle']}
                        </div>
                        <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 6px; font-weight: 600;">Requested API Scopes:</div>
                        <ul style="margin: 0; padding-left: 20px; font-size: 0.8rem; color: #475569; line-height: 1.6;">
                            {''.join(f'<li><code style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:0.75rem;">{scope}</code></li>' for scope in cfg['scopes'])}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_back, c_action = st.columns([1, 1.6])
            with c_back:
                if st.button("← Back to Channels", use_container_width=True):
                    st.session_state["selected_oauth_channel"] = None
                    st.rerun()
            with c_action:
                if is_connected:
                    if st.button(f"Revoke & Disconnect", key="btn_oauth_revoke", type="secondary", use_container_width=True):
                        st.session_state["linked_social_accounts"][selected] = False
                        st.session_state["selected_oauth_channel"] = None
                        st.toast(f"Disconnected {cfg['name']} access token.", icon="ℹ️")
                        st.rerun()
                else:
                    if st.button(f"Allow Access & Authorize API", key="btn_oauth_allow", type="primary", use_container_width=True):
                        st.session_state["linked_social_accounts"][selected] = True
                        st.session_state["selected_oauth_channel"] = None
                        st.toast(f"Successfully authorized {cfg['name']}!", icon="✅")
                        st.rerun()
            return

        # Main View: 4 Official Platform Cards
        st.markdown(
            """
            <div style="margin-bottom: 20px;">
                <p style="margin: 0; color: #475569; font-size: 0.88rem; line-height: 1.45;">
                    Link your active digital marketing channels to enable <b>real-time autonomous ad campaigns</b>, 
                    continuous budget shifts, AI copy distribution, and instant customer comment responses.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        grid_cols = st.columns(2)
        channel_keys = ["meta_fb", "instagram", "tiktok", "youtube"]
        
        for idx, ch_key in enumerate(channel_keys):
            cfg = channels[ch_key]
            is_connected = st.session_state["linked_social_accounts"].get(ch_key, False)
            col_target = grid_cols[idx % 2]
            
            with col_target:
                status_badge = (
                    f'<span style="display:inline-flex; align-items:center; gap:5px; background:#ecfdf5; color:#15803d; border:1px solid #bbf7d0; font-size:0.72rem; font-weight:700; padding:3px 10px; border-radius:999px; line-height:1;"><span style="width:6px; height:6px; border-radius:50%; background:#22c55e;"></span>Connected</span>'
                    if is_connected
                    else f'<span style="display:inline-flex; align-items:center; gap:5px; background:#f8fafc; color:#64748b; border:1px solid #e2e8f0; font-size:0.72rem; font-weight:600; padding:3px 10px; border-radius:999px; line-height:1;"><span style="width:6px; height:6px; border-radius:50%; background:#94a3b8;"></span>Disconnected</span>'
                )

                st.markdown(
                    f"""
                    <div style="background: {'#f8fafc' if is_connected else '#ffffff'}; border: 1.5px solid {'#cbd5e1' if is_connected else '#e2e8f0'}; border-radius: 16px; padding: 18px 18px 14px 18px; margin-bottom: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                {cfg['svg_logo']}
                                <div>
                                    <div style="font-weight: 800; color: #0f172a; font-size: 0.98rem; line-height: 1.2;">{cfg['name']}</div>
                                    <div style="font-size: 0.73rem; color: #64748b; margin-top: 2px;">{cfg['tagline']}</div>
                                </div>
                            </div>
                            <div>{status_badge}</div>
                        </div>
                        <div style="font-size: 0.77rem; color: #475569; background: #ffffff; border-radius: 8px; padding: 7px 12px; border: 1px solid #e2e8f0; margin-bottom: 2px;">
                            <span style="color:#94a3b8; font-weight:600;">Account:</span> {cfg['account_handle'] if is_connected else '<span style="color:#64748b; font-style:italic;">Ready for OAuth linking</span>'}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                btn_label = f"⚙️ Manage Connection" if is_connected else f"⚡ Connect {cfg['name'].split()[0]}"
                btn_type = "secondary" if is_connected else "primary"
                if st.button(btn_label, key=f"btn_modal_{ch_key}", type=btn_type, use_container_width=True):
                    st.session_state["selected_oauth_channel"] = ch_key
                    st.rerun()
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Sleek Single-Line Apple Frosted Header
    header_cols = st.columns([7.6, 2.4])
    with header_cols[0]:
        st.markdown(
            f"""
            <div class="am-apple-glass-header" style="margin-bottom: 16px; padding: 10px 22px;">
              <div class="am-top-left" style="gap: 12px;">
                {logo_html}
                <div>
                  <div style="font-weight: 800; font-size: 1.05rem; color: #0f172a; letter-spacing: -0.02em; line-height: 1.1;">
                    AdMitra <span style="font-weight:600; font-size:0.68rem; color:#0284c7; background:rgba(2,132,199,0.08); border:1px solid rgba(2,132,199,0.25); padding:1px 6px; border-radius:5px; margin-left:4px;">PRO</span>
                  </div>
                  <div style="font-size: 0.7rem; color: var(--text-sub);">AI Marketing Command Center</div>
                </div>
              </div>
              <div class="am-top-right" style="gap: 8px;">
                {api_pill}
                {meta_pill}
                <span class="am-pill" style="padding:4px 10px; font-size:0.72rem;">{account_name}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_cols[1]:
        connected_count = sum(1 for v in st.session_state["linked_social_accounts"].values() if v)
        if st.button(f"🔗 Linked Accounts ({connected_count}/4)", key="btn_trigger_oauth_modal", use_container_width=True):
            st.session_state["selected_oauth_channel"] = None
            show_connect_channels_dialog()

    # Sleek Tab Selector with generous whitespace (Linear style tabs)
    tab_names = [f"{icon} {label}" for _, icon, label in NAV_ITEMS]
    nav_keys = [k for k, _, _ in NAV_ITEMS]
    
    current_idx = nav_keys.index(st.session_state["active_nav_page"]) if st.session_state["active_nav_page"] in nav_keys else 0

    # Clean horizontal pill row using st.segmented_control (or fallback to clean styled buttons)
    cols = st.columns(len(NAV_ITEMS))
    for idx, (key, icon, label) in enumerate(NAV_ITEMS):
        with cols[idx]:
            is_active = (st.session_state["active_nav_page"] == key)
            label_text = f"{icon} {label}"
            btn_kind = "primary" if is_active else "secondary"
            if st.button(label_text, key=f"nav_link_{key}", type=btn_kind, use_container_width=True):
                st.session_state["active_nav_page"] = key
                st.rerun()

    # Sleek High-Contrast Dark Divider Bar framing the navigation area
    st.markdown(
        """
        <div style="
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, rgba(15, 23, 42, 0.08) 0%, rgba(15, 23, 42, 0.85) 25%, rgba(15, 23, 42, 0.85) 75%, rgba(15, 23, 42, 0.08) 100%);
            border-radius: 999px;
            margin: 22px 0 28px 0;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
        "></div>
        """,
        unsafe_allow_html=True,
    )
    return st.session_state.get("active_nav_page", "home")


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="am-page-header">
          <h1 class="am-page-title">{title}</h1>
          <p class="am-page-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", trend: str = "flat", icon: str = "📌") -> str:
    delta_html = f'<div class="am-kpi-delta {trend}">{delta}</div>' if delta else ""
    return (
        f'<div class="am-kpi">'
        f'<div class="am-kpi-top"><span class="am-kpi-label">{label}</span>'
        f'<span class="am-kpi-icon">{icon}</span></div>'
        f'<div class="am-kpi-value">{value}</div>'
        f'{delta_html}</div>'
    )


def kpi_row(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for col, html in zip(cols, cards):
        with col:
            st.markdown(html, unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        """
        <div class="am-footer">
          <div><b>AdMitra v2.4</b> — Autonomous AI Marketing Suite • SLIIT IRWA Capstone Project</div>
          <div>Meta Marketing Graph API • Powered by Multi-Agent Architecture</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_open(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="am-card"><div class="am-card-title">{title}</div>'
        f'<div class="am-card-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def to_bullets(text: str, max_items: int = 5, max_chars: int = 120) -> list[str]:
    import re

    items: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", line).strip()
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


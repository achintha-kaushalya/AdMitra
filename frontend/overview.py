"""
frontend/overview.py — Executive overview page (KPI cards, charts, alerts).
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from frontend.theme import kpi_card, kpi_row, page_header

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#c3cde0", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#1c2740", zeroline=False),
    yaxis=dict(gridcolor="#1c2740", zeroline=False),
)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return default


def _short(name: str, n: int = 22) -> str:
    name = str(name).replace('Post: ', '')
    return name if len(name) <= n else name[: n - 1] + "…"


def render_overview(metrics: list, health_score: int, issues: list, sentiment: str) -> None:
    page_header("Overview", "Real-time snapshot of your ad account performance and health.")

    rows = [m for m in metrics if isinstance(m, dict)]
    total_spend = sum(_num(m.get("spend")) for m in rows)
    total_results = sum(_num(m.get("results_count")) for m in rows)
    impressions = sum(_num(m.get("impressions")) for m in rows)
    active = [m for m in rows if "ACTIVE" in str(m.get("status", "")).upper()]
    roas_vals = [_num(m.get("current_ROAS")) for m in rows if _num(m.get("current_ROAS")) > 0]
    ctr_vals = [_num(m.get("current_CTR")) for m in rows if _num(m.get("current_CTR")) > 0]
    avg_roas = sum(roas_vals) / len(roas_vals) if roas_vals else 0.0
    avg_ctr = sum(ctr_vals) / len(ctr_vals) if ctr_vals else 0.0

    kpi_row(
        [
            kpi_card("Total Spend", f"${total_spend:,.2f}", f"{len(rows)} ad sets tracked", "flat", "💵"),
            kpi_card("Avg ROAS", f"{avg_roas:.2f}x", "Return on ad spend", "up" if avg_roas >= 2 else "down", "📈"),
            kpi_card("Avg CTR", f"{avg_ctr:.2f}%", f"{int(impressions):,} impressions", "flat", "🖱️"),
            kpi_card("Active Ad Sets", str(len(active)), f"{int(total_results):,} total results", "up" if active else "flat", "🚀"),
            kpi_card("Account Health", f"{health_score}/100", f"{len(issues)} open issues",
                     "up" if health_score >= 80 else "down", "🛡️"),
        ]
    )
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.7, 1])
    with left:
        st.markdown('<div class="am-card-title">Spend vs. Results by Ad Set</div>'
                    '<div class="am-card-sub">Top ad sets by spend</div>', unsafe_allow_html=True)
        top = sorted(rows, key=lambda m: _num(m.get("spend")), reverse=True)[:8]
        if top:
            names = [_short(m.get("name", "Ad Set")) for m in top]
            fig = go.Figure()
            fig.add_bar(x=names, y=[_num(m.get("spend")) for m in top], name="Spend ($)",
                        marker_color="#6366f1")
            fig.add_scatter(x=names, y=[_num(m.get("current_ROAS")) for m in top], name="ROAS",
                            yaxis="y2", mode="lines+markers", line=dict(color="#34d399", width=3))
            fig.update_layout(**_LAYOUT, height=330, legend=dict(orientation="h", y=1.12),
                              yaxis2=dict(overlaying="y", side="right", showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No campaign data yet. Run a system audit from the sidebar.")

    with right:
        st.markdown('<div class="am-card-title">Account Health</div>'
                    '<div class="am-card-sub">Composite diagnostic score</div>', unsafe_allow_html=True)
        color = "#10b981" if health_score >= 80 else "#f59e0b" if health_score >= 50 else "#ef4444"
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=health_score,
            number=dict(font=dict(size=40, color="#fff")),
            gauge=dict(axis=dict(range=[0, 100], tickcolor="#475569"), bar=dict(color=color),
                       bgcolor="#16213a", borderwidth=0),
        ))
        gauge.update_layout(**_LAYOUT, height=260)
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Audience sentiment: **{sentiment}**")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    t_col, a_col = st.columns([1.7, 1])
    with t_col:
        st.markdown('<div class="am-card-title">Ad Set Performance</div>'
                    '<div class="am-card-sub">Sorted by ROAS</div>', unsafe_allow_html=True)
        if rows:
            table = [
                {
                    "Ad Set": _short(m.get("name", ""), 34),
                    "Status": str(m.get("status", "")).title(),
                    "Spend ($)": round(_num(m.get("spend")), 2),
                    "CTR (%)": round(_num(m.get("current_CTR")), 2),
                    "ROAS": round(_num(m.get("current_ROAS")), 2),
                    "Results": int(_num(m.get("results_count"))),
                }
                for m in sorted(rows, key=lambda x: _num(x.get("current_ROAS")), reverse=True)[:10]
            ]
            st.dataframe(table, use_container_width=True, hide_index=True)
    with a_col:
        st.markdown('<div class="am-card-title">Alerts</div>'
                    '<div class="am-card-sub">Latest diagnostic findings</div>', unsafe_allow_html=True)
        if not issues:
            st.success("No open issues. Account looks healthy.")
        for issue in issues[:5]:
            sev = str(issue.get("severity", "info")).lower()
            icon = {"critical": "🔴", "high": "🔴", "warning": "🟠", "medium": "🟠"}.get(sev, "🔵")
            st.markdown(f"{icon} {issue.get('message', issue.get('type', 'Issue'))}")

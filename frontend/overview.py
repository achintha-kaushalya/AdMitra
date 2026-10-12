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
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#e2e8f0", zeroline=False),
    yaxis=dict(gridcolor="#e2e8f0", zeroline=False),
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
    page_header("Command Center Overview", "Real-time snapshot of your autonomous Meta ad operations and system health.")

    rows = [m for m in metrics if isinstance(m, dict)]
    total_spend = sum(_num(m.get("spend")) for m in rows)
    total_results = sum(_num(m.get("results_count")) for m in rows)
    impressions = sum(_num(m.get("impressions")) for m in rows)
    
    # Active sets: check both status and effective_status
    active_sets = [
        m for m in rows 
        if "ACTIVE" in str(m.get("status", "")).upper() 
        or "ACTIVE" in str(m.get("effective_status", "")).upper()
    ]
    active_count = len(active_sets) if active_sets else len(rows)

    roas_vals = [_num(m.get("current_ROAS")) for m in rows if _num(m.get("current_ROAS")) > 0]
    avg_roas = sum(roas_vals) / len(roas_vals) if roas_vals else 0.0

    # Impressions-weighted CTR calculation
    total_clicks = sum(_num(m.get("clicks")) for m in rows if _num(m.get("clicks")) > 0)
    if total_clicks > 0 and impressions > 0:
        avg_ctr = (total_clicks / impressions) * 100.0
    else:
        # Fallback to impressions-weighted average of CTR
        weighted_ctr_sum = sum(_num(m.get("current_CTR")) * _num(m.get("impressions")) for m in rows)
        avg_ctr = (weighted_ctr_sum / impressions) if impressions > 0 else (sum(_num(m.get("current_CTR")) for m in rows) / len(rows) if rows else 0.0)

    results_label = f"{int(total_results):,} conversions" if total_results > 0 else "Delivery active"

    kpi_row(
        [
            kpi_card("Total Spend", f"${total_spend:,.2f}", f"{len(rows)} ad sets tracked", "flat", "💵"),
            kpi_card("Avg ROAS", f"{avg_roas:.2f}x", "Target > 2.0x", "up" if avg_roas >= 2 else "down", "📈"),
            kpi_card("Avg CTR", f"{avg_ctr:.2f}%", f"{int(impressions):,} impressions", "up" if avg_ctr >= 1.5 else "flat", "🖱️"),
            kpi_card("Active Ad Sets", str(active_count), results_label, "up" if active_count > 0 else "flat", "🚀"),
            kpi_card("Shield Health", f"{health_score}/100", f"{len(issues)} open issues",
                     "up" if health_score >= 80 else "down", "🛡️"),
        ]
    )
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.7, 1])
    with left:
        st.markdown('<div class="am-card-title">Spend vs. Results by Ad Set</div>'
                    '<div class="am-card-sub">Top ad sets by spend & ROAS</div>', unsafe_allow_html=True)
        top = sorted(rows, key=lambda m: _num(m.get("spend")), reverse=True)[:8]
        if top:
            names = [_short(m.get("name", "Ad Set")) for m in top]
            fig = go.Figure()
            fig.add_bar(
                x=names,
                y=[_num(m.get("spend")) for m in top],
                name="Spend ($)",
                marker=dict(color="#0284c7", opacity=0.85, line=dict(color="#0369a1", width=1.5)),
            )
            fig.add_scatter(
                x=names,
                y=[_num(m.get("current_ROAS")) for m in top],
                name="ROAS",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="#0f172a", width=3.5),
                marker=dict(color="#0f172a", size=9, line=dict(color="#ffffff", width=2)),
            )
            layout_cfg = dict(_LAYOUT)
            layout_cfg.pop("yaxis", None)
            fig.update_layout(
                **layout_cfg,
                height=330,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(color="#0f172a", size=12)),
                yaxis=dict(title=dict(text="Spend ($)", font=dict(color="#0284c7", size=12)), gridcolor="#e2e8f0", zeroline=False),
                yaxis2=dict(title=dict(text="ROAS (x)", font=dict(color="#0f172a", size=12)), overlaying="y", side="right", showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No campaign data yet. Run a system audit from the sidebar.")

    with right:
        st.markdown('<div class="am-card-title">Account Health Score</div>'
                    '<div class="am-card-sub">Real-time diagnostics composite</div>', unsafe_allow_html=True)
        color = "#16a34a" if health_score >= 80 else "#d97706" if health_score >= 50 else "#dc2626"
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            number=dict(font=dict(size=44, color="#0f172a", family="Plus Jakarta Sans, sans-serif")),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor="#94a3b8", tickfont=dict(color="#64748b")),
                bar=dict(color=color, thickness=0.3),
                bgcolor="#f1f5f9",
                borderwidth=1,
                bordercolor="#e2e8f0",
            ),
        ))
        gauge_layout = dict(_LAYOUT)
        gauge_layout.pop("margin", None)
        gauge.update_layout(**gauge_layout, height=270, margin=dict(l=15, r=15, t=20, b=10))
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Audience sentiment: **{sentiment}**")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # Ad Set Performance: Clean full-width data presentation
    st.markdown('<div class="am-card-title">Ad Set Performance</div>'
                '<div class="am-card-sub">Comprehensive overview sorted by ROAS efficiency</div>', unsafe_allow_html=True)
    if rows:
        table = [
            {
                "Ad Set Name": m.get("name", "Ad Set"),
                "Status": "🟢 Active" if "ACTIVE" in str(m.get("status", "")).upper() or "ACTIVE" in str(m.get("effective_status", "")).upper() else "⚪ Paused",
                "Spend (USD)": f"${round(_num(m.get('spend')), 2):,.2f}",
                "CTR (%)": f"{round(_num(m.get('current_CTR')), 2):.2f}%",
                "ROAS": f"{round(_num(m.get('current_ROAS')), 2):.2f}x",
                "Conversions / Results": f"{int(_num(m.get('results_count'))):,}",
                "Impressions": f"{int(_num(m.get('impressions'))):,}",
            }
            for m in sorted(rows, key=lambda x: _num(x.get("current_ROAS")), reverse=True)[:15]
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    if issues:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="am-card-title">Active Health Alerts</div>'
                    '<div class="am-card-sub">Latest diagnostic findings requiring attention</div>', unsafe_allow_html=True)
        alert_cols = st.columns(min(len(issues[:3]), 3))
        for idx, issue in enumerate(issues[:3]):
            with alert_cols[idx]:
                sev = str(issue.get("severity", "info")).lower()
                icon = "🔴" if sev in ("critical", "high") else ("🟠" if sev in ("warning", "medium") else "🔵")
                msg = issue.get("message", issue.get("type", "Issue"))
                st.markdown(
                    f"""
                    <div style="background: rgba(2, 132, 199, 0.04); border: 1px solid rgba(2, 132, 199, 0.16); border-radius: 10px; padding: 12px 14px; font-size: 0.84rem; color: #0f172a;">
                        <span style="font-size: 1rem; margin-right: 6px;">{icon}</span> <b>{issue.get('type', 'Alert')}</b>: {msg}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

"""Streamlit dashboard for the AdMitra marketing automation system."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx
import streamlit as st


API_URL = "http://localhost:8000/check-account"


def _mock_response(product: str, offer: str, tone: str, comment: str) -> dict[str, Any]:
    """Provide a complete demo response when the FastAPI service is offline."""
    return {
        "status": "success",
        "source": "mock",
        "results": {
            "diagnostic": {
                "status": "success",
                "agent": "DiagnosticAgent",
                "result": {
                    "issues": [
                        {"type": "paused_ad_set", "severity": "medium", "count": 1},
                        {"type": "billing_issue", "severity": "high", "count": 1},
                    ],
                    "recommendations": [
                        "Review the paused ad set before the next campaign launch.",
                        "Resolve the billing flag to prevent delivery interruption.",
                    ],
                },
            },
            "performance": {
                "status": "success",
                "agent": "PerformanceAgent",
                "result": {
                    "summary": "CPM is rising while CTR remains stable. Review audience quality and creative fatigue.",
                    "metrics": {"CPM change": "+12.4%", "CTR change": "-2.1%", "ROAS change": "+8.6%"},
                    "recommendations": ["Test a fresh creative and narrow low-intent placements."],
                },
            },
            "budget": {
                "status": "success",
                "agent": "BudgetAgent",
                "result": {
                    "summary": "Shift a portion of spend from low-return campaigns to the strongest ROAS segment.",
                    "flagged_campaigns": ["Weekend Awareness"],
                    "recommendations": ["Reallocate 15% of spend to the top-performing campaign."],
                },
            },
            "content": {
                "status": "success",
                "agent": "ContentAgent",
                "result": {
                    "english": {
                        "headline": f"{product}: {offer}"[:40],
                        "body": f"Discover {product} today and enjoy {offer}."[:125],
                        "call_to_action": "Shop now",
                    },
                    "sinhala": {
                        "headline": f"{product}: {offer}"[:40],
                        "body": f"අද {product} සොයා {offer} භුක්ති විඳින්න."[:125],
                        "call_to_action": "දැන් මිලදී ගන්න",
                    },
                    "tone": tone,
                    "source": "mock",
                },
            },
            "engagement": {
                "status": "success",
                "agent": "EngagementAgent",
                "result": {
                    "comment": comment,
                    "sentiment": {"label": "POSITIVE", "score": 0.97},
                    "entities": [],
                    "reply": "Thank you for your kind words. We are delighted to hear that!",
                    "posted": False,
                    "dry_run": True,
                },
            },
        },
    }


def _run_audit(payload: dict[str, Any]) -> tuple[dict[str, Any], bool, str | None]:
    try:
        response = httpx.post(API_URL, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json(), False, None
    except (httpx.HTTPError, ValueError) as exc:
        return _mock_response(
            str(payload["product"]),
            str(payload["offer"]),
            str(payload["tone"]),
            str(payload["comment"]),
        ), True, str(exc)


def _agent_result(data: dict[str, Any], name: str) -> dict[str, Any]:
    agent = data.get("results", {}).get(name, {})
    return agent.get("result", {}) if isinstance(agent, dict) else {}


def _audit_score(data: dict[str, Any]) -> int:
    results = data.get("results", {})
    errors = sum(1 for item in results.values() if item.get("status") == "error")
    issues = len(_agent_result(data, "diagnostic").get("issues", []))
    return max(0, min(100, 100 - (errors * 25) - (issues * 10)))


def _show_overview(data: dict[str, Any], used_mock: bool) -> None:
    diagnostic = _agent_result(data, "diagnostic")
    performance = _agent_result(data, "performance")
    engagement = _agent_result(data, "engagement")
    issues = diagnostic.get("issues", [])
    score = _audit_score(data)

    st.markdown("### Account overview")
    status_label = "Demo data" if used_mock else "Live API"
    status_color = "#f59e0b" if used_mock else "#22c55e"
    st.markdown(
        f'<div class="status-pill"><span style="color:{status_color}">●</span> {status_label} '
        f' · Last run: {datetime.now().strftime("%H:%M:%S")}</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(4)
    columns[0].metric("Health score", f"{score}/100", "Account readiness")
    columns[1].metric("Open issues", len(issues), "Needs attention" if issues else "All clear")
    columns[2].metric("Sentiment", engagement.get("sentiment", {}).get("label", "N/A"))
    columns[3].metric("Agent coverage", f"{len(data.get('results', {}))}/5", "Agents responded")

    metrics = performance.get("metrics", {})
    if metrics:
        st.markdown("#### Performance movement")
        chart_rows = []
        for label, value in metrics.items():
            try:
                chart_rows.append({"Metric": label, "Change (%)": float(str(value).replace("%", "").replace("+", ""))})
            except (TypeError, ValueError):
                continue
        if chart_rows:
            st.bar_chart(chart_rows, x="Metric", y="Change (%)", color="#f97316", height=220)

    severity_counts = {}
    for issue in issues:
        severity = str(issue.get("severity", "info")).capitalize()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    if severity_counts:
        st.markdown("#### Issue severity")
        st.dataframe(
            [{"Severity": severity, "Issues": count} for severity, count in severity_counts.items()],
            hide_index=True,
            use_container_width=True,
        )


def _show_diagnostic(data: dict[str, Any]) -> None:
    result = _agent_result(data, "diagnostic")
    issues = result.get("issues", [])
    st.metric("Issues found", len(issues))
    if issues:
        for issue in issues:
            severity = str(issue.get("severity", "info")).upper()
            st.write(f"**{severity}**  {issue.get('type', 'Issue')}")
    else:
        st.success("No account issues reported.")
    for recommendation in result.get("recommendations", []):
        st.write(f"- {recommendation}")


def _show_performance(data: dict[str, Any]) -> None:
    result = _agent_result(data, "performance")
    st.write(result.get("summary", "No performance summary available."))
    metrics = result.get("metrics", {})
    if metrics:
        columns = st.columns(min(3, len(metrics)))
        for column, (label, value) in zip(columns, metrics.items()):
            column.metric(str(label), str(value))
    for recommendation in result.get("recommendations", []):
        st.write(f"- {recommendation}")


def _show_budget(data: dict[str, Any]) -> None:
    result = _agent_result(data, "budget")
    st.write(result.get("summary", "No budget summary available."))
    flagged = result.get("flagged_campaigns", [])
    st.write(f"Flagged campaigns: {', '.join(map(str, flagged)) if flagged else 'None'}")
    for recommendation in result.get("recommendations", []):
        st.write(f"- {recommendation}")


def _show_content(data: dict[str, Any]) -> None:
    result = _agent_result(data, "content")
    english, sinhala = st.columns(2)
    for column, label, copy in (
        (english, "English", result.get("english", {})),
        (sinhala, "Sinhala", result.get("sinhala", {})),
    ):
        with column:
            st.markdown(f"**{label}**")
            st.write(f"**{copy.get('headline', 'No headline')}**")
            st.write(copy.get("body", "No body copy."))
            st.caption(f"CTA: {copy.get('call_to_action', 'N/A')}")


def _show_engagement(data: dict[str, Any]) -> None:
    result = _agent_result(data, "engagement")
    sentiment = result.get("sentiment", {})
    st.metric("Sentiment", sentiment.get("label", "UNKNOWN"), sentiment.get("score"))
    st.write(f"**Draft reply:** {result.get('reply', 'No reply generated.')}")
    st.caption("Dry run: reply was not posted." if result.get("dry_run", True) else "Reply posted.")


def main() -> None:
    st.set_page_config(page_title="AdMitra Dashboard", page_icon="📊", layout="wide")
    st.markdown(
        """
        <style>
        .main { background: #f8fafc; }
        .block-container { padding-top: 2rem; max-width: 1400px; }
        .status-pill { display: inline-block; padding: 0.35rem 0.75rem; border-radius: 999px;
                       background: #fff7ed; color: #475569; font-size: 0.85rem; margin-bottom: 1rem; }
        [data-testid="stMetric"] { background: white; border: 1px solid #e2e8f0;
                                    border-radius: 10px; padding: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("AdMitra — AI Marketing Assistant")
    st.caption("A live command center for campaign health, performance, creative, and engagement.")

    with st.sidebar:
        st.header("Campaign inputs")
        product = st.text_input("Product", value="Jeans")
        offer = st.text_input("Offer", value="20% off")
        tone = st.selectbox("Tone", ["friendly", "professional", "urgent"])
        comment = st.text_area("Customer comment", value="Great support!")
        dry_run = st.toggle("Dry run", value=True)
        st.divider()
        st.caption("Backend: http://localhost:8000")

    if st.button("🔍 Run Account & Campaign Audit", type="primary", use_container_width=True):
        if not product.strip() or not offer.strip():
            st.error("Product and offer are required.")
            return
        payload = {
            "product": product.strip(),
            "offer": offer.strip(),
            "tone": tone,
            "comment": comment.strip(),
            "dry_run": dry_run,
        }
        with st.spinner("Running the marketing audit..."):
            data, used_mock, error = _run_audit(payload)
        st.session_state["audit_data"] = data
        if used_mock:
            st.warning("Backend is offline, so sample results are shown.")
            if error:
                st.caption(f"Connection detail: {error}")
        else:
            st.success("Audit completed.")

    data = st.session_state.get("audit_data")
    if not data:
        st.info("Enter campaign details and run an audit to view the results.")
        return

    used_mock = data.get("source") == "mock"
    _show_overview(data, used_mock)
    st.divider()

    cards = st.tabs([
        "🚨 Diagnostic Report",
        "📈 Performance Analysis",
        "💰 Budget Reallocation",
        "✍️ Bilingual Ad Creatives",
        "💬 Customer Engagement",
    ])
    with cards[0]:
        _show_diagnostic(data)
    with cards[1]:
        _show_performance(data)
    with cards[2]:
        _show_budget(data)
    with cards[3]:
        _show_content(data)
    with cards[4]:
        _show_engagement(data)

    with st.expander("Raw JSON"):
        st.json(data)
        st.download_button(
            "Download audit JSON",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name="admitra-audit.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
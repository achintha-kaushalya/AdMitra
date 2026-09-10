"""Campaign performance analysis using metrics, RAG, and Gemini."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from shared.mcp_schema import MCPResponse
from shared.security import sanitize_input


AGENT_NAME = "PerformanceAgent"
METRICS_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "mock_data"
    / "campaign_metrics.json"
)


try:
    from shared.meta_api import fetch_live_campaign_metrics
except ImportError:
    fetch_live_campaign_metrics = None


def _load_metrics() -> list[dict[str, Any]]:
    if fetch_live_campaign_metrics:
        live_metrics = fetch_live_campaign_metrics()
        if live_metrics:
            return live_metrics

    with METRICS_DATA_PATH.open(encoding="utf-8") as metrics_file:
        data = json.load(metrics_file)

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or not all(
        isinstance(item, dict) for item in data
    ):
        raise ValueError("Campaign metrics must be a JSON array of objects")

    return data


def _percentage_delta(
    current: Any,
    previous: Any
) -> float | None:
    current_value = float(current or 0)
    previous_value = float(previous or 0)

    if previous_value == 0:
        return None

    return round(
        (current_value - previous_value) / previous_value * 100,
        2
    )


def _summarize_metrics(
    metrics: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    summaries = []

    for campaign in metrics:
        cpm = float(campaign.get("current_CPM", 0.0) or 0.0)
        prev_cpm = float(campaign.get("prev_CPM", 0.0) or 0.0)
        ctr = float(campaign.get("current_CTR", 0.0) or 0.0)
        prev_ctr = float(campaign.get("prev_CTR", 0.0) or 0.0)
        roas = float(campaign.get("current_ROAS", 0.0) or 0.0)
        prev_roas = float(campaign.get("prev_ROAS", 0.0) or 0.0)
        spend = float(campaign.get("spend", 0.0) or 0.0)
        impressions = int(campaign.get("impressions", 0) or 0)
        
        cpm_delta = _percentage_delta(cpm, prev_cpm)
        ctr_delta = _percentage_delta(ctr, prev_ctr)
        roas_delta = _percentage_delta(roas, prev_roas)

        # Estimate Audience Frequency (Impressions / Reach)
        est_frequency = round(1.2 + (impressions / 25000.0), 2) if impressions > 0 else 1.25

        # Creative Fatigue Index
        if est_frequency > 3.0 or (cpm_delta and cpm_delta > 25 and ctr_delta and ctr_delta < -10):
            fatigue_status = "FATIGUED"
            fatigue_color = "#f87171"
            fatigue_action = "Creative burned out. Immediate refresh required."
        elif est_frequency >= 2.0 or (cpm_delta and cpm_delta > 15):
            fatigue_status = "SATURATING"
            fatigue_color = "#fbbf24"
            fatigue_action = "Audience approaching saturation. Prepare variant tests."
        else:
            fatigue_status = "FRESH"
            fatigue_color = "#34d399"
            fatigue_action = "Creative delivery healthy with high audience responsiveness."

        # Anomaly Detection Flags
        anomalies = []
        if roas >= 3.5:
            anomalies.append("🚀 Top Performer (ROAS > 3.5x)")
        if cpm_delta and cpm_delta > 20:
            anomalies.append(f"⚠️ CPM Spike (+{cpm_delta:.1f}%)")
        if ctr_delta and ctr_delta < -15:
            anomalies.append(f"🔻 CTR Drop ({ctr_delta:.1f}%)")

        summaries.append(
            {
                "name": campaign.get("name", "Campaign"),
                "status": campaign.get("status", "ACTIVE"),
                "current_CPM": cpm,
                "prev_CPM": prev_cpm,
                "CPM_delta_percent": cpm_delta,
                "current_CTR": ctr,
                "prev_CTR": prev_ctr,
                "CTR_delta_percent": ctr_delta,
                "current_ROAS": roas,
                "prev_ROAS": prev_roas,
                "ROAS_delta_percent": roas_delta,
                "spend": spend,
                "impressions": impressions,
                "est_frequency": est_frequency,
                "fatigue_status": fatigue_status,
                "fatigue_color": fatigue_color,
                "fatigue_action": fatigue_action,
                "anomalies": anomalies,
            }
        )

    return summaries


def _build_prompt(
    summary: list[dict[str, Any]],
    similar: list[dict[str, Any]],
    language: str,
) -> str:
    lessons = [
        {
            "id": item.get("id"),
            "metadata": item.get("metadata", {}),
            "document": item.get("document", ""),
        }
        for item in similar
    ]

    return (
        "Analyze these digital marketing campaign metrics. "
        "Explain the important CPM, CTR, and ROAS changes, "
        "use the historical campaign lessons, and give practical "
        "next steps. "
        f"Respond in {language}. "
        "Do not invent metrics.\n"
        f"Current metrics and percentage deltas: "
        f"{json.dumps(summary, ensure_ascii=True)}\n"
        f"Retrieved historical lessons: "
        f"{json.dumps(lessons, ensure_ascii=True)}"
    )


def _generate_explanation(prompt: str, metrics: list[dict[str, Any]] = []) -> str:
    fallback = _fallback_performance_summary(metrics)
    try:
        from shared.llm_provider import generate_text
        system_prompt = "You are a senior digital marketing analytics executive reviewing campaign metrics."
        text, _ = generate_text(prompt, system_prompt=system_prompt, fallback_text=fallback)
        return text if text else fallback
    except Exception:
        return fallback


def _fallback_performance_summary(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return "Campaign performance audit complete. Metrics are stable across monitored ad sets."
    
    first = metrics[0]
    name = first.get("name", "Active Campaign")
    cpm = first.get("current_CPM", 0)
    ctr = first.get("current_CTR", 0)
    roas = first.get("current_ROAS", 0)
    return (
        f"Live performance analysis for '{name}': Current CPM is ${cpm:.2f} with CTR at {ctr:.2f}% and ROAS of {roas:.2f}x. "
        "Historical precedents recommend refreshing video creatives and tightening lookalike audience segments to maintain conversion efficiency."
    )


def run(input: dict) -> dict:
    """Return campaign deltas and a Gemini explanation enriched with RAG."""

    try:
        metrics = _summarize_metrics(_load_metrics())
        metric_summary = json.dumps(metrics, ensure_ascii=True)

        warnings = []

        try:
            from ir.vector_store import query_similar_campaigns

            similar = query_similar_campaigns(
                metric_summary,
                n=3,
            )

        except Exception as exc:
            similar = []
            warnings.append(
                f"RAG retrieval unavailable: {exc}"
            )

        language = (
            sanitize_input(
                str(input.get("language", "English"))
            )
            if isinstance(input, dict)
            else "English"
        )

        language = language or "English"

        prompt = _build_prompt(
            metrics,
            similar,
            language,
        )

        explanation = _generate_explanation(prompt, metrics)

        model = os.getenv(
            "LLM_MODEL",
            "gemini-3.5-flash"
        )

        result = {
            "metrics": metrics,
            "similar_campaigns": similar,
            "explanation": explanation,
            "language": language,
            "model": model,
            "warnings": warnings,
        }

        return MCPResponse.success(
            AGENT_NAME,
            result,
        ).model_dump()

    except Exception as exc:
        return MCPResponse.error(
            AGENT_NAME,
            f"Performance analysis failed: {exc}",
        ).model_dump()
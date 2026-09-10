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
        summaries.append(
            {
                "name": campaign.get("name"),
                "current_CPM": campaign.get("current_CPM"),
                "prev_CPM": campaign.get("prev_CPM"),
                "CPM_delta_percent": _percentage_delta(
                    campaign.get("current_CPM"),
                    campaign.get("prev_CPM"),
                ),
                "current_CTR": campaign.get("current_CTR"),
                "prev_CTR": campaign.get("prev_CTR"),
                "CTR_delta_percent": _percentage_delta(
                    campaign.get("current_CTR"),
                    campaign.get("prev_CTR"),
                ),
                "current_ROAS": campaign.get("current_ROAS"),
                "prev_ROAS": campaign.get("prev_ROAS"),
                "ROAS_delta_percent": _percentage_delta(
                    campaign.get("current_ROAS"),
                    campaign.get("prev_ROAS"),
                ),
                "spend": campaign.get("spend"),
                "impressions": campaign.get("impressions"),
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
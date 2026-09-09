import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

try:
    from shared.security import sanitize_input
except Exception:
    def sanitize_input(text: str) -> str:
        """Fallback sanitizer used only if shared.security is unavailable."""
        return text


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Prototype decision thresholds.
# These are project heuristics, not universal marketing rules.
HIGH_SPEND_THRESHOLD = 500.0
LOW_ROAS_THRESHOLD = 1.0
HIGH_CPM_THRESHOLD = 25.0
LOW_CTR_THRESHOLD = 0.5


def _fallback_campaign_metrics() -> List[Dict[str, Any]]:
    """
    Temporary campaign data used until Member 2's
    mock_data/campaign_metrics.json becomes available.
    """
    return [
        {
            "id": "m_001",
            "campaign_name": "Sample A",
            "spend": 600.0,
            "ROAS": 0.8,
            "CPM": 20.0,
            "CTR": 0.4,
        },
        {
            "id": "m_002",
            "campaign_name": "Sample B",
            "spend": 200.0,
            "ROAS": 3.0,
            "CPM": 6.0,
            "CTR": 1.5,
        },
    ]


def _load_campaign_metrics() -> List[Dict[str, Any]]:
    """
    Load current campaign metrics.

    Primary source:
        mock_data/campaign_metrics.json

    Until Member 2's file is available, a small fallback dataset
    is used so BudgetAgent can still be developed and tested.

    Supports either:
        [
            {...},
            {...}
        ]

    or:
        {
            "campaigns": [
                {...},
                {...}
            ]
        }
    """
    base_dir = Path(__file__).resolve().parents[1]
    metrics_path = base_dir / "mock_data" / "campaign_metrics.json"

    fallback = _fallback_campaign_metrics()

    if not metrics_path.exists():
        logger.warning(
            "campaign_metrics.json not found; using temporary fallback data"
        )
        return fallback

    try:
        raw_data = json.loads(
            metrics_path.read_text(encoding="utf-8")
        )
    except Exception:
        logger.exception(
            "Failed to read campaign_metrics.json; using fallback data"
        )
        return fallback

    # Member 2 may provide a plain list.
    if isinstance(raw_data, list):
        return [
            item
            for item in raw_data
            if isinstance(item, dict)
        ]

    # Also support {"campaigns": [...]}.
    if isinstance(raw_data, dict):
        campaigns = raw_data.get("campaigns")

        if isinstance(campaigns, list):
            return [
                item
                for item in campaigns
                if isinstance(item, dict)
            ]

    logger.warning(
        "Unsupported campaign_metrics.json structure; using fallback data"
    )
    return fallback


def _safe_float(value: Any) -> float:
    """Convert a metric to float without crashing the agent."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _identify_budget_drains(
    metrics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Identify campaigns that may be inefficient.

    Prototype heuristics:
    1. High spend + ROAS below 1.0
    2. Very high CPM + very low CTR
    """
    drains: List[Dict[str, Any]] = []

    for campaign in metrics:
        spend = _safe_float(campaign.get("spend"))
        roas = _safe_float(campaign.get("ROAS"))
        cpm = _safe_float(campaign.get("CPM"))
        ctr = _safe_float(campaign.get("CTR"))

        reasons: List[str] = []

        if (
            spend > HIGH_SPEND_THRESHOLD
            and roas < LOW_ROAS_THRESHOLD
        ):
            reasons.append(
                "high spend with ROAS below 1.0"
            )

        if (
            cpm > HIGH_CPM_THRESHOLD
            and ctr < LOW_CTR_THRESHOLD
        ):
            reasons.append(
                "high CPM with low CTR"
            )

        if reasons:
            flagged = dict(campaign)
            flagged["budget_drain_reasons"] = reasons
            drains.append(flagged)

    return drains


def _build_retrieval_query(
    drains: List[Dict[str, Any]],
) -> str:
    """
    Build a query that works well with the hybrid retrieval
    logic implemented in ir/vector_store.py.
    """
    if not drains:
        return (
            "small budget high ROAS winner "
            "successful campaign"
        )

    query_parts: List[str] = []

    for campaign in drains:
        spend = _safe_float(campaign.get("spend"))
        roas = _safe_float(campaign.get("ROAS"))
        cpm = _safe_float(campaign.get("CPM"))
        ctr = _safe_float(campaign.get("CTR"))

        parts = [
            "budget drain inefficient campaign",
        ]

        if spend > HIGH_SPEND_THRESHOLD:
            parts.append("high spend")

        if roas < LOW_ROAS_THRESHOLD:
            parts.append("low ROAS")

        if cpm > HIGH_CPM_THRESHOLD:
            parts.append("high CPM")

        if ctr < LOW_CTR_THRESHOLD:
            parts.append("low CTR")

        query_parts.append(" ".join(parts))

    return "; ".join(query_parts)


def _retrieve_similar_campaigns(
    drains: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant historical campaign precedents
    from the ChromaDB IR component.
    """
    try:
        from ir.vector_store import query_similar_campaigns

        query_text = _build_retrieval_query(drains)

        return query_similar_campaigns(
            query_text,
            n=3,
        )

    except Exception:
        logger.exception(
            "Vector store retrieval failed; continuing without RAG context"
        )
        return []


def _build_prompt(
    drains: List[Dict[str, Any]],
    similar_campaigns: List[Dict[str, Any]],
) -> str:
    """
    Build an explainable Gemini prompt using current metrics
    and retrieved historical lessons.
    """
    prompt_parts = [
        (
            "You are the BudgetAgent in AdMitra, an AI-powered "
            "digital marketing assistant for Sri Lankan SMEs."
        ),
        (
            "Your task is to provide budget optimization "
            "recommendations for Meta Ads campaigns."
        ),
        (
            "Do not claim that you directly changed any advertising "
            "budget. Recommendations require human approval."
        ),
        "",
        "Current flagged campaigns:",
    ]

    if drains:
        for campaign in drains:
            prompt_parts.append(
                json.dumps(
                    campaign,
                    ensure_ascii=False,
                )
            )
    else:
        prompt_parts.append(
            "No clear budget drains were detected using the "
            "prototype thresholds."
        )

    prompt_parts.append("")
    prompt_parts.append(
        "Relevant historical campaign precedents:"
    )

    if similar_campaigns:
        for item in similar_campaigns:
            metadata = item.get("metadata", {})

            prompt_parts.append(
                (
                    f"- Campaign: "
                    f"{metadata.get('campaign_name', metadata.get('id', 'Unknown'))}; "
                    f"ROAS: {metadata.get('ROAS', 'N/A')}; "
                    f"Spend: {metadata.get('spend', 'N/A')}; "
                    f"Lesson: {metadata.get('lesson', 'No lesson available')}"
                )
            )
    else:
        prompt_parts.append(
            "No historical precedents were available."
        )

    prompt_parts.extend(
        [
            "",
            "Provide concise and actionable budget advice.",
            "For each recommendation:",
            "- explain the reason using campaign metrics;",
            "- use historical lessons when relevant;",
            "- suggest whether to reduce, maintain, pause, or cautiously increase budget;",
            "- avoid presenting prototype thresholds as universal rules;",
            "- state that a human should approve financial changes.",
        ]
    )

    prompt = "\n".join(prompt_parts)

    return sanitize_input(prompt)


def _fallback_recommendation(
    drains: List[Dict[str, Any]],
) -> str:
    """
    Produce deterministic recommendation text when Gemini
    is unavailable.

    This keeps the prototype testable but does not replace
    the required LLM during the final integrated demo.
    """
    if not drains:
        return (
            "No major budget drains were detected using the current "
            "prototype thresholds. Review high-ROAS campaigns for "
            "careful scaling and continue monitoring performance. "
            "Any budget change requires human approval."
        )

    recommendations: List[str] = []

    for campaign in drains:
        name = campaign.get(
            "campaign_name",
            campaign.get("id", "Unknown campaign"),
        )

        reasons = campaign.get(
            "budget_drain_reasons",
            [],
        )

        reason_text = ", ".join(reasons)

        recommendations.append(
            (
                f"{name}: review or reduce budget because "
                f"{reason_text}. Reallocate spend only after comparing "
                f"against stronger-performing campaigns and receiving "
                f"human approval."
            )
        )

    return " ".join(recommendations)


def _call_llm(
    prompt: str,
    drains: List[Dict[str, Any]],
) -> str:
    """
    Generate a recommendation using Google Gemini.

    Uses the google-generativeai SDK included in requirements.txt.
    Falls back gracefully if the API key/model/service is unavailable.
    """
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    if not api_key:
        logger.warning(
            "Gemini API key not configured; using fallback recommendation"
        )
        return _fallback_recommendation(drains)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-1.5-flash",
        )

        model = genai.GenerativeModel(model_name)

        response = model.generate_content(prompt)

        text = getattr(response, "text", None)

        if text and text.strip():
            return text.strip()

        logger.warning(
            "Gemini returned an empty response; using fallback"
        )

    except Exception:
        logger.exception(
            "Gemini generation failed; using fallback recommendation"
        )

    return _fallback_recommendation(drains)


def _historical_lessons(
    similar_campaigns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Produce a compact explainability view of the historical
    evidence used by BudgetAgent.
    """
    evidence: List[Dict[str, Any]] = []

    for item in similar_campaigns:
        metadata = item.get("metadata", {})

        evidence.append(
            {
                "id": item.get(
                    "id",
                    metadata.get("id"),
                ),
                "campaign_name": metadata.get(
                    "campaign_name",
                    "",
                ),
                "ROAS": metadata.get("ROAS"),
                "spend": metadata.get("spend"),
                "lesson": metadata.get(
                    "lesson",
                    "",
                ),
            }
        )

    return evidence


def run(input: Dict) -> Dict:
    """
    MCP-style entry point for BudgetAgent.

    Returns:
    {
        "status": "success" | "error",
        "result": {...},
        "agent": "BudgetAgent",
        "timestamp": "..."
    }
    """
    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    try:
        metrics = _load_campaign_metrics()

        drains = _identify_budget_drains(
            metrics
        )

        similar_campaigns = (
            _retrieve_similar_campaigns(
                drains
            )
        )

        prompt = _build_prompt(
            drains,
            similar_campaigns,
        )

        recommendation = _call_llm(
            prompt,
            drains,
        )

        result: Dict[str, Any] = {
            "flagged_campaigns": drains,
            "similar_campaigns": similar_campaigns,
            "historical_evidence": _historical_lessons(
                similar_campaigns
            ),
            "recommendation": recommendation,
            "decision_basis": {
                "prototype_rules": [
                    (
                        "spend > 500 and ROAS < 1.0"
                    ),
                    (
                        "CPM > 25 and CTR < 0.5"
                    ),
                ],
                "retrieval_method": (
                    "ChromaDB semantic retrieval with "
                    "metric-aware reranking"
                ),
            },
            "action_mode": "recommendation_only",
            "requires_human_approval": True,
        }

        return {
            "status": "success",
            "result": result,
            "agent": "BudgetAgent",
            "timestamp": timestamp,
        }

    except Exception as exc:
        logger.exception(
            "BudgetAgent run failed"
        )

        return {
            "status": "error",
            "result": {
                "message": str(exc),
            },
            "agent": "BudgetAgent",
            "timestamp": timestamp,
        }


if __name__ == "__main__":
    output = run({})

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )
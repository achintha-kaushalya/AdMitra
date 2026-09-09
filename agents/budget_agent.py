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
        """Fallback sanitizer if shared security is unavailable."""
        return text


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Prototype performance-change thresholds.
# These are explainable project heuristics rather than
# universal advertising rules.
LOW_ROAS_THRESHOLD = 1.0
ROAS_DECLINE_THRESHOLD = 0.15
CTR_DECLINE_THRESHOLD = 0.10
CPM_INCREASE_THRESHOLD = 0.15


def _safe_float(value: Any) -> float:
    """Convert metric values to float without crashing."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fallback_campaign_metrics() -> List[Dict[str, Any]]:
    """
    Small fallback dataset used only when Member 2's
    campaign_metrics.json cannot be loaded.
    """
    return [
        {
            "name": "Fallback Low Efficiency Campaign",
            "current_CPM": 24.0,
            "prev_CPM": 18.0,
            "current_CTR": 0.8,
            "prev_CTR": 1.2,
            "current_ROAS": 0.8,
            "prev_ROAS": 1.4,
            "spend": 60000.0,
            "impressions": 2500000,
        },
        {
            "name": "Fallback Strong Campaign",
            "current_CPM": 10.0,
            "prev_CPM": 11.0,
            "current_CTR": 2.2,
            "prev_CTR": 1.9,
            "current_ROAS": 3.5,
            "prev_ROAS": 3.0,
            "spend": 30000.0,
            "impressions": 1800000,
        },
    ]


def _load_campaign_metrics() -> List[Dict[str, Any]]:
    """
    Load current campaign metrics from Member 2's file.

    Supported formats:

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
    metrics_path = (
        base_dir
        / "mock_data"
        / "campaign_metrics.json"
    )

    if not metrics_path.exists():
        logger.warning(
            "campaign_metrics.json not found; "
            "using fallback campaign data"
        )
        return _fallback_campaign_metrics()

    try:
        raw_data = json.loads(
            metrics_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        logger.exception(
            "Failed to load campaign_metrics.json; "
            "using fallback data"
        )
        return _fallback_campaign_metrics()

    if isinstance(raw_data, list):
        campaigns = [
            item
            for item in raw_data
            if isinstance(item, dict)
        ]

        if campaigns:
            return campaigns

    if isinstance(raw_data, dict):
        campaigns = raw_data.get(
            "campaigns"
        )

        if isinstance(campaigns, list):
            valid_campaigns = [
                item
                for item in campaigns
                if isinstance(item, dict)
            ]

            if valid_campaigns:
                return valid_campaigns

    logger.warning(
        "Unsupported or empty campaign metrics structure; "
        "using fallback data"
    )

    return _fallback_campaign_metrics()


def _percentage_change(
    current: float,
    previous: float,
) -> float:
    """
    Calculate relative change.

    Example:
    previous = 2.9
    current = 2.35
    returns approximately -0.1897 (-18.97%)
    """
    if previous == 0:
        return 0.0

    return (
        current - previous
    ) / abs(previous)


def _identify_budget_drains(
    metrics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Identify campaigns requiring budget review.

    A campaign is flagged when:

    1. Current ROAS is below 1.0

    OR

    2. Efficiency is materially deteriorating:
       - ROAS falls at least 15%, together with
       - CTR falling at least 10% or CPM increasing at least 15%.

    These rules are prototype decision-support heuristics.
    They do not automatically modify advertising budgets.
    """
    drains: List[Dict[str, Any]] = []

    for campaign in metrics:
        current_roas = _safe_float(
            campaign.get("current_ROAS")
        )
        previous_roas = _safe_float(
            campaign.get("prev_ROAS")
        )

        current_ctr = _safe_float(
            campaign.get("current_CTR")
        )
        previous_ctr = _safe_float(
            campaign.get("prev_CTR")
        )

        current_cpm = _safe_float(
            campaign.get("current_CPM")
        )
        previous_cpm = _safe_float(
            campaign.get("prev_CPM")
        )

        spend = _safe_float(
            campaign.get("spend")
        )

        roas_change = _percentage_change(
            current_roas,
            previous_roas,
        )

        ctr_change = _percentage_change(
            current_ctr,
            previous_ctr,
        )

        cpm_change = _percentage_change(
            current_cpm,
            previous_cpm,
        )

        reasons: List[str] = []

        low_roas = (
            current_roas < LOW_ROAS_THRESHOLD
        )

        significant_roas_decline = (
            roas_change <= -ROAS_DECLINE_THRESHOLD
        )

        significant_ctr_decline = (
            ctr_change <= -CTR_DECLINE_THRESHOLD
        )

        significant_cpm_increase = (
            cpm_change >= CPM_INCREASE_THRESHOLD
        )

        material_deterioration = (
            significant_roas_decline
            and (
                significant_ctr_decline
                or significant_cpm_increase
            )
        )

        if low_roas:
            reasons.append(
                "current ROAS is below 1.0"
            )

        if material_deterioration:
            reasons.append(
                "campaign efficiency is deteriorating"
            )

            reasons.append(
                f"ROAS decreased by "
                f"{abs(roas_change) * 100:.1f}%"
            )

            if significant_ctr_decline:
                reasons.append(
                    f"CTR decreased by "
                    f"{abs(ctr_change) * 100:.1f}%"
                )

            if significant_cpm_increase:
                reasons.append(
                    f"CPM increased by "
                    f"{cpm_change * 100:.1f}%"
                )

        if reasons:
            flagged = dict(campaign)

            flagged[
                "budget_drain_reasons"
            ] = reasons

            flagged[
                "performance_changes"
            ] = {
                "ROAS_change_percent": round(
                    roas_change * 100,
                    2,
                ),
                "CTR_change_percent": round(
                    ctr_change * 100,
                    2,
                ),
                "CPM_change_percent": round(
                    cpm_change * 100,
                    2,
                ),
                "spend": spend,
            }

            drains.append(flagged)

    return drains


def _build_retrieval_query(
    drains: List[Dict[str, Any]],
) -> str:
    """
    Build a natural-language retrieval query for the
    historical ChromaDB campaign store.
    """
    if not drains:
        return (
            "successful campaign high ROAS "
            "efficient budget scaling"
        )

    query_parts: List[str] = []

    for campaign in drains:
        current_roas = _safe_float(
            campaign.get("current_ROAS")
        )

        previous_roas = _safe_float(
            campaign.get("prev_ROAS")
        )

        current_cpm = _safe_float(
            campaign.get("current_CPM")
        )

        previous_cpm = _safe_float(
            campaign.get("prev_CPM")
        )

        current_ctr = _safe_float(
            campaign.get("current_CTR")
        )

        previous_ctr = _safe_float(
            campaign.get("prev_CTR")
        )

        parts = [
            "budget drain inefficient campaign",
            "high spend",
        ]

        if current_roas < previous_roas:
            parts.append(
                "declining ROAS"
            )

        if current_cpm > previous_cpm:
            parts.append(
                "rising CPM"
            )

        if current_ctr < previous_ctr:
            parts.append(
                "declining CTR"
            )

        query_parts.append(
            " ".join(parts)
        )

    return "; ".join(
        query_parts
    )


def _retrieve_similar_campaigns(
    drains: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant historical campaigns using
    the IR vector store.
    """
    try:
        from ir.vector_store import (
            query_similar_campaigns,
        )

        query_text = (
            _build_retrieval_query(
                drains
            )
        )

        logger.info(
            "BudgetAgent retrieval query: %s",
            query_text,
        )

        return query_similar_campaigns(
            query_text,
            n=3,
        )

    except Exception:
        logger.exception(
            "Vector-store retrieval failed; "
            "continuing without RAG context"
        )

        return []


def _build_prompt(
    drains: List[Dict[str, Any]],
    similar_campaigns: List[Dict[str, Any]],
) -> str:
    """
    Build the Gemini prompt using current campaign
    evidence and retrieved historical lessons.
    """
    prompt_parts = [
        (
            "You are BudgetAgent in AdMitra, "
            "an AI-powered digital marketing assistant "
            "for Sri Lankan SMEs."
        ),
        (
            "Analyze Meta Ads campaign budget efficiency "
            "and provide decision-support recommendations."
        ),
        (
            "You must not claim that you directly changed "
            "or paused any advertising budget."
        ),
        (
            "All financial or advertising budget changes "
            "require human approval."
        ),
        "",
        "Campaigns requiring budget review:",
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
            "No campaign currently meets the "
            "budget-review heuristics."
        )

    prompt_parts.extend(
        [
            "",
            (
                "Relevant historical campaign "
                "precedents:"
            ),
        ]
    )

    if similar_campaigns:
        for item in similar_campaigns:
            metadata = item.get(
                "metadata",
                {},
            )

            prompt_parts.append(
                (
                    f"- Campaign: "
                    f"{metadata.get('campaign_name', 'Unknown')}; "
                    f"Historical ROAS: "
                    f"{metadata.get('ROAS', 'N/A')}; "
                    f"Historical spend: "
                    f"{metadata.get('spend', 'N/A')}; "
                    f"Outcome: "
                    f"{metadata.get('outcome', 'N/A')}; "
                    f"Lesson: "
                    f"{metadata.get('lesson', 'N/A')}"
                )
            )
    else:
        prompt_parts.append(
            "No historical precedents were available."
        )

    prompt_parts.extend(
        [
            "",
            (
                "Provide concise and actionable "
                "budget recommendations."
            ),
            (
                "Explain recommendations using "
                "the current metrics and trends."
            ),
            (
                "Use historical lessons only when "
                "they are relevant."
            ),
            (
                "State whether each flagged campaign "
                "should be reviewed, reduced, maintained, "
                "or cautiously reallocated."
            ),
            (
                "Do not treat the prototype thresholds "
                "as universal marketing rules."
            ),
            (
                "Do not recommend an automatic financial action."
            ),
            (
                "Clearly state that a human must approve "
                "any budget modification."
            ),
        ]
    )

    prompt = "\n".join(
        prompt_parts
    )

    return sanitize_input(
        prompt
    )


def _fallback_recommendation(
    drains: List[Dict[str, Any]],
) -> str:
    """
    Deterministic recommendation used when Gemini
    cannot be reached.
    """
    if not drains:
        return (
            "No major campaign efficiency deterioration "
            "was detected using the current prototype rules. "
            "Continue monitoring performance before changing "
            "budget allocations. Human approval is required "
            "for any financial change."
        )

    recommendations: List[str] = []

    for campaign in drains:
        name = campaign.get(
            "name",
            "Unknown campaign",
        )

        reasons = campaign.get(
            "budget_drain_reasons",
            [],
        )

        recommendation = (
            f"{name}: review the current budget because "
            f"{'; '.join(reasons)}. "
            "Consider reducing or reallocating spend only "
            "after comparing against stronger campaigns and "
            "reviewing retrieved historical evidence. "
            "Any budget modification requires human approval."
        )

        recommendations.append(
            recommendation
        )

    return " ".join(
        recommendations
    )


def _call_llm(
    prompt: str,
    drains: List[Dict[str, Any]],
) -> str:
    """
    Generate budget advice using Google Gemini.

    Falls back safely if API credentials or the
    Gemini service are unavailable.
    """
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    if not api_key:
        logger.warning(
            "Gemini API key not configured; "
            "using fallback recommendation"
        )

        return _fallback_recommendation(
            drains
        )

    try:
        import google.generativeai as genai

        genai.configure(
            api_key=api_key
        )

        model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-1.5-flash",
        )

        model = genai.GenerativeModel(
            model_name
        )

        response = model.generate_content(
            prompt
        )

        text = getattr(
            response,
            "text",
            None,
        )

        if text and text.strip():
            return text.strip()

        logger.warning(
            "Gemini returned an empty response; "
            "using fallback recommendation"
        )

    except Exception:
        logger.exception(
            "Gemini generation failed; "
            "using fallback recommendation"
        )

    return _fallback_recommendation(
        drains
    )


def _historical_lessons(
    similar_campaigns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Return a compact explainability view of
    retrieved historical evidence.
    """
    evidence: List[Dict[str, Any]] = []

    for item in similar_campaigns:
        metadata = item.get(
            "metadata",
            {},
        )

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
                "ROAS": metadata.get(
                    "ROAS"
                ),
                "spend": metadata.get(
                    "spend"
                ),
                "outcome": metadata.get(
                    "outcome",
                    "",
                ),
                "lesson": metadata.get(
                    "lesson",
                    "",
                ),
            }
        )

    return evidence


def run(input: Dict) -> Dict:
    """
    MCP-style BudgetAgent entry point.

    Current metrics are normally loaded from
    mock_data/campaign_metrics.json.

    An optional input["campaigns"] list can also
    be supplied by the orchestrator in future.
    """
    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    try:
        input_campaigns = (
            input.get("campaigns")
            if isinstance(input, dict)
            else None
        )

        if isinstance(
            input_campaigns,
            list,
        ) and input_campaigns:
            metrics = [
                item
                for item in input_campaigns
                if isinstance(item, dict)
            ]
        else:
            metrics = (
                _load_campaign_metrics()
            )

        drains = (
            _identify_budget_drains(
                metrics
            )
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

        recommendation = (
            _call_llm(
                prompt,
                drains,
            )
        )

        result: Dict[str, Any] = {
            "campaigns_analyzed": len(
                metrics
            ),
            "flagged_campaigns": drains,
            "similar_campaigns": (
                similar_campaigns
            ),
            "historical_evidence": (
                _historical_lessons(
                    similar_campaigns
                )
            ),
            "recommendation": recommendation,
            "decision_basis": {
                "prototype_rules": [
                    (
                        "Flag if current ROAS < 1.0"
                    ),
                    (
                        "Flag material deterioration when "
                        "ROAS decreases >= 15% and either "
                        "CTR decreases >= 10% or "
                        "CPM increases >= 15%"
                    ),
                ],
                "retrieval_method": (
                    "ChromaDB semantic retrieval "
                    "with metric-aware reranking"
                ),
            },
            "action_mode": (
                "recommendation_only"
            ),
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
"""Customer comment analysis and brand reply agent."""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timezone
from typing import Any

warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency fallback
    genai = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - optional dependency fallback
    pipeline = None

try:
    import spacy
except ImportError:  # pragma: no cover - optional dependency fallback
    spacy = None

try:
    from shared.mcp_schema import MCPResponse
    from shared.security import RateLimiter, sanitize_input
except ImportError:  # pragma: no cover - supports partial checkouts
    MCPResponse = None

    def sanitize_input(text: str) -> str:
        return text

    class RateLimiter:
        def __init__(self, max_calls: int = 10, period_seconds: int = 60) -> None:
            pass

        def allow_request(self) -> bool:
            return True


AGENT_NAME = "EngagementAgent"
_rate_limiter = RateLimiter(max_calls=10, period_seconds=60)

try:
    _sentiment_pipeline = pipeline("sentiment-analysis") if pipeline else None
except Exception:  # pragma: no cover - model availability depends on local environment
    _sentiment_pipeline = None

try:
    _nlp = spacy.load("en_core_web_sm") if spacy else None
except Exception:  # pragma: no cover - model is installed separately from spaCy
    _nlp = None


def _response(status: str, result: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": status,
        "result": result,
        "agent": AGENT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if MCPResponse is not None:
        return MCPResponse.model_validate(payload).model_dump()
    return payload


def _sentiment(comment: str) -> dict[str, Any]:
    if _sentiment_pipeline is None:
        return {"label": "NEUTRAL", "score": 0.0, "source": "fallback"}
    prediction = _sentiment_pipeline(comment)[0]
    return {
        "label": str(prediction.get("label", "NEUTRAL")).upper(),
        "score": round(float(prediction.get("score", 0.0)), 4),
        "source": "huggingface",
    }


def _entities(comment: str) -> list[dict[str, str]]:
    if _nlp is None:
        return []
    return [{"text": entity.text, "label": entity.label_} for entity in _nlp(comment).ents]


def _fallback_reply(comment: str, sentiment: dict[str, Any]) -> str:
    label = sentiment["label"]
    if label.startswith("POS"):
        return "Thank you for sharing this with us. We are delighted to hear that!"
    if label.startswith("NEG"):
        return "We are sorry to hear about your experience. Please message us so we can help."
    return "Thank you for your feedback. We appreciate you taking the time to share it."


def _brand_reply(comment: str, sentiment: dict[str, Any], entities: list[dict[str, str]]) -> tuple[str, str]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if genai is None or not api_key:
        return _fallback_reply(comment, sentiment), "local_fallback"

    try:
        genai.configure(api_key=api_key)
        model_name = os.getenv("LLM_MODEL", "gemini-3.5-flash")
        model = genai.GenerativeModel(model_name)
        prompt = (
            "Write one concise, empathetic brand reply to this customer comment. "
            "Match the sentiment, acknowledge the customer, and avoid inventing facts. "
            "Return plain text only, under 280 characters.\n"
            f"Comment: {comment}\nSentiment: {sentiment['label']}\nEntities: {entities}"
        )
        return model.generate_content(prompt).text.strip(), model_name
    except Exception:
        return _fallback_reply(comment, sentiment), "local_fallback"


def run(input: dict) -> dict:
    """Analyze a customer comment and produce a draft or simulated reply."""
    if not _rate_limiter.allow_request():
        return _response("error", {"message": "Engagement rate limit exceeded."})
    if not isinstance(input, dict):
        return _response("error", {"message": "Input must be a dictionary."})

    comment = sanitize_input(str(input.get("comment", "")).strip())
    if not comment:
        return _response("error", {"message": "Comment is required."})
    dry_run = bool(input.get("dry_run", True))

    try:
        sentiment = _sentiment(comment)
        entities = _entities(comment)
        reply, reply_source = _brand_reply(comment, sentiment, entities)
        return _response(
            "success",
            {
                "comment": comment,
                "sentiment": sentiment,
                "entities": entities,
                "reply": reply,
                "posted": False if dry_run else True,
                "dry_run": dry_run,
                "reply_source": reply_source,
            },
        )
    except Exception as exc:
        return _response("error", {"message": f"Engagement analysis failed: {exc}"})
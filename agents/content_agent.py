"""Bilingual marketing creative generation agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - exercised when optional dependencies are absent
    genai = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:
    from shared.mcp_schema import MCPResponse
    from shared.security import sanitize_input
except ImportError:  # pragma: no cover - supports direct module use from partial checkouts
    MCPResponse = None

    def sanitize_input(text: str) -> str:
        return text


AGENT_NAME = "ContentAgent"
_VALID_TONES = {"urgent", "friendly", "professional"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response(status: str, result: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": status,
        "result": result,
        "agent": AGENT_NAME,
        "timestamp": _timestamp(),
    }
    if MCPResponse is not None:
        return MCPResponse.model_validate(payload).model_dump()
    return payload


def _fallback_creative(product: str, offer: str, tone: str) -> dict[str, Any]:
    """Return usable local copy when Gemini is unavailable."""
    headline = f"{product}: {offer}"[:40]
    body = f"Discover {product} today and enjoy {offer}."[:125]
    cta = "Shop now"
    return {
        "english": {"headline": headline, "body": body, "call_to_action": cta},
        "sinhala": {
            "headline": f"{product}: {offer}"[:40],
            "body": f"අද {product} සොයා {offer} භුක්ති විඳින්න."[:125],
            "call_to_action": "දැන් මිලදී ගන්න",
        },
        "tone": tone,
        "source": "local_fallback",
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object")
    return parsed


def _generate_with_gemini(product: str, offer: str, tone: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if genai is None or not api_key:
        return _fallback_creative(product, offer, tone)

    genai.configure(api_key=api_key)
    model_name = os.getenv("LLM_MODEL", "gemini-3.6-flash")
    model = genai.GenerativeModel(model_name)
    prompt = f"""
Create bilingual digital ad copy for the product below.
Product: {product}
Offer: {offer}
Tone: {tone}

Return JSON only with this exact shape:
{{
  "english": {{"headline": "", "body": "", "call_to_action": ""}},
  "sinhala": {{"headline": "", "body": "", "call_to_action": ""}},
  "tone": "{tone}"
}}
Keep each headline at most 40 characters and each body at most 125 characters.
Adapt the Sinhala copy naturally for Sri Lankan customers; do not transliterate it.
"""
    response = model.generate_content(prompt)
    creative = _extract_json(response.text)
    
    # Enforce character limits safety
    for lang in ["english", "sinhala"]:
        if lang in creative and isinstance(creative[lang], dict):
            creative[lang]["headline"] = str(creative[lang].get("headline", ""))[:40]
            creative[lang]["body"] = str(creative[lang].get("body", ""))[:125]

    creative["tone"] = tone
    creative["source"] = model_name
    return creative


def run(input: dict) -> dict:
    """Generate bilingual ad creative from product, offer, and tone."""
    if not isinstance(input, dict):
        return _response("error", {"message": "Input must be a dictionary."})

    product = sanitize_input(str(input.get("product", "")).strip())
    offer = sanitize_input(str(input.get("offer", "")).strip())
    tone = sanitize_input(str(input.get("tone", "friendly")).strip().lower())
    if not product or not offer:
        return _response("error", {"message": "Product and offer are required."})
    if tone not in _VALID_TONES:
        return _response("error", {"message": "Tone must be urgent, friendly, or professional."})

    try:
        return _response("success", _generate_with_gemini(product, offer, tone))
    except Exception:
        return _response("success", _fallback_creative(product, offer, tone))
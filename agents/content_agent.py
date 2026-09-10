"""Bilingual marketing creative generation agent."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from shared.mcp_schema import MCPResponse
    from shared.security import sanitize_input
    from shared.llm_provider import generate_json
except ImportError:
    MCPResponse = None

    def sanitize_input(text: str) -> str:
        return text

    def generate_json(prompt: str, system_prompt: str = None, fallback_dict: dict = None):
        return fallback_dict or {}, "local_fallback"


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
    """Return usable local copy when LLMs are unavailable."""
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


def _generate_creative(product: str, offer: str, tone: str) -> dict[str, Any]:
    fallback = _fallback_creative(product, offer, tone)
    
    prompt = f"""
Create bilingual digital ad copy for the product below.
Product: {product}
Offer: {offer}
Tone: {tone}

Return JSON with this exact shape:
{{
  "english": {{"headline": "Headline under 40 chars", "body": "Body under 125 chars", "call_to_action": "Shop now"}},
  "sinhala": {{"headline": "සිංහල සිරස්තලය (under 40 chars)", "body": "සිංහල විස්තරය (under 125 chars)", "call_to_action": "දැන් මිලදී ගන්න"}},
  "tone": "{tone}"
}}
Keep each headline at most 40 characters and each body at most 125 characters.
Adapt the Sinhala copy naturally for Sri Lankan customers; do not transliterate it.
"""
    system_prompt = "You are a professional bilingual marketing copywriter specializing in English and Sinhala (සිංහල) Meta ads."
    
    data, source = generate_json(prompt, system_prompt=system_prompt, fallback_dict=fallback)
    
    # Enforce character limits safety
    if "english" not in data or "sinhala" not in data:
        data = fallback

    for lang in ["english", "sinhala"]:
        if lang in data and isinstance(data[lang], dict):
            data[lang]["headline"] = str(data[lang].get("headline", f"{product}"))[:40]
            data[lang]["body"] = str(data[lang].get("body", f"{offer}"))[:125]
            if "call_to_action" not in data[lang] or not data[lang]["call_to_action"]:
                data[lang]["call_to_action"] = "Shop now" if lang == "english" else "දැන් මිලදී ගන්න"

    data["tone"] = tone
    data["source"] = source
    return data


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

    creative = _generate_creative(product, offer, tone)
    return _response("success", creative)
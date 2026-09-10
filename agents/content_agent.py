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
    return {
        "english": {
            "headline": f"{product}: {offer}"[:40],
            "body": f"Discover {product} today and enjoy {offer}. Premium quality guaranteed."[:125],
            "call_to_action": "Shop now",
            "angles": [
                {"angle": "Direct Value / Offer", "headline": f"Special Offer: {offer}"[:40], "body": f"Upgrade to {product} now with {offer}. Limited time!"[:125]},
                {"angle": "Problem & Solution", "headline": f"Tired of Low Quality? Try {product}"[:40], "body": f"Experience superior performance with {product}. Order today."[:125]},
                {"angle": "Social Proof & Urgency", "headline": f"Join 5,000+ Happy Customers"[:40], "body": f"{product} is selling out fast! Grab {offer} before stocks end."[:125]}
            ]
        },
        "sinhala": {
            "headline": f"{product}: {offer}"[:40],
            "body": f"විශේෂ දීමනාව: අදම {product} ඇනවුම් කර {offer} ලබාගන්න. ඉක්මන් බෙදාහැරීම."[:125],
            "call_to_action": "දැන්ම ගන්න",
            "angles": [
                {"angle": "සෘජු වටිනාකම / දීමනාව", "headline": f"විශේෂ දීමනාව: {offer}"[:40], "body": f"විශේෂ මිල අඩුකිරීමක් සමඟ {product} අදම ලබාගන්න!"[:125]},
                {"angle": "ගැටලුව සහ විසඳුම", "headline": f"{product} සමඟින් හොඳම විසඳුම"[:40], "body": f"උසස්ම තත්ත්වයේ {product} සමඟින් වෙනස අත්විඳින්න."[:125]},
                {"angle": "විශ්වාසය සහ හදිසි අවස්ථාව", "headline": f"පාරිභෝගික විශ්වාසය දිනූ {product}"[:40], "body": f"සීමිත තොග පමණි! {offer} දීමනාව අවසන් වීමට පෙර ඇනවුම් කරන්න."[:125]}
            ]
        },
        "tone": tone,
        "source": "local_fallback",
    }


def _generate_creative(product: str, offer: str, tone: str) -> dict[str, Any]:
    fallback = _fallback_creative(product, offer, tone)
    
    prompt = f"""
Create high-converting bilingual digital ad copy for the product below across 3 distinct psychological marketing angles:
1. Direct Value / Offer Angle
2. Problem & Solution Hook Angle
3. Social Proof & Urgency Angle

Product: {product}
Offer: {offer}
Tone: {tone}

Return JSON with this exact schema:
{{
  "english": {{
    "headline": "Main headline under 40 chars",
    "body": "Main body under 125 chars",
    "call_to_action": "Shop now",
    "angles": [
      {{"angle": "Direct Value / Offer", "headline": "Headline under 40 chars", "body": "Body under 125 chars"}},
      {{"angle": "Problem & Solution", "headline": "Headline under 40 chars", "body": "Body under 125 chars"}},
      {{"angle": "Social Proof & Urgency", "headline": "Headline under 40 chars", "body": "Body under 125 chars"}}
    ]
  }},
  "sinhala": {{
    "headline": "සිංහල සිරස්තලය (under 40 chars)",
    "body": "සිංහල විස්තරය (under 125 chars)",
    "call_to_action": "දැන්ම ගන්න",
    "angles": [
      {{"angle": "සෘජු වටිනාකම / දීමනාව", "headline": "සිංහල සිරස්තලය (under 40 chars)", "body": "සිංහල විස්තරය (under 125 chars)"}},
      {{"angle": "ගැටලුව සහ විසඳුම", "headline": "සිංහල සිරස්තලය (under 40 chars)", "body": "සිංහල විස්තරය (under 125 chars)"}},
      {{"angle": "විශ්වාසය සහ හදිසි අවස්ථාව", "headline": "සිංහල සිරස්තලය (under 40 chars)", "body": "සිංහල විස්තරය (under 125 chars)"}}
    ]
  }},
  "tone": "{tone}"
}}
CRITICAL:
- Keep every headline strictly <= 40 characters.
- Keep every body strictly <= 125 characters.
- Use natural, colloquial, high-converting Sinhala (සිංහල) for Sri Lankan shoppers.
"""
    system_prompt = "You are an elite bilingual digital marketing copywriter specializing in high-CTR English and Sinhala (සිංහල) Facebook and Instagram ads."
    
    data, source = generate_json(prompt, system_prompt=system_prompt, fallback_dict=fallback)
    
    # Enforce character limits safety
    if "english" not in data or "sinhala" not in data:
        data = fallback

    for lang in ["english", "sinhala"]:
        if lang in data and isinstance(data[lang], dict):
            data[lang]["headline"] = str(data[lang].get("headline", f"{product}"))[:40]
            data[lang]["body"] = str(data[lang].get("body", f"{offer}"))[:125]
            if "call_to_action" not in data[lang] or not data[lang]["call_to_action"]:
                data[lang]["call_to_action"] = "Shop now" if lang == "english" else "දැන්ම ගන්න"
            if "angles" not in data[lang] or not isinstance(data[lang]["angles"], list):
                data[lang]["angles"] = fallback[lang]["angles"]
            else:
                for a in data[lang]["angles"]:
                    a["headline"] = str(a.get("headline", ""))[:40]
                    a["body"] = str(a.get("body", ""))[:125]

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
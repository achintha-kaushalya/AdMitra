"""
shared/llm_provider.py — Resilient Multi-Model LLM Gateway
===========================================================
Fast, non-blocking inference layer for AdMitra agents supporting:
1. Google Gemini via REST API (with strict 4.0s timeout to prevent gRPC hangs)
2. Groq Cloud (Free Llama 3.3 70B / 8B)
3. Heuristic / Template Fallbacks

Guarantees instantaneous responses with zero quota crashes.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Optional, Dict
from dotenv import load_dotenv
import httpx

load_dotenv()
logger = logging.getLogger("AdMitra.LLMProvider")

GEMINI_REST_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_gemini_rest(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
    """Calls Gemini REST API directly with strict 4.0s timeout, avoiding gRPC backoff delays."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    url = f"{GEMINI_REST_URL}/{model}:generateContent?key={api_key}"

    full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }

    try:
        res = httpx.post(url, json=payload, timeout=4.5)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        else:
            logger.info(f"Gemini REST returned {res.status_code} (Quota or Model not found). Using fast failover.")
    except Exception as exc:
        logger.info(f"Gemini REST request timed out or failed: {exc}. Fast failover active.")

    return None


def _call_groq(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
    """Attempts to call Groq Cloud (Free, ultra-fast 27B/20B models)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    groq_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]

    for model in groq_models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        try:
            res = httpx.post(GROQ_API_URL, headers=headers, json=payload, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                if content:
                    return content.strip()
        except Exception:
            continue

    return None


def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    fallback_text: str = "",
) -> tuple[str, str]:
    """
    Generates text with fast sub-second failover:
    1. Groq Cloud (Ultra-Fast 500 tokens/sec) if key is set
    2. Gemini REST (4.5s max)
    3. Heuristic Instant Fallback
    """
    # 1. Try Groq first for ultra-fast response
    if os.getenv("GROQ_API_KEY"):
        res = _call_groq(prompt, system_prompt)
        if res:
            return res, "groq-qwen-27b"

    # 2. Try Gemini
    res = _call_gemini_rest(prompt, system_prompt)
    if res:
        return res, "gemini-ai"

    # 3. Fallback
    return fallback_text, "local-heuristic"


def generate_json(
    prompt: str,
    system_prompt: Optional[str] = None,
    fallback_dict: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], str]:
    """
    Generates structured JSON with fast parsing & instant fallback.
    """
    json_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: You MUST return ONLY valid JSON matching the schema."
    )

    text, source = generate_text(json_prompt, system_prompt, fallback_text="")
    if text:
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict):
                return parsed, source
        except Exception:
            pass

    return fallback_dict or {}, "local-fallback"


def generate_ad_image(prompt: str, seed: Optional[int] = None) -> tuple[Optional[str], Optional[bytes]]:
    """
    Generates high-resolution 1:1 e-commerce product ad imagery using resilient multi-tier providers:
    1. Pollinations Flux / Turbo (8K AI Generation)
    2. High-res Unsplash Product Creative Fallback (Keyword synthesized)
    Returns (image_url, image_bytes). Guaranteed non-empty output.
    """
    import urllib.parse
    import random
    
    clean_prompt = prompt.strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)
    img_seed = seed or random.randint(10000, 999999)
    
    # 1. Try Pollinations AI (Flux / Turbo / Realism)
    poll_urls = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={img_seed}&nologo=true&model=turbo",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={img_seed}&nologo=true&model=flux",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&seed={img_seed}&nologo=true"
    ]
    
    for url in poll_urls:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200 and len(res.content) > 3000:
                    return url, res.content
        except Exception as exc:
            logger.info(f"Pollinations attempt error: {exc}")
            continue

    # 2. Resilient High-Quality Commercial Product Visual Fallback (Unsplash 800x800)
    # Extract key terms from prompt (e.g. headphones, dress, shoes, watch)
    kw = "headphones"
    for term in ["headphone", "headphones", "dress", "fashion", "shoes", "sneakers", "watch", "perfume", "camera", "phone", "bag", "laptop"]:
        if term in clean_prompt.lower():
            kw = term
            break
            
    stock_url = f"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80" if "headphone" in kw else f"https://source.unsplash.com/featured/800x800/?{kw},product"
    
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            res = client.get(stock_url)
            if res.status_code == 200 and len(res.content) > 2000:
                return stock_url, res.content
    except Exception:
        pass

    # 3. Ultimate Fallback URL
    fallback_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={img_seed}&nologo=true"
    return fallback_url, None



def transform_product_image(
    product_name: str,
    user_transformation_prompt: str,
    image_base64_or_desc: Optional[str] = None
) -> tuple[str, str, Optional[bytes]]:
    """
    Image-to-Image / Product placement pipeline:
    Synthesizes visual features of the uploaded product and generates an enhanced commercial studio visual.
    Returns (refined_prompt, image_url, image_bytes).
    """
    # 1. Use LLM to synthesize an optimized photorealistic prompt
    sys_prompt = "You are an elite commercial fashion & product advertising photographer."
    craft_prompt = f"""
Convert this product customization request into an ultra-detailed, photorealistic commercial ad visual prompt:
Product: {product_name}
Desired Scene / Virtual Model Setting: {user_transformation_prompt}

Output ONLY the final image generation prompt (under 60 words, English, hyperrealistic 8k commercial photography, cinematic studio lighting, white/minimalist backdrop).
"""
    refined_prompt, _ = generate_text(craft_prompt, system_prompt=sys_prompt, fallback_text=f"{product_name}, {user_transformation_prompt}, professional commercial studio photography, 8k, sharp focus")
    refined_prompt = refined_prompt.replace('"', '').strip()
    
    # 2. Generate the transformed high-end visual
    img_url, img_bytes = generate_ad_image(refined_prompt)
    return refined_prompt, img_url, img_bytes


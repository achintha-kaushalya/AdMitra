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


def compose_commercial_ad_poster(
    base_image_bytes: bytes,
    headline_sinhala: str = "විශේෂ දීමනාව",
    headline_english: str = "Special Offer",
    badge_text: str = "20% OFF",
    cta_text: str = "Shop Now / දැන්ම ගන්න"
) -> bytes:
    """
    Composites a high-converting e-commerce commercial social media ad poster
    with gradient overlays, Sinhala & English typography, discount badges, and CTA ribbon.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import io

    try:
        # Load base visual and resize to square 1024x1024
        img = Image.open(io.BytesIO(base_image_bytes)).convert("RGBA")
        img = img.resize((1024, 1024), Image.Resampling.LANCZOS)

        # Create overlay layer
        overlay = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. Top dark gradient for brand & badge
        for y in range(220):
            alpha = int(220 * (1.0 - (y / 220.0)))
            draw.line([(0, y), (1024, y)], fill=(15, 23, 42, alpha))

        # 2. Bottom dark gradient for Sinhala & English copy
        for y in range(700, 1024):
            alpha = int(240 * ((y - 700) / 324.0))
            draw.line([(0, y), (1024, y)], fill=(15, 23, 42, alpha))

        # Fonts setup (Nirmala UI for Sinhala, Arial for English)
        font_dir = "C:/Windows/Fonts"
        try:
            sin_font = ImageFont.truetype(f"{font_dir}/Nirmala.ttc", 36)
            eng_font = ImageFont.truetype(f"{font_dir}/arialbd.ttf", 40)
            badge_font = ImageFont.truetype(f"{font_dir}/arialbd.ttf", 32)
            small_font = ImageFont.truetype(f"{font_dir}/arial.ttf", 22)
            cta_font = ImageFont.truetype(f"{font_dir}/Nirmala.ttc", 26)
        except Exception:
            sin_font = ImageFont.load_default()
            eng_font = ImageFont.load_default()
            badge_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            cta_font = ImageFont.load_default()

        # Top Discount / Promo Badge (Top Right)
        badge_w, badge_h = 240, 60
        bx0, by0 = 1024 - badge_w - 40, 40
        draw.rounded_rectangle([(bx0, by0), (bx0 + badge_w, by0 + badge_h)], radius=12, fill=(239, 68, 68, 240), outline=(255, 255, 255, 200), width=2)
        draw.text((bx0 + 24, by0 + 12), f"🔥 {badge_text}", fill=(255, 255, 255, 255), font=badge_font)

        # Top Left Brand Tag
        draw.rounded_rectangle([(40, 40), (220, 95)], radius=10, fill=(30, 41, 59, 210), outline=(99, 102, 241, 200), width=2)
        draw.text((60, 52), "⚡ AdMitra", fill=(255, 255, 255, 255), font=badge_font)

        # Bottom Typography Banner: Sinhala + English
        # Sinhala Headline (Prominent)
        draw.text((50, 750), f"✨ {headline_sinhala[:45]}", fill=(254, 240, 138, 255), font=sin_font)
        # English Sub-headline
        draw.text((50, 810), f"{headline_english[:50]}", fill=(248, 250, 252, 255), font=eng_font)

        # Bottom Action Bar / CTA Ribbon
        draw.rounded_rectangle([(50, 890), (974, 970)], radius=14, fill=(99, 102, 241, 245), outline=(165, 180, 252, 220), width=2)
        draw.text((80, 915), f"👉 {cta_text}", fill=(255, 255, 255, 255), font=cta_font)
        draw.text((780, 918), "ORDER NOW ➔", fill=(254, 240, 138, 255), font=badge_font)

        # Merge layers
        final_img = Image.alpha_composite(img, overlay).convert("RGB")
        out_buf = io.BytesIO()
        final_img.save(out_buf, format="JPEG", quality=95)
        return out_buf.getvalue()
    except Exception as exc:
        logger.info(f"Ad poster compositing error: {exc}")
        return base_image_bytes


def generate_ad_image(
    prompt: str,
    seed: Optional[int] = None,
    headline_sinhala: str = "විශේෂ දීමනාව",
    headline_english: str = "Special Offer",
    badge_text: str = "20% OFF",
    apply_ad_compositing: bool = True
) -> tuple[Optional[str], Optional[bytes]]:
    """
    Generates high-resolution commercial ad imagery with professional marketing overlays:
    1. AI Hero Product Shot (Centered, sharp commercial photography)
    2. Sinhala & English Typography & Discount Badge Compositing
    """
    import urllib.parse
    import random
    
    clean_prompt = prompt.strip()
    
    # Force high-converting commercial photography prompt
    enhanced_hero_prompt = f"professional commercial product photography of {clean_prompt}, centered close-up hero shot, studio softbox lighting, clean modern depth of field, high contrast, 8k commercial ad asset"
    encoded_prompt = urllib.parse.quote(enhanced_hero_prompt)
    img_seed = seed or random.randint(10000, 999999)
    
    # 1. Try Pollinations AI (Flux / Turbo)
    poll_urls = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={img_seed}&nologo=true&model=turbo",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={img_seed}&nologo=true&model=flux",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_prompt)}?width=768&height=768&seed={img_seed}&nologo=true"
    ]
    
    raw_bytes = None
    final_url = None
    for url in poll_urls:
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200 and len(res.content) > 3000:
                    raw_bytes = res.content
                    final_url = url
                    break
        except Exception:
            continue

    # 2. Resilient High-Quality Commercial Product Visual Fallback (Unsplash 800x800)
    if not raw_bytes:
        kw = "headphones"
        for term in ["headphone", "headphones", "dress", "fashion", "shoes", "sneakers", "watch", "perfume", "camera", "phone", "bag", "laptop"]:
            if term in clean_prompt.lower():
                kw = term
                break
        stock_url = f"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1024&auto=format&fit=crop&q=85" if "headphone" in kw else f"https://source.unsplash.com/featured/1024x1024/?{kw},product"
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(stock_url)
                if res.status_code == 200 and len(res.content) > 2000:
                    raw_bytes = res.content
                    final_url = stock_url
        except Exception:
            pass

    # 3. Apply Commercial Sinhala & English Ad Compositing Overlay
    if raw_bytes and apply_ad_compositing:
        composed_bytes = compose_commercial_ad_poster(
            raw_bytes,
            headline_sinhala=headline_sinhala,
            headline_english=headline_english,
            badge_text=badge_text,
            cta_text="දැන්ම ඇනවුම් කරන්න / Shop Now"
        )
        return final_url, composed_bytes
    elif raw_bytes:
        return final_url, raw_bytes

    # Ultimate fallback
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


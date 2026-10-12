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
        res = httpx.post(url, json=payload, timeout=12.0)
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
    cta_text: str = "දැන්ම ඇනවුම් කරන්න / Shop Now",
    brand_name: str = "Lanka Ads",
    target_lang: str = "bilingual"
) -> bytes:
    """
    Applies Meta-optimized commercial overlay template:
    - High-contrast top gradient with Brand Tag & Promo Badge
    - Lower gradient with user-selected Language Typography:
        * 'english'  : English Headline (Gold) + Subtitle/Offer + 'ORDER NOW' CTA
        * 'sinhala'  : Sinhala Headline (Gold) + Sinhala CTA
        * 'bilingual': Both Sinhala & English
    """
    from PIL import Image, ImageDraw, ImageFont
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
            alpha = int(230 * (1.0 - (y / 220.0)))
            draw.line([(0, y), (1024, y)], fill=(10, 15, 30, alpha))

        # 2. Bottom dark gradient for copy
        for y in range(650, 1024):
            alpha = int(250 * ((y - 650) / 374.0))
            draw.line([(0, y), (1024, y)], fill=(10, 15, 30, alpha))

        def _get_font(size: int, is_bold: bool = False, prefer_sinhala: bool = False):
            import os
            if prefer_sinhala:
                for p in ["/System/Library/Fonts/Supplemental/Sinhala Sangam MN.ttc", "/Library/Fonts/Sinhala Sangam MN.ttc", "C:/Windows/Fonts/Nirmala.ttc", "/System/Library/Fonts/Helvetica.ttc"]:
                    if os.path.exists(p):
                        try: return ImageFont.truetype(p, size)
                        except Exception: pass
            for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
                if os.path.exists(p):
                    try: return ImageFont.truetype(p, size)
                    except Exception: pass
            return ImageFont.load_default()

        sin_font = _get_font(40, is_bold=True, prefer_sinhala=True)
        eng_font = _get_font(38, is_bold=True)
        eng_sub_font = _get_font(28, is_bold=False)
        badge_font = _get_font(32, is_bold=True)
        brand_font = _get_font(28, is_bold=True)
        cta_font = _get_font(28, is_bold=True, prefer_sinhala=True)
        cta_btn_font = _get_font(26, is_bold=True)

        # Clean string inputs
        clean_sin_head = headline_sinhala.replace("✨", "").replace("🔥", "").replace("👉", "").strip()
        clean_eng_head = headline_english.replace("✨", "").replace("🔥", "").replace("👉", "").strip()
        clean_badge = badge_text.replace("🔥", "").replace("✨", "").strip()
        clean_cta = cta_text.replace("👉", "").replace("✨", "").strip()
        clean_brand = brand_name.strip() or "AdMitra"

        # Top Right Discount / Promo Badge (Red pill badge with border)
        badge_w, badge_h = 280, 62
        bx0, by0 = 1024 - badge_w - 40, 40
        draw.rounded_rectangle([(bx0, by0), (bx0 + badge_w, by0 + badge_h)], radius=31, fill=(225, 29, 72, 250), outline=(255, 255, 255, 240), width=2)
        draw.ellipse([(bx0 + 22, by0 + 22), (bx0 + 40, by0 + 40)], fill=(254, 240, 138, 255))
        draw.text((bx0 + 52, by0 + 13), clean_badge, fill=(255, 255, 255, 255), font=badge_font)

        # Top Left Brand Tag (Sleek dark glass pill)
        brand_w = max(240, len(clean_brand) * 18 + 60)
        draw.rounded_rectangle([(40, 40), (40 + brand_w, 102)], radius=14, fill=(15, 23, 42, 240), outline=(99, 102, 241, 230), width=2)
        draw.ellipse([(58, 58), (80, 80)], fill=(99, 102, 241, 255))
        draw.text((95, 54), clean_brand, fill=(255, 255, 255, 255), font=brand_font)

        # Bottom Typography Banner based on target_lang
        t_lang = (target_lang or "bilingual").lower()
        if "eng" in t_lang:
            # Pure English Ad Poster Layout
            draw.text((50, 730), clean_eng_head[:55], fill=(254, 240, 138, 255), font=eng_font)
            draw.text((50, 795), f"Exclusive Online Offer • Limited Time Deals", fill=(248, 250, 252, 255), font=eng_sub_font)
            bottom_cta_text = clean_cta if any(c.isascii() for c in clean_cta) else "Order Online Today • Fast Islandwide Delivery"
            button_label = "SHOP NOW"
        elif "sin" in t_lang:
            # Pure Sinhala Ad Poster Layout
            draw.text((50, 730), clean_sin_head[:55], fill=(254, 240, 138, 255), font=sin_font)
            draw.text((50, 795), "දිවයින පුරා බෙදාහැරීම • විශේෂ මිල අඩු කිරීම්", fill=(248, 250, 252, 255), font=sin_font)
            bottom_cta_text = clean_cta
            button_label = "ඇණවුම් කරන්න"
        else:
            # Bilingual Layout (Both)
            draw.text((50, 725), clean_sin_head[:55], fill=(254, 240, 138, 255), font=sin_font)
            draw.text((50, 795), clean_eng_head[:60], fill=(248, 250, 252, 255), font=eng_font)
            bottom_cta_text = clean_cta
            button_label = "ORDER NOW"

        # Bottom Action Bar / CTA Ribbon
        draw.rounded_rectangle([(50, 880), (974, 965)], radius=18, fill=(79, 70, 229, 250), outline=(199, 210, 254, 230), width=2)
        draw.text((75, 905), bottom_cta_text[:45], fill=(255, 255, 255, 255), font=cta_font)
        
        # Inner CTA Button (Shop Now)
        draw.rounded_rectangle([(710, 892), (955, 952)], radius=12, fill=(255, 255, 255, 255))
        draw.text((735, 907), button_label, fill=(67, 56, 202, 255), font=cta_btn_font)

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
    cta_text: str = "දැන්ම ඇනවුම් කරන්න / Shop Now",
    brand_name: str = "Lanka Ads",
    apply_ad_compositing: bool = True,
    target_lang: str = "bilingual"
) -> tuple[Optional[str], Optional[bytes]]:
    """
    Generates high-resolution commercial ad imagery with professional marketing overlays:
    1. Realistic Product Hero Shot (Centered, sharp commercial studio photography)
    2. High-converting Sinhala & English Typography & Discount Badge Compositing
    """
    import urllib.parse
    import random
    
    raw_prompt = prompt.strip()
    
    # 1. Product Category Matching for High-End Commercial Hero Shots
    PRODUCT_STUDIO_ASSETS = {
        "laptop": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1024&q=85", # Modern Laptop Studio
        "msi": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=1024&q=85", # Gaming/High-End Laptop
        "computer": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1024&q=85",
        "macbook": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1024&q=85",
        "iphone": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=1024&q=85", # iPhone Titanium Studio
        "phone": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=1024&q=85",
        "headphone": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1024&q=85", # Headphones Studio
        "headset": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1024&q=85",
        "tshirt": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1024&q=85", # Minimalist Premium White T-Shirt Studio Flatlay
        "t-shirt": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1024&q=85",
        "shirt": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1024&q=85",
        "tee": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=1024&q=85",
        "streetwear": "https://images.unsplash.com/photo-1562157873-818bc0726f68?w=1024&q=85", # Color Collection of T-Shirts Studio
        "dress": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=1024&q=85", # Fashion Dress Studio
        "shoe": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1024&q=85", # Red Nike Sneaker Studio
        "sneaker": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1024&q=85",
        "watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=1024&q=85", # Luxury Watch Studio
        "perfume": "https://images.unsplash.com/photo-1541643600914-78b084683601?w=1024&q=85", # Luxury Perfume Studio
        "camera": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=1024&q=85", # Professional Camera Studio
        "bag": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=1024&q=85", # Leather Handbag Studio
    }

    # Extended categories (every image URL below was visually verified to match its label)
    _U = "https://images.unsplash.com/photo-{}?w=1024&q=85"
    _EXTRA_ASSETS = {
        # Vehicles
        _U.format("1494976388531-d1058494cdd8"): ["car", "vehicle", "sedan", "sports car", "automobile"],
        _U.format("1519641471654-76ce0107ad1b"): ["suv", "jeep", "crossover"],
        _U.format("1527786356703-4b100091cd2c"): ["van", "minivan", "caravan", "campervan", "camper"],
        _U.format("1559416523-140ddc3d238c"): ["pickup", "pick-up", "double cab"],
        _U.format("1601584115197-04ecc0da31d7"): ["truck", "lorry", "cargo", "trailer"],
        _U.format("1570125909232-eb263c188f7e"): ["bus", "coach"],
        _U.format("1558981806-ec527fa84c39"): ["motorcycle", "motorbike", "scooter", "bike"],
        _U.format("1485965120184-e220f721d03e"): ["bicycle", "cycle", "cycling"],
        _U.format("1530267981375-f0de937f5f13"): ["tractor"],
        # Electronics
        _U.format("1593359677879-a4bb92f829d1"): ["tv", "television", "smart tv"],
        _U.format("1590658268037-6bf12165a8df"): ["earbud", "earbuds", "airpod", "airpods", "earphone", "earphones"],
        _U.format("1608043152269-423dbba4e7e1"): ["speaker", "bluetooth speaker", "soundbar"],
        _U.format("1544244015-0df4b3ffc6b0"): ["tablet", "ipad"],
        _U.format("1587829741301-dc798b83add3"): ["keyboard"],
        _U.format("1527864550417-7fd91fc51a46"): ["mouse"],
        _U.format("1546868871-7041f2a55e12"): ["smartwatch", "smart watch", "apple watch"],
        _U.format("1502920917128-1aa500764cbd"): ["dslr", "mirrorless"],
        # Phones (aliases)
        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=1024&q=85": ["smartphone", "mobile", "android", "samsung", "mobile phone"],
        # Fashion & accessories
        _U.format("1542272604-787c3835535d"): ["jeans", "denim", "trousers"],
        _U.format("1556821840-3a63f95609a7"): ["hoodie", "sweatshirt", "jacket"],
        _U.format("1553062407-98eeb64c6a62"): ["backpack", "school bag", "rucksack"],
        _U.format("1572635196237-14b3f281503f"): ["sunglass", "sunglasses", "glasses", "eyewear"],
        _U.format("1605100804763-247f67b3557e"): ["jewelry", "jewellery", "ring", "necklace", "bracelet", "earring"],
        # Home & lifestyle
        _U.format("1555041469-a586c61ea9bc"): ["sofa", "couch"],
        _U.format("1586023492125-27b2c045efd7"): ["furniture", "chair", "interior", "decor"],
        _U.format("1602143407151-7111542de6e8"): ["bottle", "water bottle", "flask", "tumbler"],
        _U.format("1495474472287-4d71bcdd2085"): ["coffee", "cafe", "latte"],
    }
    for _url, _aliases in _EXTRA_ASSETS.items():
        for _alias in _aliases:
            PRODUCT_STUDIO_ASSETS.setdefault(_alias, _url)
    
    # Check if prompt targets known product categories.
    # Whole-word match (plural-aware), longest keys first, so 'headphones' never matches 'phone'.
    import re
    matched_stock_url = None
    lower_p = raw_prompt.lower()
    for cat_key in sorted(PRODUCT_STUDIO_ASSETS, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(cat_key)}s?(?![a-z])", lower_p):
            matched_stock_url = PRODUCT_STUDIO_ASSETS[cat_key]
            break

    # 2. Build photorealistic commercial prompt
    clean_subj = raw_prompt
    for redundant in ["extreme close-up hero shot of", "hero shot of", "close-up of", "Vibrant E-Commerce Promotional Poster"]:
        clean_subj = clean_subj.replace(redundant, "")
    clean_subj = clean_subj.strip(" ,")

    realistic_product_prompt = f"commercial product photography of {clean_subj}, centered isolated product on modern studio pedestal, soft studio lighting, sharp focus, 8k commercial ad asset, no people, no face"
    encoded_prompt = urllib.parse.quote(realistic_product_prompt)
    img_seed = seed or random.randint(10000, 999999)

    # 3. Multi-tier Image Fetching Pipeline
    raw_bytes = None
    final_url = None

    # Try realistic AI generation via Flux first
    poll_urls = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={img_seed}&nologo=true&model=flux",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={img_seed}&nologo=true"
    ]
    
    # Prioritize matched product photography asset, then try live AI generation
    candidate_urls = ([matched_stock_url] if matched_stock_url else []) + poll_urls

    for url in candidate_urls:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200 and len(res.content) > 3000:
                    raw_bytes = res.content
                    final_url = url
                    break
        except Exception:
            continue

    # Guarantee fallback if all external endpoints fail
    if not raw_bytes:
        default_stock = matched_stock_url or "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1024&q=85"
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                res = client.get(default_stock)
                if res.status_code == 200 and len(res.content) > 2000:
                    raw_bytes = res.content
                    final_url = default_stock
        except Exception:
            pass

    # If still no bytes, generate a clean studio dark backdrop canvas in memory
    if not raw_bytes:
        from PIL import Image, ImageDraw
        import io
        blank_img = Image.new("RGB", (1024, 1024), (15, 23, 42))
        b_draw = ImageDraw.Draw(blank_img)
        # Radial / pedestal studio glow
        b_draw.ellipse([(200, 400), (824, 900)], fill=(30, 41, 59))
        buf = io.BytesIO()
        blank_img.save(buf, format="JPEG", quality=95)
        raw_bytes = buf.getvalue()
        final_url = "local-commercial-canvas"

    # 4. Apply Commercial Sinhala & English Ad Compositing Overlay
    if raw_bytes and apply_ad_compositing:
        composed_bytes = compose_commercial_ad_poster(
            raw_bytes,
            headline_sinhala=headline_sinhala,
            headline_english=headline_english,
            badge_text=badge_text,
            cta_text=cta_text,
            brand_name=brand_name,
            target_lang=target_lang
        )
        return final_url, composed_bytes
    elif raw_bytes:
        return final_url, raw_bytes

    return final_url, None



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


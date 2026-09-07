"""
shared/security.py — AdMitra Security Utilities
================================================
Provides three security primitives used across the entire system:
  1. Fernet symmetric encryption / decryption of sensitive tokens.
  2. Input sanitization to block LLM prompt-injection attacks.
  3. A thread-safe rate limiter for agent-level call throttling.

Author  : Member 1 — Backend Lead
Project : AdMitra (IT3041 — IRWA, SLIIT)
"""

import os
import re
import time
import threading
from collections import deque
from typing import Deque

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Fernet Token Encryption
# ---------------------------------------------------------------------------

def _build_fernet() -> Fernet:
    """
    Loads Fernet key from the FERNET_KEY env variable.
    If not set (e.g. during local dev), generates ONE key for the session and warns.
    NEVER commit a real key — always use .env for secrets.
    """
    key: str | None = os.getenv("FERNET_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        print(
            "[security WARNING] FERNET_KEY not set in environment. "
            "A temporary key has been generated for this session only. "
            "Set FERNET_KEY in your .env file for persistent encryption."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


# Module-level singleton — ensures encrypt and decrypt always share the same key
_FERNET_INSTANCE: Fernet = _build_fernet()


def encrypt_token(token: str) -> str:
    """
    Encrypts a plaintext string token using Fernet symmetric encryption.

    Args:
        token: Plaintext string to encrypt (e.g. an API key or user token).

    Returns:
        URL-safe base64-encoded encrypted string.
    """
    return _FERNET_INSTANCE.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """
    Decrypts a Fernet-encrypted token back to plaintext.

    Args:
        encrypted: URL-safe base64-encoded encrypted string.

    Returns:
        Original plaintext string.

    Raises:
        cryptography.fernet.InvalidToken: If the token is invalid or tampered.
    """
    return _FERNET_INSTANCE.decrypt(encrypted.encode()).decode()


# ---------------------------------------------------------------------------
# 2. Prompt Injection Sanitizer
# ---------------------------------------------------------------------------

# Ordered list of regex patterns to strip prompt-injection attack phrases.
# Add new patterns as new attack vectors are discovered.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?.*instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(your|all)\s+(previous\s+)?instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+different\s+(AI|assistant|model)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(are|were)\s+)?(a\s+)?[A-Za-z\s]+without\s+(any\s+)?restrictions?", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(safety|guidelines|instructions?)", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+(have\s+no|don['']t\s+have)\s+(limits?|restrictions?)", re.IGNORECASE),
    re.compile(r"new\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
]


def sanitize_input(text: str) -> str:
    """
    Strips known prompt-injection attack phrases from a text string.

    This is a defense-in-depth measure; always use with LLM calls.

    Args:
        text: Raw user-supplied or external input string.

    Returns:
        Sanitized text with injection phrases removed (replaced with empty string).
    """
    if not isinstance(text, str):
        return str(text)
    sanitized = text
    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub("", sanitized)
    # Collapse excessive whitespace left behind by stripping
    sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()
    return sanitized


# ---------------------------------------------------------------------------
# 3. Thread-Safe Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Thread-safe sliding-window rate limiter.

    Tracks call timestamps within a rolling time window and rejects
    requests that exceed the configured maximum calls per period.

    Usage:
        limiter = RateLimiter(max_calls=10, period_seconds=60)
        if not limiter.allow_request():
            return {"status": "error", "result": {"message": "Rate limit exceeded."}}

    Attributes:
        max_calls      : Maximum number of calls allowed within `period_seconds`.
        period_seconds : Length of the sliding window in seconds (default 60).
    """

    def __init__(self, max_calls: int | None = None, period_seconds: int = 60) -> None:
        if max_calls is None:
            max_calls = int(os.getenv("ENGAGEMENT_RATE_LIMIT", "10"))
        self.max_calls: int = max_calls
        self.period_seconds: int = period_seconds
        self._calls: Deque[float] = deque()
        self._lock: threading.Lock = threading.Lock()

    def allow_request(self) -> bool:
        """
        Check whether a new request is within rate limits.

        Returns:
            True  — request is allowed (call count is within limit).
            False — request is rejected (rate limit exceeded).
        """
        now = time.monotonic()
        with self._lock:
            cutoff = now - self.period_seconds
            # Evict timestamps older than the sliding window
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()
            if len(self._calls) < self.max_calls:
                self._calls.append(now)
                return True
            return False

    def remaining(self) -> int:
        """Returns how many calls are still allowed in the current window."""
        now = time.monotonic()
        with self._lock:
            cutoff = now - self.period_seconds
            active = sum(1 for t in self._calls if t >= cutoff)
            return max(0, self.max_calls - active)

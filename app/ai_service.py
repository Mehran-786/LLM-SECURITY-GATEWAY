from app.config import GROQ_API_KEY, SECURITY_SYSTEM_PROMPT

# ──────────────────────────────────────────────────────────────────────────────
# Groq is 100% compatible with the OpenAI Python SDK.
# We just point the client at Groq's base URL and use a Groq model name.
# ──────────────────────────────────────────────────────────────────────────────
_GROQ_BASE_URL  = "https://api.groq.com/openai/v1"
_GROQ_MODEL     = "llama-3.1-8b-instant"     # free, fast — active Groq model

# Placeholder keys that mean "the user hasn't configured this yet"
_PLACEHOLDER_KEYS = {"gsk-your-real-groq-key-here", "sk-your-real-key-here",
                     "your_key_here", "your_key*here", ""}

def _key_is_valid(key) -> bool:
    """Return True only when the key is a non-empty, non-placeholder string."""
    return bool(key) and key.strip() not in _PLACEHOLDER_KEYS


# ──────────────────────────────────────────────────────────────────────────────
# Lazy-initialise the Groq client (via OpenAI SDK) on first use.
# ──────────────────────────────────────────────────────────────────────────────
_client = None

def _get_client():
    """Return a cached Groq client, or None if the key is absent/invalid."""
    global _client

    if _client is not None:
        return _client

    if not _key_is_valid(GROQ_API_KEY):
        return None

    from openai import OpenAI
    _client = OpenAI(
        api_key=GROQ_API_KEY.strip(),   # strip any accidental whitespace
        base_url=_GROQ_BASE_URL,
    )
    return _client


# ──────────────────────────────────────────────────────────────────────────────
# Public function
# ──────────────────────────────────────────────────────────────────────────────
def get_ai_response(user_input: str) -> str:
    """
    Send user_input through the security system prompt and return the AI reply.
    Uses the Groq API (free, fast) via the OpenAI-compatible SDK.

    Fallback behaviour:
      • Missing / placeholder key  → friendly setup message
      • Authentication error       → [Groq API Error] message
      • Rate-limit error           → [Groq API Error] message
      • Any other exception        → [Groq API Error] message
    """

    # ── Guard: key missing or still a placeholder ─────────────────────────
    if not _key_is_valid(GROQ_API_KEY):
        return (
            f"[System] Groq API Key missing. "
            f"Get a free key at https://console.groq.com/keys, "
            f"add it to your .env file as GROQ_API_KEY=gsk_..., "
            f"and restart the server. "
            f"Simulated receipt of: {user_input}"
        )

    client = _get_client()

    messages = [
        {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
        {"role": "user",   "content": user_input},
    ]

    try:
        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=_GROQ_MODEL,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content  # type: ignore[return-value]

    except Exception as exc:
        exc_str = str(exc).lower()

        if "authentication" in exc_str or "api key" in exc_str or "invalid" in exc_str or "401" in exc_str:
            return (
                "[Groq API Error] Authentication failed — your GROQ_API_KEY is invalid or expired. "
                "Get a new key at https://console.groq.com/keys and update your .env file."
            )
        if "quota" in exc_str or "rate limit" in exc_str or "429" in exc_str or "limit" in exc_str:
            return (
                "[Groq API Error] Rate limit reached. "
                "Groq's free tier is generous — please wait a moment and try again."
            )

        # Generic fallback — never surface raw exception text to the UI
        return (
            f"[Groq API Error] The AI service is temporarily unavailable ({type(exc).__name__}). "
            f"Simulated receipt of: {user_input}"
        )
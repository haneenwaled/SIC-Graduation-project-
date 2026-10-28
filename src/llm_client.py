"""Thin wrapper around the Google Gen AI SDK with friendly, secret-free error messages."""
from __future__ import annotations

from .config import Config


class LLMError(Exception):
    """Error whose message is safe to show to the user (never contains the API key)."""

    def __init__(self, message: str, kind: str = "unknown"):
        super().__init__(message)
        self.kind = kind


SETUP_HELP = (
    "Gemini API key not configured. Copy `.env.example` to `.env`, set `GEMINI_API_KEY=<your key>` "
    "(create one at https://aistudio.google.com/apikey) and restart the app."
)


def classify_error(exc: Exception) -> LLMError:
    """Map SDK / network exceptions to a user-friendly LLMError."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc).lower()
    if code in (401, 403) or "api key" in text or "permission" in text or "unauthenticated" in text:
        return LLMError("Gemini rejected the API key or permissions. Check GEMINI_API_KEY in `.env`.", "auth")
    if code == 429 or "quota" in text or "resource_exhausted" in text or "rate" in text and "limit" in text:
        return LLMError("Gemini quota or rate limit reached. Wait a minute and retry, or check your plan.", "quota")
    if code == 404 or "not found" in text or "not supported" in text:
        return LLMError("The configured Gemini model is unavailable. Change GEMINI_MODEL in `.env` "
                        "(run `python scripts/smoke_test_gemini.py` to list models).", "model")
    if code in (500, 502, 503, 504) or "unavailable" in text or "overloaded" in text:
        return LLMError("Gemini is temporarily unavailable. Please retry shortly.", "server")
    if any(w in text for w in ("connect", "timeout", "timed out", "network", "dns", "name resolution")):
        return LLMError("Network problem while contacting Gemini. Check your internet connection.", "network")
    return LLMError(f"Unexpected Gemini error ({type(exc).__name__}). Details are hidden to protect secrets.", "unknown")


class GeminiClient:
    def __init__(self, config: Config, client=None):
        self.config = config
        self._client = client  # injectable for tests

    @property
    def available(self) -> bool:
        return self._client is not None or self.config.api_key_configured

    def _get_client(self):
        if self._client is None:
            if not self.config.api_key_configured:
                raise LLMError(SETUP_HELP, "config")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.config.gemini_api_key.strip())
            except Exception as exc:
                raise classify_error(exc) from None
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text; tries fallback models only if the primary model is unavailable (404)."""
        from google.genai import types

        client = self._get_client()
        models = [self.config.gemini_model, *self.config.gemini_fallback_models]
        last: LLMError | None = None
        for model in models:
            try:
                resp = client.models.generate_content(
                    model=model, contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt, temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens))
                text = (getattr(resp, "text", None) or "").strip()
                if not text:
                    raise LLMError("Gemini returned an empty or blocked response. Try rephrasing the question.", "empty")
                return text
            except LLMError:
                raise
            except Exception as exc:
                last = classify_error(exc)
                if last.kind != "model":
                    raise last from None
        raise last or LLMError("No Gemini model could be used.", "model")

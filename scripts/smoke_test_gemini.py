"""Manual live check of the Gemini configuration (needs internet + a real key in .env).

Run from the project root:   python scripts/smoke_test_gemini.py
It never prints your API key.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config  # noqa: E402
from src.llm_client import SETUP_HELP, GeminiClient, LLMError  # noqa: E402


def main() -> int:
    cfg = Config.from_env()
    if not cfg.api_key_configured:
        print("FAIL:", SETUP_HELP)
        return 1
    client = GeminiClient(cfg)
    print(f"Configured model: {cfg.gemini_model} (fallbacks: {', '.join(cfg.gemini_fallback_models) or 'none'})")
    try:
        names = [m.name.replace("models/", "") for m in client._get_client().models.list()]
        print(f"Models visible to this key: {len(names)}")
        print("Configured model available:", "YES" if cfg.gemini_model in names else "NOT LISTED - set GEMINI_MODEL in .env")
        print("Some available models:", ", ".join(n for n in names if "gemini" in n)[:400])
        print("Test generation:", client.generate("Reply with the single word OK.", "Say OK.")[:80])
    except LLMError as exc:
        print("FAIL:", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__} (details hidden to protect secrets)")
        return 1
    print("SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

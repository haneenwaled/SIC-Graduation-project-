"""Optional live smoke test. Skipped unless RUN_LIVE_TESTS=1 and GEMINI_API_KEY is set.

PowerShell:  $env:RUN_LIVE_TESTS = "1"; python -m pytest tests/test_live_gemini.py -v
"""
import os

import pytest

from src.config import Config
from src.llm_client import GeminiClient

pytestmark = pytest.mark.live


@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to call the real API")
def test_gemini_answers_a_trivial_prompt():
    cfg = Config.from_env()
    if not cfg.api_key_configured:
        pytest.skip("GEMINI_API_KEY not configured")
    out = GeminiClient(cfg).generate("Reply with the single word OK.", "Say OK.")
    assert out.strip()

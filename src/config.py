"""Single place for all configuration. Values come from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Exact filenames the application expects inside the data folder.
MARKDOWN_FILES = {
    "retention_playbook.md": "retention_playbook",
    "promotion_policy.md": "promotion_policy",
    "business_rules_kpis.md": "business_rules",
}
CATALOG_FILE = "product_catalog_documents.jsonl"
CUSTOMER_FILE = "customer_lapse_predictions.csv"
REQUIRED_FILES = [*MARKDOWN_FILES, CATALOG_FILE, CUSTOMER_FILE]

# Document types used as retrieval metadata (policy vs. catalog stay distinguishable).
KNOWLEDGE_DOC_TYPES = ("retention_playbook", "promotion_policy", "business_rules")
CATALOG_DOC_TYPE = "product_catalog"

RISK_ORDER = ["Low", "Medium", "High"]
# Cut points documented in business_rules_kpis.md section 9.1 (lower bound inclusive).
RISK_THRESHOLDS = {"Medium": 0.30, "High": 0.50}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class Config:
    data_dir: Path = PROJECT_ROOT / "data"
    cache_dir: Path = PROJECT_ROOT / ".cache" / "index"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_models: list[str] = field(default_factory=list)
    temperature: float = 0.2
    max_output_tokens: int = 2048
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 6
    min_score: float = 0.2

    @property
    def api_key_configured(self) -> bool:
        key = self.gemini_api_key.strip()
        return bool(key) and key != "your_gemini_api_key_here"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Config":
        load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
        fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-flash-latest")
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            gemini_fallback_models=[m.strip() for m in fallbacks.split(",") if m.strip()],
            temperature=_env_float("GEMINI_TEMPERATURE", 0.2),
            max_output_tokens=_env_int("GEMINI_MAX_OUTPUT_TOKENS", 2048),
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            chunk_size=_env_int("CHUNK_SIZE", 800),
            chunk_overlap=_env_int("CHUNK_OVERLAP", 100),
            top_k=_env_int("TOP_K", 6),
            min_score=_env_float("MIN_SCORE", 0.2),
        )

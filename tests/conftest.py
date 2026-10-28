"""Small temporary fixtures: tiny versions of the five input files. No real customer data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import Config
from src.embeddings import HashingEmbedder

PLAYBOOK = """# Retention Playbook

## 3. Recommended Actions

### 3.3 High Risk
Personal outreach by an account owner. Consider a non-discount incentive first. Human review for the focus list.

### 3.1 Low Risk
Standard communication only. Avoid discounts.

## 4. Cancellations

Diagnose repeated cancellations before acting. Service recovery is preferred over discounts.
"""
POLICY = """# Promotion Policy

## 8. Promotion Decision Matrix

Outcomes are Not Recommended, Eligible for Review and Requires Approval. Any promotion for a focus list customer requires approval by an authorized approver.

## 9. Approval

Discount limits are a Data Gap. Human approval is mandatory for credits and rebates.
"""
RULES = """# Business Rules and KPIs

## 9.1 Risk Tier Thresholds

Low is below 0.30, Medium from 0.30 to below 0.50, High is 0.50 or above. Calibration is Pending Validation.

## 12. Customer Value

Customer value is historical net revenue. Profit requires cost data, which is a Data Gap.
"""
CATALOG = [
    {"id": "10001", "text": "Product ID: 10001\nProduct Description: RED WRAPPING TAPE\naverage_price: 0.8\nmedian_price: 0.8\ntotal_quantity: 100\npurchase_lines: 10\norder_count: 10\ntotal_revenue: 80.0",
     "metadata": {"product_id": "10001", "source": "x.csv"}},
    {"id": "10002", "text": "Product ID: 10002\nProduct Description: BLUE GARDEN GNOME\naverage_price: 5.0\nmedian_price: 5.0\ntotal_quantity: 20\npurchase_lines: 4\norder_count: 4\ntotal_revenue: 100.0",
     "metadata": {"product_id": "10002", "source": "x.csv"}},
    {"id": "10003", "text": "Product ID: 10003\nProduct Description: CERAMIC TEA MUG\naverage_price: 2.0\nmedian_price: 2.0\ntotal_quantity: 50\npurchase_lines: 8\norder_count: 8\ntotal_revenue: 100.0",
     "metadata": {"product_id": "10003", "source": "x.csv"}},
]
CSV = """customer_id,snapshot_date,lapse_probability,risk_category
1,2011-08-01,0.20,Low
2,2011-08-01,0.70,High
1,2011-09-01,0.90,High
2,2011-09-01,0.55,High
3,2011-09-01,0.40,Medium
4,2011-09-01,0.10,Low
5,2011-09-01,0.95,High
6,2011-09-01,0.30,Medium
"""


def write_fixture_data(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "retention_playbook.md").write_text(PLAYBOOK, encoding="utf-8")
    (d / "promotion_policy.md").write_text(POLICY, encoding="utf-8")
    (d / "business_rules_kpis.md").write_text(RULES, encoding="utf-8")
    (d / "product_catalog_documents.jsonl").write_text("\n".join(json.dumps(r) for r in CATALOG) + "\n", encoding="utf-8")
    (d / "customer_lapse_predictions.csv").write_text(CSV, encoding="utf-8")
    return d


@pytest.fixture
def data_dir(tmp_path) -> Path:
    return write_fixture_data(tmp_path / "data")


@pytest.fixture
def config(tmp_path, data_dir) -> Config:
    return Config(data_dir=data_dir, cache_dir=tmp_path / "cache", gemini_api_key="", chunk_size=400,
                  chunk_overlap=50, top_k=4, min_score=0.05)


@pytest.fixture
def embedder() -> HashingEmbedder:
    return HashingEmbedder()


class FakeLLM:
    """Records the prompt it receives instead of calling Gemini."""

    def __init__(self, reply: str = "FAKE ANSWER", error: Exception | None = None):
        self.reply, self.error, self.system, self.prompt = reply, error, None, None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system, self.prompt = system_prompt, user_prompt
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()

"""Structured customer-risk data: validation and deterministic Pandas queries (no LLM involved)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import RISK_ORDER, RISK_THRESHOLDS

REQUIRED_COLUMNS = ["customer_id", "snapshot_date", "lapse_probability", "risk_category"]

PROBABILITY_VS_CATEGORY = (
    "**Model probability vs. business risk category.** `lapse_probability` is the model's estimated chance "
    "(0-1) that a customer makes no valid purchase in the prediction horizon. `risk_category` (Low / Medium / "
    "High) is a business label derived from that probability using cut points of about 0.30 and 0.50 "
    "(business_rules_kpis.md, section 9.1). The probability is a continuous ranking signal; the category is a "
    "coarse grouping. Whether the probability is calibrated (a true 70% chance) is not verified, "
    "so treat both as estimates."
)


class CustomerDataError(Exception):
    """Raised when the customer file is missing or structurally unusable."""


@dataclass
class QualityReport:
    rows_in_file: int = 0
    rows_valid: int = 0
    issues: list[str] = field(default_factory=list)
    invalid_rows: int = 0
    duplicate_rows: int = 0
    tier_mismatch_rows: int = 0

    @property
    def ok(self) -> bool:
        return not self.issues


def _expected_tier(p: float) -> str:
    if p >= RISK_THRESHOLDS["High"]:
        return "High"
    if p >= RISK_THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


def validate_customer_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    """Validate schema and values. Bad rows are excluded and reported, never repaired silently."""
    report = QualityReport(rows_in_file=len(raw))
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise CustomerDataError(f"Customer file is missing required column(s): {', '.join(missing)}")

    df = raw[REQUIRED_COLUMNS].copy()
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["lapse_probability"] = pd.to_numeric(df["lapse_probability"], errors="coerce")
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
    df["risk_category"] = df["risk_category"].astype("string").str.strip().str.title()

    bad_id = df["customer_id"].isna() | (df["customer_id"] % 1 != 0)
    bad_date = df["snapshot_date"].isna()
    bad_prob = df["lapse_probability"].isna() | (df["lapse_probability"] < 0) | (df["lapse_probability"] > 1)
    bad_cat = ~df["risk_category"].isin(RISK_ORDER)
    invalid = bad_id | bad_date | bad_prob | bad_cat
    for label, mask in [("customer_id missing/non-integer", bad_id), ("snapshot_date unparseable", bad_date),
                        ("lapse_probability missing or outside 0-1", bad_prob),
                        ("risk_category missing or not Low/Medium/High", bad_cat)]:
        if mask.any():
            report.issues.append(f"{int(mask.sum())} row(s): {label}")
    report.invalid_rows = int(invalid.sum())
    df = df[~invalid].copy()

    df["customer_id"] = df["customer_id"].astype("int64")
    df["risk_category"] = pd.Categorical(df["risk_category"].astype(str), categories=RISK_ORDER, ordered=True)

    dup = df.duplicated(subset=["customer_id", "snapshot_date"], keep="first")
    if dup.any():
        report.duplicate_rows = int(dup.sum())
        report.issues.append(f"{report.duplicate_rows} duplicate (customer_id, snapshot_date) row(s); first kept")
        df = df[~dup]

    # SF-6 / HR-10: a category that disagrees with the documented cut points must not be used.
    expected = df["lapse_probability"].map(_expected_tier)
    mismatch = expected != df["risk_category"].astype(str)
    if mismatch.any():
        report.tier_mismatch_rows = int(mismatch.sum())
        report.issues.append(
            f"{report.tier_mismatch_rows} row(s) have a risk_category that conflicts with the documented "
            "0.30/0.50 cut points; these rows are excluded (business_rules_kpis.md SF-6, HR-10)")
        df = df[~mismatch]

    df = df.reset_index(drop=True)
    report.rows_valid = len(df)
    return df, report


class CustomerData:
    """Wraps the validated DataFrame and exposes the deterministic query functions."""

    def __init__(self, df: pd.DataFrame, report: QualityReport, source: str = ""):
        self.df = df
        self.report = report
        self.source = source

    @classmethod
    def from_csv(cls, path: Path) -> "CustomerData":
        path = Path(path)
        if not path.is_file():
            raise CustomerDataError(f"Missing required input file: {path.name}. Place it in: {path.parent}")
        try:
            raw = pd.read_csv(path)
        except Exception as exc:
            raise CustomerDataError(f"Could not read {path.name}: {exc}") from exc
        df, report = validate_customer_frame(raw)
        if df.empty:
            raise CustomerDataError(f"{path.name} has no valid rows after validation: {'; '.join(report.issues)}")
        return cls(df, report, source=path.name)

    # ---- snapshots ---------------------------------------------------------
    def snapshots(self) -> list[pd.Timestamp]:
        return sorted(self.df["snapshot_date"].unique())

    def latest_snapshot(self) -> pd.Timestamp:
        return self.df["snapshot_date"].max()

    def _snap(self, snapshot: pd.Timestamp | str | None) -> pd.DataFrame:
        snap = self.latest_snapshot() if snapshot is None else pd.Timestamp(snapshot)
        return self.df[self.df["snapshot_date"] == snap]

    # ---- queries -----------------------------------------------------------
    def counts_by_category(self, snapshot=None) -> pd.DataFrame:
        """Distinct customers (not rows) per category, with percentages."""
        d = self._snap(snapshot)
        total = d["customer_id"].nunique()
        grp = d.groupby("risk_category", observed=False)["customer_id"].nunique().reindex(RISK_ORDER, fill_value=0)
        out = grp.rename("customers").reset_index()
        out["percent"] = (out["customers"] / total * 100).round(1) if total else 0.0
        return out

    def total_customers(self, snapshot=None) -> int:
        return int(self._snap(snapshot)["customer_id"].nunique())

    def total_rows(self, snapshot=None) -> int:
        return len(self._snap(snapshot))

    def get_customer(self, customer_id: int) -> pd.DataFrame:
        """All snapshot records for a customer, newest first (empty frame if unknown)."""
        d = self.df[self.df["customer_id"] == int(customer_id)]
        return d.sort_values("snapshot_date", ascending=False).reset_index(drop=True)

    def customers_in_category(self, category: str, snapshot=None) -> pd.DataFrame:
        d = self._snap(snapshot)
        return d[d["risk_category"].astype(str).str.lower() == category.lower()] \
            .sort_values(["lapse_probability", "customer_id"], ascending=[False, True]).reset_index(drop=True)

    def sort_by_probability(self, snapshot=None, ascending: bool = False, n: int | None = None,
                            category: str | None = None) -> pd.DataFrame:
        d = self._snap(snapshot)
        if category:
            d = d[d["risk_category"].astype(str).str.lower() == category.lower()]
        d = d.sort_values(["lapse_probability", "customer_id"], ascending=[ascending, True])
        return (d.head(n) if n else d).reset_index(drop=True)

    def urgency_percentile(self, customer_id: int, snapshot=None) -> float | None:
        """Percent rank of the customer's probability within the snapshot (descriptive only)."""
        d = self._snap(snapshot)
        row = d[d["customer_id"] == int(customer_id)]
        if row.empty:
            return None
        p = row["lapse_probability"].iloc[0]
        return round(float((d["lapse_probability"] < p).sum() / len(d) * 100), 1)

    def probability_stats(self, snapshot=None) -> dict:
        s = self._snap(snapshot)["lapse_probability"]
        return {"min": float(s.min()), "median": float(s.median()), "mean": float(s.mean()), "max": float(s.max())}


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Display-friendly copy of a customer frame."""
    out = df.copy()
    if "snapshot_date" in out:
        out["snapshot_date"] = pd.to_datetime(out["snapshot_date"]).dt.strftime("%Y-%m-%d")
    if "risk_category" in out:
        out["risk_category"] = out["risk_category"].astype(str)
    if "lapse_probability" in out:
        out["lapse_probability"] = out["lapse_probability"].round(4)
    return out
